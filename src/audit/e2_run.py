"""E2 — uji ulang pada SELURUH data, 6 model x 4 protokol x 3 versi.

Protokol: lit  = semua kolom (termasuk Seq/Offset) + acak 80/20
          noid = tanpa kolom identitas + acak 80/20
          b12  = BS1->BS2 (tanpa identitas)
          b21  = BS2->BS1 (tanpa identitas)
Versi A juga dinilai terhadap label terkoreksi.
Biner (TPR/FPR) diturunkan dari prediksi multikelas (pred != Benign).

Jalur paralel: python e2_run.py --models HGB,RF,KNN --lane lane1
Angka mentah per run -> results/e2_runs_<lane>.csv
Config per run       -> results/e2_configs_<lane>.jsonl
"""
import argparse
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.model_selection import train_test_split

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common_s as S

warnings.filterwarnings("ignore", category=UserWarning)

PROTOCOLS = ["noid", "b12", "b21", "lit"]
# kebijakan seed (penyimpangan dari "10 seed semua": lihat REPORT E7)
SEEDS_PLAN = {
    "lit":  {"HGB": 3, "RF": 3, "DT": 3, "LR": 3, "MLP": 3, "KNN": 3},
    "noid": {"HGB": 10, "RF": 10, "DT": 10, "LR": 3, "MLP": 3, "KNN": 3},
    "b12":  {"HGB": 3, "RF": 3, "DT": 3, "LR": 1, "MLP": 3, "KNN": 1},
    "b21":  {"HGB": 3, "RF": 3, "DT": 3, "LR": 1, "MLP": 3, "KNN": 1},
}
KNN_TRAIN_CAP = 200_000


