# EVIDENCE_gaps — karya yang DIKELUARKAN dari Tabel perbandingan

Aturan: sebuah baris hanya masuk `tables/T_related.tex` bila SEMUA kolom bukti
(dataset, cacat, metode, skala, rilis) bisa diisi dari sumber primer yang kami
buka sendiri. Karya di bawah tetap disitasi di Bagian 2, tetapi tidak menjadi
baris tabel.

| karya | sudah terverifikasi | yang kurang | alasan dikeluarkan |
|---|---|---|---|
| `liu2022_errorprevalence` | metadata Crossref lengkap (judul, 5 penulis, CNS 2022, hal. 254--262, DOI) | abstrak/teks penuh | Crossref tidak memuat abstrak; tidak ada salinan terbuka yang bisa kami buka. Ringkasan agregator (aminer, CPS-VO) BUKAN sumber primer, jadi kolom "cacat", "metode", dan "skala" tidak boleh diisi. **Ini kehilangan terbesar**: karya ini melaporkan logika pelabelan yang direkayasa-balik, persis tetangga terdekat kami. |
| `lanvin2022_errors_cicids` | metadata Crossref lengkap (LNCS, hal. 18--33, DOI) | abstrak | halaman HAL diblokir pelindung bot (Anubis); laman Springer tidak dibuka. |
| `goldschmidt2025_survey` | metadata Crossref lengkap (Computers & Security 156:104510) | abstrak | Crossref tidak memuat abstrak untuk entri ini; versi arXiv tidak diunduh ulang karena survei tidak melaporkan cacat dataset tertentu yang bisa diisi ke kolom "skala". |
| `sarhan2022_standardfeature` | metadata Crossref lengkap (Mobile Networks and Applications 27:357--370) | abstrak | judul mendukung klaim di Bagian 2, tetapi kolom "cacat" dan "skala" tidak bisa diisi tanpa abstrak. Catatan: arXiv 2011.09144 berjudul BERBEDA ("NetFlow Datasets for Machine Learning-based NIDS"), jadi tidak kami perlakukan sebagai versi yang sama. |
| `sommer2010_closedworld` | metadata Crossref (IEEE S&P 2010, hal. 305--316) | abstrak | PDF penulis 404; karya ini soal praktik evaluasi, bukan cacat satu dataset. |
| `frenay2014_labelnoise`, `song2023_noisylabels` | metadata Crossref; abstrak Song dari arXiv | — | sengaja tidak dimasukkan: survei metode label noise, bukan audit dataset IDS. (arXiv 1902.00232 yang sempat diunduh untuk Frenay TERNYATA makalah lain soal operator Dunford-Pettis; berkas itu dibuang sebagai bukti.) |
| `sharafaldin2018_cicids2017`, `moustafa2015_unswnb15`, `booij2022_toniot` | metadata Crossref lengkap | abstrak | makalah dataset; dikutip di Bagian 2 sebagai sumber dataset yang kami pindai, bukan sebagai audit. |
| `bouke2024_leakagefree`, `harshdeep2025_deeptransids`, `saranya2025_ibertroa`, `olaniyi2026_slr_5g` | metadata Crossref lengkap (DOI ditemukan dan diverifikasi di v11) | abstrak | studi pengguna 5G-NIDD; sudah terwakili di Tabel 1 naskah. Hanya empat studi pengguna dengan abstrak terbuka (Uccello, Ilias, Moubayed, Lassoued) yang dijadikan baris tabel perbandingan. |
| `kapoor2023_leakage`, `geirhos2020_shortcut`, `arp2022_dosdonts`, `northcutt2021_confidentlearning` | abstrak lengkap (arXiv/Crossref) | — | sengaja tidak dimasukkan: karya metodologis lintas bidang, bukan audit satu dataset IDS; dikutip di Bagian 2. |

## Akibatnya pada klaim

Karena Liu dkk., Lanvin dkk., dan Goldschmidt & Chudá tidak menjadi baris tabel,
pembaca TIDAK boleh membaca tabel itu sebagai daftar lengkap audit dataset IDS.
Caption tabel menyatakan batas ini, dan Bagian 2 tetap membahas ketiganya dalam
teks. Jika pemilik dapat membuka abstrak ketiga karya itu (mis. lewat akses
institusi ITS ke IEEE Xplore dan SpringerLink), menambahkannya ke tabel hanya
perlu menambah satu baris data di `build_related.py` beserta kutipannya.
