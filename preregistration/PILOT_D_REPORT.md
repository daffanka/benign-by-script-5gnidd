# Pilot D (CPLA) — audit lintas-partisi + koreksi vs pemulihan tugas hilir

Aturan skor, rezim noise, ambang CPLA, dan gerbang dikunci di docstring `cpla.py` sebelum run (sha256 `599d2aeef79dfd1c…`, lengkap di `results/SCRIPT.sha256`). Angka mentah: `results/runs.csv`; blok CPLA: `results/cpla_blocks.jsonl`; suntikan: `results/inject.jsonl`.

## Ringkasan

**Gerbang utama: GAGAL.** CPLA tidak mengalahkan pembanding pada pemulihan tugas hilir. Median ΔF1 CPLA − no-op = +0.0000 atas 54 sel (menang 24, kalah 26); satu-satunya pembanding yang dikalahkannya secara signifikan adalah OOF lintas-partisi.

**Noise berblok sering tidak merusak tugas hilir.** Hanya 13 dari 54 sel tersuntik yang kerusakannya terukur (oracle-buang − no-op ≥ 0,01 macro-F1); di sel lain tidak ada yang bisa dipulihkan oleh korektor mana pun.

**Yang CPLA menangi: kerusakan.** Pada data bersih CPLA membuang 2,5% baris (cleanlab 6,1%, OOF global 10,0%, OOF lintas-partisi 13,3%) dan tidak menurunkan macro-F1 — G3 satu-satunya gerbang yang terpenuhi. Jadi CPLA = korektor paling konservatif, bukan korektor paling berguna.

**Kegagalan terbesar di sel paling merusak.** Pada 5G-NIDD R1 8% (blok 5.169 baris, no-op 0,875 vs oracle 0,992) CPLA memulihkan 0 — begitu juga cleanlab dan OOF global; mekanismenya diverifikasi di bagian "Mengapa CPLA gagal".

## Dataset, partisi, split

| dataset | baris train / test | fitur | kelas | partisi train | sumber train | Benign | split evaluasi |
|---|---|---|---|---|---|---|---|
| 5G-NIDD versi C | 64.607 / 28.355 | 42 | 9 | 10 | 79 | `Benign` | antar-partisi sejati: train BS1 → test BS2 |
| UNSW-NB15 | 69.994 / 29.999 | 39 | 10 | 3 | 32 | `Normal` | antar-partisi sejati: train berkas 1–3 → test berkas 4 |
| CSE-CIC-IDS2018 | 69.997 / 30.000 | 77 | 15 | 10 | 2.723 | `Benign` | urutan baris dalam berkas 70/30 (BUKAN antar-berkas; lihat penyimpangan 1) |

Blok R1 terbesar yang tersedia (partisi × sumber × kelas) dan pasangan R2 terpilih:

| dataset | grup R1 terbesar | n | pasangan R2 | aturan pemilihan pasangan |
|---|---|---|---|---|
| 5G-NIDD versi C | TCPConnect1.csv / 10.155.15.1 / TCPConnectScan | 5896 | SYNScan ↔ UDPScan | cadangan: kebingungan OOF lintas-partisi = 9996 |
| UNSW-NB15 | UNSW-NB15_1.csv / 175.45.176.1 / Generic | 4471 | DoS ↔ Exploits | massa konflik vektor identik = 3314 |
| CSE-CIC-IDS2018 | Bruteforce-Wednesday-14-02-2018 / 6|26883|230|32 / SSH-Bruteforce | 3464 | Benign ↔ Infilteration | massa konflik vektor identik = 142 |

## Ukuran blok yang benar-benar tersuntik

