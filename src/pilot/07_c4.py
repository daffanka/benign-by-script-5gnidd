"""Pilot C4 — verifikasi salah-label 5G-NIDD dan uji versi terkoreksi.

1. Sebaran baris Benign-konflik per file capture + baris 'berbentuk flood'.
2. Profil peran IP (10.155.15.7 / 10.155.15.4 dan semua SrcAddr).
3. Pohon kedalaman 2 pada kolom mentah: aturan pemisah Benign-konflik vs UDPFlood.
4. Jalinan waktu per 10 detik di capture UDPFlood BS1 (korelasi).
5. Cek 'kembar': pasangan record identik dengan dua label.
6. Pola salah-label serupa di kelas serangan lain.
7. Versi terkoreksi: relabel lalu bandingkan Bayes/split acak/lintas-BS/biner.
"""
import importlib.util
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text

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

ID_COLS = c2.ID_COLS
LABELS = ["Label", "Attack Type", "Attack Tool"]
META = ["__bs", "__file", "__y"]
VICTIM = "10.41.150.68"


def load_raw_files():
    """Semua CSV per-BS dengan kolom __bs, __file, __y."""
    parts = []
    for bs in ["bs1", "bs2"]:
        base = os.path.join(C.CACHE, bs)
        for root, _, fs in os.walk(base):
            for f in sorted(fs):
                if not f.lower().endswith(".csv"):
                    continue
                p = pd.read_csv(os.path.join(root, f), low_memory=False)
                p.columns = [c.strip() for c in p.columns]
                p["__bs"] = bs.upper()
                p["__file"] = f
                parts.append(p)
    d = pd.concat(parts, ignore_index=True)
    d = d.loc[d["Attack Type"].notna()].reset_index(drop=True)
    d["__y"] = d["Attack Type"].astype(str)
    return d


def feats_sets():
    feats_all = c3.combined_feats()
    feats42 = [c for c in feats_all if c not in ID_COLS]
    return feats_all, feats42


def conflict_mask(d, feats42):
    h = pd.util.hash_pandas_object(d[feats42], index=False).to_numpy()
    y = d["__y"].to_numpy()
    df = pd.DataFrame({"h": h, "y": y})
    tab = df.groupby(["h", "y"], sort=False).size().unstack(fill_value=0)
    both = tab.index[(tab.get("Benign", 0) > 0) & (tab.get("UDPFlood", 0) > 0)]
    conf = np.isin(h, both)
    return h, conf, tab.loc[both]


def attacker_ips(d):
    udp = d.loc[d["__y"] == "UDPFlood"]
    att = udp["SrcAddr"].astype(str).value_counts(normalize=True)
    return set(att.index[att >= 0.01])


def flood_shape_mask(d):
    """udp, 1-2 paket, 42/84 byte, ke korban — apa pun labelnya."""
    return ((d["Proto"].astype(str) == "udp")
            & (pd.to_numeric(d["TotPkts"], errors="coerce").isin([1, 2]))
            & (pd.to_numeric(d["TotBytes"], errors="coerce").isin([42, 84]))
            & (d["DstAddr"].astype(str) == VICTIM)).to_numpy()


def task1(d, feats42):
    t0 = time.time()
    _, conf, _ = conflict_mask(d, feats42)
    ben_conf = conf & (d["__y"].to_numpy() == "Benign")
    shape = flood_shape_mask(d)
    out = {"n_benign_konflik": int(ben_conf.sum()), "per_file": {}}
    grp = d.groupby(["__bs", "__file"], sort=True)
    for (bs, f), idx in grp.indices.items():
        m_conf = ben_conf[idx]
        m_shape = shape[idx]
        yb = (d["__y"].to_numpy()[idx] == "Benign")
        out["per_file"][f"{bs}/{f}"] = {
            "rows": int(len(idx)),
            "benign_konflik": int(m_conf.sum()),
            "bentuk_flood_total": int(m_shape.sum()),
            "bentuk_flood_label_benign": int((m_shape & yb).sum()),
            "bentuk_flood_label_lain": int((m_shape & ~yb).sum()),
        }
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c4_task1.json", out)
    C.log(f"c4.1 done ({out['n_benign_konflik']} baris konflik disebar)")


