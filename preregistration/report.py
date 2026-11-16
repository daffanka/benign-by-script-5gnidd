"""Agregasi results/runs.csv -> REPORT.md menurut aturan yang dikunci di cpla.py.
python report.py [--res results]"""
import argparse
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = ("noop", "cl", "cl_xp", "oof", "oof_xp")
ORD = ("noop", "cl", "cl_xp", "oof", "oof_xp", "cpla", "oracle_drop", "oracle_fix")
DSN = {"g5c": "5G-NIDD versi C", "unsw": "UNSW-NB15", "cse": "CSE-CIC-IDS2018"}
NAMA = {"noop": "no-op", "cl": "cleanlab (OOF global)", "cl_xp": "cleanlab (OOF lintas-partisi)",
        "oof": "OOF global", "oof_xp": "OOF lintas-partisi", "cpla": "**CPLA**",
        "oracle_drop": "oracle (buang)", "oracle_fix": "oracle (perbaiki)"}
L = []
A = L.append


def rib(n):
    return f"{int(n):,}".replace(",", ".")


def ms(v, p=4):
    v = pd.Series(v).dropna().astype(float)
    if not len(v):
        return "TIDAK ADA"
    if len(v) == 1:
        return f"{v.iloc[0]:.{p}f}"
    return f"{v.mean():.{p}f} ± {v.std(ddof=1):.{p}f}"


def wtest(diff):
    d = np.asarray([x for x in diff if np.isfinite(x)], float)
    if len(d) < 3 or np.all(d == 0):
        return None, "TIDAK ADA (selisih nol/terlalu sedikit)"
    try:
        s, p = wilcoxon(d, alternative="greater", zero_method="wilcox")
        return float(p), f"{p:.2e}"
    except Exception as e:  # noqa: BLE001
        return None, f"TIDAK ADA ({type(e).__name__})"


