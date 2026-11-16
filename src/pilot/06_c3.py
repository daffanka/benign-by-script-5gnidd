"""Pilot C3 — lanjutan audit 5G-NIDD (CPU, <=2 jam). Lihat REPORT_C3.md.

1. Akar konflik Benign<->UDPFlood pada file mentah per-BS (112 kolom).
2. Batas atas Bayes dengan fitur mentah non-identitas.
3. Replikasi lintas model (RF, MLP, HGB) pada 4 protokol split.
4. Protokol literatur (semua kolom, acak 80/20): akurasi & macro-F1, multi & biner.
5. Koreksi label-shift EM (Saerens) pada lintas-BS tanpa identitas.
6. Tugas biner lintas-BS: TPR/FPR dengan dan tanpa identitas.
"""
import importlib.util
import os
import re
import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

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

ID_COLS = c2.ID_COLS  # Seq, Offset, sVid, dVid, SrcTCPBase, DstTCPBase
LABELS = ["Label", "Attack Type", "Attack Tool"]
# kolom identitas file mentah (interpretasi instruksi "alamat IP, MAC, StartTime,
# Seq, Offset, basis TCP" + padanan langsungnya: LastTime ikut StartTime; OUI ikut
# MAC; sIpId/dIpId = counter header IP; Rank/AutoId/SrcId = nomor record/sensor;
# sVid/dVid = VLAN id, konsisten dengan definisi identitas C1/C2)
RAW_ID_EXCL = ["SrcAddr", "DstAddr", "SrcMac", "DstMac", "SrcOui", "DstOui",
               "StartTime", "LastTime", "Seq", "Offset", "SrcTCPBase", "DstTCPBase",
               "sIpId", "dIpId", "Rank", "AutoId", "SrcId", "sVid", "dVid"]
T3_CAP = 200_000


def combined_feats():
    sample = C.load_sample("5gnidd")
    feats, _, _, _, _, _ = C.dataset_columns("5gnidd", sample)
    return feats


def load_raw():
    d1, _, _ = c2.load_bs("bs1")
    d2, _, _ = c2.load_bs("bs2")
    d1["__bs"] = "BS1"
    d2["__bs"] = "BS2"
    d = pd.concat([d1, d2], ignore_index=True)
    d["__y"] = d["Attack Type"].astype(str)
    return d


def parse_mmss(s):
    m = re.match(r"^\s*(\d+):(\d+(?:\.\d+)?)\s*$", str(s))
    return float(m.group(1)) * 60 + float(m.group(2)) if m else np.nan


