"""Agregasi results/runs.csv -> REPORT.md. python report.py"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
MODELS = ["MLP3", "CNN1D", "LSTM", "TRF", "TABICL"]
COMBOS = [("lit", "A"), ("noid", "A"), ("noid", "B"),
          ("b12", "A"), ("b12", "B"), ("b21", "A"), ("b21", "B")]
PNAME = {"lit": "(i) lit acak 80/20", "noid": "(ii) noid acak 80/20",
         "b12": "(iii) BS1→BS2", "b21": "(iv) BS2→BS1"}
ARCH = {
    "MLP3": "MLP 3 lapis tersembunyi 256-128-64 ReLU",
    "CNN1D": "Conv1d(1→32,k5)-MaxPool2-Conv1d(32→64,k3)-MaxPool2-FC128",
    "LSTM": "LSTM(input=1, hidden=64) atas urutan fitur, keluaran langkah terakhir",
    "TRF": "Transformer encoder 2 lapis (d=32, 4 head, ff=64) + pos-embedding, mean-pool",
    "TABICL": "TabICL v2 (checkpoint lokal), konteks seimbang ≤10.000 baris train",
}


def ms(g, col, p=4):
    v = g[col].dropna().astype(float)
    if not len(v):
        return "TIDAK ADA"
    m = f"{v.mean():.{p}f}"
    return f"{m} ± {v.std(ddof=1):.{p}f}" if len(v) > 1 else m


def main():
    df = pd.read_csv(os.path.join(RES, "runs.csv"))
    classes = sorted(c[len("rec_"):] for c in df.columns
                     if c.startswith("rec_") and not c.startswith("rec_korr_"))
    L = []
    A = L.append
    A("# Replikasi deep learning K4 — audit 5G-NIDD\n")
    A("Data: `study_5gnidd_audit/cache/full.parquet` (keluaran make_clean.py; hanya dibaca). "
      "1.215.890 baris, 9 kelas; versi A = label asli, B = relabel 281.529 baris "
      "(aturan C4). Seed 0/1/2. GPU RTX 3070 Ti Laptop 8 GB, python d-env "
      "(torch 2.11.0+cu128), tabicl dari conda project-data-fixed.\n")
    A("Model (arsitektur dipilih sendiri — spesifikasi hanya menyebut jenisnya; "
      "semua torch: Adam lr 1e-3, batch 8192, 10 epoch, CE tanpa bobot kelas, "
      "tanpa early stopping; fitur = encode_features pilot_audit [numerik apa adanya, "
      "nominal → kode kategori], inf→NaN → imputasi median train → standardisasi "
      "mu/sd train; TabICL menerima matriks imputasi tanpa standardisasi):\n")
    for m in MODELS:
        A(f"- **{m}**: {ARCH[m]}")
    A("")
    A("Protokol: (i) `lit` = semua 48 kolom termasuk Seq/Offset, acak 80/20 "
      "stratified, versi A, dinilai vs label asli DAN label terkoreksi; "
      "(ii) `noid` = 42 fitur non-identitas, acak 80/20, versi A dan B; "
      "(iii) `b12` = latih BS1 uji BS2; (iv) `b21` = latih BS2 uji BS1 "
      "(keduanya non-identitas, A dan B). Biner diturunkan dari multikelas "
      "(pred ≠ Benign). Catatan: seluruh 281.529 baris salah-label berada di BS1, "
      "jadi test b12 tidak memuat baris salah-label, test b21 memuat semuanya.\n")

    n_runs = len(df)
    A(f"Run selesai: **{n_runs}** dari 105 rencana (7 protokol-versi × 5 model × 3 seed)."
      + (" **ADA RUN TERPOTONG** — lihat penyimpangan." if n_runs < 105 else "") + "\n")

    # tabel utama
    for metr, judul, p in (("f1_macro", "Macro-F1", 4), ("acc", "Akurasi", 4)):
        A(f"## {judul} (mean ± sd atas 3 seed)\n")
        A("| protokol-versi | " + " | ".join(MODELS) + " |")
        A("|---" * 6 + "|")
        for proto, ver in COMBOS:
            cells = []
            for m in MODELS:
                g = df[(df.protokol == proto) & (df.versi == ver) & (df.model == m)]
                cells.append(ms(g, metr, p))
            A(f"| {PNAME[proto]} — {ver} | " + " | ".join(cells) + " |")
        A("")

    A("## TPR / FPR biner (mean atas 3 seed; serangan = pred ≠ Benign)\n")
    A("| protokol-versi | " + " | ".join(MODELS) + " |")
    A("|---" * 6 + "|")
    for proto, ver in COMBOS:
        cells = []
        for m in MODELS:
            g = df[(df.protokol == proto) & (df.versi == ver) & (df.model == m)]
            if not len(g):
                cells.append("TIDAK ADA")
                continue
            cells.append(f"{g.tpr.astype(float).mean():.4f} / "
                         f"{g.fpr.astype(float).mean():.4f}")
        A(f"| {PNAME[proto]} — {ver} | " + " | ".join(cells) + " |")
    A("")

    # protokol (i): vs korr + % mis -> Benign
    A("## Protokol (i) lit — versi A dinilai vs label asli DAN label terkoreksi\n")
    A("| model | acc vs asli | acc vs korr | macro-F1 vs asli | macro-F1 vs korr "
      "| % baris salah-label di test yang diprediksi Benign | n salah-label di test eval |")
    A("|---" * 7 + "|")
    for m in MODELS:
        g = df[(df.protokol == "lit") & (df.versi == "A") & (df.model == m)]
        nm = (str(int(g.n_mis_test_eval.astype(float).mean()))
              if len(g) and g.n_mis_test_eval.notna().any() else "TIDAK ADA")
        A(f"| {m} | {ms(g, 'acc')} | {ms(g, 'acc_korr')} | {ms(g, 'f1_macro')} "
          f"| {ms(g, 'f1_macro_korr')} | {ms(g, 'pct_mis_benign', 2)} | {nm} |")
    A("")
    A("(Juga dihitung — gratis — untuk semua run versi A lain; kolom `*_korr` dan "
      "`pct_mis_benign` di `results/runs.csv`. Pada b21-A seluruh 281.529 baris "
      "salah-label ada di test.)\n")
    gb = df[(df.protokol == "b21") & (df.versi == "A")]
    if len(gb):
        A("Ringkas b21-A, % salah-label diprediksi Benign: "
          + "; ".join(f"{m}: {ms(gb[gb.model == m], 'pct_mis_benign', 2)}"
                      for m in MODELS) + ".\n")

    A("### Protokol (i) — recall per kelas vs LABEL TERKOREKSI (mean ± sd)\n")
    A("| model | " + " | ".join(classes) + " |")
    A("|---" * (len(classes) + 1) + "|")
    for m in MODELS:
        g = df[(df.protokol == "lit") & (df.versi == "A") & (df.model == m)]
        A(f"| {m} | " + " | ".join(ms(g, f"rec_korr_{c}", 3) for c in classes) + " |")
    A("")

    # recall per kelas
    A("## Recall per kelas vs label referensi masing-masing versi (mean ± sd atas 3 seed)\n")
    for proto, ver in COMBOS:
        A(f"### {PNAME[proto]} — versi {ver}\n")
        A("| model | " + " | ".join(classes) + " |")
        A("|---" * (len(classes) + 1) + "|")
        for m in MODELS:
            g = df[(df.protokol == proto) & (df.versi == ver) & (df.model == m)]
            A(f"| {m} | " + " | ".join(ms(g, f"rec_{c}", 3) for c in classes) + " |")
        A("")

    # runtime
    A("## Runtime\n")
    tot = df.fit_s.astype(float).sum() + df.pred_s.astype(float).sum()
    A(f"- Total fit+pred semua run: {tot/60:.1f} menit; per model (fit, rerata): "
      + "; ".join(f"{m} {df[df.model == m].fit_s.astype(float).mean():.0f}s"
                  for m in MODELS) + ".")
    A(f"- TabICL: konteks {df[df.model == 'TABICL'].n_ctx.astype(float).mean():.0f} "
      f"rerata; prediksi {df[df.model == 'TABICL'].baris_per_detik.astype(float).mean():.0f} "
      "baris/detik rerata.\n")

    A("## Penyimpangan dan keputusan\n")
    A("""1. Arsitektur, optimasi, dan jumlah epoch TIDAK ditentukan spesifikasi — pilihan
   saya dicatat di atas dan di `results/configs.jsonl`; tanpa early stopping dan tanpa
   bobot kelas (meniru praktik literatur sederhana).
