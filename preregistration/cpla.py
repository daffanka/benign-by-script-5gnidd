"""Pilot D (CPLA) — apakah audit lintas-partisi + koreksi menang pada pemulihan tugas
hilir di bawah noise label BERBLOK? CPU saja, mandiri (tidak menulis ke folder lain).

=============================== ATURAN DIKUNCI =================================
Dokumen ini ditulis dan di-hash SEBELUM run; tidak ada baris di bawah yang diubah
setelah hasil korektor pertama kali dilihat (hash: results/SCRIPT.sha256).

A. DATA (kebenaran dasar = label asli dataset bersih; hanya baris yang KITA suntik
   yang dianggap salah-label)
   ds=cse     CSE-CIC-IDS2018 (10 parquet TrafficForML; label Benign = "Benign")
              partisi audit = berkas (= hari capture, 10).
              sumbu "sumber" = PROKSI sidik-jari tumpukan: string gabungan
              (Protocol, Init Fwd Win Bytes, Init Bwd Win Bytes, Fwd Seg Size Min).
              split evaluasi = urutan baris tersimpan dalam setiap berkas:
              70% pertama -> train, 30% terakhir -> test. (Parquet pra-proses tidak
              punya IP/Timestamp, dan setiap kelas serangan hanya ada di SATU berkas,
              jadi split antar-berkas akan menghapus kelas dari train.)
              fitur = 77 kolom selain Label.
   ds=unsw    UNSW-NB15 (4 CSV penuh, 49 kolom; label Benign = "Normal")
              partisi audit = berkas; train = berkas 1,2,3; test = berkas 4.
              sumbu sumber = srcip (asli). fitur = 39 kolom (49 - 8 identitas
              [srcip,sport,dstip,dsport,Stime,Ltime,stcpb,dtcpb] - attack_cat - Label).
              attack_cat kosong -> "Normal"; "Backdoors" disatukan ke "Backdoor".
   ds=g5c     5G-NIDD versi C (study_5gnidd_audit/cache/full.parquet, __keepC;
              hanya DIBACA). label Benign = "Benign".
              partisi audit = __file; sumbu sumber = SrcAddr;
              train = BS1, test = BS2 (split antar-partisi sejati). fitur = feats42.
   Subsampel: kuota per berkas (train N_TRAIN/|berkas train|, test N_TEST/|berkas test|),
   di dalam berkas kuota ditutup per kelas (cap dicari biner), acak seed 0 — SAMA untuk
   semua skenario/seed agar sel sebanding. Nominal -> kode kategori dari peta yang
   dibangun di train (nilai tak dikenal di test -> -1); numerik float32, inf -> NaN.

B. REZIM NOISE (hanya menyentuh train; test selalu label asli)
   ukuran blok = {1%, 3%, 8%} dari baris train (dibulatkan); ukuran tercapai dicatat.
   R1 "terpisah-fitur": blok = satu grup (partisi x kelas!=Benign x sumber) ->
      labelnya diubah menjadi Benign. Grup layak = n>=30; seed s memilih grup
      PERINGKAT ke-(s+1) menurut n di antara grup dengan n >= target (jika kurang dari
      s+1 grup layak: pakai grup terbesar yang ada, ukuran tercapai dicatat).
      Di dalam grup, baris dipilih acak (seed) sampai target.
   R2 "ambigu": pasangan kelas (a,b) = pasangan dengan MASSA KONFLIK terbesar, yaitu
      sum atas vektor fitur identik (hash uint64 dari fitur yang dikanonikalkan)
      yang memuat >1 label: min(count_a, count_b). Jika massa konflik total = 0,
      pasangan diambil dari kebingungan OOF lintas-partisi pada label BERSIH
      (C[a,b]+C[b,a] terbesar); aturan mana yang dipakai dicatat.
      Blok = baris kelas a dan b di SATU partisi (bukan satu sumber), dipilih acak
      (seed), porsi a:b sebanding ketersediaan, lalu label DITUKAR (a->b, b->a).
      Seed s memilih partisi peringkat ke-(s+1) menurut jumlah baris pasangan itu.
   R0 "kontrol": tidak ada suntikan (semua korektor dijalankan apa adanya).

C. KOREKTOR (semua hanya melihat fitur + label tercemar pada TRAIN, lalu
   membuang/merelabel baris; model hilir lalu dilatih ulang pada data terkoreksi)
   noop        tanpa koreksi.
   cl          cleanlab 2.9.0 find_label_issues(filter_by="prune_by_noise_rate")
               atas probabilitas OOF GLOBAL; baris bermasalah dibuang.
               (Bila cleanlab tidak ada: confident-joint sendiri — dicatat.)
   cl_xp       sama, tetapi atas probabilitas OOF LINTAS-PARTISI (kontrol kebugaran:
               agar kemenangan CPLA tidak sekadar efek sumber probabilitas).
   oof         buang baris dengan label != prediksi OOF GLOBAL.
   oof_xp      buang baris dengan label != prediksi OOF LINTAS-PARTISI.
   cpla        audit lintas-partisi + agregasi blok + buang blok (rinci di D).
   oracle_drop buang tepat baris tersuntik (acuan atas untuk korektor "buang").
   oracle_fix  pulihkan label asli baris tersuntik (acuan atas mutlak).
   OOF GLOBAL = StratifiedKFold(5, shuffle, seed) mengabaikan partisi.
   OOF LINTAS-PARTISI = partisi dialokasikan utuh ke k=min(5,|partisi|) lipatan
   (greedy seimbang per jumlah baris, urutan diacak seed); jadi partisi suatu baris
   tidak pernah ikut melatih model yang memprediksinya.
   PENJAGA DUKUNGAN (v2, lihat catatan revisi di bawah): sebuah baris hanya boleh
   DITANDAI oleh korektor mana pun bila label yang diberikannya punya >= MIN_N baris
   di data latih lipatan yang memprediksinya. Bila tidak (model lipatan itu tak pernah
   melihat kelas tsb), ketidaksepakatan tidak informatif dan baris dibiarkan.
   Penjaga dipakai SERAGAM oleh cl, cl_xp, oof, oof_xp, dan cpla.
   Model (auditor dan hilir, identik): HistGradientBoostingClassifier(max_iter=100,
   learning_rate=0.1, max_bins=255, early_stopping=False, l2_regularization=0.1,
   random_state=seed) — setelan yang sama dengan E2 study_5gnidd_audit.

D. CPLA (parameter DIKUNCI: MIN_N=30, RATE_MIN=0.60, Z_MIN=5.0, BG_MAX=0.30)
   1. yhat = prediksi OOF LINTAS-PARTISI.
   0. hanya baris yang lolos PENJAGA DUKUNGAN ikut dihitung (lihat C).
   2. grup g = (partisi, sumber, label_diberikan) dengan n_g baris.
      blok b = (g, q) = baris di g yang diprediksi q != label_diberikan;
      rate_b = n_b / n_g.
   3. latar pasangan (label_diberikan -> q): kumpulan rate_b' dari semua grup g'
      dengan partisi BERBEDA, label_diberikan sama, n_g' >= MIN_N.
      med = median(latar), MAD = median(|latar - med|);
      z = (rate_b - med) / (1.4826*MAD + 0.01). Jika latar kosong: z = inf.
   4. Blok DIBUANG (seluruh grup g) bila n_b >= MIN_N dan rate_b >= RATE_MIN
      dan z >= Z_MIN dan med <= BG_MAX. (med > BG_MAX = pasangan yang memang
      ambigu di mana-mana -> tidak dibuang; penjaga ini melindungi dari rezim R2.)
   5. CPLA hanya membuang; tidak merelabel.

E. METRIK (model hilir dilatih pada train terkoreksi, dinilai pada TEST label asli)
   utama: macro-F1 (labels = seluruh kelas, zero_division=0) dan FPR biner
          (serangan = pred != Benign; FPR = FP/(FP+TN) pada baris test yang benar Benign).
   sekunder: F1 deteksi biner (positif = serangan), akurasi, TPR.
   diagnostik: presisi/recall deteksi noise tiap korektor terhadap baris tersuntik
          (flagged = dibuang ATAU label diubah), jumlah baris dibuang.
   fraksi pemulihan macro-F1 = (F1_X - F1_noop) / (F1_oracle_drop - F1_noop),
          dihitung hanya bila (F1_oracle_drop - F1_noop) >= 0.01.

F. GERBANG (dihitung atas sel = dataset x rezim x ukuran x seed; 3 dataset x 2 rezim
   x 3 ukuran x 3 seed = 54 sel tersuntik, plus 9 sel kontrol)
   G1 DOMINASI: median(macro-F1 CPLA - macro-F1 X) > 0 untuk SETIAP
      X in {noop, cl, cl_xp, oof, oof_xp}, DAN Wilcoxon signed-rank satu sisi
      (alternatif: CPLA lebih besar) p < 0.05 untuk setiap X.
   G2 PEMULIHAN: median fraksi pemulihan macro-F1 CPLA >= 0.50 atas sel yang
      memenuhi syarat (F1_oracle_drop - F1_noop >= 0.01).
   G3 TIDAK MERUSAK: pada 9 sel kontrol, median(macro-F1 CPLA - macro-F1 noop)
      >= -0.005 DAN median(FPR CPLA - FPR noop) <= +0.005.
   GERBANG UTAMA = G1 and G2 and G3. Sub-gerbang per rezim dilaporkan dengan aturan
   sama (G1/G2 atas 27 sel rezim itu; G3 dipakai bersama).
   FPR dilaporkan sebagai metrik utama kedua (arah: lebih kecil lebih baik) dengan
   median selisih + Wilcoxon, tetapi TIDAK masuk syarat gerbang.
G. REVISI MEKANIS v2 — JUJUR DICATAT
   Versi v1 (hash 185500799bb21ccf) dijalankan sebagai UJI ASAP (hasil tersimpan di
   results_smoke/, 12k baris, g5c, 1 seed, 1 ukuran). Uji asap itu membuka cacat
   MEKANIS, bukan preferensi skor: pada 5G-NIDD partisi = berkas dan tiap berkas
   praktis memuat satu kelas serangan, sehingga saat satu partisi dihold-out kelasnya
   HILANG dari data latih lipatan; akibatnya oof_xp/cl_xp/cpla membuang 35-37% data
   BERSIH (f1 kontrol 0,99 -> 0,16-0,56) semata karena model lipatan tak mengenal
   kelas itu. Perbaikan: PENJAGA DUKUNGAN di C, dipakai seragam oleh semua korektor.
   Angka uji asap v1 SUDAH TERLIHAT sebelum perbaikan ini; ambang CPLA (MIN_N,
   RATE_MIN, Z_MIN, BG_MAX), definisi rezim, metrik, dan GERBANG (F) TIDAK diubah.
=============================== AKHIR ATURAN ===================================

Pemakaian: python cpla.py [--smoke] [--preflight] [--max-hours H] [--ds g5c,unsw,cse]
                          [--tag _g5c]
Keluaran: results/runs{tag}.csv (satu baris per sel x korektor),
          results/inject{tag}.jsonl, results/preflight{tag}.json,
          results/cpla_blocks{tag}.jsonl, results/run{tag}.log
Tiga dataset dijalankan sebagai tiga proses paralel (tag berbeda, 5 thread tiap proses,
total 15 <= core logis - 3) agar masuk anggaran waktu; report.py menggabungkan.
"""
import argparse
import glob
import hashlib
import json
import os
import sys
import time

