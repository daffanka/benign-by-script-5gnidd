# Verdik kelas kuartil (Q1/Q2/Q3/Q4) — "Benign by Script" (naskah v11.3)

Disusun 2026-11-16. Label: **FAKTA** = dibaca dari naskah atau berkas hasil; **PENILAIAN** = pendapat saya sebagai reviewer; **BELUM TERVERIFIKASI** = tidak ada sumber yang bisa saya buka. Kuartil SJR, APC, dan status Scopus jurnal TIDAK saya verifikasi dari SCImago (diblokir pelindung bot); angkanya berasal dari catatan riset sebelumnya. Peluang yang tertulis adalah tebakan terinformasi, bukan data.

## 1. Verdik satu paragraf

**PENILAIAN.** Kelas yang paling realistis untuk paper ini adalah **Q2 sebagai target aman dan Q1 sebagai target ambisius**. Q3 dan Q4 tidak perlu dituju: peluangnya tinggi tetapi tidak memenuhi syarat Q2 minimum Anda, dan tidak menambah nilai bagi paper yang kontribusi intinya kuat. Kekuatannya: temuan konkret dan dapat diverifikasi (281.529 flow salah label, 23,15% dataset, mekanisme eksak yang dibuktikan tiga cara), pada dataset yang dipakai luas, dengan hasil negatif yang dilaporkan terbuka dan angka yang diperiksa mekanis (FAKTA dari naskah). Yang menahannya dari Q1 yang pasti: kebaruan terletak pada dataset dan mekanisme, bukan pada metode baru; label "benar" masih kesimpulan sendiri (penulis dataset belum dihubungi); temuan jalan pintas Seq/Offset sudah dilaporkan pihak lain (Abraheem dkk. 2026); dan naskah masih panjang (36 halaman satu kolom, 19 dua kolom) dengan lima klaim yang menyebar.

## 2. Tabel kelas

| Kelas | Cocok? | Syarat agar berhasil | Contoh jurnal dari catatan riset (BELUM TERVERIFIKASI kuartil/APC) | Peluang diterima setelah revisi (SUBJEKTIF) |
|---|---|---|---|---|
| **Q1** | Mungkin, jika syarat terpenuhi | Konfirmasi penulis dataset; fokus ke satu klaim tajam (pangkas ke sekitar 20 halaman); baris Liu dkk. dan Lanvin dkk. masuk tabel perbandingan; seed dan model diseragamkan; protokol pencarian karya terdahulu terdokumentasi | Computers & Security (SJR 1,598), Computer Networks (1,144), J. Information Security and Applications (0,905), Cybersecurity SpringerOpen (1,056), IEEE Access (0,884) | sekitar 30-45% jika syarat terpenuhi; sekitar 15-25% jika tidak |
| **Q2** | **Ya, target aman** | Perbaikan P0 saja: konfirmasi atau bantahan penulis dataset dicatat, angka dan referensi terverifikasi, tata letak bersih | Applied Intelligence (0,889, jalur langganan tanpa biaya), PeerJ Computer Science (0,618; menilai kesahihan, bukan kebaruan; APC USD 2.370) | sekitar 55-70% (Q2 atau lebih tinggi, dalam satu atau dua pengiriman) jika P0 terpenuhi |
| **Q3** | Tidak disarankan | Hanya sebagai jaring pengaman terakhir; tidak memenuhi syarat Q2 minimum ITS | tidak ada yang saya sebut (tidak ada data terverifikasi) | tinggi, tetapi tidak berguna untuk syarat Anda |
| **Q4** | Tidak disarankan | Sama seperti Q3 | tidak ada yang saya sebut | tinggi, tetapi tidak berguna untuk syarat Anda |

Keterangan: ACM DTRAP dan ACM JDIQ (disebut di verdik rigor sebelumnya karena cocok topik) belum diketahui apakah terindeks Scopus atau berapa kuartil SJR-nya; verifikasi dulu sebelum dipertimbangkan.

## 3. Alasan per kriteria (PENILAIAN, dengan dasar FAKTA)