def task1():
    t0 = time.time()
    d = load_raw()
    feats42 = [c for c in combined_feats() if c not in ID_COLS]
    h = pd.util.hash_pandas_object(d[feats42], index=False).to_numpy()
    y = d["__y"].to_numpy()
    df = pd.DataFrame({"h": h, "y": y})
    tab = df.groupby(["h", "y"], sort=False).size().unstack(fill_value=0)
    both = tab.index[(tab.get("Benign", 0) > 0) & (tab.get("UDPFlood", 0) > 0)]
    conf_mask = np.isin(h, both)
    ben_conf = d.loc[conf_mask & (y == "Benign")]
    udp_rows = d.loc[y == "UDPFlood"]

    def topfrac(s, k=8):
        vc = s.astype(str).value_counts(normalize=True).head(k)
        return {str(i): round(float(v) * 100, 2) for i, v in vc.items()}

    # IP penyerang/korban UDPFlood: alamat yang mencakup >=1% baris serangan
    att = udp_rows["SrcAddr"].astype(str).value_counts(normalize=True)
    vic = udp_rows["DstAddr"].astype(str).value_counts(normalize=True)
    att_ips = set(att.index[att >= 0.01])
    vic_ips = set(vic.index[vic >= 0.01])
    inv = (ben_conf["SrcAddr"].astype(str).isin(att_ips | vic_ips)
           | ben_conf["DstAddr"].astype(str).isin(att_ips | vic_ips))

    # jendela waktu serangan per BS (StartTime format 'MM:SS.f' — lihat penyimpangan)
    windows, inwin = {}, {}
    for bs in ["BS1", "BS2"]:
        tu = udp_rows.loc[udp_rows["__bs"] == bs, "StartTime"].map(parse_mmss)
        tb = ben_conf.loc[ben_conf["__bs"] == bs, "StartTime"].map(parse_mmss)
        lo, hi = float(np.nanmin(tu)), float(np.nanmax(tu))
        windows[bs] = {"min_s": lo, "max_s": hi,
                       "parse_fail_pct": round(100 * float(tu.isna().mean()), 2)}
        inwin[bs] = round(100 * float(((tb >= lo) & (tb <= hi)).mean()), 2)

    # 5 vektor konflik terbesar
    tab2 = tab.loc[both].copy()
    tab2["rows"] = tab2.get("Benign", 0) + tab2.get("UDPFlood", 0)
    top5 = tab2.sort_values("rows", ascending=False).head(5)
    show = ["Proto", "Dur", "TotPkts", "SrcPkts", "DstPkts", "TotBytes",
            "SrcBytes", "DstBytes", "sTtl", "dTtl", "Rate", "State"]
    top5_out = []
    for hv in top5.index:
        rows = d.loc[h == hv]
        rec = {"n_benign": int(top5.loc[hv].get("Benign", 0)),
               "n_udpflood": int(top5.loc[hv].get("UDPFlood", 0)),
               "fitur": {c: str(rows.iloc[0][c]) for c in show},
               "SrcAddr_top": topfrac(rows["SrcAddr"], 4),
               "DstAddr_top": topfrac(rows["DstAddr"], 4),
               "Dport_top": topfrac(rows["Dport"], 4)}
        top5_out.append(rec)

    out = {
        "rows_raw_total": int(len(d)),
        "n_vektor_konflik_ben_udp": int(len(both)),
        "n_baris_benign_konflik": int(len(ben_conf)),
        "pct_benign_konflik_dari_semua_benign":
            round(100 * len(ben_conf) / int((y == "Benign").sum()), 2),
        "benign_konflik_SrcAddr_top": topfrac(ben_conf["SrcAddr"]),
        "benign_konflik_DstAddr_top": topfrac(ben_conf["DstAddr"]),
        "benign_konflik_Proto_top": topfrac(ben_conf["Proto"]),
        "benign_konflik_Dport_top": topfrac(ben_conf["Dport"]),
        "udp_attacker_ips": sorted(att_ips), "udp_victim_ips": sorted(vic_ips),
        "pct_benign_konflik_melibatkan_ip_serangan": round(100 * float(inv.mean()), 2),
        "jendela_udpflood": windows,
        "pct_benign_konflik_dalam_jendela": inwin,
        "top5_vektor": top5_out,
        "runtime_s": round(time.time() - t0, 1),
    }
    C.save_json("c3_task1.json", out)
    C.log(f"c3.1 done conflictBenign={len(ben_conf)} invIP%={out['pct_benign_konflik_melibatkan_ip_serangan']}")


def task2():
    t0 = time.time()
    d = load_raw()
    feats = [c for c in d.columns
             if c not in LABELS + RAW_ID_EXCL + ["__bs", "__y"]]
    h = pd.util.hash_pandas_object(d[feats], index=False).to_numpy()
    y = d["__y"].to_numpy()
    g = pd.DataFrame({"h": h, "y": y})
    counts = g.groupby(["h", "y"], sort=False).size().rename("n").reset_index()
    maj = counts.sort_values("n", ascending=False).drop_duplicates("h")
    pred = g.merge(maj[["h", "y"]].rename(columns={"y": "pred"}), on="h", how="left")["pred"].to_numpy()
    nconf = counts.groupby("h")["y"].nunique()
    out = {
        "n_fitur_mentah_nonid": len(feats),
        "fitur_dipakai": feats,
        "rows": int(len(d)),
        "bayes_accuracy": round(float(accuracy_score(y, pred)), 4),
        "bayes_macro_f1": round(float(f1_score(y, pred, average="macro", zero_division=0)), 4),
        "pct_baris_vektor_konflik": round(100 * float(
            g["h"].isin(nconf.index[nconf > 1]).mean()), 2),
        "runtime_s": round(time.time() - t0, 1),
    }
    C.save_json("c3_task2.json", out)
    C.log(f"c3.2 done bayesAcc={out['bayes_accuracy']} bayesF1={out['bayes_macro_f1']}")