NTHREAD = max(1, (os.cpu_count() or 4) - 3)
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(v, str(NTHREAD))

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = r"<DATA_ROOT>\data"
G5_FULL = os.path.join(PROJ, "study_5gnidd_audit", "cache", "full.parquet")
G5_FEATS = os.path.join(PROJ, "study_5gnidd_audit", "cache", "feats.json")

MIN_N, RATE_MIN, Z_MIN, BG_MAX = 30, 0.60, 5.0, 0.30
SIZES = (0.01, 0.03, 0.08)
SEEDS = (0, 1, 2)
CORRECTORS = ("noop", "cl", "cl_xp", "oof", "oof_xp", "cpla",
              "oracle_drop", "oracle_fix")
N_TRAIN, N_TEST = 70_000, 30_000
KFOLD = 5

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
CSE_SRC = ["Protocol", "Init Fwd Win Bytes", "Init Bwd Win Bytes", "Fwd Seg Size Min"]

T0 = time.time()
RES = None  # diisi main()
TAG = ""


def log(*a):
    s = f"[{time.time() - T0:7.0f}s] " + " ".join(str(x) for x in a)
    print(s, flush=True)
    if RES:
        with open(os.path.join(RES, f"run{TAG}.log"), "a", encoding="utf-8") as f:
            f.write(s + "\n")


