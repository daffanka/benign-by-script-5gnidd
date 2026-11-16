"""Pilot C (K4) — run steps 01-04 for every available dataset, then write
pilot_audit/REPORT.md.  Usage: python pilot_audit/run_all.py [--report-only]
"""
import os
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C

STEPS = ["01_profile.py", "02_single_feature.py", "03_split_gap.py", "04_ablation.py"]

DEVIATIONS = [
    "CICIoMT2024 tidak ditemukan di laptop (pencarian 'iomt' di seluruh "
    "<DATA_ROOT> dan drive lain hanya menemukan PDF paper). "
    "Audit berjalan dengan 2 dari 3 dataset. Catatan: ada CIC-ToN-IoT-V2.parquet di "
    "proj/data/cictoniot tetapi itu dataset berbeda (ToN-IoT), tidak dipakai.",
    "LightGBM tidak terpasang di d-env maupun conda base, dan instalasi paket "
    "ditolak oleh kebijakan izin sesi. Pengganti: sklearn "
    "HistGradientBoostingClassifier (algoritma GBDT histogram yang sama; "
    "max_iter=100, lr=0.1, max_bins=255, early_stopping=False, CPU).",
    "Untuk anggaran CPU 3 jam, pelatihan model (langkah 03/04) memakai sampel "
    f"berstratifikasi maksimum {C.MODEL_CAP:,} baris dari cache <=1 juta baris; "
    "profil (langkah 01) tetap dihitung pada SELURUH baris kedua dataset "
    "(5G-NIDD penuh di RAM; CICIoT2023 streaming hash eksak).",
    "5G-NIDD Combined.csv tidak punya kolom waktu ataupun file asal, jadi grup "
    "protokol (c) = 10 blok berurutan menurut urutan baris CSV (proksi waktu; "
    "urutan baris mengikuti penggabungan capture per serangan).",
    "Kolom pertama 5G-NIDD (indeks ekspor tanpa nama, 'row_id') dikeluarkan dari "
    "fitur di semua protokol karena artefak ekspor, tetapi tetap dilaporkan "
    "sebagai kolom identitas. Kolom identitas lain (Seq, Offset, sVid, dVid, "
    "SrcTCPBase, DstTCPBase) IKUT sebagai fitur di langkah 03 dan baru dibuang "
    "pada ablasi (langkah 04), sesuai desain audit.",
    "Kolom 'Attack Tool' 5G-NIDD diperlakukan sebagai metadata label (bukan "
    "fitur) karena menyebut nama alat serangan.",
    "Model memakai l2_regularization=0.1 (bukan 0): tanpa itu HGB sklearn "
    "divergen (skor mentah ~1e6, macro-F1 runtuh pada sebagian seed) karena "
    "tidak punya padanan min_sum_hessian_in_leaf=1e-3 bawaan LightGBM; "
    "l2=0.1 adalah pengganti fungsional penjaga itu.",
    "Baris CICIoT2023 dengan Label kosong (NaN) dibuang dan dihitung "
    "(lihat 'label_na_rows_dropped' di profil).",
    "Kolom dengan <2 nilai non-NaN berbeda pada sampel model dibuang sebelum "
    "fit karena binner HGB sklearn crash pada kolom degenerate (di 5G-NIDD: "
    "sVid/dVid yang praktis seluruhnya NaN); daftar per run ada di log.",
    "Sampling cache memakai seed 0; seed 0/1/2 dipakai untuk split dan model. "
    "Langkah 02 (probing fitur tunggal) memakai seed 0 saja (peringkat, bukan estimasi).",
    "Duplikat CICIoT2023 dihitung pada fitur yang di-cast ke float32 agar hash "
    "stabil antar-chunk; ini bisa menyatukan nilai yang hanya beda presisi "
    "(estimasi duplikat sedikit lebih tinggi dari hitungan float64).",
]