| dataset | rezim | target % | target baris | tercapai (3 seed) | kurang dari target |
|---|---|---|---|---|---|
| 5G-NIDD versi C | R1 | 1.0% | 646 | 646, 646, 646 | tidak |
| 5G-NIDD versi C | R1 | 3.0% | 1.938 | 1938, 1938, 1938 | tidak |
| 5G-NIDD versi C | R1 | 8.0% | 5.169 | 5169, 5169, 5169 | tidak |
| 5G-NIDD versi C | R2 | 1.0% | 646 | 646, 646, 646 | tidak |
| 5G-NIDD versi C | R2 | 3.0% | 1.938 | 1938, 1938, 1938 | tidak |
| 5G-NIDD versi C | R2 | 8.0% | 5.169 | 5169, 4908, 4908 | ya |
| UNSW-NB15 | R1 | 1.0% | 700 | 700, 700, 700 | tidak |
| UNSW-NB15 | R1 | 3.0% | 2.100 | 2100, 2100, 2100 | tidak |
| UNSW-NB15 | R1 | 8.0% | 5.600 | 4471, 4471, 4471 | ya |
| UNSW-NB15 | R2 | 1.0% | 700 | 700, 700, 700 | tidak |
| UNSW-NB15 | R2 | 3.0% | 2.100 | 2100, 2100, 2100 | tidak |
| UNSW-NB15 | R2 | 8.0% | 5.600 | 5600, 5600, 5600 | tidak |
| CSE-CIC-IDS2018 | R1 | 1.0% | 700 | 700, 700, 700 | tidak |
| CSE-CIC-IDS2018 | R1 | 3.0% | 2.100 | 2100, 2100, 2100 | tidak |
| CSE-CIC-IDS2018 | R1 | 8.0% | 5.600 | 3464, 3464, 3464 | ya |
| CSE-CIC-IDS2018 | R2 | 1.0% | 700 | 700, 700, 700 | tidak |
| CSE-CIC-IDS2018 | R2 | 3.0% | 2.100 | 2100, 2100, 2100 | tidak |
| CSE-CIC-IDS2018 | R2 | 8.0% | 5.600 | 5600, 5600, 5600 | tidak |

Fraksi baris train yang bisa diaudit lintas-partisi (penjaga dukungan): 5G-NIDD versi C 0.64; UNSW-NB15 1.00; CSE-CIC-IDS2018 0.68.

## Macro-F1 pada test (metrik kemenangan utama)

### 5G-NIDD versi C (mean ± sd atas 3 seed)

| rezim / ukuran | no-op | cleanlab (OOF global) | cleanlab (OOF lintas-partisi) | OOF global | OOF lintas-partisi | **CPLA** | oracle (buang) | oracle (perbaiki) |
|---|---|---|---|---|---|---|---|---|
| kontrol bersih | 0.9917 ± 0.0000 | 0.9922 ± 0.0001 | 0.9918 ± 0.0002 | 0.9922 ± 0.0004 | 0.9841 ± 0.0062 | 0.9924 ± 0.0000 | TIDAK ADA | TIDAK ADA |
| R1 1.0% | 0.9916 ± 0.0002 | 0.9922 ± 0.0002 | 0.9917 ± 0.0003 | 0.9919 ± 0.0015 | 0.9794 ± 0.0137 | 0.9916 ± 0.0005 | 0.9917 ± 0.0003 | 0.9917 ± 0.0000 |
| R1 3.0% | 0.9910 ± 0.0007 | 0.9916 ± 0.0005 | 0.9907 ± 0.0009 | 0.9902 ± 0.0024 | 0.9830 ± 0.0088 | 0.9915 ± 0.0009 | 0.9913 ± 0.0004 | 0.9917 ± 0.0000 |
| R1 8.0% | 0.8748 ± 0.0004 | 0.8750 ± 0.0002 | 0.8755 ± 0.0001 | 0.8749 ± 0.0007 | 0.9051 ± 0.0603 | 0.8750 ± 0.0003 | 0.9921 ± 0.0001 | 0.9917 ± 0.0000 |
| R2 1.0% | 0.9917 ± 0.0001 | 0.9923 ± 0.0003 | 0.9919 ± 0.0004 | 0.9917 ± 0.0012 | 0.8888 ± 0.0755 | 0.8984 ± 0.0812 | 0.9916 ± 0.0005 | 0.9917 ± 0.0000 |
| R2 3.0% | 0.9903 ± 0.0010 | 0.9892 ± 0.0039 | 0.9905 ± 0.0007 | 0.9914 ± 0.0001 | 0.9308 ± 0.0738 | 0.9130 ± 0.0472 | 0.9915 ± 0.0003 | 0.9917 ± 0.0000 |
| R2 8.0% | 0.8442 ± 0.0003 | 0.8443 ± 0.0004 | 0.8443 ± 0.0003 | 0.8445 ± 0.0002 | 0.8193 ± 0.0334 | 0.8125 ± 0.0549 | 0.9032 ± 0.0767 | 0.9917 ± 0.0000 |

### UNSW-NB15 (mean ± sd atas 3 seed)

