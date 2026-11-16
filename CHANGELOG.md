# Changelog

Format: tanggal — perubahan. Repo ini belum pernah dipublikasikan.

## 2026-11-16 — paket awal (belum dirilis)

- Repo reproduksi disusun dari hasil yang sudah ada; TIDAK ada eksperimen baru.
- `src/`: skrip audit (E1-E9), deep learning, pilot, dan pembangun naskah.
- `results/`: ringkasan JSON/CSV + `NUMBERS.json` (2.626 entri) + tabel LaTeX.
  Berkas `e8_scenarios.json` (14 MB, indeks baris skenario injeksi) SENGAJA
  tidak disertakan karena melebihi batas 10 MB; dapat dibangun ulang dengan
  `src/audit/e8.py` (seed tetap).
- `paper/`: `main_v10.tex` — naskah dengan 7 perbaikan angka dan satu gambar
  posisi kontribusi. Naskah asli tidak diubah; diff ada di paket pembimbing.
- `preregistration/`: skrip studi korektor beserta docstring pra-registrasi dan
  hash; lihat `PREREG_HASH.md`.
- Pembersihan privasi: semua jalur absolut diganti placeholder
  (`<DATA_ROOT>`, `<HOME>`). Lihat `../PRIVACY_SCAN.md`.
- Tidak ada `git init`, tidak ada remote, tidak ada push.

## 2026-11-16 (later the same day) — v11.1 paper sources

- `paper/` now holds the v11.1 manuscript: 39 cited references (all verified
  against Crossref, arXiv or an author-repository PDF), a two-panel related-work
  table with per-cell evidence, and a positioning figure without unassessed cells.
- Novelty claim narrowed to the sources actually searched; the search itself is
  documented in `docs/SUPPLEMENT_S1.md` (forward citations of the dataset paper
  via OpenAlex, keyword queries to arXiv and Crossref, one unpublished
  presentation opened and summarised from the file itself).
- Added `paper/make_2col_v11_1.py`, which derives the two-column layout.
- `.gitignore` now excludes `internal/`, `owner_supplied/`, compiled PDFs,
  archives, raw API responses and build directories; figure PDFs stay tracked.
- The repository copy of the manuscript carries `\ead{[corresponding author
  email]}` instead of the author's address; the working copy outside the
  repository keeps the real address.
