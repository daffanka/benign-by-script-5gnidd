"""E4 — dosis shortcut pada protokol literatur (versi A, semua kolom, acak 80/20):
buang Seq saja, Offset saja, keduanya, dan semua kolom identitas; plus
permutation importance Seq dan Offset per kelas.

Model: HGB seed 0-2. Keluaran: results/e4_runs.csv, e4_perm.json, e4_configs.jsonl.
"""
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.model_selection import train_test_split

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common_s as S

CSV = "e4_runs.csv"
COLS = ["set_fitur", "seed", "n_feats", "acc", "f1_macro", "acc_korr",
        "f1_korr", "fit_s"]


def main():
    t_all = time.time()
    d, fj = S.load_full()
    feats_all = fj["feats_all"]
    id_cols = fj["id_cols"]
    classes = fj["classes"]
    y = d["__y"].to_numpy().astype(str)
    yc = d["__ycorr"].to_numpy().astype(str)
    X = S.encode_features(d, feats_all)

    sets = {
        "semua": feats_all,
        "minus_Seq": [c for c in feats_all if c != "Seq"],
        "minus_Offset": [c for c in feats_all if c != "Offset"],
        "minus_Seq_Offset": [c for c in feats_all if c not in ("Seq", "Offset")],
        "minus_semua_identitas": [c for c in feats_all if c not in id_cols],
    }
    for fs_name, feats in sets.items():
        for seed in range(3):
            t0 = time.time()
            tr, te = train_test_split(np.arange(len(d)), test_size=0.2,
                                      random_state=seed, stratify=y)
            cols = [c for c in feats if X.iloc[tr][c].nunique(dropna=True) >= 2]
            m = S.make_model("HGB", seed)
            m.fit(X.iloc[tr][cols], y[tr])
            pred = m.predict(X.iloc[te][cols])
            row = {"set_fitur": fs_name, "seed": seed, "n_feats": len(cols),
                   "acc": round(float(accuracy_score(y[te], pred)), 6),
                   "f1_macro": round(float(f1_score(
                       y[te], pred, average="macro", labels=classes,
                       zero_division=0)), 6),
                   "acc_korr": round(float(accuracy_score(yc[te], pred)), 6),
                   "f1_korr": round(float(f1_score(
                       yc[te], pred, average="macro", labels=classes,
                       zero_division=0)), 6),
                   "fit_s": round(time.time() - t0, 1)}
            S.append_csv(CSV, row, COLS)
            S.append_jsonl("e4_configs.jsonl", {
                **row, "protokol": "lit acak 80/20 versi A",
                "model_desc": S.MODEL_DESC["HGB"]})
            S.log(f"E4 {fs_name} s{seed} f1={row['f1_macro']} "
                  f"f1korr={row['f1_korr']}", tag="e4")

    # permutation importance Seq & Offset per kelas (model 'semua', seed 0)
    t0 = time.time()
    tr, te = train_test_split(np.arange(len(d)), test_size=0.2,
                              random_state=0, stratify=y)
    cols = [c for c in feats_all if X.iloc[tr][c].nunique(dropna=True) >= 2]
    m = S.make_model("HGB", 0)
    m.fit(X.iloc[tr][cols], y[tr])
    Xte = X.iloc[te][cols].reset_index(drop=True)
    yte = y[te]
    base_pred = m.predict(Xte)
    base_rec = dict(zip(classes, recall_score(yte, base_pred, average=None,
                                              labels=classes, zero_division=0)))
    base_acc = float(accuracy_score(yte, base_pred))
    rng = np.random.default_rng(0)
    out = {"baseline_acc": round(base_acc, 6),
           "baseline_recall": {c: round(float(v), 6) for c, v in base_rec.items()},
           "n_repeats": 5, "per_kolom": {}}
    for col in ["Seq", "Offset"]:
        drops_rec = {c: [] for c in classes}
        drops_acc = []
        for rep in range(5):
            Xp = Xte.copy()
            Xp[col] = rng.permutation(Xp[col].to_numpy())
            pp = m.predict(Xp)
            drops_acc.append(base_acc - float(accuracy_score(yte, pp)))
            rec = recall_score(yte, pp, average=None, labels=classes,
                               zero_division=0)
            for c, r in zip(classes, rec):
                drops_rec[c].append(base_rec[c] - float(r))
        out["per_kolom"][col] = {
            "drop_acc_mean": round(float(np.mean(drops_acc)), 6),
            "drop_recall_per_kelas": {c: round(float(np.mean(v)), 6)
                                      for c, v in drops_rec.items()}}
        S.log(f"E4 perm {col}: drop_acc={out['per_kolom'][col]['drop_acc_mean']}",
              tag="e4")
    out["runtime_s"] = round(time.time() - t0, 1)
    S.save_json("e4_perm.json", out)
    S.log(f"E4 selesai ({(time.time()-t_all)/60:.1f} menit)", tag="e4")


if __name__ == "__main__":
    main()
