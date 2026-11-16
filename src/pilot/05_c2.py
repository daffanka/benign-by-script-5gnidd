"""Pilot C2 — lanjutan audit 5G-NIDD saja (CPU, <=1 jam).

1. Ablasi identitas saja (split acak, seed 0/1/2): (i) semua fitur,
   (ii) minus kolom identitas saja, (iii) hanya Seq+Offset.
2. Rentang min-max Seq/Offset per kelas + tumpang-tindih antar kelas.
3. Split acak yang menjaga vektor fitur identik (tanpa kolom identitas) tidak
   melintasi train/test; batas atas Bayes; 10 pasangan kelas teratas yang
   berbagi vektor fitur.
4. Split bergrup benar: latih di satu base station (BS1/BS2), uji di lainnya,
   dua arah, dengan dan tanpa kolom identitas.

Hasil -> results/c2_*.json + REPORT_C2.md.
"""
import importlib.util
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C

_spec = importlib.util.spec_from_file_location("step03", os.path.join(HERE, "03_split_gap.py"))
step03 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(step03)

ID_COLS = ["Seq", "Offset", "sVid", "dVid", "SrcTCPBase", "DstTCPBase"]  # + row_id (never a feature)
GOLD = np.uint64(0x9E3779B97F4A7C15)


def prep_sample():
    df = C.load_sample("5gnidd")
    feats, _, _, y_multi, _, _ = C.dataset_columns("5gnidd", df)
    idx = np.sort(C.stratified_cap(y_multi, C.MODEL_CAP, seed=0))
    return df.iloc[idx], feats, y_multi[idx]


def fit_eval(X, ym, tr, te, seed, all_classes):
    m = step03.make_model(seed)
    Xtr = X.iloc[tr]
    cols = [c for c in X.columns if Xtr[c].nunique(dropna=True) >= 2]
    m.fit(Xtr[cols], ym[tr])
    pred = m.predict(X.iloc[te][cols])
    f1 = f1_score(ym[te], pred, average="macro", labels=all_classes, zero_division=0)
    rec = recall_score(ym[te], pred, average=None, labels=all_classes, zero_division=0)
    return float(f1), {str(c): round(float(r), 4) for c, r in zip(all_classes, rec)}


def task1():
    t0 = time.time()
    df, feats, ym = prep_sample()
    all_classes = np.unique(ym)
    variants = {
        "i_semua_fitur": feats,
        "ii_minus_identitas": [c for c in feats if c not in ID_COLS],
        "iii_hanya_seq_offset": ["Seq", "Offset"],
    }
    out = {"n_rows": int(len(df)), "variants": {}}
    for name, cols in variants.items():
        X = C.encode_features(df, cols)
        f1s = []
        for seed in C.SEEDS:
            tr, te = train_test_split(np.arange(len(ym)), test_size=0.3,
                                      random_state=seed, stratify=ym)
            f1, _ = fit_eval(X, ym, tr, te, seed, all_classes)
            f1s.append(round(f1, 4))
            C.log(f"c2.1 {name} seed={seed} macroF1={f1:.4f}")
        out["variants"][name] = {"n_features": len(cols), "macro_f1_seeds": f1s,
                                 "mean": round(float(np.mean(f1s)), 4),
                                 "sd": round(float(np.std(f1s, ddof=1)), 4)}
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c2_task1.json", out)


