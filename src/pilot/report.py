"""Pilot Scan: agregasi results/*.json -> REPORT.md. python report.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
ORDER = ["ciciot", "cse", "cictoniot", "unsw"]
NAMA = {"ciciot": "CICIoT2023", "cse": "CSE-CIC-IDS2018",
        "cictoniot": "CIC-ToN-IoT-V2", "unsw": "UNSW-NB15"}

# Butir 1: status kolom identitas pada "versi CSV yang umum dipakai".
# [LOKAL] = diverifikasi dari berkas di laptop; [UMUM] = pengetahuan latar tentang
# distribusi aslinya, TIDAK diverifikasi dari berkas lokal.
CATATAN_ID = {
    "ciciot": "[LOKAL] MERGED_CSV resmi hanya memuat fitur agregat jendela paket + Label; "
              "tidak ada kolom IP/port/timestamp/ID sama sekali, jadi tidak ada yang bisa "
              "bocor lewat kolom identitas pada versi yang umum dipakai.",
    "cse": "[LOKAL] Parquet di laptop sudah tanpa kolom identitas. [UMUM] CSV asli "
           "'TrafficForML_CICFlowMeter' memuat Timestamp dan Dst Port (dan berkas hari "
           "Tuesday-20-02-2018 juga Flow ID/Src IP/Dst IP); banyak pipeline publik ikut "
           "memakai Dst Port/Timestamp sebagai fitur.",
    "cictoniot": "[LOKAL] Parquet di laptop sudah tanpa kolom identitas; glosarium "
                 "'CICFLowMeter Features.csv' (75 fitur) juga tanpa identitas. [UMUM] CSV asli "
                 "CIC-ToN-IoT-V2 (CICFlowMeter) memuat Flow ID, Src/Dst IP, Src/Dst Port, "
                 "Timestamp; versi lokal juga membawa kolom 'Label' biner yang merupakan "
                 "bocoran label murni terhadap kelas 'Attack'.",
    "unsw": "[LOKAL] CSV penuh (4 berkas) = versi umum, memuat srcip/sport/dstip/dsport "
            "(identitas), Stime/Ltime (timestamp), dan stcpb/dtcpb (nomor urut dasar TCP = "
            "mirip-identitas), plus kolom Label biner. [LOKAL] Versi train/test resmi "
            "(UNSW_NB15_training-set) membuang IP/port/waktu TETAPI tetap menyimpan "
            "stcpb/dtcpb sebagai fitur.",
}


def J(ds):
    p = os.path.join(RES, ds + ".json")
    return json.load(open(p)) if os.path.exists(p) else None


def pct(x):
    return f"{x:.2f}%".replace(".", ",")


def num(x):
    return f"{x:,}".replace(",", ".")


def f4(x):
    return f"{x:.4f}".replace(".", ",") if isinstance(x, float) else str(x)


def main():
    L = []
    A = L.append
    A("# Pilot Scan — kualitas label 4 dataset IDS (seluruh baris)\n")
    A("Vektor fitur = semua kolom non-identitas, numerik dikanonikalkan float32; "
      "baris dikelompokkan lewat hash 64-bit (pd.util.hash_pandas_object). "
      "**Duplikat** = baris di luar kemunculan pertama vektornya ((N − vektor unik)/N). "
      "**Konflik** = baris yang vektor fiturnya muncul dengan ≥2 label berbeda. "
      "**Batas atas Bayes** = akurasi/macro-F1 bila tiap vektor diprediksi label "
      "mayoritasnya (performa maksimum model fitur-murni apa pun pada data ini).\n")

    # ringkasan lintas dataset
    A("## Ringkasan (butir 2)\n")
    A("| dataset | baris | vektor unik | % duplikat | vektor konflik | % baris konflik label | Bayes akurasi | Bayes macro-F1 |")
    A("|---|---|---|---|---|---|---|---|")
    for ds in ORDER:
        d = J(ds)
        if not d:
            A(f"| {NAMA[ds]} | TIDAK ADA (pindaian gagal/belum selesai) | | | | | | |")
            continue
        r = d["ringkasan"]
        A(f"| {NAMA[ds]} | {num(r['n_baris'])} | {num(r['n_vektor_unik'])} "
          f"| {pct(r['pct_baris_duplikat'])} | {num(r['n_vektor_konflik'])} "
          f"| {pct(r['pct_baris_konflik_label'])} | {f4(r['bayes_akurasi'])} "
          f"| {f4(r['bayes_macro_f1'])} |")
    A("")

    for ds in ORDER:
        d = J(ds)
        if not d:
            continue
        A(f"## {NAMA[ds]}\n")
        k = d["kolom"]
        A(f"**Butir 1 — kolom identitas.** Terdeteksi lokal: "
          f"{', '.join(c for c in k['identitas_lokal'] if c != 'Label_biner') or 'TIDAK ADA'}"
          f"{'; bocoran label: Label_biner' if 'Label_biner' in k['identitas_lokal'] else ''}. "
          f"Fitur dipakai: {len(k['fitur'])} kolom"
          f" (nominal: {', '.join(k['nominal']) or 'tidak ada'}).")
        A(f"{CATATAN_ID[ds]}\n")
        ce = d["catatan_ekstra"]
        cat_items = []
        if ce.get("label_nan_dibuang"):
            cat_items.append(f"{num(ce['label_nan_dibuang'])} baris tanpa label dibuang")
        if "biner_vs_kelas_mismatch" in ce:
            cat_items.append(f"ketidakcocokan label biner vs kelas: {num(ce['biner_vs_kelas_mismatch'])} baris")
        if ce.get("nilai_nonnumerik_jadi_nan"):
            s = ", ".join(f"{c}: {num(n)}" for c, n in sorted(
                ce["nilai_nonnumerik_jadi_nan"].items(), key=lambda t: -t[1]))
            cat_items.append(f"nilai non-numerik -> NaN ({s})")
        if ce.get("attack_cat_mentah"):
            raw = ce["attack_cat_mentah"]
            s = ", ".join(f"`{repr(c)[1:-1]}`×{num(n)}" for c, n in sorted(
                raw.items(), key=lambda t: -t[1]))
            cat_items.append(f"nilai attack_cat mentah (spasi dipertahankan): {s}")
        if cat_items:
            A("Catatan data: " + "; ".join(cat_items) + ".\n")
        dist = d["distribusi_label"]
        A(f"Kelas: {len(dist)}; benign = `{d['label_benign']}`; 5 terbesar: "
          + ", ".join(f"`{c}` {num(n)}" for c, n in list(dist.items())[:5]) + ".\n")

        A("**Butir 3 — 10 pasangan kelas terbesar yang berbagi vektor identik** "
          "(baris = jumlah baris kedua kelas pada vektor-vektor bersama):\n")
        A("| # | kelas A | kelas B | vektor bersama | baris |")
        A("|---|---|---|---|---|")
        for i, p in enumerate(d["pasangan_top10"], 1):
            A(f"| {i} | {p['kelas_a']} | {p['kelas_b']} | {num(p['vektor'])} | {num(p['baris'])} |")
        if not d["pasangan_top10"]:
            A("| - | TIDAK ADA konflik | | | |")
        A("")

        A("**Butir 4 — detail 3 pasangan terbesar** (3 vektor konflik terbesar per pasangan):\n")
        for p in d["pasangan_top3_detail"]:
            A(f"- **{p['kelas_a']} vs {p['kelas_b']}**")
            for v in p["vektor"]:
                lab = ", ".join(f"{c}: {num(n)}" for c, n in sorted(
                    v["label_baris"].items(), key=lambda t: -t[1]))
                A(f"  - vektor `{v['hash']}` — {num(v['baris_vektor'])} baris total ({lab})")
                ex = v.get("contoh_fitur")
                if isinstance(ex, dict):
                    nz = {c: val for c, val in ex.items()
                          if (isinstance(val, str) and val not in ("0.0", "0", "nan"))
                          or (isinstance(val, float) and val == val and val != 0)}
                    nol = len(ex) - len(nz)
                    A(f"    - fitur ≠ 0: " + ", ".join(
                        f"{c}={val if isinstance(val, str) else round(val, 4)}"
                        for c, val in nz.items()) + f" (+{nol} fitur bernilai 0/NaN)")
                for mname, dd in v.get("sebaran", {}).items():
                    parts = []
                    for lname, cnts in dd.items():
                        s = ", ".join(f"{kk}×{num(n)}" for kk, n in cnts.items())
                        parts.append(f"{lname}: [{s}]")
                    A(f"    - sebaran {mname}: " + "; ".join(parts))
        if not d["pasangan_top3_detail"]:
            A("- TIDAK ADA")
        A("")

        m = d["model_satu_fitur"]
        rows = m["hasil"]
        okb = [r for r in rows if isinstance(r["auc_biner"], float)]
        okm = [r for r in rows if isinstance(r["macro_f1_multikelas"], float)]
        A(f"**Butir 5 — model satu-fitur** (DecisionTree max_depth=3; sampel {num(m['n_sampel'])} "
          f"baris, latih {num(m['latih'])} / uji {num(m['uji'])}):\n")
        A("| peringkat | biner: kolom | jenis | ROC-AUC | multikelas: kolom | jenis | macro-F1 |")
        A("|---|---|---|---|---|---|---|")
        tb = sorted(okb, key=lambda r: -r["auc_biner"])[:5]
        tm = sorted(okm, key=lambda r: -r["macro_f1_multikelas"])[:5]
        for i in range(5):
            b = tb[i] if i < len(tb) else None
            mm = tm[i] if i < len(tm) else None
            A(f"| {i + 1} | {b['kolom'] if b else ''} | {b['jenis'] if b else ''} "
              f"| {f4(b['auc_biner']) if b else ''} | {mm['kolom'] if mm else ''} "
              f"| {mm['jenis'] if mm else ''} | {f4(mm['macro_f1_multikelas']) if mm else ''} |")
        gagal = [r["kolom"] for r in rows if not isinstance(r["auc_biner"], float)
                 or not isinstance(r["macro_f1_multikelas"], float)]
        if gagal:
            A(f"\nKolom gagal dievaluasi: {', '.join(gagal)}.")
        w = d["waktu_detik"]
        A(f"\nWaktu: pass A {w['pass_a']}s, statistik {w['statistik']}s, "
          f"pass B {w['pass_b']}s, model satu-fitur {w['task5']}s.\n")

    A("## Butir 6 — penyimpangan dan keputusan\n")
    du = J("unsw")
    A(f"1. Keempat dataset ditemukan di laptop (UNSW-NB15 = versi 4-CSV penuh"
      f"{', ' + num(du['ringkasan']['n_baris']) + ' baris' if du else ''}); "
      f"TIDAK ADA dataset yang hilang, TIDAK ADA unduhan.")
    A("""2. Pengelompokan vektor memakai hash 64-bit, bukan perbandingan byte penuh; perkiraan
   tabrakan ~N²/2⁶⁵ ≈ 0,06 vektor pada 46,7 jt baris (diabaikan, bisa menggeser hitungan
   ±1 vektor).