def make_models(seed):
    return {
        "HGB": step03.make_model(seed),
        "RF": Pipeline([("imp", SimpleImputer(strategy="median")),
                        ("m", RandomForestClassifier(n_estimators=100, n_jobs=-1,
                                                     random_state=seed))]),
        "MLP": Pipeline([("imp", SimpleImputer(strategy="median")),
                         ("sc", StandardScaler()),
                         ("m", MLPClassifier(hidden_layer_sizes=(100,), max_iter=50,
                                             early_stopping=True, random_state=seed))]),
    }


def _random_split_data(feat_set):
    df = C.load_sample("5gnidd")
    feats, _, _, y_multi, _, _ = C.dataset_columns("5gnidd", df)
    if feat_set == "noid":
        feats = [c for c in feats if c not in ID_COLS]
    idx = np.sort(C.stratified_cap(y_multi, T3_CAP, seed=0))
    X = C.encode_features(df.iloc[idx], feats)
    X = X[[c for c in X.columns if X[c].nunique(dropna=True) >= 2]]
    return X, y_multi[idx]


def _crossbs_data(tr_name):
    d = load_raw()
    feats = [c for c in combined_feats() if c not in ID_COLS]
    sides = {}
    for bs in ["BS1", "BS2"]:
        dd = d.loc[d["__bs"] == bs]
        i = np.sort(C.stratified_cap(dd["__y"].to_numpy(), T3_CAP, seed=0))
        sides[bs] = dd.iloc[i]
    te_name = "BS2" if tr_name == "BS1" else "BS1"
    raw = pd.concat([sides[tr_name][feats], sides[te_name][feats]], ignore_index=True)
    X = C.encode_features(raw, feats)
    X = X[[c for c in X.columns if X[c].nunique(dropna=True) >= 2]]
    ym = np.concatenate([sides[tr_name]["__y"].to_numpy(), sides[te_name]["__y"].to_numpy()])
    ntr = len(sides[tr_name])
    return X, ym, np.arange(ntr), np.arange(ntr, len(X))


def task3():
    t0 = time.time()
    out = {"cap_rows": T3_CAP, "protocols": {}}
    datasets = {
        "acak_semua_fitur": ("random", "all"),
        "acak_tanpa_identitas": ("random", "noid"),
        "BS1->BS2_tanpa_identitas": ("crossbs", "BS1"),
        "BS2->BS1_tanpa_identitas": ("crossbs", "BS2"),
    }
    for proto, (kind, arg) in datasets.items():
        if kind == "random":
            X, ym = _random_split_data(arg)
        else:
            X, ym, tr_fix, te_fix = _crossbs_data(arg)
        all_classes = np.unique(ym)
        res = {}
        for mname in ["HGB", "RF", "MLP"]:
            f1s = []
            for seed in C.SEEDS:
                ts = time.time()
                if kind == "random":
                    tr, te = train_test_split(np.arange(len(ym)), test_size=0.3,
                                              random_state=seed, stratify=ym)
                else:
                    tr, te = tr_fix, te_fix
                m = make_models(seed)[mname]
                m.fit(X.iloc[tr], ym[tr])
                pred = m.predict(X.iloc[te])
                f1 = f1_score(ym[te], pred, average="macro",
                              labels=all_classes, zero_division=0)
                f1s.append(round(float(f1), 4))
                C.log(f"c3.3 {proto} {mname} seed={seed} macroF1={f1:.4f} ({time.time()-ts:.0f}s)")
            res[mname] = {"macro_f1_seeds": f1s,
                          "mean": round(float(np.mean(f1s)), 4),
                          "sd": round(float(np.std(f1s, ddof=1)), 4)}
        out["protocols"][proto] = res
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c3_task3.json", out)
    C.log("c3.3 done")