def task2():
    t0 = time.time()
    df = pd.read_csv(C.PATH_5GNIDD, low_memory=False,
                     usecols=["Seq", "Offset", "Attack Type"])
    y = df["Attack Type"].astype(str).to_numpy()
    out = {"rows": int(len(df)), "per_class": {}, "overlap": {}}
    for col in ["Seq", "Offset"]:
        v = pd.to_numeric(df[col], errors="coerce").to_numpy()
        tab = {}
        for cls in np.unique(y):
            vv = v[y == cls]
            tab[cls] = {"n": int(len(vv)), "min": float(np.nanmin(vv)),
                        "max": float(np.nanmax(vv))}
        out["per_class"][col] = tab
        # % baris kelas c yang nilainya jatuh di dalam rentang kelas lain
        ov = {}
        for cls in tab:
            others = [(tab[d]["min"], tab[d]["max"]) for d in tab if d != cls]
            vv = v[y == cls]
            inside = np.zeros(len(vv), dtype=bool)
            for mn, mx in others:
                inside |= (vv >= mn) & (vv <= mx)
            ov[cls] = round(100.0 * float(inside.mean()), 2)
        out["overlap"][col] = ov
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c2_task2.json", out)
    C.log("c2.2 done")


def _hash_feats(df, cols):
    return pd.util.hash_pandas_object(df[cols], index=False).to_numpy()


def task3():
    t0 = time.time()
    # (a) split acak sadar-duplikat pada sampel model, fitur tanpa identitas
    df, feats, ym = prep_sample()
    feats_noid = [c for c in feats if c not in ID_COLS]
    X = C.encode_features(df, feats_noid)
    groups = _hash_feats(df, feats_noid)
    all_classes = np.unique(ym)
    f1s = []
    for seed in C.SEEDS:
        gss = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=seed)
        tr, te = next(gss.split(X, ym, groups=groups))
        f1, _ = fit_eval(X, ym, tr, te, seed, all_classes)
        f1s.append(round(f1, 4))
        C.log(f"c2.3 dedup-aware seed={seed} macroF1={f1:.4f} "
              f"(train={len(tr)}, test={len(te)})")

    # (b) batas atas Bayes pada SELURUH data (label mayoritas per vektor fitur)
    full = pd.read_csv(C.PATH_5GNIDD, low_memory=False)
    full = full.rename(columns={full.columns[0]: "row_id"})
    yfull = full["Attack Type"].astype(str).to_numpy()
    h = _hash_feats(full, feats_noid)
    g = pd.DataFrame({"h": h, "y": yfull})
    counts = g.groupby(["h", "y"], sort=False).size().rename("n").reset_index()
    maj = counts.sort_values("n", ascending=False).drop_duplicates("h")
    pred = g.merge(maj[["h", "y"]].rename(columns={"y": "pred"}), on="h", how="left")["pred"].to_numpy()
    bayes_f1 = f1_score(yfull, pred, average="macro", zero_division=0)
    bayes_acc = accuracy_score(yfull, pred)

    # (c) 10 pasangan kelas teratas yang berbagi vektor fitur identik
    nlab = counts.groupby("h")["y"].transform("nunique")
    conf = counts[nlab > 1]
    pairs = conf.merge(conf, on="h")
    pairs = pairs[pairs["y_x"] < pairs["y_y"]]
    agg = (pairs.assign(rows=lambda d: d["n_x"] + d["n_y"])
           .groupby(["y_x", "y_y"])
           .agg(n_vectors=("h", "nunique"), n_rows=("rows", "sum"))
           .sort_values("n_rows", ascending=False).head(10).reset_index())
    out = {
        "dedup_aware_split": {"macro_f1_seeds": f1s,
                              "mean": round(float(np.mean(f1s)), 4),
                              "sd": round(float(np.std(f1s, ddof=1)), 4),
                              "n_features": len(feats_noid)},
        "bayes_upper_bound_full": {"rows": int(len(full)),
                                   "macro_f1": round(float(bayes_f1), 4),
                                   "accuracy": round(float(bayes_acc), 4)},
        "top10_shared_class_pairs": [
            {"kelas_1": r.y_x, "kelas_2": r.y_y, "n_vektor_bersama": int(r.n_vectors),
             "n_baris_terlibat": int(r.n_rows)} for r in agg.itertuples()],
        "runtime_s": round(time.time() - t0, 1),
    }
    C.save_json("c2_task3.json", out)
    C.log(f"c2.3 done bayesF1={bayes_f1:.4f} acc={bayes_acc:.4f}")