| rezim / ukuran | no-op | cleanlab (OOF global) | cleanlab (OOF lintas-partisi) | OOF global | OOF lintas-partisi | **CPLA** | oracle (buang) | oracle (perbaiki) |
|---|---|---|---|---|---|---|---|---|
| kontrol bersih | 0.6910 ± 0.0000 | 0.6806 ± 0.0003 | 0.6804 ± 0.0000 | 0.6789 ± 0.0064 | 0.6777 ± 0.0000 | 0.6798 ± 0.0000 | TIDAK ADA | TIDAK ADA |
| R1 1.0% | 0.6890 ± 0.0010 | 0.6828 ± 0.0019 | 0.6755 ± 0.0035 | 0.6772 ± 0.0039 | 0.6727 ± 0.0013 | 0.6863 ± 0.0036 | 0.6854 ± 0.0010 | 0.6910 ± 0.0000 |
| R1 3.0% | 0.6826 ± 0.0082 | 0.6747 ± 0.0070 | 0.6744 ± 0.0081 | 0.6708 ± 0.0079 | 0.6737 ± 0.0041 | 0.6605 ± 0.0361 | 0.6827 ± 0.0039 | 0.6910 ± 0.0000 |
| R1 8.0% | 0.6901 ± 0.0000 | 0.6830 ± 0.0006 | 0.6805 ± 0.0000 | 0.6788 ± 0.0067 | 0.6786 ± 0.0000 | 0.6891 ± 0.0000 | 0.6930 ± 0.0000 | 0.6910 ± 0.0000 |
| R2 1.0% | 0.6895 ± 0.0020 | 0.6816 ± 0.0031 | 0.6783 ± 0.0040 | 0.6804 ± 0.0042 | 0.6727 ± 0.0046 | 0.6828 ± 0.0048 | 0.6925 ± 0.0038 | 0.6910 ± 0.0000 |
| R2 3.0% | 0.6911 ± 0.0019 | 0.6832 ± 0.0014 | 0.6808 ± 0.0011 | 0.6825 ± 0.0036 | 0.6739 ± 0.0012 | 0.6828 ± 0.0052 | 0.6842 ± 0.0048 | 0.6910 ± 0.0000 |
| R2 8.0% | 0.6791 ± 0.0071 | 0.6755 ± 0.0110 | 0.6663 ± 0.0124 | 0.6742 ± 0.0051 | 0.6578 ± 0.0090 | 0.6720 ± 0.0055 | 0.6768 ± 0.0024 | 0.6910 ± 0.0000 |

### CSE-CIC-IDS2018 (mean ± sd atas 3 seed)

| rezim / ukuran | no-op | cleanlab (OOF global) | cleanlab (OOF lintas-partisi) | OOF global | OOF lintas-partisi | **CPLA** | oracle (buang) | oracle (perbaiki) |
|---|---|---|---|---|---|---|---|---|
| kontrol bersih | 0.1954 ± 0.0000 | 0.2087 ± 0.0045 | 0.2093 ± 0.0022 | 0.2149 ± 0.0007 | 0.2040 ± 0.0076 | 0.2033 ± 0.0000 | TIDAK ADA | TIDAK ADA |
| R1 1.0% | 0.1942 ± 0.0006 | 0.2043 ± 0.0025 | 0.2034 ± 0.0045 | 0.2050 ± 0.0020 | 0.1988 ± 0.0053 | 0.2004 ± 0.0062 | 0.2014 ± 0.0015 | 0.1954 ± 0.0000 |
| R1 3.0% | 0.1781 ± 0.0291 | 0.1891 ± 0.0272 | 0.2064 ± 0.0064 | 0.1867 ± 0.0272 | 0.1973 ± 0.0050 | 0.2073 ± 0.0059 | 0.2015 ± 0.0039 | 0.1954 ± 0.0000 |
| R1 8.0% | 0.1951 ± 0.0000 | 0.2083 ± 0.0025 | 0.2071 ± 0.0038 | 0.2029 ± 0.0032 | 0.2030 ± 0.0077 | 0.2045 ± 0.0023 | 0.2157 ± 0.0000 | 0.1954 ± 0.0000 |
| R2 1.0% | 0.1946 ± 0.0004 | 0.2077 ± 0.0034 | 0.2115 ± 0.0060 | 0.2059 ± 0.0070 | 0.2036 ± 0.0063 | 0.2053 ± 0.0002 | 0.1969 ± 0.0041 | 0.1954 ± 0.0000 |
| R2 3.0% | 0.1938 ± 0.0009 | 0.2079 ± 0.0061 | 0.2130 ± 0.0073 | 0.2034 ± 0.0093 | 0.1991 ± 0.0037 | 0.2033 ± 0.0020 | 0.2039 ± 0.0009 | 0.1954 ± 0.0000 |
| R2 8.0% | 0.1925 ± 0.0026 | 0.2087 ± 0.0028 | 0.2021 ± 0.0016 | 0.2048 ± 0.0037 | 0.1996 ± 0.0025 | 0.1984 ± 0.0063 | 0.2018 ± 0.0006 | 0.1954 ± 0.0000 |

