"""E8 — uji umum prosedur audit dengan salah-label berblok SUNTIKAN.

Data: versi C (925.573 baris, bersih). Skenario suntikan (satu per run):
  - atk2benign_full   : semua flow kelas serangan dari satu IP penyerang
                        (modal) di file capture kelas itu -> Benign (8 kelas x 2 BS)
  - atk2benign_early50: hanya 50% flow paling awal menurut StartTime
  - benign2atk        : blok Benign >= 1000 flow dari satu SrcAddr di satu file
                        -> kelas serangan file itu (4 per BS)
Prosedur (semua hanya melihat label tercemar; HGB max_iter=50 seragam):
  a) OOF 5-fold dalam file capture, DENGAN kolom identitas
  b) sama, tanpa identitas
  c) OOF 3-fold seluruh data, tanpa identitas
  d) lintas-capture: latih di BS lain, tandai label != prediksi (dua arah)
  f) confident learning (aturan confident-joint sederhana) pada probabilitas (c)
  g) auditor study_h2_auditors: DILEWATI (terkunci endpoint H2 domain teks)

Pemakaian:
  python e8.py prep              # cache prediksi kontrol + daftar skenario + baris kontrol
  python e8.py run i0 i1 lane    # jalankan skenario [i0, i1)
  python e8.py summary           # agregat + Wilcoxon
"""
import json
import os
import re
import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import KFold, StratifiedKFold

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common_s as S

CTRL_PQ = os.path.join(S.CACHE, "e8_ctrl.parquet")
CTRL_NPZ = os.path.join(S.CACHE, "e8_ctrl.npz")
SCEN_JSON = os.path.join(S.RESULTS, "e8_scenarios.json")
CSV = "e8_runs.csv"
COLS = ["skenario", "tipe", "bs", "file", "kelas", "ip", "n_poison",
        "prosedur", "n_flag", "n_tp", "precision", "recall", "f1", "runtime_s"]


def hgb(seed=0):
    return HistGradientBoostingClassifier(
        max_iter=50, learning_rate=0.1, max_bins=255,
        early_stopping=False, random_state=seed, l2_regularization=0.1)


def parse_mmss(s):
    m = re.match(r"^\s*(\d+):(\d+(?:\.\d+)?)\s*$", str(s))
    return float(m.group(1)) * 60 + float(m.group(2)) if m else np.nan


def load_c():
    d, fj = S.load_full()
    d = d.loc[d["__keepC"].to_numpy()].reset_index(drop=True)
    y0 = d["__y"].to_numpy().astype(str)
    return d, fj, y0


def encode_sets(d, fj):
    Xall = S.encode_features(d, fj["feats_all"])
    return Xall, Xall[fj["feats42"]]


def oof_file(Xf, yf):
    """Prediksi OOF 5-fold di dalam satu file (StratifiedKFold; KFold bila ada
    kelas < 5)."""
    cols = [c for c in Xf.columns if Xf[c].nunique(dropna=True) >= 2]
    Xf = Xf[cols]
    vc = pd.Series(yf).value_counts()
    if (vc < 5).any() or len(vc) < 2:
        if len(vc) < 2:
            return np.full(len(yf), yf[0], dtype=object)
        splits = KFold(5, shuffle=True, random_state=0).split(Xf)
    else:
        splits = StratifiedKFold(5, shuffle=True, random_state=0).split(Xf, yf)
    pred = np.empty(len(yf), dtype=object)
    for tr, te in splits:
        m = hgb()
        m.fit(Xf.iloc[tr], yf[tr])
        pred[te] = m.predict(Xf.iloc[te])
    return pred


def oof_global(X42, y, want_proba):
    """OOF 3-fold seluruh data (penyimpangan dari 5-fold demi anggaran)."""
    cols = [c for c in X42.columns if X42[c].nunique(dropna=True) >= 2]
    Xg = X42[cols]
    pred = np.empty(len(y), dtype=object)
    proba = None
    classes = None
    for tr, te in StratifiedKFold(3, shuffle=True, random_state=0).split(Xg, y):
        m = hgb()
        m.fit(Xg.iloc[tr], y[tr])
        if want_proba:
            p = m.predict_proba(Xg.iloc[te])
            if proba is None:
                classes = list(m.classes_)
                proba = np.zeros((len(y), len(classes)), np.float32)
            # samakan urutan kelas antar fold
            for j, c in enumerate(m.classes_):
                proba[te, classes.index(c)] = p[:, j]
            pred[te] = np.asarray(m.classes_)[p.argmax(1)]
        else:
            pred[te] = m.predict(Xg.iloc[te])
    return pred, proba, classes


