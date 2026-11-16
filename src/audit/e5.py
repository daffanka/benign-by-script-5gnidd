"""E5 — prosedur audit memakai LABEL ASLI saja, dinilai terhadap 281.529 baris
salah-label (kebenaran = kolom __mis dari E1).

(a) ketidakcocokan OOF dalam satu file capture, DENGAN kolom identitas
(b) sama, TANPA kolom identitas
(c) ketidakcocokan OOF pada seluruh data, tanpa kolom identitas
    (+ varian keyakinan >= 0,95)
(d) lintas-capture: latih di BS2 -> tandai Benign BS1 yang diprediksi serangan,
    dan sebaliknya
(e) pencocokan record lintas-file berlabel beda (kunci 8 kolom)

Model prosedur (a)-(d): HGB seed 0 (setelan C1-C5). Keluaran:
results/e5_runs.csv + e5_configs.jsonl.
"""
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, StratifiedKFold

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common_s as S

CSV = "e5_runs.csv"
COLS = ["prosedur", "deskripsi", "n_flag", "n_benar", "precision", "recall",
        "runtime_s"]


def report(proc, desc, flag, mis, t0, extra=None):
    n_flag = int(flag.sum())
    n_tp = int((flag & mis).sum())
    row = {"prosedur": proc, "deskripsi": desc, "n_flag": n_flag,
           "n_benar": n_tp,
           "precision": round(n_tp / n_flag, 4) if n_flag else "",
           "recall": round(n_tp / int(mis.sum()), 4),
           "runtime_s": round(time.time() - t0, 1)}
    S.append_csv(CSV, row, COLS)
    S.append_jsonl("e5_configs.jsonl", {
        "prosedur": proc, "deskripsi": desc,
        "model": S.MODEL_DESC["HGB"] + ", seed 0",
        "label": "asli (tanpa koreksi)",
        "kebenaran": "281529 baris aturan C4", **(extra or {})})
    S.log(f"E5 {proc}: flag={n_flag} prec={row['precision']} "
          f"rec={row['recall']}", tag="e5")


def oof_per_file(d, X, mis, with_id_tag, desc):
    t0 = time.time()
    y = d["__y"].to_numpy().astype(str)
    flag = np.zeros(len(d), bool)
    for (bs, f), idx in d.groupby(["__bs", "__file"], sort=True).indices.items():
        yl = y[idx]
        Xl = X.iloc[idx]
        cols = [c for c in Xl.columns if Xl[c].nunique(dropna=True) >= 2]
        Xl = Xl[cols]
        vc = pd.Series(yl).value_counts()
        if (vc < 5).any():
            splitter = KFold(5, shuffle=True, random_state=0).split(Xl)
        else:
            splitter = StratifiedKFold(5, shuffle=True,
                                       random_state=0).split(Xl, yl)
        pred = np.empty(len(idx), dtype=object)
        for tr, te in splitter:
            m = S.make_model("HGB", 0)
            m.fit(Xl.iloc[tr], yl[tr])
            pred[te] = m.predict(Xl.iloc[te])
        flag[idx] = pred != yl
        S.log(f"E5 {with_id_tag} {bs}/{f}: n={len(idx)} "
              f"flag={int((pred != yl).sum())}", tag="e5")
    report(with_id_tag, desc, flag, mis, t0,
           {"fold": "5-fold per file (StratifiedKFold; KFold bila ada kelas <5)"})