## FPR biner pada test (lebih kecil lebih baik)

### 5G-NIDD versi C (mean ± sd atas 3 seed)

| rezim / ukuran | no-op | cleanlab (OOF global) | cleanlab (OOF lintas-partisi) | OOF global | OOF lintas-partisi | **CPLA** | oracle (buang) | oracle (perbaiki) |
|---|---|---|---|---|---|---|---|---|
| kontrol bersih | 0.0003 ± 0.0000 | 0.0003 ± 0.0001 | 0.0003 ± 0.0000 | 0.0009 ± 0.0001 | 0.0007 ± 0.0003 | 0.0004 ± 0.0000 | TIDAK ADA | TIDAK ADA |
| R1 1.0% | 0.0004 ± 0.0002 | 0.0007 ± 0.0001 | 0.0004 ± 0.0002 | 0.0010 ± 0.0001 | 0.0006 ± 0.0001 | 0.0002 ± 0.0001 | 0.0003 ± 0.0001 | 0.0003 ± 0.0000 |
| R1 3.0% | 0.0005 ± 0.0004 | 0.0004 ± 0.0003 | 0.0006 ± 0.0005 | 0.0011 ± 0.0003 | 0.0007 ± 0.0004 | 0.0002 ± 0.0001 | 0.0007 ± 0.0005 | 0.0003 ± 0.0000 |
| R1 8.0% | 0.0002 ± 0.0002 | 0.0004 ± 0.0003 | 0.0002 ± 0.0002 | 0.0003 ± 0.0002 | 0.0003 ± 0.0003 | 0.0001 ± 0.0000 | 0.0008 ± 0.0004 | 0.0003 ± 0.0000 |
| R2 1.0% | 0.0004 ± 0.0002 | 0.0005 ± 0.0003 | 0.0003 ± 0.0000 | 0.0010 ± 0.0001 | 0.0009 ± 0.0005 | 0.0005 ± 0.0004 | 0.0003 ± 0.0000 | 0.0003 ± 0.0000 |
| R2 3.0% | 0.0005 ± 0.0004 | 0.0007 ± 0.0003 | 0.0002 ± 0.0000 | 0.0009 ± 0.0001 | 0.0006 ± 0.0000 | 0.0005 ± 0.0004 | 0.0005 ± 0.0003 | 0.0003 ± 0.0000 |
| R2 8.0% | 0.0003 ± 0.0000 | 0.0004 ± 0.0000 | 0.0003 ± 0.0001 | 0.0009 ± 0.0002 | 0.0009 ± 0.0005 | 0.0005 ± 0.0003 | 0.0002 ± 0.0001 | 0.0003 ± 0.0000 |

### UNSW-NB15 (mean ± sd atas 3 seed)

| rezim / ukuran | no-op | cleanlab (OOF global) | cleanlab (OOF lintas-partisi) | OOF global | OOF lintas-partisi | **CPLA** | oracle (buang) | oracle (perbaiki) |
|---|---|---|---|---|---|---|---|---|
| kontrol bersih | 0.0188 ± 0.0000 | 0.0186 ± 0.0000 | 0.0186 ± 0.0000 | 0.0186 ± 0.0000 | 0.0194 ± 0.0000 | 0.0188 ± 0.0000 | TIDAK ADA | TIDAK ADA |
| R1 1.0% | 0.0190 ± 0.0001 | 0.0190 ± 0.0005 | 0.0190 ± 0.0003 | 0.0186 ± 0.0000 | 0.0193 ± 0.0001 | 0.0190 ± 0.0003 | 0.0188 ± 0.0000 | 0.0188 ± 0.0000 |
| R1 3.0% | 0.0190 ± 0.0000 | 0.0190 ± 0.0005 | 0.0186 ± 0.0001 | 0.0192 ± 0.0006 | 0.0194 ± 0.0003 | 0.0187 ± 0.0001 | 0.0188 ± 0.0000 | 0.0188 ± 0.0000 |
| R1 8.0% | 0.0190 ± 0.0000 | 0.0190 ± 0.0003 | 0.0186 ± 0.0000 | 0.0194 ± 0.0000 | 0.0206 ± 0.0000 | 0.0188 ± 0.0000 | 0.0188 ± 0.0000 | 0.0188 ± 0.0000 |
| R2 1.0% | 0.0188 ± 0.0000 | 0.0186 ± 0.0001 | 0.0187 ± 0.0001 | 0.0186 ± 0.0000 | 0.0193 ± 0.0001 | 0.0188 ± 0.0001 | 0.0188 ± 0.0000 | 0.0188 ± 0.0000 |
| R2 3.0% | 0.0188 ± 0.0000 | 0.0186 ± 0.0000 | 0.0186 ± 0.0001 | 0.0186 ± 0.0000 | 0.0193 ± 0.0001 | 0.0188 ± 0.0000 | 0.0188 ± 0.0000 | 0.0188 ± 0.0000 |
| R2 8.0% | 0.0188 ± 0.0000 | 0.0186 ± 0.0000 | 0.0188 ± 0.0003 | 0.0186 ± 0.0000 | 0.0192 ± 0.0001 | 0.0188 ± 0.0000 | 0.0187 ± 0.0001 | 0.0188 ± 0.0000 |