def jenc(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))


# ------------------------------------------------------------------ subsampel
def cap_quota(counts, budget):
    """cap c sehingga sum(min(n_i,c)) mendekati budget (cari biner)."""
    counts = np.asarray(counts)
    if counts.sum() <= budget:
        return int(counts.max()) if len(counts) else 0
    lo, hi = 1, int(counts.max())
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if np.minimum(counts, mid).sum() <= budget:
            lo = mid
        else:
            hi = mid - 1
    return lo


def sample_file(y, budget, rng):
    """indeks terpilih dalam satu berkas: kuota ditutup per kelas."""
    cls, inv = np.unique(y, return_inverse=True)
    counts = np.bincount(inv, minlength=len(cls))
    c = cap_quota(counts, budget)
    keep = []
    for k in range(len(cls)):
        idx = np.flatnonzero(inv == k)
        if len(idx) > c:
            idx = rng.choice(idx, c, replace=False)
        keep.append(idx)
    return np.sort(np.concatenate(keep)) if keep else np.array([], int)


# ------------------------------------------------------------------ pemuatan
def prep_g5c(rng):
    d = pd.read_parquet(G5_FULL)
    fj = json.load(open(G5_FEATS, encoding="utf-8"))
    d = d[d["__keepC"].to_numpy()]
    feats = fj["feats42"]
    out = {}
    for split, bs in (("train", "BS1"), ("test", "BS2")):
        dd = d[d["__bs"] == bs]
        files = sorted(dd["__file"].unique())
        budget = (N_TRAIN if split == "train" else N_TEST) / len(files)
        parts = []
        for f in files:
            sub = dd[dd["__file"] == f]
            sel = sample_file(sub["__y"].to_numpy().astype(str), budget, rng)
            parts.append(sub.iloc[sel])
        dd = pd.concat(parts)
        out[split] = dict(F=dd[feats], y=dd["__y"].to_numpy().astype(str),
                          part=dd["__file"].to_numpy().astype(str),
                          src=dd["SrcAddr"].to_numpy().astype(str))
    return out, feats, "Benign", []