| Faktor | Mendorong ke atas | Menahan ke bawah |
|---|---|---|
| Kebaruan | Kesalahan label berskala blok pada dataset 5G terkemuka; aturan pelabelan eksak (FAKTA: Bagian 5.3 naskah) | Tidak ada metode baru; "Liu dkk. untuk 5G-NIDD" adalah cara reviewer akan membacanya; jalan pintas Seq/Offset sudah dilaporkan Abraheem dkk. 2026 (FAKTA dari pembacaan agent) |
| Signifikansi | Delapan studi representatif memakai dataset ini dengan kolom identitas; skor 99,9% terkoreksi menjadi 0,74-0,77 | Dampak ke literatur belum dihitung (berapa paper terdampak) |
| Rigor | Tiga verifikasi independen; CI95; uji pra-registrasi; angka diperiksa mekanis | Seed tidak seragam; TabICL pada subset uji; satu model hilir pada studi korektor |
| Kejujuran klaim | Hasil negatif dilaporkan (gerbang F1 dan gerbang korektor tidak terpenuhi) | Lima kontribusi menyebar, memperluas permukaan serangan reviewer |
| Reproduksibilitas | `make_clean.py`; manifest 2.626 angka; repo dengan commit dan tag | Lisensi redistribusi 5G-NIDD belum terverifikasi |
| Etika | Draf email ke penulis dataset sudah ada | Penulis dataset BELUM dihubungi; naskah menuduh skrip pelabelan salah |
| Penyajian | Dua PDF bersih setelah perbaikan tata letak | 36 halaman versi satu kolom; banyak tabel besar |

## 4. Apa yang menggeser kelas

**Naik ke Q1 (masing-masing menaikkan peluang):** (1) penulis dataset mengonfirmasi atau menjelaskan label BS1; (2) naskah dipangkas ke klaim utama dengan Bagian 7.4 dan pemindaian empat dataset di suplemen; (3) baris Liu dkk. dan Lanvin dkk. terisi dari sumber primer; (4) replikasi independen murah (notebook 10 menit yang mencetak 281.529, aturan (sesi x IP), dan 281.505 kembaran); (5) satu putaran penyeragaman seed dan model.

**Turun ke Q2 atau di bawahnya:** penulis dataset membantah atau menjelaskan label BS1 dengan alasan sah; ada pihak lain menerbitkan audit label 5G-NIDD sebelum Anda; reviewer menilai kontribusi sebagai "laporan bug dataset" tanpa metode.

## 5. Strategi pengiriman yang saya sarankan (PENILAIAN)

1. Tetapkan sasaran Q1 pertama (Computers & Security atau Computer Networks) hanya setelah konfirmasi penulis dataset diterima atau tenggat tiga minggunya lewat.
2. Siapkan Q2 sebagai pengiriman kedua yang sudah dikemas (Applied Intelligence atau PeerJ CS), dengan ringkasan perubahan dari penolakan Q1.
3. Hindari menunda semua pengiriman menunggu Q1 sempurna: target ITS berupa Q2 minimum terpenuhi oleh pilihan nomor 2.

## 6. Yang wajib Anda verifikasi sendiri (agent tidak bisa)

1. Kuartil SJR 2025 dan kategori terbaik tiap jurnal di scimagojr.com (pilih tahun 2025, cek kuartil per kategori, dan kuartil terbaik).
2. Status indeks Scopus (Scopus Sources) untuk tiap jurnal sebelum mengirim, terutama ACM DTRAP, ACM JDIQ, dan jurnal baru.
3. APC dan jalur tanpa biaya dari halaman penerbit (Computers & Security tertulis USD 3.190 di laman Elsevier tanpa tahun dan USD 3.310 di catatan awal).
4. Aturan ITS: Peraturan Rektor 33/2025 hanya menunjuk "pedoman tersendiri" untuk S2; tanyakan ke prodi apakah yang dihitung "accepted" atau "published" dan kuartil minimalnya.

## 7. Batasan verdik ini

Saya hanya membaca teks naskah dan berkas hasil; saya tidak memeriksa data mentah 5G-NIDD, sehingga kebenaran temuan tidak saya verifikasi sendiri. Peluang di atas adalah perkiraan subjektif, bukan statistik penerimaan jurnal. Penilaian berubah jika penulis dataset merespons atau jika karya baru tentang label 5G-NIDD muncul.