3. Numerik dikanonikalkan float32 (+0=-0); nilai yang hanya beda di luar presisi float32
   dianggap sama — konsisten dengan praktik Pilot B.
4. "Baris duplikat" dihitung TANPA memandang label (vektor fitur saja); "baris konflik" =
   semua baris milik vektor yang berlabel ≥2.
5. Jumlah baris pasangan kelas = baris kelas A + baris kelas B pada vektor bersama; satu
   vektor berlabel ≥3 menyumbang ke setiap pasangan di dalamnya.
6. Label mayoritas Bayes: seri dipecah deterministik (kode label terbesar); macro-F1
   dirata-rata atas semua kelas yang ada di data.
7. Model satu-fitur dievaluasi dengan belah-dua sampel 200k (latih 100k, uji 100k, acak
   seed 1); spesifikasi tidak menentukan protokol evaluasi. Kolom nominal/IP di-factorize
   (kode kategori arbitrer); ±inf diganti ±maks float32; NaN ditangani pemecah pohon sklearn.
8. UNSW: attack_cat kosong -> 'Normal'; label dipakai APA ADANYA setelah strip spasi
   (varian 'Backdoor'/'Backdoors' TIDAK digabung — lihat catatan data); sport/dsport
   heksadesimal (mis. 0x000b) diparse basis-16; stcpb/dtcpb diperlakukan mirip-identitas
   (nomor urut TCP acak per koneksi) dan DIKELUARKAN dari vektor fitur.
9. CIC-ToN-IoT-V2: kolom 'Label' biner dikeluarkan dari vektor fitur (bocoran label) tetapi
   diikutkan di model satu-fitur dengan tanda 'bocoran-label'; kelas = kolom 'Attack'.
10. Pemindaian hanya membaca data; TIDAK ADA berkas di luar pilot_scan/ yang ditulis,
    TIDAK ADA commit. CPU saja (17 thread, prioritas BelowNormal).
11. PELANGGARAN BATAS WAKTU: run penuh 5.847 s = 1,62 jam, melebihi batas 1,5 jam
    sekitar 7 menit (CICIoT2023 45 jt baris × 2 pass lebih lambat dari perkiraan);
    uji asap 92 s dilakukan sebelumnya.""")
    out = os.path.join(HERE, "REPORT.md")
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("tulis", out)


if __name__ == "__main__":
    main()