def cl_flags(proba, classes, y):
    """Aturan confident-joint sederhana (cleanlab tidak terpasang):
    t_k = rata-rata p(k) pada baris berlabel k; baris ditandai bila ada kelas k
    dengan p_ik >= t_k dan argmax p pada kelas-kelas confident itu != label."""
    classes = np.asarray(classes)
    t = np.array([proba[y == c, j].mean() if (y == c).any() else 1.1
                  for j, c in enumerate(classes)], np.float32)
    M = proba >= t[None, :]
    masked = np.where(M, proba, -1.0)
    j = masked.argmax(1)
    return M.any(1) & (classes[j] != y)


def fit_cross(X42, y, i_tr, i_te):
    cols = [c for c in X42.columns
            if X42.iloc[i_tr][c].nunique(dropna=True) >= 2]
    m = hgb()
    m.fit(X42.iloc[i_tr][cols], y[i_tr])
    return m.predict(X42.iloc[i_te][cols])


def build_scenarios(d, y0):
    bs = d["__bs"].to_numpy()
    fl = d["__file"].to_numpy()
    ip = d["SrcAddr"].to_numpy().astype(str)
    tsec = d["StartTime"].map(parse_mmss).to_numpy()
    classes = sorted(set(y0))
    atk = [c for c in classes if c != "Benign"]
    scen = []
    for b in ["BS1", "BS2"]:
        for cls in atk:
            m = (bs == b) & (y0 == cls)
            if not m.any():
                continue
            f = pd.Series(fl[m]).mode().iloc[0]
            mm = m & (fl == f)
            top_ip = pd.Series(ip[mm]).value_counts().index[0]
            cand = np.flatnonzero(mm & (ip == top_ip))
            scen.append({"tipe": "atk2benign_full", "bs": b, "file": f,
                         "kelas": cls, "ip": top_ip, "label_baru": "Benign",
                         "idx": cand.tolist()})
            order = cand[np.argsort(tsec[cand])]
            scen.append({"tipe": "atk2benign_early50", "bs": b, "file": f,
                         "kelas": cls, "ip": top_ip, "label_baru": "Benign",
                         "idx": order[:len(order) // 2].tolist()})
    for b in ["BS1", "BS2"]:
        m = (bs == b) & (y0 == "Benign")
        g = (pd.DataFrame({"f": fl[m], "ip": ip[m], "i": np.flatnonzero(m)})
             .groupby(["f", "ip"]))
        sizes = g.size().sort_values(ascending=False)
        sizes = sizes[sizes >= 1000]
        chosen, used_files = [], set()
        for (f, a), n in sizes.items():  # file berbeda dulu, lalu sisanya
            if f not in used_files:
                chosen.append((f, a))
                used_files.add(f)
            if len(chosen) == 4:
                break
        for (f, a), n in sizes.items():
            if len(chosen) == 4:
                break
            if (f, a) not in chosen:
                chosen.append((f, a))
        for f, a in chosen[:4]:
            idx = g.get_group((f, a))["i"].to_numpy()
            atk_cls = pd.Series(y0[(bs == b) & (fl == f)
                                   & (y0 != "Benign")]).mode().iloc[0]
            scen.append({"tipe": "benign2atk", "bs": b, "file": f,
                         "kelas": "Benign", "ip": a, "label_baru": atk_cls,
                         "idx": idx.tolist()})
    for i, sc in enumerate(scen):
        sc["skenario"] = f"s{i:02d}_{sc['tipe']}_{sc['bs']}_{sc['kelas']}"
        sc["n_poison"] = len(sc["idx"])
    return scen


def row(sc, proc, flag, poison_mask, t0, csv_name=CSV):
    n_flag = int(flag.sum())
    tp = int((flag & poison_mask).sum())
    npo = int(poison_mask.sum())
    prec = tp / n_flag if n_flag else 0.0
    rec = tp / npo if npo else ""
    f1 = (2 * prec * rec / (prec + rec)) if (n_flag and npo and (prec + rec) > 0) \
        else (0.0 if npo else "")
    r = {"skenario": sc["skenario"], "tipe": sc["tipe"], "bs": sc["bs"],
         "file": sc["file"], "kelas": sc["kelas"], "ip": sc["ip"],
         "n_poison": npo, "prosedur": proc, "n_flag": n_flag, "n_tp": tp,
         "precision": round(prec, 4), "recall": round(rec, 4) if rec != "" else "",
         "f1": round(f1, 4) if f1 != "" else "",
         "runtime_s": round(time.time() - t0, 1)}
    S.append_csv(csv_name, r, COLS)
    return r


def prep():
    t0 = time.time()
    d, fj, y0 = load_c()
    Xall, X42 = encode_sets(d, fj)
    fb = (d["__bs"] + "/" + d["__file"]).to_numpy()
    S.log(f"E8 prep: n={len(d)}", tag="e8")

    scen = build_scenarios(d, y0)
    with open(SCEN_JSON, "w", encoding="utf-8") as f:
        json.dump(scen, f, indent=1)
    S.log(f"E8 prep: {len(scen)} skenario "
          f"({sum(s['tipe']=='atk2benign_full' for s in scen)} full, "
          f"{sum(s['tipe']=='atk2benign_early50' for s in scen)} early50, "
          f"{sum(s['tipe']=='benign2atk' for s in scen)} benign2atk)", tag="e8")

    ctrl = pd.DataFrame(index=range(len(d)))
    for name, X in [("pf_id", Xall), ("pf_noid", X42)]:
        pred = np.empty(len(d), dtype=object)
        for f in np.unique(fb):
            m = fb == f
            pred[m] = oof_file(X.loc[m], y0[m])
            S.log(f"E8 prep {name} {f}: flag={int((pred[m]!=y0[m]).sum())}",
                  tag="e8")
        ctrl[name] = pred.astype(str)
    cpred, cproba, cclasses = oof_global(X42, y0, want_proba=True)
    ctrl["c_pred"] = cpred.astype(str)
    np.savez_compressed(CTRL_NPZ, proba=cproba, classes=np.array(cclasses))
    S.log("E8 prep: OOF global kontrol selesai", tag="e8")
    bs = d["__bs"].to_numpy()
    i1, i2 = np.flatnonzero(bs == "BS1"), np.flatnonzero(bs == "BS2")
    dpred = np.empty(len(d), dtype=object)
    dpred[i1] = fit_cross(X42, y0, i2, i1)   # dilatih BS2, prediksi BS1
    dpred[i2] = fit_cross(X42, y0, i1, i2)   # dilatih BS1, prediksi BS2
    ctrl["d_pred"] = dpred.astype(str)
    ctrl.to_parquet(CTRL_PQ, index=False)

    # baris kontrol negatif (tanpa suntikan): hanya jumlah baris tertandai
    sc0 = {"skenario": "kontrol_negatif", "tipe": "kontrol", "bs": "-",
           "file": "-", "kelas": "-", "ip": "-"}
    nopoison = np.zeros(len(d), bool)
    for proc, flag in [
            ("a_perfile_id", ctrl["pf_id"].to_numpy() != y0),
            ("b_perfile_noid", ctrl["pf_noid"].to_numpy() != y0),
            ("c_global_noid", ctrl["c_pred"].to_numpy() != y0),
            ("d_lintas_capture", ctrl["d_pred"].to_numpy() != y0),
            ("f_confident", cl_flags(cproba, cclasses, y0))]:
        row(sc0, proc, flag, nopoison, t0)
    S.log(f"E8 prep selesai ({(time.time()-t0)/60:.1f} menit)", tag="e8")


def run(i0, i1, lane):
    csv_name = f"e8_runs_{lane}.csv"
    d, fj, y0 = load_c()
    Xall, X42 = encode_sets(d, fj)
    fb = (d["__bs"] + "/" + d["__file"]).to_numpy()
    bs = d["__bs"].to_numpy()
    ctrl = pd.read_parquet(CTRL_PQ)
    npz = np.load(CTRL_NPZ, allow_pickle=True)
    scen = json.load(open(SCEN_JSON, encoding="utf-8"))
    i1_, i2_ = np.flatnonzero(bs == "BS1"), np.flatnonzero(bs == "BS2")
    for sc in scen[i0:i1]:
        t_sc = time.time()
        poison = np.zeros(len(d), bool)
        poison[np.asarray(sc["idx"], int)] = True
        y = y0.copy()
        y[poison] = sc["label_baru"]
        fkey = f"{sc['bs']}/{sc['file']}"
        mfile = fb == fkey
        # (a)/(b): hanya file tersuntik yang dihitung ulang
        for proc, X, base in [("a_perfile_id", Xall, "pf_id"),
                              ("b_perfile_noid", X42, "pf_noid")]:
            t0 = time.time()
            flag = ctrl[base].to_numpy() != y0  # file lain tak berubah
            pred_f = oof_file(X.loc[mfile], y[mfile])
            flag[mfile] = pred_f != y[mfile]
            row(sc, proc, flag, poison, t0, csv_name)
        # (c) OOF global dengan label tercemar (+ probabilitas untuk f)
        t0 = time.time()
        pred_c, proba_c, cls_c = oof_global(X42, y, want_proba=True)
        row(sc, "c_global_noid", pred_c != y, poison, t0, csv_name)
        t0 = time.time()
        row(sc, "f_confident", cl_flags(proba_c, cls_c, y), poison, t0, csv_name)
        # (d): sisi tercemar pakai prediksi kontrol (model dilatih BS bersih,
        # label latihnya tak berubah); sisi bersih perlu refit model tercemar
        t0 = time.time()
        ipois = i1_ if sc["bs"] == "BS1" else i2_
        iclean = i2_ if sc["bs"] == "BS1" else i1_
        flag = np.zeros(len(d), bool)
        flag[ipois] = ctrl["d_pred"].to_numpy()[ipois] != y[ipois]
        pred_clean = fit_cross(X42, y, ipois, iclean)
        flag[iclean] = pred_clean != y[iclean]
        row(sc, "d_lintas_capture", flag, poison, t0, csv_name)
        S.log(f"E8 {lane} {sc['skenario']} n_poison={sc['n_poison']} "
              f"({time.time()-t_sc:.0f}s)", tag=f"e8_{lane}")
    S.log(f"E8 {lane} selesai skenario [{i0},{i1})", tag=f"e8_{lane}")


def summary():
    import glob
    from scipy import stats
    parts = [pd.read_csv(os.path.join(S.RESULTS, CSV))]
    for p in sorted(glob.glob(os.path.join(S.RESULTS, "e8_runs_lane*.csv"))):
        parts.append(pd.read_csv(p))
    allr = (pd.concat(parts, ignore_index=True)
            .drop_duplicates(["skenario", "prosedur"], keep="last"))
    allr.to_csv(os.path.join(S.RESULTS, CSV), index=False)  # gabung jadi satu
    r = allr.loc[allr["tipe"] != "kontrol"].copy()
    r["f1"] = pd.to_numeric(r["f1"], errors="coerce")
    piv = r.pivot_table(index="skenario", columns="prosedur", values="f1")
    procs = list(piv.columns)
    out = {"n_skenario": int(len(piv)), "per_prosedur": {}, "wilcoxon_d_vs": {},
           "terbaik": {}}
    for p in procs:
        out["per_prosedur"][p] = {
            "f1_mean": round(float(piv[p].mean()), 4),
            "f1_median": round(float(piv[p].median()), 4),
            "prec_mean": round(float(r.loc[r.prosedur == p, "precision"].mean()), 4),
            "rec_mean": round(float(pd.to_numeric(
                r.loc[r.prosedur == p, "recall"], errors="coerce").mean()), 4)}
    best = piv.idxmax(axis=1)
    mx = piv.max(axis=1)
    for p in procs:  # hitung seri: semua yang menyamai F1 maksimum dihitung
        out["terbaik"][p] = int((piv[p] >= mx - 1e-9).sum())
    for p in procs:
        if p == "d_lintas_capture":
            continue
        x, z = piv["d_lintas_capture"], piv[p]
        try:
            w = stats.wilcoxon(x, z)
            out["wilcoxon_d_vs"][p] = {
                "stat": round(float(w.statistic), 1),
                "p_two_sided": float(w.pvalue),
                "mean_diff_d_minus": round(float((x - z).mean()), 4)}
        except ValueError as e:
            out["wilcoxon_d_vs"][p] = {"error": str(e)}
    # ringkasan per tipe skenario
    out["f1_mean_per_tipe"] = {
        t: {p: round(float(r.loc[(r.tipe == t) & (r.prosedur == p), "f1"].mean()), 4)
            for p in procs} for t in r["tipe"].unique()}
    S.save_json("e8_summary.json", out)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prep":
        prep()
    elif cmd == "run":
        run(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif cmd == "summary":
        summary()