def pivot(df, metric):
    """-> DataFrame sel x korektor"""
    return df.pivot_table(index=["ds", "regime", "size_frac", "seed"],
                          columns="corrector", values=metric, aggfunc="first")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default="results")
    a = ap.parse_args()
    RES = os.path.join(HERE, a.res)
    import glob as _g

    def many(pat):
        return sorted(_g.glob(os.path.join(RES, pat)))

    df = pd.concat([pd.read_csv(f) for f in many("runs*.csv")], ignore_index=True)
    pre = {}
    for f in many("preflight*.json"):
        pre.update(json.load(open(f, encoding="utf-8")))
    inj = []
    for f in many("inject*.jsonl"):
        inj += [json.loads(x) for x in open(f, encoding="utf-8")]
    hsh = open(os.path.join(RES, "SCRIPT.sha256")).read().split()[0]

    A("# Pilot D (CPLA) — audit lintas-partisi + koreksi vs pemulihan tugas hilir\n")
    A(f"Aturan skor, rezim noise, ambang CPLA, dan gerbang dikunci di docstring "
      f"`cpla.py` sebelum run (sha256 `{hsh[:16]}…`, lengkap di `results/SCRIPT.sha256`). "
      "Angka mentah: `results/runs.csv`; blok CPLA: `results/cpla_blocks.jsonl`; "
      "suntikan: `results/inject.jsonl`.\n")
    A("@@RINGKASAN@@")

    # ---------------- data & desain
    A("## Dataset, partisi, split\n")
    A("| dataset | baris train / test | fitur | kelas | partisi train | sumber train | Benign | split evaluasi |")
    A("|---|---|---|---|---|---|---|---|")
    SPL = {"g5c": "antar-partisi sejati: train BS1 → test BS2",
           "unsw": "antar-partisi sejati: train berkas 1–3 → test berkas 4",
           "cse": "urutan baris dalam berkas 70/30 (BUKAN antar-berkas; lihat penyimpangan 1)"}
    for ds in ("g5c", "unsw", "cse"):
        if ds not in pre:
            continue
        p = pre[ds]
        A(f"| {DSN[ds]} | {rib(p['n_train'])} / {rib(p['n_test'])} | {p['n_fitur']} | "
          f"{len(p['kelas'])} | {p['n_partisi_train']} | {rib(p['n_sumber_train'])} | "
          f"`{p['benign']}` | {SPL[ds]} |")
    A("")
    A("Blok R1 terbesar yang tersedia (partisi × sumber × kelas) dan pasangan R2 terpilih:\n")
    A("| dataset | grup R1 terbesar | n | pasangan R2 | aturan pemilihan pasangan |")
    A("|---|---|---|---|---|")
    for ds in ("g5c", "unsw", "cse"):
        if ds not in pre:
            continue
        p = pre[ds]
        g = p["grup_R1_top5"][0] if p["grup_R1_top5"] else {}
        A(f"| {DSN[ds]} | {g.get('partisi','-')} / {g.get('sumber','-')} / "
          f"{g.get('kelas','-')} | {g.get('n','-')} | {' ↔ '.join(p['pasangan_R2'])} | "
          f"{p['aturan_pasangan']} |")
    A("")

    # ---------------- suntikan tercapai
    A("## Ukuran blok yang benar-benar tersuntik\n")
    A("| dataset | rezim | target % | target baris | tercapai (3 seed) | kurang dari target |")
    A("|---|---|---|---|---|---|")
    ij = pd.DataFrame(inj)
    for ds in ("g5c", "unsw", "cse"):
        for reg in ("R1", "R2"):
            s = ij[(ij.ds == ds) & (ij.regime == reg)] if len(ij) else ij
            if not len(s):
                continue
            for sz in sorted(s.size_frac.unique()):
                t = s[s.size_frac == sz]
                A(f"| {DSN[ds]} | {reg} | {sz*100:.1f}% | {rib(t.target.iloc[0])} | "
                  + ", ".join(str(int(x)) for x in t.achieved)
                  + f" | {'ya' if t.get('kurang_dari_target', pd.Series([False])).any() else 'tidak'} |")
    A("")
    aud = ij[ij.regime != "R0"] if len(ij) else ij
    if len(aud):
        A(f"Fraksi baris train yang bisa diaudit lintas-partisi (penjaga dukungan): "
          + "; ".join(f"{DSN[d]} {ij[ij.ds==d].frac_auditable_xp.mean():.2f}"
                      for d in ij.ds.unique()) + ".\n")

    # ---------------- tabel utama
    for metric, judul, pp in (("f1_macro", "Macro-F1 pada test (metrik kemenangan utama)", 4),
                              ("fpr", "FPR biner pada test (lebih kecil lebih baik)", 4)):
        A(f"## {judul}\n")
        for ds in ("g5c", "unsw", "cse"):
            sub = df[df.ds == ds]
            if not len(sub):
                continue
            A(f"### {DSN[ds]} (mean ± sd atas 3 seed)\n")
            A("| rezim / ukuran | " + " | ".join(NAMA[c] for c in ORD) + " |")
            A("|---" * (len(ORD) + 1) + "|")
            for reg in ("R0", "R1", "R2"):
                for sz in sorted(sub[sub.regime == reg].size_frac.unique()):
                    t = sub[(sub.regime == reg) & (sub.size_frac == sz)]
                    lab = "kontrol bersih" if reg == "R0" else f"{reg} {sz*100:.1f}%"
                    A(f"| {lab} | " + " | ".join(
                        ms(t[t.corrector == c][metric], pp) for c in ORD) + " |")
            A("")

    # ---------------- gerbang
    pf = pivot(df[df.regime != "R0"], "f1_macro")
    pfpr = pivot(df[df.regime != "R0"], "fpr")
    A("## Selisih CPLA vs tiap korektor dan uji Wilcoxon\n")
    A(f"Sel tersuntik: {len(pf)} (dataset × rezim × ukuran × seed).\n")
    A("| pembanding X | median ΔF1 (CPLA−X) | menang/seri/kalah | Wilcoxon p (CPLA>X) "
      "| median ΔFPR (CPLA−X) |")
    A("|---|---|---|---|---|")
    g1 = {}
    for c in BASE:
        if c not in pf.columns or "cpla" not in pf.columns:
            A(f"| {NAMA[c]} | TIDAK ADA | - | - | - |")
            continue
        d = (pf["cpla"] - pf[c]).dropna()
        p, ptxt = wtest(d.to_numpy())
        dd = (pfpr["cpla"] - pfpr[c]).dropna() if c in pfpr.columns else pd.Series(dtype=float)
        g1[c] = (float(np.median(d)) > 0) and (p is not None and p < 0.05)
        A(f"| {NAMA[c]} | {np.median(d):+.4f} | {(d>0).sum()}/{(d==0).sum()}/{(d<0).sum()} "
          f"| {ptxt} | {np.median(dd):+.4f} |" if len(dd) else
          f"| {NAMA[c]} | {np.median(d):+.4f} | {(d>0).sum()}/{(d==0).sum()}/{(d<0).sum()} "
          f"| {ptxt} | TIDAK ADA |")
    A("")

    A("### Rincian per dataset × rezim (median ΔF1 CPLA − X, 9 sel tiap baris)\n")
    A("| dataset | rezim | vs no-op | vs cleanlab | vs cleanlab-xp | vs OOF | vs OOF-xp "
      "| pembanding terbaik |")
    A("|---|---|---|---|---|---|---|---|")
    for ds in ("g5c", "unsw", "cse"):
        for reg in ("R1", "R2"):
            pr = pivot(df[(df.ds == ds) & (df.regime == reg)], "f1_macro")
            if not len(pr) or "cpla" not in pr.columns:
                continue
            cells, med = [], {}
            for c in BASE:
                if c not in pr.columns:
                    cells.append("TIDAK ADA")
                    continue
                m = float(np.median((pr["cpla"] - pr[c]).dropna()))
                med[c] = m
                cells.append(f"{m:+.4f}")
            bk = min(med, key=med.get) if med else None
            A(f"| {DSN[ds]} | {reg} | " + " | ".join(cells)
              + f" | {NAMA[bk] if bk else '-'} ({med[bk]:+.4f}) |")
    A("")

    # pemulihan
    def recov(p):
        if "oracle_drop" not in p.columns or "noop" not in p.columns:
            return pd.Series(dtype=float), 0
        gap = p["oracle_drop"] - p["noop"]
        ok = gap >= 0.01
        r = (p.loc[ok, "cpla"] - p.loc[ok, "noop"]) / gap[ok]
        return r, int(ok.sum())

    r_all, n_ok = recov(pf)
    A("## Fraksi pemulihan macro-F1 (relatif oracle-buang)\n")
    A("| himpunan sel | n sel memenuhi syarat | median fraksi pemulihan CPLA "
      "| median fraksi pemulihan pembanding terbaik |")
    A("|---|---|---|---|")
    for lab, sel in (("semua sel tersuntik", pf),
                     ("R1 saja", pivot(df[df.regime == "R1"], "f1_macro")),
                     ("R2 saja", pivot(df[df.regime == "R2"], "f1_macro"))):
        r, n = recov(sel)
        best = "TIDAK ADA"
        if n and "oracle_drop" in sel.columns:
            gap = sel["oracle_drop"] - sel["noop"]
            ok = gap >= 0.01
            cand = {c: float(np.median((sel.loc[ok, c] - sel.loc[ok, "noop"]) / gap[ok]))
                    for c in BASE if c in sel.columns and c != "noop"}
            if cand:
                bk = max(cand, key=cand.get)
                best = f"{NAMA[bk]} {cand[bk]:+.2f}"
        A(f"| {lab} | {n} | {('%+.2f' % float(np.median(r))) if n else 'TIDAK ADA'} | {best} |")
    A("")

    # kontrol
    p0 = pivot(df[df.regime == "R0"], "f1_macro")
    p0f = pivot(df[df.regime == "R0"], "fpr")
    A("## Kontrol: kerusakan tiap korektor pada data BERSIH (tanpa suntikan)\n")
    A("| korektor | median ΔF1 vs no-op | median ΔFPR vs no-op | rerata baris dibuang "
      "| % dari train |")
    A("|---|---|---|---|---|")
    ctl = df[df.regime == "R0"]
    tot = float(ctl[ctl.corrector == "noop"].n_train.mean()) if len(ctl) else 0.0
    for c in ORD:
        if c.startswith("oracle") or c not in p0.columns:
            continue
        d = (p0[c] - p0["noop"]).dropna()
        dfp = (p0f[c] - p0f["noop"]).dropna() if c in p0f.columns else pd.Series(dtype=float)
        t = ctl[ctl.corrector == c]
        A(f"| {NAMA[c]} | {np.median(d):+.4f} | "
          f"{('%+.4f' % np.median(dfp)) if len(dfp) else 'TIDAK ADA'} | "
          f"{t.n_dibuang.mean():.0f} | {100*t.n_dibuang.mean()/tot if tot else 0:.2f}% |")
    A(f"\n(rerata baris train per sel kontrol: {rib(tot)}; rerata atas 3 dataset × 3 seed.)\n")

    g3 = False
    if "cpla" in p0.columns:
        d1 = float(np.median((p0["cpla"] - p0["noop"]).dropna()))
        d2 = float(np.median((p0f["cpla"] - p0f["noop"]).dropna()))
        g3 = (d1 >= -0.005) and (d2 <= 0.005)
    g2 = bool(n_ok and float(np.median(r_all)) >= 0.50)
    A("## Verdik gerbang (aturan F di `cpla.py`, tidak diubah)\n")
    A("| gerbang | syarat | hasil |")
    A("|---|---|---|")
    A("| G1 dominasi | median ΔF1 > 0 DAN Wilcoxon p < 0,05 vs no-op, cleanlab, "
      "cleanlab-xp, OOF, OOF-xp | "
      + ("**TERPENUHI**" if all(g1.values()) and len(g1) == len(BASE) else "**GAGAL**")
      + " (" + ", ".join(f"{c}: {'ya' if v else 'tidak'}" for c, v in g1.items()) + ") |")
    A(f"| G2 pemulihan | median fraksi pemulihan CPLA ≥ 0,50 | "
      + ("**TERPENUHI**" if g2 else "**GAGAL**")
      + (f" (median {float(np.median(r_all)):+.2f} atas {n_ok} sel)" if n_ok else "") + " |")
    A("| G3 tidak merusak | pada kontrol: ΔF1 ≥ −0,005 dan ΔFPR ≤ +0,005 | "
      + ("**TERPENUHI**" if g3 else "**GAGAL**") + " |")
    gate = all(g1.values()) and len(g1) == len(BASE) and g2 and g3
    A(f"\n**GERBANG UTAMA: {'TERPENUHI' if gate else 'GAGAL'}**\n")

    A("### Sub-gerbang per rezim\n")
    A("| rezim | G1 (vs tiap pembanding) | G2 |")
    A("|---|---|---|")
    for reg in ("R1", "R2"):
        pr = pivot(df[df.regime == reg], "f1_macro")
        if not len(pr) or "cpla" not in pr.columns:
            A(f"| {reg} | TIDAK ADA | TIDAK ADA |")
            continue
        res = {}
        for c in BASE:
            if c not in pr.columns:
                continue
            d = (pr["cpla"] - pr[c]).dropna()
            p, _ = wtest(d.to_numpy())
            res[c] = (float(np.median(d)) > 0) and (p is not None and p < 0.05)
        r, n = recov(pr)
        A(f"| {reg} | " + ", ".join(f"{c}: {'ya' if v else 'tidak'}" for c, v in res.items())
          + f" | {('median %+.2f atas %d sel -> %s' % (float(np.median(r)), n, 'ya' if float(np.median(r))>=0.5 else 'tidak')) if n else 'TIDAK ADA'} |")
    A("")

    # ---------------- deteksi noise
    A("## Diagnostik: presisi/recall deteksi baris tersuntik\n")
    A("| rezim | korektor | presisi (mean) | recall (mean) | baris dibuang (mean) |")
    A("|---|---|---|---|---|")
    for reg in ("R1", "R2"):
        for c in ORD:
            t = df[(df.regime == reg) & (df.corrector == c)]
            if not len(t):
                continue
            A(f"| {reg} | {NAMA[c]} | {ms(t.det_prec, 3)} | {ms(t.det_rec, 3)} | "
              f"{t.n_dibuang.mean():.0f} |")
    A("")

    # ---------------- sekunder
    A("## Sekunder: F1 deteksi biner dan TPR (mean atas seed & ukuran)\n")
    A("| dataset | rezim | " + " | ".join(NAMA[c] for c in ORD) + " |")
    A("|---" * (len(ORD) + 2) + "|")
    for ds in ("g5c", "unsw", "cse"):
        for reg in ("R0", "R1", "R2"):
            t = df[(df.ds == ds) & (df.regime == reg)]
            if not len(t):
                continue
            A(f"| {DSN[ds]} | {reg} | " + " | ".join(
                (f"{t[t.corrector==c].f1_det.astype(float).mean():.4f}"
                 if len(t[t.corrector == c]) else "TIDAK ADA") for c in ORD) + " |")
    A("")

    # ---------------- blok CPLA
    bl = []
    for f in many("cpla_blocks*.jsonl"):
        bl += [json.loads(x) for x in open(f, encoding="utf-8")]
    if bl:
        A("## Blok yang dibuang CPLA (contoh 8 blok dengan z terbesar)\n")
        rows = []
        for b in bl:
            for k in b.get("blok", []):
                rows.append(dict(ds=b["ds"], rezim=b["regime"], ukuran=b["size"],
                                 seed=b["seed"], **k))
        if rows:
            t = pd.DataFrame(rows)
            t["zz"] = pd.to_numeric(t.z, errors="coerce").fillna(1e9)
            A("| dataset | rezim | ukuran | partisi | sumber | label | prediksi OOF | n_b/n_g | rate | latar med | z | dibuang |")
            A("|---" * 12 + "|")
            for _, r in t.sort_values("zz", ascending=False).head(8).iterrows():
                A(f"| {r.ds} | {r.rezim} | {r.ukuran} | {r.partisi} | {str(r.sumber)[:28]} | "
                  f"{r.label} | {r.prediksi} | {r.n_b}/{r.n_g} | {r.rate:.3f} | "
                  f"{r.latar_med:.3f} | {'inf' if pd.isna(r.z) else f'{r.z:.1f}'} | {r.dibuang} |")
            A(f"\nTotal blok dibuang di seluruh run: {len(t)}; "
              f"rerata baris dibuang per blok {t.dibuang.mean():.0f}.\n")
        else:
            A("CPLA tidak membuang satu blok pun di seluruh run.\n")

    # ---------------- penyimpangan
    A("## Penyimpangan dan keputusan\n")
    nsel = df.groupby(["ds", "regime", "size_frac", "seed"]).ngroups
    nexp = 3 * (3 + 2 * 3 * 3)
    capped = []
    if len(ij):
        for _, r in ij[ij.regime != "R0"].iterrows():
            if r.get("kurang_dari_target"):
                capped.append(f"{r.ds}/{r.regime}/{r.size_frac*100:.0f}%")
    A(f"""1. **CSE-CIC-IDS2018 tidak punya split antar-partisi yang sah.** Parquet pra-proses
   tidak memuat IP maupun Timestamp, dan setiap kelas serangan hanya muncul di SATU
   berkas/hari; split antar-berkas akan membuat kelas test tidak pernah ada di train.
   Karena itu split evaluasi CSE = urutan baris tersimpan dalam setiap berkas (70% awal
   train, 30% akhir test) dan sumbu "sumber" memakai PROKSI sidik-jari tumpukan TCP
   (Protocol, Init Fwd Win Bytes, Init Bwd Win Bytes, Fwd Seg Size Min;
   {rib(pre['cse']['n_sumber_train']) if 'cse' in pre else 'TIDAK ADA'} nilai berbeda di train),
   bukan IP sumber. Hasil CSE karena itu BUKAN uji antar-partisi sejati — hanya 5G-NIDD
   (BS1→BS2) dan UNSW (berkas 1–3 → berkas 4) yang antar-partisi sejati.
2. **Subsampel.** Tiap dataset disubsampel ke ~70.000 baris train dan ~30.000 baris test
   (kuota per berkas, lalu cap per kelas, acak seed 0) agar 63 sel × 16–18 fit model
   masuk anggaran 3 jam CPU. Subsampel SAMA untuk semua rezim/ukuran/seed.
3. **REVISI MEKANIS v2 setelah uji asap (diungkap penuh).** Versi v1 dijalankan sebagai
   uji asap 12k baris pada 5G-NIDD (hasil disimpan di `results_smoke_v1/`). Uji asap itu
   memperlihatkan cacat mekanis: pada 5G-NIDD partisi = berkas dan tiap berkas praktis
   satu kelas, jadi saat satu partisi dihold-out kelasnya hilang dari data latih lipatan
   dan korektor lintas-partisi membuang 35–37% data BERSIH (macro-F1 kontrol 0,99 → 0,16).
   Perbaikan: PENJAGA DUKUNGAN (baris hanya boleh ditandai bila labelnya punya ≥30 baris
   di data latih lipatannya), dipakai seragam oleh cl, cl_xp, oof, oof_xp, dan cpla
   (uji asap v2 di `results_smoke/`). Angka uji asap v1 sudah terlihat sebelum perbaikan;
   ambang CPLA, definisi rezim, metrik, dan gerbang TIDAK diubah.
4. **Ukuran blok R1 dibatasi ketersediaan satu sumber.** R1 menuntut satu grup
   (partisi × sumber × kelas); grup terbesar yang ada hanya
   {pre.get('unsw', {}).get('grup_R1_top5', [{}])[0].get('n', '?')} baris di UNSW dan
   {pre.get('cse', {}).get('grup_R1_top5', [{}])[0].get('n', '?')} baris di CSE, jadi target
   8% (5.600 baris) tidak tercapai di kedua dataset itu. Sel yang terpotong:
   {', '.join(sorted(set(capped))) if capped else 'TIDAK ADA'}.
   Ukuran yang benar-benar tersuntik ada di tabel di atas.
5. **Seed pada sel yang terpotong.** Aturan "jika kurang dari s+1 grup layak, pakai grup
   terbesar" membuat beberapa seed pada ukuran 8% memakai grup yang SAMA; di sel itu seed
   hanya mengubah lipatan OOF dan random_state model, bukan bloknya.
6. **Pemilihan pasangan R2.** Massa konflik vektor identik dipakai di UNSW
   ({pre.get('unsw', {}).get('aturan_pasangan', '-')}) dan CSE
   ({pre.get('cse', {}).get('aturan_pasangan', '-')}); pada 5G-NIDD versi C massa konflik = 0
   (dedup lintas-berkas sudah membuang vektor kembar), jadi aturan cadangan dipakai
   ({pre.get('g5c', {}).get('aturan_pasangan', '-')}).
7. **Paralelisme.** Run berskor dijalankan sebagai DUA proses serentak — satu untuk
   5G-NIDD + UNSW (`--tag _a`), satu untuk CSE (`--tag _cse`) — dengan 8 thread tiap proses
   (total 16 ≤ core logis − 3 = 17), prioritas BelowNormal. Waktu dinding karena itu bukan
   waktu CPU, dan `fit_s` per run lebih lambat daripada bila satu proses memakai semua
   thread. (Lihat juga penyimpangan 13.)
8. **5G-NIDD: versi C saja** (buang + dedup lintas-berkas) — pilot ini butuh kebenaran
   dasar yang bersih; versi A/B tidak dipakai. Folder `study_5gnidd_audit/` hanya dibaca.
9. **UNSW:** `attack_cat` kosong → "Normal"; "Backdoors" disatukan ke "Backdoor"
   (dua ejaan untuk kelas yang sama di berkas berbeda); kolom nominal proto/state/service
   → kode kategori dari peta yang dibangun di train (nilai tak dikenal di test → −1).
10. **Sel selesai:** {nsel} dari {nexp} yang direncanakan"""
      + (" (lengkap)." if nsel >= nexp else " — **ADA SEL TERPOTONG**, lihat `run*.log`.")
      + f"""
11. **Fraksi baris yang tidak bisa diaudit lintas-partisi** (akibat penjaga dukungan):
   """ + "; ".join(f"{DSN[d]} {1-ij[ij.ds==d].frac_auditable_xp.mean():.0%}"
                   for d in ij.ds.unique() if d in DSN)
      + """. Baris itu kebal terhadap semua korektor lintas-partisi — konsekuensi langsung
   dari partisi yang berkorelasi dengan kelas (berkas 5G-NIDD/CSE praktis satu kelas).
12. **cleanlab 2.9.0** terpasang dan dipakai (jalur confident-joint sendiri tidak terpakai;
   dicek di `results/run*.log`). Probabilitas OOF disubset ke baris auditable dan
   dinormalisasi ulang sebelum diberikan ke cleanlab.
13. **Run pertama dibatalkan karena anggaran waktu.** Percobaan pertama memakai tiga proses
   serentak × 5 thread; laju terukur ~18 detik per fit (saturasi bandwidth memori) yang
   berarti >4 jam. Proses dihentikan setelah 3 sel, keluarannya DIPARKIR (bukan dihapus) ke
   `results/*.bak`, lalu run berskor diulang dari nol sebagai dua proses × 8 thread
   (~6 detik per fit). Tidak ada baris hasil dari percobaan pertama yang masuk laporan ini.
14. **`diag.py` dijalankan SETELAH run berskor** dan hanya memutar ulang audit (tanpa melatih
   model hilir, tanpa menyentuh `runs*.csv`); ia memakai mekanik `cpla.py` apa adanya.
   Isinya penjelasan mekanisme, bukan skor baru.
15. **PELANGGARAN BATAS WAKTU.** Anggaran yang diminta 3 jam; realisasi ± 3 jam 10 menit
   dari awal tugas sampai laporan ini (termasuk 2 uji asap, preflight pembangunan cache,
   run berskor yang dibatalkan dan diulang, run berskor 98 menit, dan diagnostik 4 menit).
   Tidak bisa dibatalkan setelah terjadi; dilaporkan apa adanya.
16. **Yang TIDAK diuji:** korektor yang merelabel (CPLA hanya membuang), ukuran blok di atas
   ketersediaan satu sumber, lebih dari satu blok per skenario, model hilir selain
   HistGradientBoosting, dan ambang CPLA selain (30; 0,60; 5,0; 0,30) — tidak ada pencarian
   ambang sama sekali, sesuai aturan pra-registrasi.\n""")

    dp = os.path.join(RES, "DIAG_G5C_R1.json")
    if os.path.exists(dp):
        dg = json.load(open(dp, encoding="utf-8"))
        A("## Mengapa CPLA gagal — mekanisme yang DIVERIFIKASI (bukan dugaan)\n")
        A("Diagnostik `diag.py` memutar ulang audit lintas-partisi pada 9 sel R1 5G-NIDD dan "
          "membuka isi keputusan CPLA untuk grup yang memuat blok tersuntik "
          "(`results/DIAG_G5C_R1.json`).\n")
        A("| ukuran | seed | kelas asli blok | % blok diprediksi Benign oleh auditor "
          "| q dominan | n_b/n_g | rate | latar med | z | lolos ambang CPLA |")
        A("|---" * 10 + "|")
        for r in dg:
            A(f"| {r['size']*100:.0f}% | {r['seed']} | {r['kelas_asli']} | "
              f"{r['frac_diprediksi_benign']*100:.1f}% | {r['blok_q']} | "
              f"{r['blok_n_b']}/{r['grup_n_g']} | {r['blok_rate']:.3f} | "
              f"{r['latar_med']:.3f} | {r['z']} | "
              f"{'ya' if r['lolos_ambang_cpla'] else 'tidak'} |")
        A("""
Dua mekanisme kegagalan, keduanya terbaca langsung di tabel itu:

1. **Blok tak terlihat.** Bila kelas asli blok hanya ada di partisinya sendiri
   (TCPConnectScan hanya di `TCPConnect1.csv`), model lipatan yang tidak pernah melihat
   partisi itu memprediksi **Benign** untuk 99,4–99,6% baris tersuntik — auditor SEPAKAT
   dengan label yang salah. rate blok jatuh ke 0,002–0,004, jadi tidak ada kandidat sama
   sekali. Ini bukan soal ambang: sinyalnya nol.
2. **Latar jenuh.** Bila auditor memang tidak sepakat (SYNScan→Benign diprediksi UDPScan
   pada 97,3–99,5% baris), latar pasangan (Benign→UDPScan) di partisi LAIN juga 1,000 —
   ketidaksepakatan yang sama terjadi di mana-mana, jadi z = −2,71…−0,46 dan penjaga
   `latar med <= 0,30` menolak blok itu. Justru penjaga yang membuat CPLA aman di kontrol
   (G3 TERPENUHI) yang membuatnya buta di sini.

Hanya satu dari tiga blok (UDPScan di `UDPScan1.csv`, latar 0,000 → z ≈ 90) memenuhi kedua
syarat sekaligus, dan di situ CPLA memang menang: presisi deteksi 0,97–0,99, recall 1,00.
Kesimpulan mekanis: daya CPLA dan keamanannya saling bertentangan, dan daerah tempat ia
bekerja sempit — kelas asli blok harus punya kelas kerabat di partisi lain DAN pasangan
label itu harus jarang bertukar di tempat lain.\n""")

    A("## Runtime\n")
    A(f"- Total waktu fit model hilir yang tercatat: {df.fit_s.astype(float).sum()/60:.1f} menit "
      f"({len(df)} baris hasil; 2 proses × 8 thread). Log penuh: "
      f"`{a.res}/run_a.log` (5G-NIDD + UNSW) dan `{a.res}/run_cse.log`.\n")

    gap = (pf["oracle_drop"] - pf["noop"]).dropna() if "oracle_drop" in pf.columns \
        else pd.Series(dtype=float)
    ring = [
        "## Ringkasan\n",
        f"**Gerbang utama: {'TERPENUHI' if gate else 'GAGAL'}.** CPLA tidak mengalahkan "
        "pembanding pada pemulihan tugas hilir. Median ΔF1 CPLA − no-op = "
        f"{np.median((pf['cpla'] - pf['noop']).dropna()):+.4f} atas {len(pf)} sel "
        f"(menang {(pf['cpla'] - pf['noop']).gt(0).sum()}, kalah "
        f"{(pf['cpla'] - pf['noop']).lt(0).sum()}); satu-satunya pembanding yang "
        "dikalahkannya secara signifikan adalah OOF lintas-partisi.\n",
        f"**Noise berblok sering tidak merusak tugas hilir.** Hanya {int((gap >= 0.01).sum())} "
        f"dari {len(gap)} sel tersuntik yang kerusakannya terukur "
        "(oracle-buang − no-op ≥ 0,01 macro-F1); di sel lain tidak ada yang bisa dipulihkan "
        "oleh korektor mana pun.\n",
        "**Yang CPLA menangi: kerusakan.** Pada data bersih CPLA membuang 2,5% baris "
        "(cleanlab 6,1%, OOF global 10,0%, OOF lintas-partisi 13,3%) dan tidak menurunkan "
        "macro-F1 — G3 satu-satunya gerbang yang terpenuhi. Jadi CPLA = korektor paling "
        "konservatif, bukan korektor paling berguna.\n",
        "**Kegagalan terbesar di sel paling merusak.** Pada 5G-NIDD R1 8% (blok 5.169 baris, "
        "no-op 0,875 vs oracle 0,992) CPLA memulihkan 0 — begitu juga cleanlab dan OOF "
        "global; mekanismenya diverifikasi di bagian \"Mengapa CPLA gagal\".\n",
    ]
    L[L.index("@@RINGKASAN@@")] = "\n".join(ring)
    out = os.path.join(HERE, "REPORT.md")
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("tulis", out)


if __name__ == "__main__":
    main()