def main():
    t_all = time.time()
    d, fj = S.load_full()
    feats_all, feats42 = fj["feats_all"], fj["feats42"]
    y = d["__y"].to_numpy().astype(str)
    mis = d["__mis"].to_numpy()
    S.log(f"E5 mulai: n={len(d)} truth={int(mis.sum())}", tag="e5")
    Xall = S.encode_features(d, feats_all)
    X42 = Xall[feats42]

    # (a) + (b) OOF per file
    oof_per_file(d, Xall, mis, "a_perfile_id",
                 "OOF 5-fold dalam tiap file capture, DENGAN kolom identitas")
    oof_per_file(d, X42, mis, "b_perfile_noid",
                 "OOF 5-fold dalam tiap file capture, tanpa kolom identitas")

    # (c) OOF global tanpa identitas
    t0 = time.time()
    Xg = X42[[c for c in X42.columns if X42[c].nunique(dropna=True) >= 2]]
    skf = StratifiedKFold(5, shuffle=True, random_state=0)
    pred = np.empty(len(y), dtype=object)
    conf = np.zeros(len(y))
    for fi, (tr, te) in enumerate(skf.split(Xg, y)):
        m = S.make_model("HGB", 0)
        m.fit(Xg.iloc[tr], y[tr])
        p = m.predict_proba(Xg.iloc[te])
        pred[te] = m.classes_[p.argmax(1)]
        conf[te] = p.max(1)
        S.log(f"E5 c fold {fi+1}/5", tag="e5")
    flag_c = pred != y
    report("c_global_noid", "OOF 5-fold seluruh data, tanpa kolom identitas",
           flag_c, mis, t0, {"fold": "StratifiedKFold(5, shuffle, seed 0)"})
    report("c_global_noid_conf95", "sama, hanya ketidakcocokan keyakinan >= 0,95",
           flag_c & (conf >= 0.95), mis, t0)

    # (d) lintas-capture
    bs = d["__bs"].to_numpy()
    flags_d = {}
    for tr_bs, te_bs in [("BS2", "BS1"), ("BS1", "BS2")]:
        t0 = time.time()
        itr = np.flatnonzero(bs == tr_bs)
        ite = np.flatnonzero(bs == te_bs)
        cols = [c for c in X42.columns
                if X42.iloc[itr][c].nunique(dropna=True) >= 2]
        m = S.make_model("HGB", 0)
        m.fit(X42.iloc[itr][cols], y[itr])
        p = m.predict(X42.iloc[ite][cols])
        flag = np.zeros(len(d), bool)
        flag[ite] = (y[ite] == "Benign") & (p != "Benign")
        flags_d[te_bs] = flag
        report(f"d_latih{tr_bs}_tandai{te_bs}",
               f"latih {tr_bs} (label asli, 42 non-ID), tandai Benign {te_bs} "
               f"yang diprediksi serangan", flag, mis, t0)
    report("d_gabungan", "gabungan dua arah prosedur d",
           flags_d["BS1"] | flags_d["BS2"], mis, time.time())

    # (e) pencocokan kunci lintas-file berlabel beda
    t0 = time.time()
    k = d["__key"].to_numpy()
    g = pd.DataFrame({"k": k, "f": (d["__bs"] + "/" + d["__file"]).to_numpy(),
                      "y": y})
    agg = g.groupby("k").agg(nf=("f", "nunique"), ny=("y", "nunique"))
    bad_keys = agg.index[(agg["nf"] > 1) & (agg["ny"] > 1)]
    flag_e = np.isin(k, bad_keys)
    report("e_kunci8", "baris dengan kunci 8 kolom yang muncul di >1 file "
           "dengan >1 label (kedua sisi ditandai)", flag_e, mis, t0,
           {"kunci": fj["key"]})
    # rincian sisi
    fb1 = flag_e & (bs == "BS1") & (y == "Benign")
    S.append_jsonl("e5_configs.jsonl", {
        "prosedur": "e_kunci8_rincian",
        "n_flag_bs1_benign": int(fb1.sum()),
        "n_flag_bs1": int((flag_e & (bs == "BS1")).sum()),
        "n_flag_bs2": int((flag_e & (bs == "BS2")).sum()),
        "catatan": "sisi BS2 (kembar UDPFlood) ikut tertandai; bila auditor "
                   "hanya menandai sisi Benign, precision = "
                   f"{round(int((fb1 & mis).sum()) / max(int(fb1.sum()),1), 4)}"})
    S.log(f"E5 selesai ({(time.time()-t_all)/60:.1f} menit)", tag="e5")


if __name__ == "__main__":
    main()