def prep_unsw(rng):
    fs = sorted(glob.glob(os.path.join(DATA, "UNSWNB15", "UNSW-NB15_[1-4].csv")))
    assert len(fs) == 4, fs
    fcols = [c for c in UNSW_NAMES if c not in UNSW_ID + ["attack_cat", "Label"]]
    fnum = [c for c in fcols if c not in UNSW_NOM]
    acc = {"train": [], "test": []}
    for f in fs:
        d = pd.read_csv(f, header=None, names=UNSW_NAMES, dtype=str,
                        keep_default_na=False, na_values=[""], low_memory=False)
        y = d["attack_cat"].str.strip()
        y = y.where(y.notna() & (y != ""), "Normal").astype(str)
        y = y.replace({"Backdoors": "Backdoor"}).to_numpy()
        F = {}
        for c in fnum:
            F[c] = pd.to_numeric(d[c], errors="coerce").astype(np.float32)
        for c in UNSW_NOM:
            F[c] = d[c].fillna("?").astype(str)
        F = pd.DataFrame(F)[fcols]
        split = "test" if f.endswith("_4.csv") else "train"
        budget = (N_TEST if split == "test" else N_TRAIN / 3)
        sel = sample_file(y, budget, rng)
        acc[split].append(dict(F=F.iloc[sel], y=y[sel],
                               part=np.full(len(sel), os.path.basename(f)),
                               src=d["srcip"].fillna("?").astype(str).to_numpy()[sel]))
        del d, F
    out = {}
    for k, lst in acc.items():
        out[k] = dict(F=pd.concat([x["F"] for x in lst]),
                      y=np.concatenate([x["y"] for x in lst]),
                      part=np.concatenate([x["part"] for x in lst]),
                      src=np.concatenate([x["src"] for x in lst]))
    return out, fcols, "Normal", UNSW_NOM


def prep_cse(rng):
    fs = sorted(glob.glob(os.path.join(DATA, "CSECICIDS2018", "*.parquet")))
    assert len(fs) == 10, fs
    acc = {"train": [], "test": []}
    feats = None
    for f in fs:
        d = pd.read_parquet(f)
        d = d[d["Label"].notna()]
        y = d.pop("Label").astype(str).to_numpy()
        if feats is None:
            feats = list(d.columns)
        src = (d[CSE_SRC[0]].astype(str) + "|" + d[CSE_SRC[1]].astype(str) + "|"
               + d[CSE_SRC[2]].astype(str) + "|" + d[CSE_SRC[3]].astype(str)).to_numpy()
        ntr = int(len(d) * 0.70)
        for split, sl in (("train", slice(0, ntr)), ("test", slice(ntr, len(d)))):
            budget = (N_TRAIN if split == "train" else N_TEST) / 10
            ys = y[sl]
            sel = sample_file(ys, budget, rng)
            acc[split].append(dict(F=d.iloc[sl].iloc[sel], y=ys[sel],
                                   part=np.full(len(sel), os.path.basename(f).split("_")[0]),
                                   src=src[sl][sel]))
        del d
    out = {}
    for k, lst in acc.items():
        out[k] = dict(F=pd.concat([x["F"] for x in lst]),
                      y=np.concatenate([x["y"] for x in lst]),
                      part=np.concatenate([x["part"] for x in lst]),
                      src=np.concatenate([x["src"] for x in lst]))
    return out, feats, "Benign", []


PREP = {"g5c": prep_g5c, "unsw": prep_unsw, "cse": prep_cse}


def encode(out, feats):
    """numerik float32 (inf->NaN); nominal -> kode peta train (tak dikenal -> -1)."""
    maps = {}
    for c in feats:
        s = out["train"]["F"][c]
        if s.dtype.kind not in "fiub":
            vals = pd.unique(s.astype(str))
            maps[c] = {v: i for i, v in enumerate(sorted(vals))}
    X = {}
    for split in ("train", "test"):
        cols = []
        for c in feats:
            s = out[split]["F"][c]
            if c in maps:
                a = s.astype(str).map(maps[c]).to_numpy(np.float64)
                a = np.where(np.isnan(a), -1.0, a).astype(np.float32)
            else:
                a = s.to_numpy(np.float32, copy=True)
                a[~np.isfinite(a)] = np.nan
            cols.append(a)
        X[split] = np.ascontiguousarray(np.stack(cols, axis=1))
    return X, list(maps)


def build(ds, cache=True):
    cdir = os.path.join(HERE, "cache")
    os.makedirs(cdir, exist_ok=True)
    p = os.path.join(cdir, f"{ds}.npz")
    if cache and os.path.exists(p):
        z = np.load(p, allow_pickle=True)
        d = {k: z[k] for k in z.files} | {"feats": list(z["feats"]),
                                          "benign": str(z["benign"])}
        n = len(d["Xtr"])
        assert len(d["ytr"]) == n and len(d["ptr"]) == n and len(d["str_"]) == n, "cache rusak"
        assert len(d["Xte"]) == len(d["yte"]), "cache rusak"
        log(f"{ds}: cache dipakai ({n} train, {len(d['Xte'])} test)")
        return d
    t = time.time()
    rng = np.random.default_rng(0)
    out, feats, benign, _ = PREP[ds](rng)
    X, nomcols = encode(out, feats)
    d = dict(Xtr=X["train"], ytr=out["train"]["y"].astype(str),
             ptr=out["train"]["part"].astype(str), str_=out["train"]["src"].astype(str),
             Xte=X["test"], yte=out["test"]["y"].astype(str),
             feats=np.array(feats, dtype=object), benign=benign,
             nom=np.array(nomcols, dtype=object))
    if cache:
        np.savez_compressed(p, **d)
    d["feats"] = feats
    d["benign"] = benign
    log(f"{ds}: siap dalam {time.time()-t:.0f}s — train {d['Xtr'].shape}, "
        f"test {d['Xte'].shape}, {len(set(d['ytr']))} kelas train")
    return d