def task4():
    t0 = time.time()
    df = C.load_sample("5gnidd")
    feats, _, y_bin_all, y_multi, _, _ = C.dataset_columns("5gnidd", df)
    idx = np.sort(C.stratified_cap(y_multi, C.MODEL_CAP, seed=0))
    X = C.encode_features(df.iloc[idx], feats)
    X = X[[c for c in X.columns if X[c].nunique(dropna=True) >= 2]]
    out = {"n_rows": int(len(idx)), "n_features": X.shape[1], "tasks": {}}
    for task, yv in [("multikelas", y_multi[idx]), ("biner", y_bin_all[idx])]:
        accs, f1s = [], []
        for seed in C.SEEDS:
            tr, te = train_test_split(np.arange(len(yv)), test_size=0.2,
                                      random_state=seed, stratify=yv)
            m = step03.make_model(seed)
            m.fit(X.iloc[tr], yv[tr])
            pred = m.predict(X.iloc[te])
            accs.append(round(float(accuracy_score(yv[te], pred)), 4))
            f1s.append(round(float(f1_score(yv[te], pred, average="macro",
                                            zero_division=0)), 4))
            C.log(f"c3.4 {task} seed={seed} acc={accs[-1]} macroF1={f1s[-1]}")
        out["tasks"][task] = {
            "accuracy_seeds": accs, "accuracy_mean": round(float(np.mean(accs)), 4),
            "macro_f1_seeds": f1s, "macro_f1_mean": round(float(np.mean(f1s)), 4),
        }
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c3_task4.json", out)
    C.log("c3.4 done")


def _metrics(y, pred, classes):
    f1 = f1_score(y, pred, average="macro", labels=classes, zero_division=0)
    rec = recall_score(y, pred, average=None, labels=classes, zero_division=0)
    rd = dict(zip(classes, rec))
    return (round(float(f1), 4), round(float(rd.get("UDPFlood", np.nan)), 4),
            round(float(rd.get("Benign", np.nan)), 4))


def task5():
    t0 = time.time()
    try:
        from sklearn.frozen import FrozenEstimator
        from sklearn.calibration import CalibratedClassifierCV
        has_cal = True
    except Exception:
        has_cal = False
    out = {"calibration": "isotonic (CalibratedClassifierCV + FrozenEstimator)"
                          if has_cal else "TIDAK TERSEDIA — probabilitas mentah",
           "directions": {}}
    d = load_raw()
    feats = [c for c in combined_feats() if c not in ID_COLS]
    sides = {}
    for bs in ["BS1", "BS2"]:
        dd = d.loc[d["__bs"] == bs]
        i = np.sort(C.stratified_cap(dd["__y"].to_numpy(), C.MODEL_CAP, seed=0))
        sides[bs] = dd.iloc[i].reset_index(drop=True)
    for tr_name in ["BS1", "BS2"]:
        te_name = "BS2" if tr_name == "BS1" else "BS1"
        raw = pd.concat([sides[tr_name][feats], sides[te_name][feats]], ignore_index=True)
        X = C.encode_features(raw, feats)
        X = X[[c for c in X.columns if X[c].nunique(dropna=True) >= 2]]
        ysrc = sides[tr_name]["__y"].to_numpy()
        ytgt = sides[te_name]["__y"].to_numpy()
        Xsrc, Xtgt = X.iloc[:len(ysrc)], X.iloc[len(ysrc):]
        classes_all = np.unique(np.concatenate([ysrc, ytgt]))
        res = {"sebelum": [], "sesudah_em": [], "oracle_prior": []}
        for seed in C.SEEDS:
            tr, va = train_test_split(np.arange(len(ysrc)), test_size=0.2,
                                      random_state=seed, stratify=ysrc)
            m = step03.make_model(seed)
            m.fit(Xsrc.iloc[tr], ysrc[tr])
            if has_cal:
                cal = CalibratedClassifierCV(FrozenEstimator(m), method="isotonic")
                cal.fit(Xsrc.iloc[va], ysrc[va])
                model = cal
            else:
                model = m
            classes = model.classes_
            p = model.predict_proba(Xtgt)
            p = np.clip(p, 1e-12, 1)
            pi_s = np.array([(ysrc[tr] == c).mean() for c in classes])
            pi_s = np.clip(pi_s, 1e-12, 1)
            # sebelum
            res["sebelum"].append(_metrics(ytgt, classes[p.argmax(1)], classes_all))
            # EM Saerens
            pi_t = pi_s.copy()
            for _ in range(200):
                q = p * (pi_t / pi_s)
                q /= q.sum(1, keepdims=True)
                pi_new = q.mean(0)
                if np.abs(pi_new - pi_t).max() < 1e-8:
                    pi_t = pi_new
                    break
                pi_t = pi_new
            q = p * (pi_t / pi_s)
            q /= q.sum(1, keepdims=True)
            res["sesudah_em"].append(_metrics(ytgt, classes[q.argmax(1)], classes_all))
            # oracle: prior target sebenarnya
            pi_true = np.array([(ytgt == c).mean() for c in classes])
            qo = p * (np.clip(pi_true, 1e-12, 1) / pi_s)
            qo /= qo.sum(1, keepdims=True)
            res["oracle_prior"].append(_metrics(ytgt, classes[qo.argmax(1)], classes_all))
            C.log(f"c3.5 {tr_name}->{te_name} seed={seed} "
                  f"f1 pre={res['sebelum'][-1][0]} em={res['sesudah_em'][-1][0]} "
                  f"oracle={res['oracle_prior'][-1][0]}")
        def agg(rows):
            a = np.array(rows, dtype=float)
            return {"macro_f1": round(float(a[:, 0].mean()), 4),
                    "recall_UDPFlood": round(float(a[:, 1].mean()), 4),
                    "recall_Benign": round(float(a[:, 2].mean()), 4),
                    "macro_f1_sd": round(float(a[:, 0].std(ddof=1)), 4)}
        out["directions"][f"{tr_name}->{te_name}"] = {k: agg(v) for k, v in res.items()}
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c3_task5.json", out)
    C.log("c3.5 done")