### CSE-CIC-IDS2018 (mean ± sd atas 3 seed)

| rezim / ukuran | no-op | cleanlab (OOF global) | cleanlab (OOF lintas-partisi) | OOF global | OOF lintas-partisi | **CPLA** | oracle (buang) | oracle (perbaiki) |
|---|---|---|---|---|---|---|---|---|
| kontrol bersih | 0.0226 ± 0.0000 | 0.0391 ± 0.0008 | 0.0341 ± 0.0014 | 0.0212 ± 0.0007 | 0.0507 ± 0.0109 | 0.0842 ± 0.0000 | TIDAK ADA | TIDAK ADA |
| R1 1.0% | 0.0223 ± 0.0006 | 0.0381 ± 0.0001 | 0.0343 ± 0.0005 | 0.0214 ± 0.0008 | 0.0476 ± 0.0208 | 0.0826 ± 0.0008 | 0.0237 ± 0.0014 | 0.0226 ± 0.0000 |
| R1 3.0% | 0.0218 ± 0.0005 | 0.0380 ± 0.0015 | 0.0342 ± 0.0010 | 0.0202 ± 0.0009 | 0.0547 ± 0.0081 | 0.0824 ± 0.0024 | 0.0238 ± 0.0008 | 0.0226 ± 0.0000 |
| R1 8.0% | 0.0228 ± 0.0000 | 0.0383 ± 0.0014 | 0.0354 ± 0.0009 | 0.0211 ± 0.0006 | 0.0505 ± 0.0174 | 0.0816 ± 0.0015 | 0.0254 ± 0.0000 | 0.0226 ± 0.0000 |
| R2 1.0% | 0.0240 ± 0.0015 | 0.0390 ± 0.0006 | 0.0348 ± 0.0005 | 0.0211 ± 0.0004 | 0.0487 ± 0.0293 | 0.0827 ± 0.0009 | 0.0233 ± 0.0008 | 0.0226 ± 0.0000 |
| R2 3.0% | 0.0222 ± 0.0036 | 0.0396 ± 0.0022 | 0.0342 ± 0.0030 | 0.0194 ± 0.0019 | 0.0523 ± 0.0302 | 0.0832 ± 0.0021 | 0.0221 ± 0.0021 | 0.0226 ± 0.0000 |
| R2 8.0% | 0.0293 ± 0.0026 | 0.0505 ± 0.0060 | 0.0575 ± 0.0284 | 0.0245 ± 0.0019 | 0.0577 ± 0.0332 | 0.0970 ± 0.0152 | 0.0230 ± 0.0020 | 0.0226 ± 0.0000 |

## Selisih CPLA vs tiap korektor dan uji Wilcoxon

Sel tersuntik: 54 (dataset × rezim × ukuran × seed).

| pembanding X | median ΔF1 (CPLA−X) | menang/seri/kalah | Wilcoxon p (CPLA>X) | median ΔFPR (CPLA−X) |
|---|---|---|---|---|
| no-op | +0.0000 | 24/4/26 | 7.14e-01 | +0.0000 |
| cleanlab (OOF global) | -0.0006 | 20/0/34 | 9.93e-01 | +0.0002 |
| cleanlab (OOF lintas-partisi) | -0.0002 | 25/1/28 | 8.61e-01 | +0.0002 |
| OOF global | -0.0003 | 23/0/31 | 6.77e-01 | +0.0002 |
| OOF lintas-partisi | +0.0069 | 45/0/9 | 4.11e-04 | -0.0002 |

### Rincian per dataset × rezim (median ΔF1 CPLA − X, 9 sel tiap baris)