def run_one(lane, X, feats, yv, ycorr_v, tr, te, version, proto, model, seed,
            classes, csv_cols):
    t0 = time.time()
    ytr, yte = yv[tr], yv[te]
    tr_fit = tr
    knn_sub = ""
    if model == "KNN" and len(tr) > KNN_TRAIN_CAP:
        sub = S.stratified_cap(ytr, KNN_TRAIN_CAP, seed)
        tr_fit = tr[np.sort(sub)]
        knn_sub = len(tr_fit)
    cols = list(X.columns)
    if model == "HGB":
        Xtr_probe = X.iloc[tr_fit]
        cols = [c for c in cols if Xtr_probe[c].nunique(dropna=True) >= 2]
    m = S.make_model(model, seed)
    m.fit(X.iloc[tr_fit][cols], yv[tr_fit])
    pred = m.predict(X.iloc[te][cols])
    fit_s = round(time.time() - t0, 1)

    row = {"run_id": f"{version}|{proto}|{model}|s{seed}", "lane": lane,
           "versi": version, "protokol": proto, "model": model, "seed": seed,
           "n_train": len(tr_fit), "n_test": len(te), "n_feats": len(cols),
           "fit_s": fit_s}
    pb = (pred != "Benign")
    for tag, yref in ([("", yte)] if version != "A"
                      else [("", yte), ("_korr", ycorr_v[te])]):
        row[f"acc{tag}"] = round(float(accuracy_score(yref, pred)), 6)
        row[f"f1_macro{tag}"] = round(float(f1_score(
            yref, pred, average="macro", labels=classes, zero_division=0)), 6)
        yb = (yref != "Benign")
        row[f"tpr{tag}"] = round(float(pb[yb].mean()), 6) if yb.any() else ""
        row[f"fpr{tag}"] = round(float(pb[~yb].mean()), 6) if (~yb).any() else ""
        rec = recall_score(yref, pred, average=None, labels=classes,
                           zero_division=0)
        for c, r in zip(classes, rec):
            row[f"rec{tag}_{c}"] = round(float(r), 6)
    S.append_csv(f"e2_runs_{lane}.csv", row, csv_cols)
    S.append_jsonl(f"e2_configs_{lane}.jsonl", {
        "run_id": row["run_id"], "lane": lane, "versi": version,
        "protokol": proto, "model": model, "model_desc": S.MODEL_DESC[model],
        "seed": seed, "fitur": "semua kolom Combined" if proto == "lit"
        else "42 non-identitas", "n_feats": len(cols),
        "split": "acak 80/20 stratified" if proto in ("lit", "noid")
        else {"b12": "latih BS1, uji BS2", "b21": "latih BS2, uji BS1"}[proto],
        "n_train": int(len(tr_fit)), "n_test": int(len(te)),
        "knn_train_subsample": knn_sub, "biner": "diturunkan dari multikelas",
        "fit_s": fit_s})
    S.log(f"E2 {row['run_id']} f1={row['f1_macro']} acc={row['acc']} "
          f"({fit_s}s)", tag=f"e2_{lane}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--lane", default="lane")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--max-hours", type=float, default=3.4)
    a = ap.parse_args()
    models = a.models.split(",")
    t_start = time.time()

    d, fj = S.load_full()
    feats_all, feats42 = fj["feats_all"], fj["feats42"]
    classes = fj["classes"]
    if a.smoke:
        idx = np.sort(S.stratified_cap(d["__y"].to_numpy(), 40_000, 0))
        d = d.iloc[idx].reset_index(drop=True)
    ycorr_full = d["__ycorr"].to_numpy().astype(str)

    csv_cols = (["run_id", "lane", "versi", "protokol", "model", "seed",
                 "n_train", "n_test", "n_feats", "fit_s"]
                + [f"{m}{t}" for t in ("", "_korr")
                   for m in ["acc", "f1_macro", "tpr", "fpr"]
                   + [f"rec_{c}" for c in classes]])
    # urutkan: acc,f1,tpr,fpr,rec... lalu versi _korr
    S.log(f"E2 lane={a.lane} models={models} smoke={a.smoke}", tag=f"e2_{a.lane}")

    for version in ["A", "B", "C"]:
        mask, y = S.version_arrays(d, version)
        dv = d.loc[mask]
        yv = y[mask]
        ycorr_v = ycorr_full[mask]
        bs = dv["__bs"].to_numpy()
        t0 = time.time()
        Xall = S.encode_features(dv, feats_all)
        S.log(f"E2 {a.lane} versi {version}: n={len(dv)} encode "
              f"{time.time()-t0:.0f}s", tag=f"e2_{a.lane}")
        i_bs1 = np.flatnonzero(bs == "BS1")
        i_bs2 = np.flatnonzero(bs == "BS2")
        for proto in PROTOCOLS:
            feats = feats_all if proto == "lit" else feats42
            X = Xall[feats]
            for model in models:
                nseeds = 1 if a.smoke else SEEDS_PLAN[proto][model]
                for seed in range(nseeds):
                    if time.time() - t_start > a.max_hours * 3600:
                        S.log(f"E2 {a.lane} STOP batas waktu; run tersisa "
                              f"dipotong mulai {version}|{proto}|{model}|s{seed}",
                              tag=f"e2_{a.lane}")
                        return
                    if proto in ("lit", "noid"):
                        tr, te = train_test_split(
                            np.arange(len(dv)), test_size=0.2,
                            random_state=seed, stratify=yv)
                    elif proto == "b12":
                        tr, te = i_bs1, i_bs2
                    else:
                        tr, te = i_bs2, i_bs1
                    try:
                        run_one(a.lane, X, feats, yv, ycorr_v, tr, te, version,
                                proto, model, seed, classes, csv_cols)
                    except Exception as e:  # noqa: BLE001
                        S.log(f"E2 GAGAL {version}|{proto}|{model}|s{seed}: "
                              f"{type(e).__name__}: {e}", tag=f"e2_{a.lane}")
    S.log(f"E2 lane={a.lane} selesai ({(time.time()-t_start)/60:.1f} menit)",
          tag=f"e2_{a.lane}")


if __name__ == "__main__":
    main()
