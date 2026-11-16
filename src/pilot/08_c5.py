"""Pilot C5 — penutup audit 5G-NIDD.

1. Pencocokan record lintas-file/lintas-BS dengan kunci 8 kolom.
2. Tiga versi dataset (A asli, B relabel, C buang) x 3 protokol x HGB/RF.
3. Skor protokol literatur (label asli, semua kolom) dinilai vs label asli dan terkoreksi.
4. Butir 3 tanpa kolom identitas.
5. Sisa noise sesudah koreksi via prediksi out-of-fold 5 fold.
"""
import importlib.util
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.model_selection import StratifiedKFold, train_test_split

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C

def _load(name):
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), os.path.join(HERE, name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

step03 = _load("03_split_gap.py")
c2 = _load("05_c2.py")
c3 = _load("06_c3.py")
c4 = _load("07_c4.py")

ID_COLS = c2.ID_COLS
VICTIM = c4.VICTIM
KEY = ["StartTime", "SrcAddr", "DstAddr", "Sport", "Dport", "Proto",
       "TotPkts", "TotBytes"]


def prep():
    d = c4.load_raw_files()
    _, feats42 = c4.feats_sets()
    k = pd.util.hash_pandas_object(d[KEY].astype(str), index=False).to_numpy()
    att = c4.attacker_ips(d)
    mis = ((d["SrcAddr"].astype(str).isin(att))
           & (d["DstAddr"].astype(str) == VICTIM)
           & (d["Proto"].astype(str) == "udp")
           & d["__file"].str.startswith("UDPFlood")
           & (d["__y"] == "Benign")).to_numpy()
    y_corr = d["__y"].to_numpy().copy()
    y_corr[mis] = "UDPFlood"
    return d, feats42, k, mis, y_corr


def task1(d, k):
    t0 = time.time()
    out = {"kunci": KEY, "intra_bs": {}, "lintas_bs": {}}
    # duplikat antar file di dalam satu BS
    for bs in ["BS1", "BS2"]:
        dd = d.loc[(d["__bs"] == bs).to_numpy()]
        kk = k[(d["__bs"] == bs).to_numpy()]
        g = pd.DataFrame({"k": kk, "f": dd["__file"].to_numpy()})
        nf = g.groupby("k")["f"].nunique()
        multi = set(nf.index[nf > 1])
        rows_multi = int(g["k"].isin(multi).sum())
        combos = (g.loc[g["k"].isin(multi)].groupby("k")["f"]
                  .apply(lambda s: "+".join(sorted(set(s)))).value_counts().head(8))
        out["intra_bs"][bs] = {"n_kunci_multi_file": int(len(multi)),
                               "n_baris_terlibat": rows_multi,
                               "kombinasi_file_top": combos.to_dict()}
    # lintas BS: representatif per kunci per sisi (occurrence pertama)
    reps = {}
    for bs in ["BS1", "BS2"]:
        m = (d["__bs"] == bs).to_numpy()
        g = pd.DataFrame({"k": k[m], "file": d["__file"].to_numpy()[m],
                          "y": d["__y"].to_numpy()[m]})
        mult = g.groupby("k").size().rename("n")
        rep = g.drop_duplicates("k").set_index("k").join(mult)
        reps[bs] = rep
    both = reps["BS1"].join(reps["BS2"], how="inner", lsuffix="_1", rsuffix="_2")
    out["lintas_bs"]["n_kunci_cocok"] = int(len(both))
    out["lintas_bs"]["n_baris_bs1"] = int(both["n_1"].sum())
    out["lintas_bs"]["n_baris_bs2"] = int(both["n_2"].sum())
    mism = both["y_1"] != both["y_2"]
    out["lintas_bs"]["n_kunci_label_beda"] = int(mism.sum())
    pair = (both.groupby(["file_1", "file_2"])
            .agg(n_kunci=("y_1", "size"),
                 n_label_beda=("y_1", lambda s: int((s != both.loc[s.index, "y_2"]).sum())))
            .reset_index().sort_values("n_kunci", ascending=False))
    out["lintas_bs"]["per_pasangan_file"] = [
        {"file_bs1": r.file_1, "file_bs2": r.file_2, "n_kunci": int(r.n_kunci),
         "n_label_beda": int(r.n_label_beda)} for r in pair.itertuples()]
    lp = (both.loc[mism].groupby(["y_1", "y_2"]).size()
          .sort_values(ascending=False).head(10))
    out["lintas_bs"]["pasangan_label_beda_top"] = {f"{a} (BS1) -> {b} (BS2)": int(v)
                                                   for (a, b), v in lp.items()}
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c5_task1.json", out)
    C.log(f"c5.1 done cocok={len(both)} beda={int(mism.sum())}")


def build_versions(d, k, mis, y_corr):
    """A: asli; B: relabel; C: buang 281529 + dedup lintas-file (keep occurrence file pertama)."""
    versions = {}
    versions["A"] = (np.ones(len(d), bool), d["__y"].to_numpy())
    versions["B"] = (np.ones(len(d), bool), y_corr)
    keep = ~mis
    order_file = {f: i for i, f in enumerate(
        [f"{bs}/{fn}" for bs in ["BS1", "BS2"]
         for fn in sorted(d.loc[d["__bs"] == bs, "__file"].unique())])}
    fileidx = (d["__bs"] + "/" + d["__file"]).map(order_file).to_numpy()
    g = pd.DataFrame({"k": k[keep], "fi": fileidx[keep]})
    first = g.groupby("k")["fi"].min()
    keep_c = keep.copy()
    keep_c[keep] = (g["fi"].to_numpy() == first.loc[g["k"]].to_numpy())
    versions["C"] = (keep_c, d["__y"].to_numpy())
    return versions


def _rf(seed):
    return c3.make_models(seed)["RF"]


def task2(d, feats42, k, mis, y_corr):
    t0 = time.time()
    versions = build_versions(d, k, mis, y_corr)
    out = {"ukuran": {}, "hasil": {}}
    for v, (keep, y) in versions.items():
        out["ukuran"][v] = {
            "total": int(keep.sum()),
            "BS1": int((keep & (d["__bs"] == "BS1").to_numpy()).sum()),
            "BS2": int((keep & (d["__bs"] == "BS2").to_numpy()).sum()),
        }
    models = {"HGB": step03.make_model, "RF": _rf}
    for v, (keep, y_all) in versions.items():
        dv = d.loc[keep]
        yv = y_all[keep]
        ybv = (yv != "Benign").astype(int)
        classes = np.unique(yv)
        # sampel per sisi dan sampel acak
        sides = {}
        for bs in ["BS1", "BS2"]:
            m = (dv["__bs"] == bs).to_numpy()
            pos = np.flatnonzero(m)
            i = C.stratified_cap(yv[pos], C.MODEL_CAP, seed=0)
            sides[bs] = pos[np.sort(i)]
        irand = np.sort(C.stratified_cap(yv, C.MODEL_CAP, seed=0))
        # --- split acak ---
        Xr = C.encode_features(dv.iloc[irand], feats42)
        for mname, mk in models.items():
            f1s, recs = [], []
            for seed in C.SEEDS:
                tr, te = train_test_split(np.arange(len(irand)), test_size=0.3,
                                          random_state=seed, stratify=yv[irand])
                m = mk(seed)
                cols = [c for c in Xr.columns if Xr.iloc[tr][c].nunique(dropna=True) >= 2]
                m.fit(Xr.iloc[tr][cols], yv[irand][tr])
                pred = m.predict(Xr.iloc[te][cols])
                f1s.append(round(float(f1_score(yv[irand][te], pred, average="macro",
                                                labels=classes, zero_division=0)), 4))
                recs.append(recall_score(yv[irand][te], pred, average=None,
                                         labels=classes, zero_division=0))
                C.log(f"c5.2 {v} acak {mname} seed={seed} f1={f1s[-1]}")
            out["hasil"][f"{v}|acak|{mname}"] = {
                "macro_f1": round(float(np.mean(f1s)), 4), "seeds": f1s,
                "recall_per_class": {str(c): round(float(np.mean([r[i] for r in recs])), 4)
                                     for i, c in enumerate(classes)}}
        # --- lintas BS + biner ---
        for tr_name in ["BS1", "BS2"]:
            te_name = "BS2" if tr_name == "BS1" else "BS1"
            itr, ite = sides[tr_name], sides[te_name]
            raw = pd.concat([dv.iloc[itr][feats42], dv.iloc[ite][feats42]],
                            ignore_index=True)
            X = C.encode_features(raw, feats42)
            tr = np.arange(len(itr))
            te = np.arange(len(itr), len(itr) + len(ite))
            for mname, mk in models.items():
                f1s, recs, tprs, fprs = [], [], [], []
                for seed in C.SEEDS:
                    m = mk(seed)
                    Xtr = X.iloc[tr]
                    cols = [c for c in X.columns if Xtr[c].nunique(dropna=True) >= 2]
                    m.fit(Xtr[cols], yv[itr])
                    pred = m.predict(X.iloc[te][cols])
                    f1s.append(round(float(f1_score(yv[ite], pred, average="macro",
                                                    labels=classes, zero_division=0)), 4))
                    recs.append(recall_score(yv[ite], pred, average=None,
                                             labels=classes, zero_division=0))
                    mb = mk(seed)
                    mb.fit(Xtr[cols], ybv[itr])
                    pb = mb.predict(X.iloc[te][cols])
                    yt = ybv[ite]
                    tprs.append(float(pb[yt == 1].mean()))
                    fprs.append(float(pb[yt == 0].mean()))
                    C.log(f"c5.2 {v} {tr_name}->{te_name} {mname} seed={seed} "
                          f"f1={f1s[-1]} TPR={tprs[-1]:.4f} FPR={fprs[-1]:.4f}")
                out["hasil"][f"{v}|{tr_name}->{te_name}|{mname}"] = {
                    "macro_f1": round(float(np.mean(f1s)), 4), "seeds": f1s,
                    "recall_per_class": {str(c): round(float(np.mean([r[i] for r in recs])), 4)
                                         for i, c in enumerate(classes)},
                    "TPR": round(float(np.mean(tprs)), 4),
                    "FPR": round(float(np.mean(fprs)), 4)}
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c5_task2.json", out)
    C.log("c5.2 done")


def _lit(d, feats, mis, y_corr, name):
    t0 = time.time()
    y_orig = d["__y"].to_numpy()
    idx = np.sort(C.stratified_cap(y_orig, C.MODEL_CAP, seed=0))
    X = C.encode_features(d.iloc[idx], feats)
    yo, yc, mi = y_orig[idx], y_corr[idx], mis[idx]
    out = {"n_rows": int(len(idx)), "n_features": len(feats), "multikelas": {}, "biner": {}}
    accs = {("multi", "asli"): [], ("multi", "koreksi"): [],
            ("bin", "asli"): [], ("bin", "koreksi"): []}
    f1s = {key: [] for key in accs}
    n_mis_te, n_mis_pred_benign, n_mis_pred_benign_bin = [], [], []
    for seed in C.SEEDS:
        tr, te = train_test_split(np.arange(len(idx)), test_size=0.2,
                                  random_state=seed, stratify=yo)
        cols = [c for c in X.columns if X.iloc[tr][c].nunique(dropna=True) >= 2]
        m = step03.make_model(seed)
        m.fit(X.iloc[tr][cols], yo[tr])
        pred = m.predict(X.iloc[te][cols])
        for tag, yref in [("asli", yo[te]), ("koreksi", yc[te])]:
            accs[("multi", tag)].append(float(accuracy_score(yref, pred)))
            f1s[("multi", tag)].append(float(f1_score(yref, pred, average="macro",
                                                      zero_division=0)))
        mb = step03.make_model(seed)
        ybo = (yo != "Benign").astype(int)
        ybc = (yc != "Benign").astype(int)
        mb.fit(X.iloc[tr][cols], ybo[tr])
        pb = mb.predict(X.iloc[te][cols])
        for tag, yref in [("asli", ybo[te]), ("koreksi", ybc[te])]:
            accs[("bin", tag)].append(float(accuracy_score(yref, pb)))
            f1s[("bin", tag)].append(float(f1_score(yref, pb, average="macro",
                                                    zero_division=0)))
        mte = mi[te]
        n_mis_te.append(int(mte.sum()))
        n_mis_pred_benign.append(int((pred[mte] == "Benign").sum()))
        n_mis_pred_benign_bin.append(int((pb[mte] == 0).sum()))
        C.log(f"c5.{name} seed={seed} accAsli={accs[('multi','asli')][-1]:.4f} "
              f"accKoreksi={accs[('multi','koreksi')][-1]:.4f}")
    def mm(dic, key):
        return round(float(np.mean(dic[key])), 4)
    out["multikelas"] = {"acc_vs_asli": mm(accs, ("multi", "asli")),
                         "f1_vs_asli": mm(f1s, ("multi", "asli")),
                         "acc_vs_koreksi": mm(accs, ("multi", "koreksi")),
                         "f1_vs_koreksi": mm(f1s, ("multi", "koreksi"))}
    out["biner"] = {"acc_vs_asli": mm(accs, ("bin", "asli")),
                    "f1_vs_asli": mm(f1s, ("bin", "asli")),
                    "acc_vs_koreksi": mm(accs, ("bin", "koreksi")),
                    "f1_vs_koreksi": mm(f1s, ("bin", "koreksi"))}
    out["baris_281529_di_test_mean"] = round(float(np.mean(n_mis_te)), 1)
    out["diprediksi_benign_multi_mean"] = round(float(np.mean(n_mis_pred_benign)), 1)
    out["pct_diprediksi_benign_multi"] = round(
        100 * float(np.mean(n_mis_pred_benign)) / max(float(np.mean(n_mis_te)), 1), 2)
    out["diprediksi_benign_biner_mean"] = round(float(np.mean(n_mis_pred_benign_bin)), 1)
    out["pct_diprediksi_benign_biner"] = round(
        100 * float(np.mean(n_mis_pred_benign_bin)) / max(float(np.mean(n_mis_te)), 1), 2)
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json(f"c5_task{name}.json", out)
    C.log(f"c5.{name} done")


def task5(d, feats42, y_corr):
    t0 = time.time()
    X = C.encode_features(d, feats42)
    X = X[[c for c in X.columns if X[c].nunique(dropna=True) >= 2]]
    y = y_corr
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    pred = np.empty(len(y), dtype=object)
    conf = np.zeros(len(y))
    for fi, (tr, te) in enumerate(skf.split(X, y)):
        m = step03.make_model(0)
        m.fit(X.iloc[tr], y[tr])
        p = m.predict_proba(X.iloc[te])
        pred[te] = m.classes_[p.argmax(1)]
        conf[te] = p.max(1)
        C.log(f"c5.5 fold {fi+1}/5 done")
    bad = (pred != y) & (conf >= 0.95)
    dd = d.loc[bad]
    grp = (pd.DataFrame({"file": dd["__bs"] + "/" + dd["__file"],
                         "SrcAddr": dd["SrcAddr"].astype(str),
                         "label": y[bad], "prediksi": pred[bad]})
           .groupby(["file", "SrcAddr", "label", "prediksi"]).size()
           .sort_values(ascending=False))
    out = {
        "rows": int(len(y)), "n_salah_label_vs_oof": int((pred != y).sum()),
        "n_keyakinan_95": int(bad.sum()),
        "pct_keyakinan_95": round(100 * float(bad.mean()), 3),
        "top10_kelompok": [
            {"file": f, "SrcAddr": s, "label": l, "prediksi": p, "n": int(n)}
            for (f, s, l, p), n in grp.head(10).items()],
        "runtime_s": round(time.time() - t0, 1),
    }
    C.save_json("c5_task5.json", out)
    C.log(f"c5.5 done n95={int(bad.sum())}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    C.log("c5: loading raw per-BS files")
    d, feats42, k, mis, y_corr = prep()
    feats_all, _ = c4.feats_sets()
    tasks = {
        "1": lambda: task1(d, k),
        "2": lambda: task2(d, feats42, k, mis, y_corr),
        "3": lambda: _lit(d, feats_all, mis, y_corr, "3"),
        "4": lambda: _lit(d, feats42, mis, y_corr, "4"),
        "5": lambda: task5(d, feats42, y_corr),
    }
    for key in (list("12345") if which == "all" else [which]):
        tasks[key]()