| dataset | rezim | vs no-op | vs cleanlab | vs cleanlab-xp | vs OOF | vs OOF-xp | pembanding terbaik |
|---|---|---|---|---|---|---|---|
| 5G-NIDD versi C | R1 | +0.0002 | -0.0002 | +0.0000 | -0.0001 | +0.0084 | cleanlab (OOF global) (-0.0002) |
| 5G-NIDD versi C | R2 | -0.0537 | -0.0494 | -0.0534 | -0.0542 | +0.0010 | OOF global (-0.0542) |
| UNSW-NB15 | R1 | -0.0010 | +0.0055 | +0.0086 | +0.0086 | +0.0105 | no-op (-0.0010) |
| UNSW-NB15 | R2 | -0.0083 | -0.0002 | +0.0024 | -0.0009 | +0.0105 | no-op (-0.0083) |
| CSE-CIC-IDS2018 | R1 | +0.0100 | -0.0025 | -0.0041 | +0.0011 | +0.0055 | cleanlab (OOF lintas-partisi) (-0.0041) |
| CSE-CIC-IDS2018 | R2 | +0.0102 | -0.0047 | -0.0048 | +0.0012 | +0.0040 | cleanlab (OOF lintas-partisi) (-0.0048) |

## Fraksi pemulihan macro-F1 (relatif oracle-buang)

| himpunan sel | n sel memenuhi syarat | median fraksi pemulihan CPLA | median fraksi pemulihan pembanding terbaik |
|---|---|---|---|
| semua sel tersuntik | 13 | +0.33 | cleanlab (OOF lintas-partisi) +0.47 |
| R1 saja | 7 | +0.33 | cleanlab (OOF lintas-partisi) +0.47 |
| R2 saja | 6 | +0.38 | cleanlab (OOF lintas-partisi) +0.56 |

## Kontrol: kerusakan tiap korektor pada data BERSIH (tanpa suntikan)

| korektor | median ΔF1 vs no-op | median ΔFPR vs no-op | rerata baris dibuang | % dari train |
|---|---|---|---|---|
| no-op | +0.0000 | +0.0000 | 0 | 0.00% |
| cleanlab (OOF global) | +0.0005 | +0.0000 | 4156 | 6.09% |
| cleanlab (OOF lintas-partisi) | +0.0000 | +0.0000 | 5647 | 8.28% |
| OOF global | +0.0002 | -0.0002 | 6798 | 9.97% |
| OOF lintas-partisi | -0.0109 | +0.0006 | 9101 | 13.34% |
| **CPLA** | +0.0006 | +0.0001 | 1718 | 2.52% |

(rerata baris train per sel kontrol: 68.199; rerata atas 3 dataset × 3 seed.)

## Verdik gerbang (aturan F di `cpla.py`, tidak diubah)

| gerbang | syarat | hasil |
|---|---|---|
| G1 dominasi | median ΔF1 > 0 DAN Wilcoxon p < 0,05 vs no-op, cleanlab, cleanlab-xp, OOF, OOF-xp | **GAGAL** (noop: tidak, cl: tidak, cl_xp: tidak, oof: tidak, oof_xp: ya) |
| G2 pemulihan | median fraksi pemulihan CPLA ≥ 0,50 | **GAGAL** (median +0.33 atas 13 sel) |
| G3 tidak merusak | pada kontrol: ΔF1 ≥ −0,005 dan ΔFPR ≤ +0,005 | **TERPENUHI** |

**GERBANG UTAMA: GAGAL**

### Sub-gerbang per rezim

| rezim | G1 (vs tiap pembanding) | G2 |
|---|---|---|
| R1 | noop: tidak, cl: tidak, cl_xp: tidak, oof: ya, oof_xp: ya | median +0.33 atas 7 sel -> tidak |
| R2 | noop: tidak, cl: tidak, cl_xp: tidak, oof: tidak, oof_xp: ya | median +0.38 atas 6 sel -> tidak |

## Diagnostik: presisi/recall deteksi baris tersuntik

| rezim | korektor | presisi (mean) | recall (mean) | baris dibuang (mean) |
|---|---|---|---|---|
| R1 | no-op | TIDAK ADA | 0.000 ± 0.000 | 0 |
| R1 | cleanlab (OOF global) | 0.246 ± 0.361 | 0.265 ± 0.317 | 4397 |
| R1 | cleanlab (OOF lintas-partisi) | 0.187 ± 0.291 | 0.361 ± 0.449 | 6312 |
| R1 | OOF global | 0.199 ± 0.314 | 0.507 ± 0.467 | 7573 |
| R1 | OOF lintas-partisi | 0.148 ± 0.201 | 0.600 ± 0.491 | 10505 |
| R1 | **CPLA** | 0.294 ± 0.341 | 0.481 ± 0.509 | 2902 |
| R1 | oracle (buang) | 1.000 ± 0.000 | 1.000 ± 0.000 | 2365 |
| R1 | oracle (perbaiki) | 1.000 ± 0.000 | 1.000 ± 0.000 | 0 |
| R2 | no-op | TIDAK ADA | 0.000 ± 0.000 | 0 |
| R2 | cleanlab (OOF global) | 0.326 ± 0.328 | 0.439 ± 0.261 | 4607 |
| R2 | cleanlab (OOF lintas-partisi) | 0.288 ± 0.322 | 0.420 ± 0.339 | 7197 |
| R2 | OOF global | 0.280 ± 0.289 | 0.673 ± 0.317 | 7773 |
| R2 | OOF lintas-partisi | 0.124 ± 0.133 | 0.547 ± 0.310 | 11657 |
| R2 | **CPLA** | 0.053 ± 0.154 | 0.051 ± 0.135 | 3024 |
| R2 | oracle (buang) | 1.000 ± 0.000 | 1.000 ± 0.000 | 2709 |
| R2 | oracle (perbaiki) | 1.000 ± 0.000 | 1.000 ± 0.000 | 0 |