# ------------------------------------------------------------------ model/OOF
def model(seed):
    return HistGradientBoostingClassifier(
        max_iter=100, learning_rate=0.1, max_bins=255, early_stopping=False,
        l2_regularization=0.1, random_state=seed)


def proba_full(m, X, classes):
    p = m.predict_proba(X)
    out = np.zeros((len(X), len(classes)), np.float32)
    pos = {c: i for i, c in enumerate(classes)}
    for j, c in enumerate(m.classes_):
        out[:, pos[c]] = p[:, j]
    return out


def folds_global(y, seed):
    sk = StratifiedKFold(KFOLD, shuffle=True, random_state=seed)
    f = np.zeros(len(y), int)
    for i, (_, te) in enumerate(sk.split(np.zeros(len(y)), y)):
        f[te] = i
    return f


def folds_xp(part, seed):
    """partisi utuh -> k lipatan, greedy seimbang per jumlah baris."""
    u, cnt = np.unique(part, return_counts=True)
    k = min(KFOLD, len(u))
    rng = np.random.default_rng(seed)
    order = np.argsort(-cnt + rng.random(len(cnt)) * 1e-6)
    load = np.zeros(k)
    assign = {}
    for i in order:
        j = int(np.argmin(load))
        assign[u[i]] = j
        load[j] += cnt[i]
    return np.array([assign[p] for p in part]), k


def oof(X, y, fold, k, classes, seed):
    """-> yhat, P, auditable (penjaga dukungan: label baris punya >=MIN_N di fold-train)."""
    yhat = np.empty(len(y), dtype=object)
    P = np.zeros((len(y), len(classes)), np.float32)
    aud = np.zeros(len(y), bool)
    for i in range(k):
        te = fold == i
        tr = ~te
        m = model(seed).fit(X[tr], y[tr])
        P[te] = proba_full(m, X[te], classes)
        yhat[te] = m.predict(X[te])
        u, c = np.unique(y[tr], return_counts=True)
        ok = set(u[c >= MIN_N])
        aud[te] = np.array([yy in ok for yy in y[te]])
    return yhat.astype(str), P, aud


# ------------------------------------------------------------------ suntikan
def hash_rows(X):
    df = pd.DataFrame(X)
    return pd.util.hash_pandas_object(df, index=False).to_numpy(np.uint64)


def conflict_pairs(X, y):
    """massa konflik per pasangan kelas atas vektor fitur identik."""
    h = hash_rows(X)
    _, vid, cnt = np.unique(h, return_inverse=True, return_counts=True)
    multi = np.flatnonzero(cnt > 1)
    if not len(multi):
        return {}
    ism = np.isin(vid, multi)
    idx = np.flatnonzero(ism)
    order = np.argsort(vid[idx], kind="stable")
    idx = idx[order]
    v = vid[idx]
    bnd = np.flatnonzero(np.diff(v)) + 1
    groups = np.split(idx, bnd)
    out = {}
    for g in groups:
        lab, c = np.unique(y[g], return_counts=True)
        if len(lab) < 2:
            continue
        for i in range(len(lab)):
            for j in range(i + 1, len(lab)):
                kk = (lab[i], lab[j])
                out[kk] = out.get(kk, 0) + int(min(c[i], c[j]))
    return out


def inject(d, regime, size, seed, pair_rank, extra):
    """-> y_dirty, mask_inj, info"""
    y = d["ytr"].copy()
    n = len(y)
    target = int(round(size * n))
    rng = np.random.default_rng(1000 + seed)
    info = dict(regime=regime, size_frac=size, target=target, seed=seed)
    mask = np.zeros(n, bool)
    if regime == "R0":
        info["achieved"] = 0
        return y, mask, info
    if regime == "R1":
        key = pd.DataFrame({"p": d["ptr"], "s": d["str_"], "y": y})
        grp = key.groupby(["p", "s", "y"], sort=False).size()
        grp = grp[[yy != d["benign"] for yy in grp.index.get_level_values("y")]]
        grp = grp[grp >= MIN_N].sort_values(ascending=False)
        elig = grp[grp >= target]
        if len(elig) > seed:
            pick = elig.index[seed]
        elif len(grp):
            pick = grp.index[0]
        else:
            info["achieved"] = 0
            info["gagal"] = "tidak ada grup layak"
            return y, mask, info
        p, s, c = pick
        idx = np.flatnonzero((d["ptr"] == p) & (d["str_"] == s) & (y == c))
        if len(idx) > target:
            idx = rng.choice(idx, target, replace=False)
        y[idx] = d["benign"]
        mask[idx] = True
        info.update(blok=dict(partisi=p, sumber=s, kelas=c, n_grup=int(grp.loc[pick])),
                    achieved=int(len(idx)), label_baru=d["benign"],
                    kurang_dari_target=bool(len(idx) < target))
        return y, mask, info
    if regime == "R2":
        a, b = extra["pair"]
        cand = (y == a) | (y == b)
        pp = pd.Series(d["ptr"][cand]).value_counts()
        if not len(pp):
            info["achieved"] = 0
            info["gagal"] = "pasangan tidak ada di train"
            return y, mask, info
        p = pp.index[min(seed, len(pp) - 1)]
        ia = np.flatnonzero((d["ptr"] == p) & (y == a))
        ib = np.flatnonzero((d["ptr"] == p) & (y == b))
        tot = len(ia) + len(ib)
        if tot > target:
            na = int(round(target * len(ia) / tot))
            nb = target - na
            na, nb = min(na, len(ia)), min(nb, len(ib))
            ia = rng.choice(ia, na, replace=False) if na < len(ia) else ia
            ib = rng.choice(ib, nb, replace=False) if nb < len(ib) else ib
        y[ia] = b
        y[ib] = a
        mask[ia] = True
        mask[ib] = True
        info.update(blok=dict(partisi=str(p), pasangan=[a, b], n_a=int(len(ia)),
                              n_b=int(len(ib)), n_tersedia=int(tot)),
                    achieved=int(len(ia) + len(ib)),
                    kurang_dari_target=bool(len(ia) + len(ib) < target))
        return y, mask, info
    raise ValueError(regime)