def task2(d):
    t0 = time.time()
    web_ports = {"http", "https", "ssh", "sftp", "80", "443", "22", "115"}
    out = {"fokus": {}, "semua_srcaddr": {}}
    for ip in ["10.155.15.7", "10.155.15.4"]:
        per_bs = {}
        for bs in ["BS1", "BS2"]:
            dd = d.loc[(d["SrcAddr"].astype(str) == ip) & (d["__bs"] == bs)]
            nonudp_ben = dd.loc[(dd["__y"] == "Benign")
                                & (dd["Proto"].astype(str) != "udp")]
            per_bs[bs] = {
                "rows": int(len(dd)),
                "per_label": dd["__y"].value_counts().to_dict(),
                "per_proto": dd["Proto"].astype(str).value_counts().head(8).to_dict(),
                "benign_non_udp": int(len(nonudp_ben)),
                "benign_non_udp_dport_top":
                    nonudp_ben["Dport"].astype(str).value_counts().head(8).to_dict(),
                "benign_web_ssh": int(nonudp_ben["Dport"].astype(str)
                                      .str.lower().isin(web_ports).sum()),
            }
        out["fokus"][ip] = per_bs
    for ip, dd in d.groupby(d["SrcAddr"].astype(str)):
        out["semua_srcaddr"][ip] = {
            "rows": int(len(dd)),
            "per_label": dd["__y"].value_counts().to_dict(),
            "proto_top": dd["Proto"].astype(str).value_counts().head(5).to_dict(),
        }
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c4_task2.json", out)
    C.log("c4.2 done")


def task3(d, feats42):
    t0 = time.time()
    _, conf, _ = conflict_mask(d, feats42)
    y = d["__y"].to_numpy()
    ben_conf = conf & (y == "Benign")
    udp = y == "UDPFlood"
    sel = ben_conf | udp
    dd = d.loc[sel].copy()
    target = np.where(ben_conf[sel], "Benign-konflik", "UDPFlood")
    feats_all, _ = feats_sets()
    # kolom mentah yang DIBUANG dari Combined (minus counter record murni),
    # waktu diparse ke detik, lainnya kode kategori/numerik
    dropped = [c for c in d.columns
               if c not in feats_all + LABELS + META + ["Rank", "AutoId", "SrcId",
                                                        "Seq", "Offset"]]
    dd["StartTime_s"] = dd["StartTime"].map(c3.parse_mmss)
    dd["LastTime_s"] = dd["LastTime"].map(c3.parse_mmss)
    cols = [c for c in dropped if c not in ("StartTime", "LastTime")] + \
           ["StartTime_s", "LastTime_s"]
    X = C.encode_features(dd, cols)
    X = X[[c for c in X.columns if X[c].nunique(dropna=True) >= 2]]
    m = DecisionTreeClassifier(max_depth=2, random_state=0, class_weight="balanced")
    m.fit(X, target)
    pred = m.predict(X)
    leaf = m.apply(X)
    leaves = {}
    for lf in np.unique(leaf):
        msk = leaf == lf
        vc = pd.Series(target[msk]).value_counts()
        leaves[int(lf)] = {"n": int(msk.sum()),
                           "kelas": vc.index[0],
                           "kemurnian_pct": round(100 * float(vc.iloc[0] / msk.sum()), 2)}
    out = {
        "n_benign_konflik": int(ben_conf.sum()), "n_udpflood": int(udp.sum()),
        "n_fitur_kandidat": int(X.shape[1]),
        "aturan": export_text(m, feature_names=list(X.columns), decimals=4),
        "akurasi_train": round(float((pred == target).mean()), 4),
        "leaves": leaves,
        "catatan_encoding": "kolom kategorikal (mis. Flgs, Dir, Sport non-numerik) "
                            "jadi kode kategori integer; ambang pohon pada kolom "
                            "itu merujuk kode, bukan nilai asli",
        "runtime_s": round(time.time() - t0, 1),
    }
    C.save_json("c4_task3.json", out)
    C.log(f"c4.3 done acc={out['akurasi_train']}")