## Sekunder: F1 deteksi biner dan TPR (mean atas seed & ukuran)

| dataset | rezim | no-op | cleanlab (OOF global) | cleanlab (OOF lintas-partisi) | OOF global | OOF lintas-partisi | **CPLA** | oracle (buang) | oracle (perbaiki) |
|---|---|---|---|---|---|---|---|---|---|
| 5G-NIDD versi C | R0 | 0.9999 | 0.9998 | 0.9999 | 0.9995 | 0.9996 | 0.9998 | TIDAK ADA | TIDAK ADA |
| 5G-NIDD versi C | R1 | 0.9790 | 0.9791 | 0.9791 | 0.9786 | 0.9854 | 0.9792 | 0.9997 | 0.9999 |
| 5G-NIDD versi C | R2 | 0.9998 | 0.9997 | 0.9998 | 0.9995 | 0.9994 | 0.9994 | 0.9996 | 0.9999 |
| UNSW-NB15 | R0 | 0.9980 | 0.9981 | 0.9981 | 0.9981 | 0.9980 | 0.9980 | TIDAK ADA | TIDAK ADA |
| UNSW-NB15 | R1 | 0.9951 | 0.9937 | 0.9981 | 0.9944 | 0.9980 | 0.9980 | 0.9980 | 0.9980 |
| UNSW-NB15 | R2 | 0.9980 | 0.9981 | 0.9981 | 0.9981 | 0.9980 | 0.9980 | 0.9980 | 0.9980 |
| CSE-CIC-IDS2018 | R0 | 0.6196 | 0.6733 | 0.6707 | 0.7092 | 0.6165 | 0.5758 | TIDAK ADA | TIDAK ADA |
| CSE-CIC-IDS2018 | R1 | 0.5956 | 0.6392 | 0.6546 | 0.6351 | 0.5974 | 0.5829 | 0.6691 | 0.6196 |
| CSE-CIC-IDS2018 | R2 | 0.6137 | 0.6620 | 0.6623 | 0.6610 | 0.6017 | 0.5741 | 0.6432 | 0.6196 |

## Blok yang dibuang CPLA (contoh 8 blok dengan z terbesar)

| dataset | rezim | ukuran | partisi | sumber | label | prediksi OOF | n_b/n_g | rate | latar med | z | dibuang |
|---|---|---|---|---|---|---|---|---|---|---|---|
| g5c | R0 | 0.0 | Goldeneye1.csv | 74.125.8.137 | Benign | UDPScan | 30/31 | 0.968 | 0.000 | inf | 31 |
| g5c | R0 | 0.0 | Goldeneye1.csv | 74.125.8.137 | Benign | UDPScan | 30/31 | 0.968 | 0.000 | inf | 31 |
| g5c | R0 | 0.0 | Goldeneye1.csv | 74.125.8.137 | Benign | UDPScan | 30/31 | 0.968 | 0.000 | inf | 31 |
| g5c | R1 | 0.01 | Goldeneye1.csv | 74.125.8.137 | Benign | UDPScan | 31/31 | 1.000 | 0.000 | inf | 31 |
| g5c | R1 | 0.01 | UDPScan1.csv | 10.155.15.9 | Benign | SYNScan | 602/669 | 0.900 | 0.000 | inf | 669 |
| g5c | R1 | 0.03 | Goldeneye1.csv | 74.125.8.137 | Benign | UDPScan | 31/31 | 1.000 | 0.000 | inf | 31 |
| g5c | R1 | 0.03 | UDPScan1.csv | 10.155.15.9 | Benign | SYNScan | 1822/1961 | 0.929 | 0.000 | inf | 1961 |
| g5c | R1 | 0.08 | Goldeneye1.csv | 74.125.8.137 | Benign | UDPScan | 31/31 | 1.000 | 0.000 | inf | 31 |