# ------------------------------------------------------------------ korektor
def cl_flag(y, P, classes, aud):
    """cleanlab atas baris yang lolos penjaga dukungan; -> flag (panjang penuh), cara."""
    full = np.zeros(len(y), bool)
    sel = np.flatnonzero(aud)
    if len(sel) < 10:
        return full, "tak ada baris auditable"
    ys, Ps = y[sel], P[sel]
    cls = sorted(set(ys))
    yi = np.searchsorted(np.array(cls), ys)
    col = [classes.index(c) for c in cls]
    Ps = Ps[:, col]
    Ps = Ps / np.clip(Ps.sum(1, keepdims=True), 1e-9, None)
    try:
        from cleanlab.filter import find_label_issues
        f = find_label_issues(labels=yi, pred_probs=Ps.astype(np.float64),
                              filter_by="prune_by_noise_rate")
        full[sel] = np.asarray(f, bool)
        return full, "cleanlab"
    except Exception as e:  # noqa: BLE001
        log("cleanlab gagal ->", type(e).__name__, e, "- pakai confident-joint sendiri")
        K = len(cls)
        t = np.array([Ps[yi == j, j].mean() if (yi == j).any() else 1.0 for j in range(K)])
        above = Ps >= t[None, :]
        cnt = above.sum(1)
        guess = np.where(cnt >= 1, np.argmax(np.where(above, Ps, -1), 1), yi)
        full[sel] = (cnt >= 1) & (guess != yi) & (Ps[np.arange(len(yi)), yi] < t[yi])
        return full, "confident-joint-sendiri"


def cpla_flag(y, yhat, part, src, aud):
    """-> keep_mask, diag"""
    sel = np.flatnonzero(aud)
    if not len(sel):
        return np.ones(len(y), bool), dict(n_blok=0, dibuang=0, blok=[])
    df = pd.DataFrame({"p": part[sel], "s": src[sel], "y": y[sel], "q": yhat[sel]})
    gsz = df.groupby(["p", "s", "y"], sort=False).size().rename("n_g")
    blk = df[df.y != df.q].groupby(["p", "s", "y", "q"], sort=False).size().rename("n_b")
    if not len(blk):
        return np.ones(len(y), bool), dict(n_blok=0, dibuang=0, blok=[])
    t = blk.reset_index().merge(gsz.reset_index(), on=["p", "s", "y"], how="left")
    t["rate"] = t.n_b / t.n_g
    big = t[t.n_g >= MIN_N]
    bgmap = {k: (v["p"].to_numpy(), v["rate"].to_numpy())
             for k, v in big.groupby(["y", "q"], sort=False)}
    drop_rows = np.zeros(len(y), bool)
    chosen = []
    cand = t[(t.n_b >= MIN_N) & (t.rate >= RATE_MIN)]
    for _, r in cand.iterrows():
        bp, br = bgmap.get((r.y, r.q), (np.array([]), np.array([])))
        bg = br[bp != r.p]
        if len(bg):
            med = float(np.median(bg))
            mad = float(np.median(np.abs(bg - med)))
            z = (r.rate - med) / (1.4826 * mad + 0.01)
        else:
            med, z = 0.0, float("inf")
        if z >= Z_MIN and med <= BG_MAX:
            m = aud & (part == r.p) & (src == r.s) & (y == r.y)
            drop_rows |= m
            chosen.append(dict(partisi=str(r.p), sumber=str(r.s), label=str(r.y),
                               prediksi=str(r.q), n_b=int(r.n_b), n_g=int(r.n_g),
                               rate=round(float(r.rate), 4),
                               latar_med=round(med, 4),
                               z=(None if np.isinf(z) else round(float(z), 2)),
                               dibuang=int(m.sum())))
    return ~drop_rows, dict(n_blok=len(chosen), dibuang=int(drop_rows.sum()),
                            blok=chosen[:20])


