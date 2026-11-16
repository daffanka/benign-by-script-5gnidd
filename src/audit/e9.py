"""E9 — evaluasi tingkat blok atas hasil E8.

Untuk tiap skenario E8 x prosedur (a,b,c,d,f): baris yang ditandai dikelompokkan
per (file capture x SrcAddr x label tercemar x label prediksi).
Skor kelompok = jumlah baris ditandai x fraksi baris kelompok itu yang ditandai.
ATURAN DITETAPKAN SEBELUM MELIHAT HASIL (tidak diubah sesudahnya):
  - "baris kelompok itu" = SEMUA baris data (ditandai atau tidak) yang cocok
    dengan kunci 4-tupel; setiap baris punya label prediksi dari prosedurnya.
    Konsekuensi mekanis: untuk prosedur dengan aturan tanda pred != label
    (a,b,c,d) fraksi = 1 sehingga skor = jumlah baris ditandai; fraksi < 1
    hanya mungkin pada (f).
  - label prediksi (f) = argmax probabilitas OOF global (sama dengan prediksi c).
  - peringkat = competition rank (method="min") pada skor menurun.
  - "blok tersuntik" = kelompok dengan file & SrcAddr & label tercemar sama
    dengan suntikan; bila prediksinya terpecah jadi beberapa kelompok, dipakai
    peringkat TERBAIK (minimum); bila tak ada baris blok yang ditandai,
    peringkat = n_kelompok + 1.
Flag per baris dihitung ulang dengan mekanika e8.py yang identik (cache kontrol
+ e8_scenarios.json dipakai ulang), karena E8 hanya menyimpan agregat.

Pemakaian:
  python e9.py control           # kontrol negatif (versi C tanpa suntikan)
  python e9.py run i0 i1 lane    # skenario [i0, i1)
  python e9.py summary
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common_s as S
import e8

COLS = ["skenario", "tipe", "bs", "prosedur", "n_flag", "n_kelompok",
        "rank_blok", "top1", "top3", "skor_blok", "n_flag_blok", "frac_blok",
        "skor_top1", "grup_top1", "runtime_s"]
PROCS = ["a_perfile_id", "b_perfile_noid", "c_global_noid",
         "d_lintas_capture", "f_confident"]


def group_table(fb, ip, y, pred, flag):
    g = pd.DataFrame({"f": fb, "a": ip, "l": y, "p": pred.astype(str)})
    pop = g.groupby(["f", "a", "l", "p"], sort=False).size()
    fl = g.loc[flag].groupby(["f", "a", "l", "p"], sort=False).size()
    frac = (fl / pop.reindex(fl.index)).astype(float)
    score = (fl * frac).sort_values(ascending=False)
    return score, fl, frac


def group_rank(fb, ip, y, pred, flag, sc, proc, t0, csv_name):
    score, fl, frac = group_table(fb, ip, y, pred, flag)
    n_grp = len(score)
    rank = score.rank(method="min", ascending=False).astype(int)
    fkey = f"{sc['bs']}/{sc['file']}"
    gi = score.index
    mblk = ((gi.get_level_values(0) == fkey)
            & (gi.get_level_values(1) == sc["ip"])
            & (gi.get_level_values(2) == sc["label_baru"]))
    if n_grp and mblk.any():
        rb = int(rank[mblk].min())
        bkey = rank[mblk].idxmin()
        sb, nfb, frb = float(score.loc[bkey]), int(fl.loc[bkey]), \
            float(frac.loc[bkey])
    else:
        rb, sb, nfb, frb = n_grp + 1, 0.0, 0, 0.0
    top1 = "|".join(score.index[0]) if n_grp else "-"
    r = {"skenario": sc["skenario"], "tipe": sc["tipe"], "bs": sc["bs"],
         "prosedur": proc, "n_flag": int(flag.sum()), "n_kelompok": n_grp,
         "rank_blok": rb, "top1": int(rb == 1), "top3": int(rb <= 3),
         "skor_blok": round(sb, 1), "n_flag_blok": nfb,
         "frac_blok": round(frb, 4),
         "skor_top1": round(float(score.iloc[0]), 1) if n_grp else 0.0,
         "grup_top1": top1, "runtime_s": round(time.time() - t0, 1)}
    S.append_csv(csv_name, r, COLS)
    return r


def load_all():
    d, fj, y0 = e8.load_c()
    Xall, X42 = e8.encode_sets(d, fj)
    fb = (d["__bs"] + "/" + d["__file"]).to_numpy()
    ip = d["SrcAddr"].to_numpy().astype(str)
    ctrl = pd.read_parquet(e8.CTRL_PQ)
    npz = np.load(e8.CTRL_NPZ, allow_pickle=True)
    return d, fj, y0, Xall, X42, fb, ip, ctrl, npz


def control():
    t0 = time.time()
    d, fj, y0, Xall, X42, fb, ip, ctrl, npz = load_all()
    proba, classes = npz["proba"], list(npz["classes"])
    sc0 = {"skenario": "kontrol_negatif", "tipe": "kontrol", "bs": "-",
           "file": "-", "ip": "-", "label_baru": "-"}
    preds = {"a_perfile_id": ctrl["pf_id"].to_numpy(),
             "b_perfile_noid": ctrl["pf_noid"].to_numpy(),
             "c_global_noid": ctrl["c_pred"].to_numpy(),
             "d_lintas_capture": ctrl["d_pred"].to_numpy()}
    for proc, pred in preds.items():
        group_rank(fb, ip, y0, pred, pred != y0, sc0, proc, t0,
                   "e9_control.csv")
    flag_f = e8.cl_flags(proba, classes, y0)
    group_rank(fb, ip, y0, preds["c_global_noid"], flag_f, sc0,
               "f_confident", t0, "e9_control.csv")
    S.log(f"E9 kontrol selesai ({time.time()-t0:.0f}s)", tag="e9")


def run(i0, i1, lane):
    csv_name = f"e9_runs_{lane}.csv"
    d, fj, y0, Xall, X42, fb, ip, ctrl, npz = load_all()
    bs = d["__bs"].to_numpy()
    scen = json.load(open(e8.SCEN_JSON, encoding="utf-8"))
    i1_, i2_ = np.flatnonzero(bs == "BS1"), np.flatnonzero(bs == "BS2")
    for sc in scen[i0:i1]:
        t_sc = time.time()
        poison = np.zeros(len(d), bool)
        poison[np.asarray(sc["idx"], int)] = True
        y = y0.copy()
        y[poison] = sc["label_baru"]
        mfile = fb == f"{sc['bs']}/{sc['file']}"
        # (a)/(b): hanya file tersuntik dihitung ulang (identik E8)
        for proc, X, base in [("a_perfile_id", Xall, "pf_id"),
                              ("b_perfile_noid", X42, "pf_noid")]:
            t0 = time.time()
            pred = ctrl[base].to_numpy().astype(object)
            pred[mfile] = e8.oof_file(X.loc[mfile], y[mfile])
            group_rank(fb, ip, y, pred, pred != y, sc, proc, t0, csv_name)
        # (c) + (f)
        t0 = time.time()
        pred_c, proba_c, cls_c = e8.oof_global(X42, y, want_proba=True)
        group_rank(fb, ip, y, pred_c, pred_c != y, sc, "c_global_noid",
                   t0, csv_name)
        t0 = time.time()
        group_rank(fb, ip, y, pred_c, e8.cl_flags(proba_c, cls_c, y), sc,
                   "f_confident", t0, csv_name)
        # (d): identik E8 (sisi tercemar pakai prediksi kontrol)
        t0 = time.time()
        ipois = i1_ if sc["bs"] == "BS1" else i2_
        iclean = i2_ if sc["bs"] == "BS1" else i1_
        pred = np.empty(len(d), dtype=object)
        pred[ipois] = ctrl["d_pred"].to_numpy()[ipois]
        pred[iclean] = e8.fit_cross(X42, y, ipois, iclean)
        group_rank(fb, ip, y, pred, pred != y, sc, "d_lintas_capture",
                   t0, csv_name)
        S.log(f"E9 {lane} {sc['skenario']} ({time.time()-t_sc:.0f}s)",
              tag=f"e9_{lane}")
    S.log(f"E9 {lane} selesai [{i0},{i1})", tag=f"e9_{lane}")


def summary():
    import glob
    from scipy import stats
    parts = []
    for p in sorted(glob.glob(os.path.join(S.RESULTS, "e9_runs_lane*.csv"))):
        parts.append(pd.read_csv(p))
    r = (pd.concat(parts, ignore_index=True)
         .drop_duplicates(["skenario", "prosedur"], keep="last"))
    r.to_csv(os.path.join(S.RESULTS, "e9_runs.csv"), index=False)
    out = {"n_skenario": int(r["skenario"].nunique()), "per_prosedur": {},
           "per_tipe": {}, "wilcoxon_rank_d_vs": {}, "mcnemar_top1_d_vs": {}}
    piv_rank = r.pivot_table(index="skenario", columns="prosedur",
                             values="rank_blok")
    piv_top1 = r.pivot_table(index="skenario", columns="prosedur",
                             values="top1")
    for p in PROCS:
        rp = r.loc[r.prosedur == p]
        out["per_prosedur"][p] = {
            "pct_rank1": round(float(rp["top1"].mean() * 100), 1),
            "pct_top3": round(float(rp["top3"].mean() * 100), 1),
            "mean_rank": round(float(rp["rank_blok"].mean()), 2),
            "median_rank": round(float(rp["rank_blok"].median()), 1),
            "n_absen": int((rp["n_flag_blok"] == 0).sum())}
    for t in r["tipe"].unique():
        out["per_tipe"][t] = {
            p: {"pct_rank1": round(float(r.loc[(r.tipe == t) & (r.prosedur == p),
                                               "top1"].mean() * 100), 1),
                "pct_top3": round(float(r.loc[(r.tipe == t) & (r.prosedur == p),
                                              "top3"].mean() * 100), 1),
                "mean_rank": round(float(r.loc[(r.tipe == t) & (r.prosedur == p),
                                               "rank_blok"].mean()), 2)}
            for p in PROCS}
    for p in PROCS:
        if p == "d_lintas_capture":
            continue
        x, z = piv_rank["d_lintas_capture"], piv_rank[p]
        try:
            w = stats.wilcoxon(x, z)
            out["wilcoxon_rank_d_vs"][p] = {
                "stat": round(float(w.statistic), 1),
                "p_two_sided": float(w.pvalue),
                "mean_diff_rank_d_minus": round(float((x - z).mean()), 2)}
        except ValueError as e:
            out["wilcoxon_rank_d_vs"][p] = {"error": str(e)}
        b = int(((piv_top1["d_lintas_capture"] == 1) & (piv_top1[p] == 0)).sum())
        c = int(((piv_top1["d_lintas_capture"] == 0) & (piv_top1[p] == 1)).sum())
        pv = 1.0 if b + c == 0 else float(
            stats.binomtest(min(b, c), b + c, 0.5).pvalue)
        out["mcnemar_top1_d_vs"][p] = {"d_saja": b, "lain_saja": c,
                                       "p_exact_two_sided": round(pv, 6)}
    S.save_json("e9_summary.json", out)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "control":
        control()
    elif cmd == "run":
        run(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif cmd == "summary":
        summary()
