"""check_numbers.py — pastikan SETIAP angka di tables/*.tex DAN main.tex cocok
dengan satu entri NUMBERS.json (dalam salah satu format penulisan yang dipakai
tables_build / naskah). Keluar dengan kode 1 bila ada angka tak tertelusur.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
E = json.load(open(os.path.join(HERE, "NUMBERS.json"), encoding="utf-8"))["entries"]

# Semua representasi sah dari tiap nilai NUMBERS
valid = set()
for k, e in E.items():
    x = e["value"]
    if isinstance(x, bool) or x is None or isinstance(x, (list, dict)):
        continue
    if isinstance(x, str):
        continue
    if isinstance(x, int):
        valid.add(str(x))
        valid.add(f"{x:,}")
    else:
        for fmt in ("{:.4f}", "{:.2f}", "{:.3f}", "{:.1f}", "{:.6f}", "{}"):
            valid.add(fmt.format(x))

# Token struktural yang bukan "angka hasil": indeks kolom header, CI95,
# penomoran kecil (jumlah model/protokol/fold/seed/bagian), rasio split
# (80/20 protokol literatur; 70/30 split dalam-berkas CSE di studi korektor).
ALLOW = {"95", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "80", "20",
         "70"}

# Tambahan untuk main.tex — tiga kelompok, semuanya BUKAN angka hasil kami:
# (i) penomoran struktural naskah: jumlah model (11), studi SLR (12), skenario
#     per tipe (16), top-k seleksi fitur (25), menit jadwal testbed (30),
#     subsample/batch/budget konfigurasi (50, 100, 1000, 8192, 50000, 200000),
#     ambang keyakinan (0.95);
# (ii) konstanta skema/deskriptif dataset (jumlah kolom 52/112, byte paket
#      flood 84; 42 & 46 & 90 ada di NUMBERS sebagai n_feats);
# (iii) tidak ada tahun di sumber (sitasi lewat natbib).
ALLOW_MAIN = ALLOW | {
    "11", "12", "16", "25", "30", "50", "100", "1000", "8192", "50000",
    "200000", "0.95", "52", "84", "112", "60",
}

# Angka yang DIKUTIP dari paper bersitasi (bukan hasil kami) — hanya untuk
# main.tex; masing-masing tercantum di note K4-REFERENSI.bib / abstrak paper:
# 99.9 (frasa umum literatur, judul), 99.6 (bouke2024), 0.9997 (uccello2026),
# 0.9996 & 78 (ilias2024), 99.79 (harshdeep2025), 99.74 (saranya2025),
# 0.9998 (moubayed2024), 41.7 (olaniyi2026), 99 ("99%+").
LIT_MAIN = {"99.9", "99.6", "0.9997", "0.9996", "78", "99.79", "99.74",
            "0.9998", "41.7", "99"}


def match(tok, allow):
    if tok in allow or tok in valid:
        return True
    if ("-" + tok) in valid:  # nilai negatif ditulis tanpa tanda di token
        return True
    if tok.isdigit() and (f"{int(tok):,}" in valid or str(int(tok)) in valid):
        return True
    return False


def scan(path, txt, allow, bad):
    txt = re.sub(r"\\(?:cmidrule|multicolumn)\s*(?:\(\w*\))?\{[^}]*\}", " ", txt)
    txt = txt.replace("\\,", "")  # pemisah ribuan
    # tanda hubung/minus menjadi spasi supaya rentang "0.74--0.77" dan nilai
    # negatif tertokenisasi utuh; angka menempel nama (b12, CICIoT2023,
    # UNSW-NB15) tetap tersaring oleh lookbehind huruf/angka
    txt = txt.replace("-", " ")
    for tok in re.findall(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?", txt):
        if not match(tok, allow):
            bad.append((os.path.basename(path), tok))


bad = []
for p in sorted(glob.glob(os.path.join(HERE, "tables", "*.tex"))):
    scan(p, open(p, encoding="utf-8").read(), ALLOW, bad)

mainp = os.path.join(HERE, "main.tex")
if os.path.exists(mainp):
    txt = open(mainp, encoding="utf-8").read()
    # buang komentar, argumen perintah non-isi, opsi, ukuran, dan alamat IP
    txt = re.sub(r"(?<!\\)%.*", " ", txt)
    # argumen perintah non-isi; \texttt = nama berkas/skrip & hash skrip
    # (mis. 599d2aeef79d) — identifier, bukan angka hasil
    txt = re.sub(r"\\(?:cite[tp]?|ref|label|input|bibliography|bibliographystyle|"
                 r"documentclass|usepackage|journal|includegraphics|begin|end|"
                 r"newenvironment|cortext|corref|ead|affiliation|setlength|texttt)"
                 r"(?:\[[^\]]*\])?\{[^{}]*\}", " ", txt)
    txt = re.sub(r"\[[^\]]*\]", " ", txt)                      # sisa opsi [..]
    txt = re.sub(r"[\d.]+(?:pt|em|ex|cm|mm|in)\b", " ", txt)   # ukuran
    txt = re.sub(r"[\d.]+\\(?:line|text|column)width", " ", txt)
    txt = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", " ", txt)     # alamat IP
    scan(mainp, txt, ALLOW_MAIN | LIT_MAIN, bad)

if bad:
    print("ANGKA TAK TERTELUSUR ke NUMBERS.json:")
    for f, t in bad:
        print(f"  {f}: {t}")
    sys.exit(1)
print("check_numbers: OK — semua angka di tabel dan main.tex tertelusur ke NUMBERS.json.")