2. TabICL dievaluasi pada SUBSET test stratified 50.000 baris per run (bukan test penuh;
   throughput TabICL membuat test penuh melampaui anggaran 3 jam); model torch dievaluasi
   pada test penuh. Jumlah baris salah-label dalam subset dilaporkan di tabel.
3. TabICL memakai konteks seimbang ≤10.000 baris (kuota rata per kelas, sisa diisi acak);
   kelas dengan baris < kuota memakai semuanya.
4. Versi C (buang+dedup) TIDAK dipakai — protokol yang diminta hanya menyentuh A dan B.
5. Split b12/b21 tetap antar seed (seed hanya mengubah inisialisasi bobot / sampling
   konteks dan subset eval TabICL) — sama dengan praktik E2.
6. Praproses torch: inf→NaN, imputasi median train, standardisasi mu/sd train.
   TabICL menerima matriks imputasi TANPA standardisasi (normalisasi internal TabICL).
7. Metrik, encode fitur, dan turunan biner identik dengan E2 (study_5gnidd_audit);
   folder audit hanya dibaca, tidak diubah.
8. Uji asap 40 ribu baris (hasil di `results_smoke/`) dilakukan sebelum run penuh.
9. Run pertama memakai nama kolom CSV yang salah untuk recall-per-kelas vs label
   terkoreksi (nilainya tidak tersimpan); 15 run protokol (i) lit-A DIULANG dengan skema
   kolom yang benar (seed & konfigurasi sama; CSV lama di `results/runs_old_schema.csv.bak`
   — selisih lit-A lama vs ulangan: maks 0,00024 pada acc/macro-F1, 0,078 poin-persen
   pada pct_mis_benign; nondeterminisme GPU). Recall per
   kelas vs korr untuk run versi A protokol lain (tidak diwajibkan spesifikasi)
   TIDAK tersedia di CSV; agregat acc/F1/TPR/FPR vs korr tetap lengkap.""")
    rc = os.path.join(RES, "runs.csv")
    A(f"\nAngka mentah per run: `{os.path.relpath(rc, HERE)}`; "
      "config per run: `results/configs.jsonl`.")
    out = os.path.join(HERE, "REPORT.md")
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("tulis", out)


if __name__ == "__main__":
    main()
