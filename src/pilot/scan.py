"""Pilot Scan - kualitas label 4 dataset IDS (CPU saja, mandiri, tidak menyentuh pilot_ids/).
python scan.py [ds ...]   (default: unsw cictoniot cse ciciot)
SCAN_LIMIT=50000 python scan.py  -> uji asap (baris per berkas dibatasi, hasil ke results_smoke/)

Metode: vektor fitur (tanpa kolom identitas) di-hash uint64 (pd.util.hash_pandas_object,
numerik dikanonikalkan float32, -0 -> +0, nominal str). Pass A: hash + label + meta seluruh
baris -> duplikat, konflik label, batas atas Bayes, pasangan kelas. Pass B: contoh vektor
konflik + sampel 200k utk model satu-fitur (DecisionTree max_depth=3).
Peringatan tabrakan hash: ~N^2/2^65 -> ~0,06 tabrakan terduga pada 46,7 jt baris (diabaikan)."""
import glob
import itertools
import json
import os
import sys
import time

NTHREAD = max(1, (os.cpu_count() or 4) - 3)
os.environ.setdefault("OMP_NUM_THREADS", str(NTHREAD))

import numpy as np
import pandas as pd

try:
    import pyarrow as pa
    pa.set_cpu_count(NTHREAD)
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = r"<DATA_ROOT>\data"
TON = r"<DATA_ROOT>\proj\data\cictoniot\CIC-ToN-IoT-V2.parquet"
LIMIT = int(os.environ.get("SCAN_LIMIT", "0"))
RES = os.path.join(HERE, "results_smoke" if LIMIT else "results")
SAMPLE_N, SEED, CHUNK = 200_000, 0, 1_000_000
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:7.0f}s]", *a, flush=True)