def task4(d, feats42):
    t0 = time.time()
    _, conf, _ = conflict_mask(d, feats42)
    sel = (d["__bs"] == "BS1").to_numpy() & (d["__file"] == "UDPFlood1.csv").to_numpy()
    dd = d.loc[sel]
    tsec = dd["StartTime"].map(c3.parse_mmss).to_numpy()
    yb = dd["__y"].to_numpy()
    confb = conf[sel] & (yb == "Benign")
    bins = (tsec // 10).astype(int)
    bu = pd.Series(bins[yb == "UDPFlood"]).value_counts().sort_index()
    bb = pd.Series(bins[confb]).value_counts().sort_index()
    allb = sorted(set(bu.index) | set(bb.index))
    a = np.array([bu.get(b, 0) for b in allb], dtype=float)
    b = np.array([bb.get(b, 0) for b in allb], dtype=float)
    r = float(np.corrcoef(a, b)[0, 1]) if len(allb) > 1 else np.nan
    out = {
        "file": "BS1/UDPFlood1.csv", "rows": int(len(dd)),
        "n_udpflood": int((yb == "UDPFlood").sum()),
        "n_benign_konflik_di_file": int(confb.sum()),
        "n_bin_10s": len(allb),
        "pearson_r": round(r, 4),
        "contoh_bin_pertama_10": {str(k): [int(bu.get(k, 0)), int(bb.get(k, 0))]
                                  for k in allb[:10]},
        "runtime_s": round(time.time() - t0, 1),
    }
    C.save_json("c4_task4.json", out)
    C.log(f"c4.4 done r={r:.4f}")


def task5(d, feats42):
    t0 = time.time()
    h, conf, tab = conflict_mask(d, feats42)
    eq = tab.index[(tab["Benign"] == tab["UDPFlood"])]
    sel = np.isin(h, eq)
    dd = d.loc[sel, ["SrcAddr", "DstAddr", "Sport", "StartTime", "__y"]].copy()
    dd["h"] = h[sel]
    ben = dd.loc[dd["__y"] == "Benign"]
    udp = dd.loc[dd["__y"] == "UDPFlood"]
    key = ["h", "StartTime", "Sport", "SrcAddr", "DstAddr"]
    merged = ben.merge(udp[key].drop_duplicates(), on=key, how="left", indicator=True)
    pct = 100 * float((merged["_merge"] == "both").mean()) if len(merged) else np.nan
    out = {
        "n_vektor_seimbang": int(len(eq)),
        "n_baris_benign_vektor_seimbang": int(len(ben)),
        "pct_benign_punya_kembar_identik": round(pct, 2),
        "kunci_kembar": key[1:],
        "runtime_s": round(time.time() - t0, 1),
    }
    C.save_json("c4_task5.json", out)
    C.log(f"c4.5 done kembar%={pct:.2f}")


def task6(d):
    t0 = time.time()
    out = {"per_file": {}, "definisi": "baris Benign dalam file capture serangan "
           "dengan SrcAddr∈IP penyerang (≥1% baris serangan), DstAddr∈IP korban "
           "(≥1%), dan Proto = proto modal serangan"}
    for (bs, f), idx in d.groupby(["__bs", "__file"], sort=True).indices.items():
        dd = d.iloc[idx]
        atk = dd.loc[dd["__y"] != "Benign"]
        if len(atk) == 0:
            continue
        lab = atk["__y"].mode().iloc[0]
        att = atk["SrcAddr"].astype(str).value_counts(normalize=True)
        vic = atk["DstAddr"].astype(str).value_counts(normalize=True)
        att_ips = set(att.index[att >= 0.01])
        vic_ips = set(vic.index[vic >= 0.01])
        proto = atk["Proto"].astype(str).mode().iloc[0]
        ben = dd.loc[dd["__y"] == "Benign"]
        sus = ben.loc[ben["SrcAddr"].astype(str).isin(att_ips)
                      & ben["DstAddr"].astype(str).isin(vic_ips)
                      & (ben["Proto"].astype(str) == proto)]
        out["per_file"][f"{bs}/{f}"] = {
            "label_serangan": lab, "proto_serangan": proto,
            "n_serangan": int(len(atk)), "n_benign_file": int(len(ben)),
            "n_benign_mencurigakan": int(len(sus)),
            "pct_benign_mencurigakan": round(100 * len(sus) / max(len(ben), 1), 2),
        }
    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c4_task6.json", out)
    C.log("c4.6 done")


def _bayes(h, y):
    g = pd.DataFrame({"h": h, "y": y})
    counts = g.groupby(["h", "y"], sort=False).size().rename("n").reset_index()
    maj = counts.sort_values("n", ascending=False).drop_duplicates("h")
    pred = g.merge(maj[["h", "y"]].rename(columns={"y": "pred"}), on="h", how="left")["pred"].to_numpy()
    return (round(float((pred == y).mean()), 4),
            round(float(f1_score(y, pred, average="macro", zero_division=0)), 4))


def _fit_f1(X, ytr, yte, tr, te, seed, classes):
    m = step03.make_model(seed)
    Xtr = X.iloc[tr]
    cols = [c for c in X.columns if Xtr[c].nunique(dropna=True) >= 2]
    m.fit(Xtr[cols], ytr)
    pred = m.predict(X.iloc[te][cols])
    f1 = f1_score(yte, pred, average="macro", labels=classes, zero_division=0)
    rec = dict(zip(classes, recall_score(yte, pred, average=None,
                                         labels=classes, zero_division=0)))
    return round(float(f1), 4), rec, pred


def task7(d, feats42):
    t0 = time.time()
    att_ips = attacker_ips(d)
    y_orig = d["__y"].to_numpy()
    rule = ((d["SrcAddr"].astype(str).isin(att_ips))
            & (d["DstAddr"].astype(str) == VICTIM)
            & (d["Proto"].astype(str) == "udp")
            & d["__file"].str.startswith("UDPFlood")
            & (y_orig == "Benign")).to_numpy()
    y_corr = y_orig.copy()
    y_corr[rule] = "UDPFlood"
    out = {"aturan": "Benign & SrcAddr∈{penyerang UDPFlood} & DstAddr=korban & "
                     "Proto=udp & file capture UDPFlood",
           "ip_penyerang": sorted(att_ips), "ip_korban": VICTIM,
           "n_diubah": int(rule.sum()),
           "pct_dari_semua_baris": round(100 * float(rule.mean()), 2),
           "pct_dari_benign": round(100 * rule.sum() / int((y_orig == "Benign").sum()), 2)}

    # --- Bayes 42 fitur non-ID, sebelum vs sesudah ---
    h42 = pd.util.hash_pandas_object(d[feats42], index=False).to_numpy()
    out["bayes_42_nonid"] = {"sebelum": _bayes(h42, y_orig),
                            "sesudah": _bayes(h42, y_corr),
                            "format": "(akurasi, macro_f1)"}
    C.log(f"c4.7 bayes {out['bayes_42_nonid']}")

    feats_all, _ = feats_sets()
    feats90 = [c for c in d.columns if c not in LABELS + c3.RAW_ID_EXCL + META]
    classes = np.unique(np.concatenate([y_orig, y_corr]))

    # --- split acak tanpa ID (sampel tetap: stratified pada y_orig) ---
    idx = np.sort(C.stratified_cap(y_orig, C.MODEL_CAP, seed=0))
    Xr = C.encode_features(d.iloc[idx], feats42)
    res_rand = {}
    for tag, yv in [("sebelum", y_orig[idx]), ("sesudah", y_corr[idx])]:
        f1s = []
        for seed in C.SEEDS:
            tr, te = train_test_split(np.arange(len(idx)), test_size=0.3,
                                      random_state=seed, stratify=y_orig[idx])
            f1, _, _ = _fit_f1(Xr, yv[tr], yv[te], tr, te, seed, classes)
            f1s.append(f1)
            C.log(f"c4.7 acak42 {tag} seed={seed} f1={f1}")
        res_rand[tag] = {"mean": round(float(np.mean(f1s)), 4), "seeds": f1s}
    out["acak_tanpa_id"] = res_rand

    # --- lintas-BS: 42 fitur dan 90 fitur mentah non-ID ---
    sides_idx = {}
    for bs in ["BS1", "BS2"]:
        m = (d["__bs"] == bs).to_numpy()
        pos = np.flatnonzero(m)
        i = C.stratified_cap(y_orig[pos], C.MODEL_CAP, seed=0)
        sides_idx[bs] = pos[np.sort(i)]
    out["lintas_bs"] = {}
    for fname, feats in [("42_nonid", feats42), ("90_mentah_nonid", feats90)]:
        for tr_name in ["BS1", "BS2"]:
            te_name = "BS2" if tr_name == "BS1" else "BS1"
            itr, ite = sides_idx[tr_name], sides_idx[te_name]
            raw = pd.concat([d.iloc[itr][feats], d.iloc[ite][feats]], ignore_index=True)
            X = C.encode_features(raw, feats)
            tr = np.arange(len(itr))
            te = np.arange(len(itr), len(itr) + len(ite))
            entry = {}
            for tag, yv in [("sebelum", y_orig), ("sesudah", y_corr)]:
                f1s, recU, recB = [], [], []
                for seed in C.SEEDS:
                    f1, rec, _ = _fit_f1(X, yv[itr], yv[ite], tr, te, seed, classes)
                    f1s.append(f1)
                    recU.append(float(rec.get("UDPFlood", np.nan)))
                    recB.append(float(rec.get("Benign", np.nan)))
                    C.log(f"c4.7 {fname} {tr_name}->{te_name} {tag} seed={seed} f1={f1}")
                entry[tag] = {"macro_f1": round(float(np.mean(f1s)), 4),
                              "recall_UDPFlood": round(float(np.mean(recU)), 4),
                              "recall_Benign": round(float(np.mean(recB)), 4)}
            out["lintas_bs"][f"{fname}|{tr_name}->{te_name}"] = entry

    # --- biner lintas-BS TPR/FPR ---
    out["biner_lintas_bs"] = {}
    yb_orig = (y_orig != "Benign").astype(int)
    yb_corr = (y_corr != "Benign").astype(int)
    for fname, feats in [("semua_fitur", feats_all), ("tanpa_identitas", feats42)]:
        for tr_name in ["BS1", "BS2"]:
            te_name = "BS2" if tr_name == "BS1" else "BS1"
            itr, ite = sides_idx[tr_name], sides_idx[te_name]
            raw = pd.concat([d.iloc[itr][feats], d.iloc[ite][feats]], ignore_index=True)
            X = C.encode_features(raw, feats)
            tr = np.arange(len(itr))
            te = np.arange(len(itr), len(itr) + len(ite))
            entry = {}
            for tag, yb in [("sebelum", yb_orig), ("sesudah", yb_corr)]:
                tprs, fprs = [], []
                for seed in C.SEEDS:
                    m = step03.make_model(seed)
                    Xtr = X.iloc[tr]
                    cols = [c for c in X.columns if Xtr[c].nunique(dropna=True) >= 2]
                    m.fit(Xtr[cols], yb[itr])
                    pred = m.predict(X.iloc[te][cols])
                    yt = yb[ite]
                    tprs.append(float(pred[yt == 1].mean()))
                    fprs.append(float(pred[yt == 0].mean()))
                entry[tag] = {"TPR": round(float(np.mean(tprs)), 4),
                              "FPR": round(float(np.mean(fprs)), 4)}
                C.log(f"c4.7 biner {fname} {tr_name}->{te_name} {tag} "
                      f"TPR={entry[tag]['TPR']} FPR={entry[tag]['FPR']}")
            out["biner_lintas_bs"][f"{fname}|{tr_name}->{te_name}"] = entry

    out["runtime_s"] = round(time.time() - t0, 1)
    C.save_json("c4_task7.json", out)
    C.log("c4.7 done")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    C.log("c4: loading raw per-BS files")
    d = load_raw_files()
    _, feats42 = feats_sets()
    tasks = {"1": lambda: task1(d, feats42), "2": lambda: task2(d),
             "3": lambda: task3(d, feats42), "4": lambda: task4(d, feats42),
             "5": lambda: task5(d, feats42), "6": lambda: task6(d),
             "7": lambda: task7(d, feats42)}
    for k in (list("1234567") if which == "all" else [which]):
        tasks[k]()