def run_steps():
    py = sys.executable
    errors = []
    for ds in C.DATASETS:
        for step in STEPS:
            t0 = time.time()
            C.log(f"run_all: {ds} :: {step}")
            r = subprocess.run([py, os.path.join(HERE, step), ds],
                               capture_output=True, text=True)
            if r.returncode != 0:
                msg = f"{ds}/{step} FAILED rc={r.returncode}\n{r.stdout[-2000:]}\n{r.stderr[-4000:]}"
                C.log("run_all: " + msg)
                errors.append(msg)
            else:
                C.log(f"run_all: {ds} :: {step} ok ({time.time()-t0:.0f}s)")
    return errors


def ms(vals):
    if not vals:
        return "-"
    m = statistics.mean(vals)
    s = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return f"{m:.3f} ± {s:.3f}"


def agg(res, proto):
    return [r["macro_f1"] for r in res["results"]
            if r["protocol"] == proto and r.get("macro_f1") is not None]


def build_report(errors):
    L = []
    L.append("# Pilot C (K4) — Audit shortcut & leakage: 5G-NIDD, CICIoT2023, (CICIoMT2024)")
    L.append("")
    L.append(f"Tanggal: {time.strftime('%Y-%m-%d %H:%M')}. CPU saja (20 thread), "
             "tanpa GPU. Seed 0/1/2. Semua keluaran di `pilot_audit/`.")
    L.append("")
    L.append("## 1. Profil per dataset")
    L.append("")
    L.append("| Metrik | 5G-NIDD | CICIoT2023 | CICIoMT2024 |")
    L.append("|---|---|---|---|")
    profs = {}
    for ds in C.DATASETS:
        try:
            profs[ds] = C.load_json(f"profile_{ds}.json")
        except Exception:
            profs[ds] = None
    def row(name, fn):
        a = fn(profs["5gnidd"]) if profs.get("5gnidd") else "-"
        b = fn(profs["ciciot2023"]) if profs.get("ciciot2023") else "-"
        L.append(f"| {name} | {a} | {b} | tidak ditemukan |")
    row("Baris", lambda p: f"{p['rows']:,}")
    row("Kolom", lambda p: p["cols"])
    row("Kelas (multikelas)", lambda p: p["n_classes_multi"])
    row("% duplikat persis (fitur+label)", lambda p: f"{p['dup_exact_pct']:.2f}%")
    row("% fitur sama, label beda", lambda p: f"{p['same_feat_diff_label_pct']:.2f}%")
    row("% duplikat persis TANPA kolom identitas",
        lambda p: f"{p.get('dup_exact_pct_no_id', p['dup_exact_pct']):.2f}%")
    row("% fitur sama label beda TANPA kolom identitas",
        lambda p: f"{p.get('same_feat_diff_label_pct_no_id', p['same_feat_diff_label_pct']):.2f}%")
    row("Kolom konstan", lambda p: ", ".join(p["constant_cols"]) or "tidak ada")
    row("Kolom identitas", lambda p: ", ".join(p["identity_cols"]) or "tidak ada")
    L.append("")
    for ds in C.DATASETS:
        p = profs.get(ds)
        if p:
            L.append(f"- **{ds}**: {p['identity_cols_note']}")
    L.append("")

    L.append("## 2. Sepuluh fitur teratas (DecisionTree max_depth=3, 1 fitur, 200k baris)")
    for ds in C.DATASETS:
        try:
            sf = C.load_json(f"single_feature_{ds}.json")
        except Exception:
            L.append(f"\n(single-feature {ds}: tidak ada hasil)")
            continue
        L.append("")
        L.append(f"### {ds}")
        L.append("")
        L.append("| # | Fitur (AUC biner) | AUC | Fitur (macro-F1 multikelas) | F1 |")
        L.append("|---|---|---|---|---|")
        for i in range(10):
            b = sf["top10_auc_bin"][i] if i < len(sf["top10_auc_bin"]) else None
            m = sf["top10_f1_multi"][i] if i < len(sf["top10_f1_multi"]) else None
            bs = f"{b['feature']}{' (ID)' if b['is_identity'] else ''}" if b else "-"
            msn = f"{m['feature']}{' (ID)' if m['is_identity'] else ''}" if m else "-"
            L.append(f"| {i+1} | {bs} | {b['auc_bin'] if b else '-'} | "
                     f"{msn} | {m['f1_multi'] if m else '-'} |")
        L.append("")
        L.append(f"Top-3 yang dibuang pada ablasi: biner {sf['top3_bin']}, "
                 f"multikelas {sf['top3_multi']}.")
    L.append("")

    L.append("## 3. Macro-F1 per protokol split (mean ± sd, 3 seed)")
    L.append("")
    L.append("Model: HistGradientBoosting (pengganti LightGBM, lihat Penyimpangan). "
             "(a) acak berstratifikasi; (b) acak setelah buang duplikat persis; "
             "(c) split bergrup. Ablasi = tanpa top-3 fitur + semua kolom identitas.")
    L.append("")
    L.append("| Dataset | Fitur | (a) acak | (b) acak-dedup | (c) bergrup |")
    L.append("|---|---|---|---|---|")
    for ds in C.DATASETS:
        try:
            full = C.load_json(f"splitgap_{ds}.json")
            L.append(f"| {ds} | semua | {ms(agg(full,'a'))} | {ms(agg(full,'b'))} | "
                     f"{ms(agg(full,'c'))} |")
        except Exception:
            L.append(f"| {ds} | semua | - | - | - |")
        try:
            abl = C.load_json(f"ablation_{ds}.json")
            L.append(f"| {ds} | setelah ablasi | {ms(agg(abl,'a'))} | — | "
                     f"{ms(agg(abl,'c'))} |")
        except Exception:
            L.append(f"| {ds} | setelah ablasi | - | — | - |")
    L.append("")

    L.append("### Recall per kelas (mean 3 seed, fitur lengkap)")
    for ds in C.DATASETS:
        try:
            full = C.load_json(f"splitgap_{ds}.json")
        except Exception:
            continue
        ok_rows = [r for r in full["results"] if r.get("recall_per_class")]
        if not ok_rows:
            continue
        classes = sorted(ok_rows[0]["recall_per_class"])
        L.append("")
        L.append(f"**{ds}** (grup: {full['group_key']})")
        L.append("")
        L.append("| Kelas | (a) acak | (b) dedup | (c) bergrup |")
        L.append("|---|---|---|---|")
        for cls in classes:
            cells = []
            for proto in ["a", "b", "c"]:
                vals = [r["recall_per_class"][cls] for r in ok_rows
                        if r["protocol"] == proto]
                cells.append(ms(vals) if vals else "-")
            L.append(f"| {cls} | {cells[0]} | {cells[1]} | {cells[2]} |")
        miss = sorted({c for r in full["results"] if r["protocol"] == "c"
                       for c in r.get("classes_missing_in_train", [])})
        if miss:
            L.append("")
            L.append(f"Kelas yang pernah hilang dari train pada split bergrup: {miss}.")
    L.append("")

    L.append("## 4. Kunci grup, runtime, error, penyimpangan")
    L.append("")
    L.append("**Kunci grup:**")
    for ds in C.DATASETS:
        try:
            full = C.load_json(f"splitgap_{ds}.json")
            L.append(f"- {ds}: {full['group_key']}")
        except Exception:
            pass
    L.append("- ciciomt2024: tidak ada (dataset tidak ditemukan).")
    L.append("")
    L.append("**Runtime (detik):**")
    L.append("")
    L.append("| Dataset | 01 profil | 02 fitur tunggal | 03 split | 04 ablasi |")
    L.append("|---|---|---|---|---|")
    for ds in C.DATASETS:
        cells = []
        for name in [f"profile_{ds}.json", f"single_feature_{ds}.json",
                     f"splitgap_{ds}.json", f"ablation_{ds}.json"]:
            try:
                cells.append(f"{C.load_json(name)['runtime_s']:.0f}")
            except Exception:
                cells.append("-")
        L.append(f"| {ds} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("**Error:**")
    if errors:
        for e in errors:
            L.append(f"- ```{e[:1500]}```")
    else:
        L.append("- Tidak ada error pada eksekusi langkah 01-04.")
    L.append("")
    L.append("**Penyimpangan dari instruksi:**")
    for d in DEVIATIONS:
        L.append(f"- {d}")
    L.append("")

    with open(os.path.join(HERE, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    C.log("run_all: REPORT.md written")


if __name__ == "__main__":
    errs = [] if "--report-only" in sys.argv else run_steps()
    build_report(errs)