def task6():
    t0 = time.time()
    d = load_raw()
    feats_all = combined_feats()
    sets = {"semua_fitur": feats_all,
            "tanpa_identitas": [c for c in feats_all if c not in ID_COLS]}
    sides = {}
    for bs in ["BS1", "BS2"]:
        dd = d.loc[d["__bs"] == bs]
        i = np.sort(C.stratified_cap(dd["__y"].to_numpy(), C.MODEL_CAP, seed=0))
        sides[bs] = dd.iloc[i].reset_index(drop=True)
    out = {"directions": {}}
    for tr_name in ["BS1", "BS2"]:
        te_name = "BS2" if tr_name == "BS1" else "BS1"
        for set_name, cols in sets.items():
            raw = pd.concat([sides[tr_name][cols], sides[te_name][cols]], ignore_index=True)
            X = C.encode_features(raw, cols)
            X = X[[c for c in X.columns if X[c].nunique(dropna=True) >= 2]]
            yb_tr = (sides[tr_name]["Label"].astype(str) != "Benign").astype(int).to_numpy()
            yb_te = (sides[te_name]["Label"].astype(str) != "Benign").astype(int).to_numpy()
            ntr = len(yb_tr)
            tprs, fprs = [], []
            for seed in C.SEEDS:
                m = step03.make_model(seed)
                m.fit(X.iloc[:ntr], yb_tr)
                pred = m.predict(X.iloc[ntr:])
                tpr = float(pred[yb_te == 1].mean())
                fpr = float(pred[yb_te == 0].mean())
                tprs.append(round(tpr, 4))
                fprs.append(round(fpr, 4))
                C.log(f"c3.6 {tr_name}->{te_name} {set_name} seed={seed} TPR={tpr:.4f} FPR={fpr:.4f}")
            out["directions"][f"{tr_name}->{te_name}|{set_name}"] = {
                "TPR_seeds": tprs, "TPR_mean": round(float(np.mean(tprs)), 4),
                "FPR_seeds": fprs, "FPR_mean": round(float(np.mean(fprs)), 4),
            }
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c3_task6.json", out)
    C.log("c3.6 done")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    tasks = {"1": task1, "2": task2, "3": task3, "4": task4, "5": task5, "6": task6}
    for k in (list("123456") if which == "all" else [which]):
        tasks[k]()