def jenc(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def canon(df):
    """Kanonikalisasi utk hashing/pemodelan: numerik float32 (-0 -> +0), nominal str."""
    out = {}
    for c in df.columns:
        s = df[c]
        if s.dtype.kind in "fiub":
            a = s.to_numpy(np.float32, copy=True)
            a[a == 0] = 0.0
            out[c] = a
        else:
            out[c] = s.astype(str).to_numpy()
    return pd.DataFrame(out)


def encode(s, cat):
    for v in pd.unique(s):
        if v not in cat:
            cat[v] = len(cat)
    return s.map(cat).to_numpy(np.uint32)


def merge_extra(dst, src):
    for k, v in src.items():
        if isinstance(v, dict):
            d = dst.setdefault(k, {})
            for kk, vv in v.items():
                d[kk] = d.get(kk, 0) + vv
        else:
            dst[k] = dst.get(k, 0) + v


# ---------------- generator per dataset ----------------
UNSW_NAMES = ["srcip", "sport", "dstip", "dsport", "proto", "state", "dur", "sbytes",
              "dbytes", "sttl", "dttl", "sloss", "dloss", "service", "Sload", "Dload",
              "Spkts", "Dpkts", "swin", "dwin", "stcpb", "dtcpb", "smeansz", "dmeansz",
              "trans_depth", "res_bdy_len", "Sjit", "Djit", "Stime", "Ltime", "Sintpkt",
              "Dintpkt", "tcprtt", "synack", "ackdat", "is_sm_ips_ports", "ct_state_ttl",
              "ct_flw_http_mthd", "is_ftp_login", "ct_ftp_cmd", "ct_srv_src", "ct_srv_dst",
              "ct_dst_ltm", "ct_src_ltm", "ct_src_dport_ltm", "ct_dst_sport_ltm",
              "ct_dst_src_ltm", "attack_cat", "Label"]
UNSW_ID = ["srcip", "sport", "dstip", "dsport", "Stime", "Ltime", "stcpb", "dtcpb"]
UNSW_NOM = ["proto", "state", "service"]


def port_num(s):
    v = pd.to_numeric(s, errors="coerce").copy()
    m = v.isna() & s.str.startswith("0x", na=False)
    if m.any():
        v[m] = s[m].map(lambda x: int(x, 16))
    return v.astype(np.float64)


def gen_unsw():
    fs = sorted(glob.glob(os.path.join(DATA, "UNSWNB15", "UNSW-NB15_[1-4].csv")))
    assert len(fs) == 4, fs
    fcols = [c for c in UNSW_NAMES if c not in UNSW_ID + ["attack_cat", "Label"]]
    fnum = [c for c in fcols if c not in UNSW_NOM]
    for f in fs:
        d = pd.read_csv(f, header=None, names=UNSW_NAMES, dtype=str,
                        keep_default_na=False, na_values=[""], low_memory=False,
                        nrows=LIMIT or None)
        extra = {"attack_cat_mentah": d["attack_cat"].fillna("<KOSONG>").value_counts().to_dict()}
        y = d["attack_cat"].str.strip()
        y = y.where(y.notna() & (y != ""), "Normal").to_numpy(dtype=object)
        y = np.asarray(y, dtype=str)
        binlab = pd.to_numeric(d["Label"], errors="coerce").fillna(-1).to_numpy(np.int64)
        extra["biner_vs_kelas_mismatch"] = int(((binlab == 1) != (y != "Normal")).sum())
        F, ncoerce = {}, {}
        for c in fnum:
            v = pd.to_numeric(d[c], errors="coerce")
            nc = int((v.isna() & d[c].notna()).sum())
            if nc:
                ncoerce[c] = nc
            F[c] = v.astype(np.float32)
        for c in UNSW_NOM:
            F[c] = d[c].fillna("?")
        extra["nilai_nonnumerik_jadi_nan"] = ncoerce
        F = pd.DataFrame(F)[fcols]
        ID = pd.DataFrame({
            "srcip": d["srcip"].fillna("?"), "sport": port_num(d["sport"]),
            "dstip": d["dstip"].fillna("?"), "dsport": port_num(d["dsport"]),
            "Stime": pd.to_numeric(d["Stime"], errors="coerce"),
            "Ltime": pd.to_numeric(d["Ltime"], errors="coerce"),
            "stcpb": pd.to_numeric(d["stcpb"], errors="coerce"),
            "dtcpb": pd.to_numeric(d["dtcpb"], errors="coerce"),
            "Label_biner": binlab.astype(np.float64)})
        day = pd.to_datetime(ID["Stime"], unit="s").dt.strftime("%Y-%m-%d").to_numpy()
        meta = {"file": os.path.basename(f), "day": day,
                "srcip": d["srcip"].fillna("?").to_numpy()}
        yield dict(F=F, y=y, ID=ID, meta=meta, extra=extra)


def gen_ciciot():
    fs = sorted(glob.glob(os.path.join(DATA, "CICIoT2023", "MERGED_CSV", "*.csv")))
    assert fs
    hdr = pd.read_csv(fs[0], nrows=0).columns.tolist()
    dt = {c: np.float32 for c in hdr if c != "Label"}
    for f in fs:
        d = pd.read_csv(f, dtype=dt, nrows=LIMIT or None)
        ok = d["Label"].notna()
        extra = {"label_nan_dibuang": int((~ok).sum())}
        d = d[ok]
        y = np.asarray(d.pop("Label").astype(str), dtype=str)
        yield dict(F=d, y=y, ID=None, meta={"file": os.path.basename(f)}, extra=extra)


def gen_cse():
    fs = sorted(glob.glob(os.path.join(DATA, "CSECICIDS2018", "*.parquet")))
    assert fs
    for f in fs:
        d = pd.read_parquet(f)
        if LIMIT:
            d = d.head(LIMIT)
        ok = d["Label"].notna()
        extra = {"label_nan_dibuang": int((~ok).sum())}
        d = d[ok]
        y = np.asarray(d.pop("Label").astype(str), dtype=str)
        nm = os.path.basename(f).split("_")[0]
        yield dict(F=d, y=y, ID=None, meta={"file": nm}, extra=extra)


def gen_ton():
    d = pd.read_parquet(TON)
    if LIMIT:
        d = d.head(LIMIT)
    ok = d["Attack"].notna()
    extra = {"label_nan_dibuang": int((~ok).sum())}
    d = d[ok]
    y = np.asarray(d.pop("Attack").astype(str), dtype=str)
    binlab = pd.to_numeric(d["Label"], errors="coerce").to_numpy(np.float64)
    extra["biner_vs_kelas_mismatch"] = int(((binlab == 1) != (y != "Benign")).sum())
    d = d.drop(columns=["Label"])
    ID = pd.DataFrame({"Label_biner": binlab}, index=d.index)
    for s in range(0, len(d), CHUNK * 2):
        sl = slice(s, s + CHUNK * 2)
        yield dict(F=d.iloc[sl], y=y[sl], ID=ID.iloc[sl],
                   meta={"file": "CIC-ToN-IoT-V2.parquet"},
                   extra=extra if s == 0 else {})


CONFIG = {
    "unsw": (gen_unsw, "UNSW-NB15 (4 CSV penuh)"),
    "ciciot": (gen_ciciot, "CICIoT2023 (MERGED_CSV)"),
    "cse": (gen_cse, "CSE-CIC-IDS2018 (parquet TrafficForML)"),
    "cictoniot": (gen_ton, "CIC-ToN-IoT-V2 (parquet)"),
}
BENIGN = {"benign", "benigntraffic", "normal"}


# ---------------- pass A ----------------
def pass_a(make_gen):
    cat_y, cats, extra, info = {}, {}, {}, {}
    H_l, y_l, m_l = [], [], {}
    for ch in make_gen():
        F = canon(ch["F"])
        if not info:
            info["fitur"] = list(F.columns)
            info["nominal"] = [c for c in F.columns if F[c].dtype == object]
            info["identitas"] = list(ch["ID"].columns) if ch["ID"] is not None else []
        h = pd.util.hash_pandas_object(F, index=False).to_numpy(np.uint64)
        H_l.append(h)
        y_l.append(encode(pd.Series(ch["y"]), cat_y))
        for name in ("file", "day", "srcip"):
            if name in ch["meta"]:
                v = ch["meta"][name]
                cat = cats.setdefault(name, {})
                if isinstance(v, str):
                    if v not in cat:
                        cat[v] = len(cat)
                    arr = np.full(len(h), cat[v], np.uint32)
                else:
                    arr = encode(pd.Series(v), cat)
                m_l.setdefault(name, []).append(arr)
        merge_extra(extra, ch.get("extra", {}))
        log(f"  pass A: +{len(h)} baris (kum {sum(map(len, H_l))})")
    H = np.concatenate(H_l)
    yc = np.concatenate(y_l).astype(np.int64)
    metas = {k: np.concatenate(v) for k, v in m_l.items()}
    return H, yc, metas, cat_y, cats, extra, info


# ---------------- statistik vektor ----------------
def stats(H, yc, names, metas, cats):
    C, N = len(names), len(H)
    lex = np.lexsort((yc, H))
    Hp, yp = H[lex], yc[lex]
    del lex
    newpair = np.empty(len(Hp), bool)
    newpair[0] = True
    np.logical_or(Hp[1:] != Hp[:-1], yp[1:] != yp[:-1], out=newpair[1:])
    pid = np.cumsum(newpair) - 1
    pair_h, pair_y = Hp[newpair], yp[newpair]
    pair_cnt = np.bincount(pid).astype(np.int64)
    del Hp, yp, pid
    newvec = np.empty(len(pair_h), bool)
    newvec[0] = True
    newvec[1:] = pair_h[1:] != pair_h[:-1]
    vid = np.cumsum(newvec) - 1
    nvec = int(vid[-1]) + 1
    nlab = np.bincount(vid)
    vrows = np.bincount(vid, weights=pair_cnt).astype(np.int64)
    vstart = np.flatnonzero(newvec)
    vhash = pair_h[vstart]
    maj_cnt = np.maximum.reduceat(pair_cnt, vstart)
    o2 = np.lexsort((pair_y, pair_cnt, vid))
    maj_idx = o2[np.cumsum(nlab) - 1]
    assert np.array_equal(pair_cnt[maj_idx], maj_cnt)
    maj_y = pair_y[maj_idx]
    del o2
    acc = float(maj_cnt.sum() / N)
    conf = np.bincount(pair_y * C + maj_y[vid], weights=pair_cnt,
                       minlength=C * C).reshape(C, C)
    tp = np.diag(conf)
    fp, fn = conf.sum(0) - tp, conf.sum(1) - tp
    f1c = np.where(2 * tp + fp + fn > 0, 2 * tp / np.maximum(2 * tp + fp + fn, 1), 0.0)
    mf1 = float(f1c.mean())
    confl = nlab >= 2
    rows_confl = int(vrows[confl].sum())

    # pasangan kelas: vektor 2-label (vektorisasi) + vektor >=3 label (loop, jarang)
    pv = np.zeros(C * C, np.int64)
    pr = np.zeros(C * C, np.int64)
    two = np.flatnonzero(nlab == 2)
    s2 = vstart[two]
    k2 = r2 = np.empty(0, np.int64)
    if len(two):
        a, b = pair_y[s2], pair_y[s2 + 1]
        r2 = pair_cnt[s2] + pair_cnt[s2 + 1]
        k2 = a * C + b
        pv += np.bincount(k2, minlength=C * C)
        pr += np.bincount(k2, weights=r2, minlength=C * C).astype(np.int64)
    multi = np.flatnonzero(nlab >= 3)
    for v in multi:
        s, e = vstart[v], vstart[v] + nlab[v]
        for i in range(s, e):
            for j in range(i + 1, e):
                k = pair_y[i] * C + pair_y[j]
                pv[k] += 1
                pr[k] += pair_cnt[i] + pair_cnt[j]
    order = np.argsort(-pr)
    top10 = [dict(kelas_a=names[k // C], kelas_b=names[k % C],
                  vektor=int(pv[k]), baris=int(pr[k]))
             for k in order[:10] if pr[k] > 0]

    # 3 pasangan terbesar -> 3 vektor konflik terbesar + sebaran meta per label
    sel_detail, sel_hashes = [], []
    for k in order[:3]:
        if pr[k] == 0:
            break
        ka, kb = int(k // C), int(k % C)
        cand = []
        if len(two):
            m2 = np.flatnonzero(k2 == k)
            if len(m2):
                t = m2[np.argsort(-r2[m2])[:3]]
                cand += [(int(r2[i]), int(two[i])) for i in t]
        for v in multi:
            s, e = vstart[v], vstart[v] + nlab[v]
            ys_ = pair_y[s:e]
            if (ys_ == ka).any() and (ys_ == kb).any():
                ra = int(pair_cnt[s:e][ys_ == ka][0])
                rb = int(pair_cnt[s:e][ys_ == kb][0])
                cand.append((ra + rb, int(v)))
        cand.sort(key=lambda t: -t[0])
        vecs = []
        for rows_, v in cand[:3]:
            s, e = vstart[v], vstart[v] + nlab[v]
            lab_rows = {names[int(pair_y[i])]: int(pair_cnt[i]) for i in range(s, e)}
            h = np.uint64(vhash[v])
            idx_rows = np.flatnonzero(H == h)
            dist = {}
            for mname, codes in metas.items():
                inv = {cv: ck for ck, cv in cats[mname].items()}
                dd = {}
                for lname, lcode in ((names[c], c) for c in np.unique(yc[idx_rows])):
                    bc = np.bincount(codes[idx_rows[yc[idx_rows] == lcode]])
                    tt = np.argsort(-bc)[:5]
                    dd[lname] = {str(inv[int(t)]): int(bc[t]) for t in tt if bc[t] > 0}
                dist[mname] = dd
            vecs.append(dict(hash=f"{int(h):016x}", baris_pasangan=rows_,
                             baris_vektor=int(vrows[v]), label_baris=lab_rows,
                             sebaran=dist))
            sel_hashes.append(int(h))
        sel_detail.append(dict(kelas_a=names[ka], kelas_b=names[kb], vektor=vecs))

    summary = dict(
        n_baris=N, n_vektor_unik=nvec,
        pct_baris_duplikat=round(100 * (N - nvec) / N, 4),
        n_vektor_konflik=int(confl.sum()),
        pct_baris_konflik_label=round(100 * rows_confl / N, 4),
        bayes_akurasi=round(acc, 6), bayes_macro_f1=round(mf1, 6),
        catatan_mayoritas="seri mayoritas dipecah deterministik (kode label terbesar)")
    return summary, top10, sel_detail, sel_hashes


# ---------------- pass B: contoh vektor + sampel task 5 ----------------
def pass_b(make_gen, N, sel_hashes):
    rng = np.random.default_rng(SEED)
    idx = np.sort(rng.choice(N, min(SAMPLE_N, N), replace=False))
    sel = np.array(sorted(set(sel_hashes)), dtype=np.uint64)
    off, exem = 0, {}
    Xf, Xi, Ys = [], [], []
    for ch in make_gen():
        F = canon(ch["F"])
        n = len(F)
        h = pd.util.hash_pandas_object(F, index=False).to_numpy(np.uint64)
        if len(sel) and len(exem) < len(sel):
            for ri in np.flatnonzero(np.isin(h, sel)):
                hv = int(h[ri])
                if hv not in exem:
                    exem[hv] = {k: (v if isinstance(v, str) else float(v))
                                for k, v in F.iloc[ri].items()}
        lo, hi = np.searchsorted(idx, off), np.searchsorted(idx, off + n)
        t = idx[lo:hi] - off
        if len(t):
            Xf.append(F.iloc[t])
            if ch["ID"] is not None:
                Xi.append(canon(ch["ID"]).iloc[t])
            Ys.append(np.asarray(ch["y"])[t])
        off += n
        log(f"  pass B: {off}/{N}, contoh {len(exem)}/{len(sel)}")
    Xf = pd.concat(Xf, ignore_index=True)
    Xi = pd.concat(Xi, ignore_index=True) if Xi else None
    return Xf, Xi, np.concatenate(Ys), exem


def task5(Xf, Xi, y, benign):
    from sklearn.metrics import f1_score, roc_auc_score
    from sklearn.tree import DecisionTreeClassifier
    X = pd.concat([Xf, Xi], axis=1) if Xi is not None else Xf
    jenis = {c: "fitur" for c in Xf.columns}
    if Xi is not None:
        for c in Xi.columns:
            jenis[c] = "bocoran-label" if c == "Label_biner" else "identitas"
    rng = np.random.default_rng(SEED + 1)
    per = rng.permutation(len(X))
    X = X.iloc[per].reset_index(drop=True)
    y = y[per]
    yb = (y != benign).astype(int) if benign else None
    ymc = pd.factorize(y)[0]
    half = len(X) // 2
    rows = []
    for c in X.columns:
        col = X[c]
        v = (pd.factorize(col)[0].astype(np.float64) if col.dtype == object
             else col.to_numpy(np.float64))
        v = np.where(np.isinf(v), np.sign(v) * np.finfo(np.float32).max, v).reshape(-1, 1)
        auc = f1 = None
        if yb is not None:
            try:
                dt = DecisionTreeClassifier(max_depth=3, random_state=0).fit(v[:half], yb[:half])
                cls = list(dt.classes_)
                p1 = (dt.predict_proba(v[half:])[:, cls.index(1)] if 1 in cls
                      else np.zeros(len(v) - half))
                auc = round(float(roc_auc_score(yb[half:], p1)), 4)
            except Exception as e:
                auc = f"GAGAL: {e}"
        try:
            dt = DecisionTreeClassifier(max_depth=3, random_state=0).fit(v[:half], ymc[:half])
            f1 = round(float(f1_score(ymc[half:], dt.predict(v[half:]),
                                      average="macro", zero_division=0)), 4)
        except Exception as e:
            f1 = f"GAGAL: {e}"
        rows.append(dict(kolom=c, jenis=jenis[c], auc_biner=auc, macro_f1_multikelas=f1))
    return rows


def scan(ds):
    make_gen, judul = CONFIG[ds]
    log(f"=== {ds}: {judul} ===")
    t0 = time.time()
    H, yc, metas, cat_y, cats, extra, info = pass_a(make_gen)
    t_a = time.time() - t0
    names = [None] * len(cat_y)
    for k, v in cat_y.items():
        names[v] = str(k)
    ben = [n for n in names if n.lower() in BENIGN]
    benign = ben[0] if len(ben) == 1 else None
    dist = np.bincount(yc, minlength=len(names))
    log(f"  {ds}: N={len(H)}, kelas={len(names)}, benign={benign}")
    t0 = time.time()
    summary, top10, sel_detail, sel_hashes = stats(H, yc, names, metas, cats)
    t_s = time.time() - t0
    log(f"  {ds}: stats selesai {t_s:.0f}s: {summary}")
    N = len(H)
    del H, yc, metas
    t0 = time.time()
    Xf, Xi, ys, exem = pass_b(make_gen, N, sel_hashes)
    t_b = time.time() - t0
    for pd_ in sel_detail:
        for vec in pd_["vektor"]:
            vec["contoh_fitur"] = exem.get(int(vec["hash"], 16), "TIDAK ADA")
    t0 = time.time()
    t5 = task5(Xf, Xi, ys, benign)
    t_5 = time.time() - t0
    out = dict(
        dataset=ds, judul=judul, uji_asap=bool(LIMIT),
        kolom=dict(fitur=info["fitur"], nominal=info["nominal"],
                   identitas_lokal=info["identitas"]),
        label_benign=benign if benign else "TIDAK TERDETEKSI",
        distribusi_label={names[i]: int(dist[i]) for i in np.argsort(-dist)},
        catatan_ekstra=extra, ringkasan=summary, pasangan_top10=top10,
        pasangan_top3_detail=sel_detail,
        model_satu_fitur=dict(n_sampel=len(Xf), latih=len(Xf) // 2,
                              uji=len(Xf) - len(Xf) // 2, hasil=t5),
        waktu_detik=dict(pass_a=round(t_a, 1), statistik=round(t_s, 1),
                         pass_b=round(t_b, 1), task5=round(t_5, 1)))
    os.makedirs(RES, exist_ok=True)
    json.dump(out, open(os.path.join(RES, ds + ".json"), "w"), indent=1, default=jenc)
    log(f"  {ds}: SELESAI -> {ds}.json")


def main():
    targets = sys.argv[1:] or ["unsw", "cictoniot", "cse", "ciciot"]
    for ds in targets:
        try:
            scan(ds)
        except Exception:
            import traceback
            traceback.print_exc()
            log(f"!! {ds} GAGAL")
    log("SCAN SELESAI")


if __name__ == "__main__":
    main()