def correct(name, d, y_dirty, mask_inj, oofg, oofx, classes):
    yhat_g, Pg, aud_g = oofg
    yhat_x, Px, aud_x = oofx
    n = len(y_dirty)
    keep = np.ones(n, bool)
    ynew = y_dirty.copy()
    diag = {}
    if name == "noop":
        pass
    elif name in ("cl", "cl_xp"):
        P, aud = (Pg, aud_g) if name == "cl" else (Px, aud_x)
        flag, how = cl_flag(y_dirty, P, classes, aud)
        keep = ~np.asarray(flag, bool)
        diag["cara"] = how
    elif name == "oof":
        keep = ~(aud_g & (y_dirty != yhat_g))
    elif name == "oof_xp":
        keep = ~(aud_x & (y_dirty != yhat_x))
    elif name == "cpla":
        keep, diag = cpla_flag(y_dirty, yhat_x, d["ptr"], d["str_"], aud_x)
    elif name == "oracle_drop":
        keep = ~mask_inj
    elif name == "oracle_fix":
        ynew = d["ytr"].copy()
    else:
        raise ValueError(name)
    flagged = (~keep) | (ynew != y_dirty)
    nf = int(flagged.sum())
    ni = int(mask_inj.sum())
    diag.update(n_dibuang=int((~keep).sum()), n_direlabel=int((ynew != y_dirty).sum()),
                det_prec=(float((flagged & mask_inj).sum() / nf) if nf else None),
                det_rec=(float((flagged & mask_inj).sum() / ni) if ni else None))
    return keep, ynew, diag


# ------------------------------------------------------------------ metrik
def metrics(d, keep, ynew, seed, classes):
    out = {}
    if keep.sum() < 10 or len(set(ynew[keep])) < 2:
        return dict(gagal="train terkoreksi terlalu kecil/1 kelas",
                    n_train=int(keep.sum()))
    t = time.time()
    m = model(seed).fit(d["Xtr"][keep], ynew[keep])
    out["fit_s"] = round(time.time() - t, 1)
    pred = m.predict(d["Xte"])
    yte = d["yte"]
    out["n_train"] = int(keep.sum())
    out["acc"] = float((pred == yte).mean())
    out["f1_macro"] = float(f1_score(yte, pred, labels=classes, average="macro",
                                     zero_division=0))
    bt = yte != d["benign"]
    bp = pred != d["benign"]
    tp, fp = int((bt & bp).sum()), int((~bt & bp).sum())
    fn, tn = int((bt & ~bp).sum()), int((~bt & ~bp).sum())
    out["tpr"] = float(tp / (tp + fn)) if tp + fn else None
    out["fpr"] = float(fp / (fp + tn)) if fp + tn else None
    out["f1_det"] = float(2 * tp / (2 * tp + fp + fn)) if tp or fp or fn else None
    return out


# ------------------------------------------------------------------ orkestrasi
CSV_COLS = ["ds", "regime", "size_frac", "seed", "corrector", "n_train", "acc",
            "f1_macro", "tpr", "fpr", "f1_det", "n_dibuang", "n_direlabel",
            "det_prec", "det_rec", "n_inj", "fit_s", "gagal"]


def append_csv(path, row):
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write(",".join(CSV_COLS) + "\n")
        f.write(",".join("" if row.get(c) is None else str(row.get(c, ""))
                         for c in CSV_COLS) + "\n")


def done_keys(path):
    if not os.path.exists(path):
        return set()
    t = pd.read_csv(path)
    return {(r.ds, r.regime, f"{float(r.size_frac):.3f}", int(r.seed), r.corrector)
            for r in t.itertuples()}