def load_bs(side):
    base = os.path.join(C.CACHE, side)
    files = []
    for root, _, fs in os.walk(base):
        files += [os.path.join(root, f) for f in fs if f.lower().endswith(".csv")]
    parts = []
    for f in sorted(files):
        p = pd.read_csv(f, low_memory=False)
        p.columns = [c.strip() for c in p.columns]  # TCPConnect1.csv: 'Attack Type '
        parts.append(p)
    df = pd.concat(parts, ignore_index=True)
    n0 = len(df)
    df = df.loc[df["Attack Type"].notna()].reset_index(drop=True)
    n_na = n0 - len(df)
    return df, [os.path.basename(f) for f in sorted(files)], n_na


def task4():
    t0 = time.time()
    # fitur = kolom yang sama dengan Combined.csv (agar sebanding dengan C1);
    # kolom ekstra file mentah (IP, MAC, port, waktu, dll.) TIDAK dipakai
    sample = C.load_sample("5gnidd")
    feats_combined, _, _, _, _, _ = C.dataset_columns("5gnidd", sample)
    d1, files1, na1 = load_bs("bs1")
    d2, files2, na2 = load_bs("bs2")
    out = {"files_bs1": files1, "files_bs2": files2,
           "label_na_rows_dropped": {"BS1": int(na1), "BS2": int(na2)},
           "directions": {}}
    sets = {"semua_fitur": feats_combined,
            "tanpa_identitas": [c for c in feats_combined if c not in ID_COLS]}
    sides = {"BS1": d1, "BS2": d2}
    for s, d in sides.items():
        d["__y"] = d["Attack Type"].astype(str)
        out[f"classes_{s}"] = d["__y"].value_counts().to_dict()
    all_classes = np.unique(np.concatenate([d1["__y"].to_numpy(), d2["__y"].to_numpy()]))
    for tr_name, te_name in [("BS1", "BS2"), ("BS2", "BS1")]:
        dtr, dte = sides[tr_name], sides[te_name]
        itr = np.sort(C.stratified_cap(dtr["__y"].to_numpy(), C.MODEL_CAP, seed=0))
        ite = np.sort(C.stratified_cap(dte["__y"].to_numpy(), C.MODEL_CAP, seed=0))
        for set_name, cols in sets.items():
            raw = pd.concat([dtr.iloc[itr][cols], dte.iloc[ite][cols]],
                            ignore_index=True)
            X = C.encode_features(raw, cols)  # encode once -> kode kategori konsisten
            ym = np.concatenate([dtr["__y"].to_numpy()[itr],
                                 dte["__y"].to_numpy()[ite]])
            tr = np.arange(len(itr))
            te = np.arange(len(itr), len(X))
            f1s, recs = [], []
            for seed in C.SEEDS:
                f1, rec = fit_eval(X, ym, tr, te, seed, all_classes)
                f1s.append(round(f1, 4))
                recs.append(rec)
                C.log(f"c2.4 {tr_name}->{te_name} {set_name} seed={seed} macroF1={f1:.4f}")
            rec_mean = {k: round(float(np.mean([r[k] for r in recs])), 4)
                        for k in recs[0]}
            out["directions"][f"{tr_name}->{te_name}|{set_name}"] = {
                "n_train": int(len(tr)), "n_test": int(len(te)),
                "macro_f1_seeds": f1s, "mean": round(float(np.mean(f1s)), 4),
                "sd": round(float(np.std(f1s, ddof=1)), 4),
                "recall_per_class_mean": rec_mean,
            }
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c2_task4.json", out)
    C.log("c2.4 done")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    tasks = {"1": task1, "2": task2, "3": task3, "4": task4}
    if which == "all":
        for k in "1234":
            tasks[k]()
    else:
        tasks[which]()