Total blok dibuang di seluruh run: 204; rerata baris dibuang per blok 860.

## Penyimpangan dan keputusan

1. **CSE-CIC-IDS2018 tidak punya split antar-partisi yang sah.** Parquet pra-proses
   tidak memuat IP maupun Timestamp, dan setiap kelas serangan hanya muncul di SATU
   berkas/hari; split antar-berkas akan membuat kelas test tidak pernah ada di train.
   Karena itu split evaluasi CSE = urutan baris tersimpan dalam setiap berkas (70% awal
   train, 30% akhir test) dan sumbu "sumber" memakai PROKSI sidik-jari tumpukan TCP
   (Protocol, Init Fwd Win Bytes, Init Bwd Win Bytes, Fwd Seg Size Min;
   2.723 nilai berbeda di train),
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
   4471 baris di UNSW dan
   3464 baris di CSE, jadi target
   8% (5.600 baris) tidak tercapai di kedua dataset itu. Sel yang terpotong:
   cse/R1/8%, g5c/R2/8%, unsw/R1/8%.
   Ukuran yang benar-benar tersuntik ada di tabel di atas.
5. **Seed pada sel yang terpotong.** Aturan "jika kurang dari s+1 grup layak, pakai grup
   terbesar" membuat beberapa seed pada ukuran 8% memakai grup yang SAMA; di sel itu seed
   hanya mengubah lipatan OOF dan random_state model, bukan bloknya.
6. **Pemilihan pasangan R2.** Massa konflik vektor identik dipakai di UNSW
   (massa konflik vektor identik = 3314) dan CSE
   (massa konflik vektor identik = 142); pada 5G-NIDD versi C massa konflik = 0
   (dedup lintas-berkas sudah membuang vektor kembar), jadi aturan cadangan dipakai
   (cadangan: kebingungan OOF lintas-partisi = 9996).
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
10. **Sel selesai:** 63 dari 63 yang direncanakan (lengkap).
11. **Fraksi baris yang tidak bisa diaudit lintas-partisi** (akibat penjaga dukungan):
   5G-NIDD versi C 36%; UNSW-NB15 0%; CSE-CIC-IDS2018 32%. Baris itu kebal terhadap semua korektor lintas-partisi — konsekuensi langsung
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
   ambang sama sekali, sesuai aturan pra-registrasi.

## Mengapa CPLA gagal — mekanisme yang DIVERIFIKASI (bukan dugaan)

Diagnostik `diag.py` memutar ulang audit lintas-partisi pada 9 sel R1 5G-NIDD dan membuka isi keputusan CPLA untuk grup yang memuat blok tersuntik (`results/DIAG_G5C_R1.json`).

| ukuran | seed | kelas asli blok | % blok diprediksi Benign oleh auditor | q dominan | n_b/n_g | rate | latar med | z | lolos ambang CPLA |
|---|---|---|---|---|---|---|---|---|---|
| 1% | 0 | TCPConnectScan | 99.7% | SlowrateDoS | 2/664 | 0.003 | 0.013 | -1.03 | tidak |
| 1% | 1 | SYNScan | 0.0% | UDPScan | 646/664 | 0.973 | 1.000 | -2.71 | tidak |
| 1% | 2 | UDPScan | 1.2% | SYNScan | 602/669 | 0.900 | 0.000 | 89.99 | ya |
| 3% | 0 | TCPConnectScan | 99.4% | SYNScan | 7/1956 | 0.004 | 0.000 | 0.36 | tidak |
| 3% | 1 | SYNScan | 0.0% | UDPScan | 1935/1956 | 0.989 | 1.000 | -1.07 | tidak |
| 3% | 2 | UDPScan | 1.5% | SYNScan | 1822/1961 | 0.929 | 0.000 | 92.91 | ya |
| 8% | 0 | TCPConnectScan | 99.5% | SYNScan | 13/5187 | 0.003 | 0.000 | 0.25 | tidak |
| 8% | 1 | SYNScan | 0.0% | UDPScan | 5163/5187 | 0.995 | 1.000 | -0.46 | tidak |
| 8% | 2 | TCPConnectScan | 99.6% | SYNScan | 12/5187 | 0.002 | 0.000 | 0.23 | tidak |

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
label itu harus jarang bertukar di tempat lain.

## Runtime

- Total waktu fit model hilir yang tercatat: 77.4 menit (486 baris hasil; 2 proses × 8 thread). Log penuh: `results/run_a.log` (5G-NIDD + UNSW) dan `results/run_cse.log`.