def main():
    global RES, TAG
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--max-hours", type=float, default=2.6)
    ap.add_argument("--ds", default="g5c,unsw,cse")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    TAG = a.tag
    RES = os.path.join(HERE, "results_smoke" if a.smoke else "results")
    os.makedirs(RES, exist_ok=True)
    global N_TRAIN, N_TEST, SIZES, SEEDS
    if a.smoke:
        N_TRAIN, N_TEST = 12_000, 6_000
        SIZES, SEEDS = (0.03,), (0,)
    with open(os.path.abspath(__file__), "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
    open(os.path.join(RES, "SCRIPT.sha256"), "w").write(h + "  cpla.py\n")
    log("cpla.py sha256", h[:16], "| thread OMP", os.environ.get("OMP_NUM_THREADS"),
        "| budget", a.max_hours, "jam | smoke", a.smoke, "| tag", TAG or "(kosong)")
    csv = os.path.join(RES, f"runs{TAG}.csv")
    done = done_keys(csv)
    pre = {}
    deadline = T0 + a.max_hours * 3600
    for ds in a.ds.split(","):
        d = build(ds, cache=not a.smoke)
        classes = sorted(set(d["ytr"]) | set(d["yte"]))
        cm = conflict_pairs(d["Xtr"], d["ytr"])
        if cm:
            pair = max(cm.items(), key=lambda kv: kv[1])
            pair, how = list(pair[0]), f"massa konflik vektor identik = {pair[1]}"
        else:
            yh, _, _ = oof(d["Xtr"], d["ytr"], *folds_xp(d["ptr"], 0), classes, 0)
            t = pd.crosstab(pd.Series(d["ytr"]), pd.Series(yh))
            best, bv = None, -1
            for i, ca in enumerate(classes):
                for cb in classes[i + 1:]:
                    v = (int(t.loc[ca, cb]) if (ca in t.index and cb in t.columns) else 0) \
                        + (int(t.loc[cb, ca]) if (cb in t.index and ca in t.columns) else 0)
                    if v > bv:
                        best, bv = [ca, cb], v
            pair, how = best, f"cadangan: kebingungan OOF lintas-partisi = {bv}"
        extra = {"pair": pair}
        gs = pd.DataFrame({"p": d["ptr"], "s": d["str_"], "y": d["ytr"]}) \
            .groupby(["p", "s", "y"], sort=False).size().sort_values(ascending=False)
        gs = gs[[yy != d["benign"] for yy in gs.index.get_level_values("y")]]
        pre[ds] = dict(
            n_train=int(len(d["ytr"])), n_test=int(len(d["yte"])),
            n_fitur=int(d["Xtr"].shape[1]), benign=d["benign"],
            kelas=classes, n_partisi_train=int(len(set(d["ptr"]))),
            n_sumber_train=int(len(set(d["str_"]))),
            kelas_train=pd.Series(d["ytr"]).value_counts().to_dict(),
            kelas_test=pd.Series(d["yte"]).value_counts().to_dict(),
            pasangan_R2=pair, aturan_pasangan=how,
            grup_R1_top5=[dict(partisi=str(k[0]), sumber=str(k[1]), kelas=str(k[2]),
                               n=int(v)) for k, v in gs.head(5).items()],
            target_blok=[int(round(s * len(d["ytr"]))) for s in SIZES],
            kolom_nominal=list(d["nom"]) if "nom" in d else [])
        with open(os.path.join(RES, f"preflight{TAG}.json"), "w", encoding="utf-8") as f:
            json.dump(pre, f, indent=2, default=jenc)
        log(f"{ds}: preflight -> pasangan R2 {pair} ({how}); grup R1 terbesar "
            f"{pre[ds]['grup_R1_top5'][:1]}; target blok {pre[ds]['target_blok']}")
        if a.preflight:
            continue
        jobs = [("R0", 0.0, s) for s in SEEDS]
        jobs += [(r, sz, s) for r in ("R1", "R2") for sz in SIZES for s in SEEDS]
        for regime, size, seed in jobs:
            kk = (ds, regime, f"{size:.3f}", seed)
            want = [c for c in CORRECTORS
                    if not (regime == "R0" and c.startswith("oracle"))]
            if all((kk + (c,)) in done for c in want):
                continue
            if time.time() > deadline:
                log("BATAS WAKTU tercapai — berhenti sebelum", kk)
                return
            y_dirty, mask_inj, info = inject(d, regime, size, seed, seed, extra)
            info["ds"] = ds
            t = time.time()
            fg = folds_global(y_dirty, seed)
            oofg = oof(d["Xtr"], y_dirty, fg, KFOLD, classes, seed)
            fx, kx = folds_xp(d["ptr"], seed)
            oofx = oof(d["Xtr"], y_dirty, fx, kx, classes, seed)
            info["frac_auditable_global"] = round(float(oofg[2].mean()), 4)
            info["frac_auditable_xp"] = round(float(oofx[2].mean()), 4)
            info["k_fold_xp"] = int(kx)
            log(f"{ds} {regime} {size} s{seed}: suntik {info.get('achieved')} "
                f"({info.get('target')} target), OOF {time.time()-t:.0f}s, "
                f"auditable xp {info['frac_auditable_xp']}")
            with open(os.path.join(RES, f"inject{TAG}.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(info, default=jenc) + "\n")
            for c in CORRECTORS:
                if (ds, regime, f"{size:.3f}", seed, c) in done:
                    continue
                if regime == "R0" and c in ("oracle_drop", "oracle_fix"):
                    continue
                keep, ynew, diag = correct(c, d, y_dirty, mask_inj, oofg, oofx,
                                           classes)
                mt = metrics(d, keep, ynew, seed, classes)
                row = dict(ds=ds, regime=regime, size_frac=f"{size:.3f}", seed=seed,
                           corrector=c, n_inj=int(mask_inj.sum()))
                row.update({k: v for k, v in diag.items() if k in CSV_COLS})
                row.update({k: v for k, v in mt.items() if k in CSV_COLS})
                append_csv(csv, row)
                if c == "cpla":
                    with open(os.path.join(RES, f"cpla_blocks{TAG}.jsonl"), "a",
                              encoding="utf-8") as f:
                        f.write(json.dumps(dict(ds=ds, regime=regime, size=size,
                                                seed=seed, **diag),
                                           default=jenc) + "\n")
                log(f"  {c:12s} f1={mt.get('f1_macro')} fpr={mt.get('fpr')} "
                    f"buang={diag.get('n_dibuang')} rec={diag.get('det_rec')}")
        del d
    log("SELESAI")


if __name__ == "__main__":
    main()
