"""E3 — set fitur ala paper dataset: 25 dan 10 fitur teratas menurut ANOVA
F-score (f_classif) pada data Combined (versi A, label asli), lalu ulangi
protokol (i) lit acak 80/20 dan (iii) BS1->BS2 dengan set fitur itu.

Model: HGB seed 0-2 (lihat penyimpangan). Keluaran: results/e3_top_features.json,
e3_runs.csv, e3_configs.jsonl.
"""
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.feature_selection import f_classif
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common_s as S

CSV = "e3_runs.csv"
COLS = ["set_fitur", "protokol", "model", "seed", "n_train", "n_test",
        "acc", "f1_macro", "acc_korr", "f1_korr", "fit_s"]


def main():
    t_all = time.time()
    d, fj = S.load_full()
    feats_all = fj["feats_all"]
    classes = fj["classes"]
    y = d["__y"].to_numpy().astype(str)
    yc = d["__ycorr"].to_numpy().astype(str)
    bs = d["__bs"].to_numpy()

    X = S.encode_features(d, feats_all)
    keep = [c for c in X.columns if X[c].nunique(dropna=True) >= 2]
    Xi = pd.DataFrame(SimpleImputer(strategy="median").fit_transform(X[keep]),
                      columns=keep)
    F, _ = f_classif(Xi, y)
    F = np.nan_to_num(F, nan=0.0)
    order = np.argsort(-F)
    rank = {keep[i]: int(r + 1) for r, i in enumerate(order)}
    top25 = [keep[i] for i in order[:25]]
    top10 = [keep[i] for i in order[:10]]
    id_in = {c: rank.get(c) for c in fj["id_cols"]}
    S.save_json("e3_top_features.json", {
        "metode": "ANOVA F-score (sklearn f_classif) pada seluruh data versi A, "
                  "label asli multikelas; NaN diimputasi median; kolom konstan "
                  "dibuang; F NaN -> 0",
        "n_fitur_dinilai": len(keep),
        "top25": [{"fitur": c, "rank": rank[c], "F": round(float(F[keep.index(c)]), 1),
                   "identitas": c in fj["id_cols"]} for c in top25],
        "top10": top10,
        "rank_kolom_identitas": id_in,
        "seq_masuk_top25": "Seq" in top25, "offset_masuk_top25": "Offset" in top25,
        "seq_masuk_top10": "Seq" in top10, "offset_masuk_top10": "Offset" in top10})
    S.log(f"E3 ANOVA: top10={top10} | rank ID={id_in}", tag="e3")

    i_bs1 = np.flatnonzero(bs == "BS1")
    i_bs2 = np.flatnonzero(bs == "BS2")
    for fs_name, feats in [("top25", top25), ("top10", top10)]:
        Xf = X[feats]
        for proto in ["lit_acak_8020", "bs1_ke_bs2"]:
            for seed in range(3):
                t0 = time.time()
                if proto == "lit_acak_8020":
                    tr, te = train_test_split(np.arange(len(d)), test_size=0.2,
                                              random_state=seed, stratify=y)
                else:
                    tr, te = i_bs1, i_bs2
                cols = [c for c in feats
                        if Xf.iloc[tr][c].nunique(dropna=True) >= 2]
                m = S.make_model("HGB", seed)
                m.fit(Xf.iloc[tr][cols], y[tr])
                pred = m.predict(Xf.iloc[te][cols])
                row = {"set_fitur": fs_name, "protokol": proto, "model": "HGB",
                       "seed": seed, "n_train": len(tr), "n_test": len(te),
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
                S.append_jsonl("e3_configs.jsonl", {
                    **row, "fitur": feats, "model_desc": S.MODEL_DESC["HGB"],
                    "versi": "A (label asli)",
                    "catatan": "acc/f1 vs label asli; acc_korr/f1_korr vs "
                               "label terkoreksi"})
                S.log(f"E3 {fs_name} {proto} s{seed} f1={row['f1_macro']} "
                      f"f1korr={row['f1_korr']}", tag="e3")
    S.log(f"E3 selesai ({(time.time()-t_all)/60:.1f} menit)", tag="e3")


if __name__ == "__main__":
    main()
