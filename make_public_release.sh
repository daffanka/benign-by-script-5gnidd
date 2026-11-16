#!/usr/bin/env bash
# make_public_release.sh - salin repo TANPA folder internal/ untuk rilis publik.
# Tidak melakukan git init, tidak menambah remote, tidak push. Jalankan dari
# dalam folder repo ini.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DST="${1:-${SRC}_public}"

if [ -e "$DST" ]; then
  echo "Tujuan sudah ada: $DST - hapus atau beri nama lain." >&2
  exit 1
fi

mkdir -p "$DST"
# salin semua KECUALI internal/, .git/, dan arsip
( cd "$SRC" && find . -type f \
    -not -path "./internal/*" \
    -not -path "./.git/*" \
    -not -name "*.zip" \
    -print0 ) | while IFS= read -r -d '' f; do
  mkdir -p "$DST/$(dirname "$f")"
  cp "$SRC/$f" "$DST/$f"
done

echo "Rilis publik disalin ke: $DST"
echo "Periksa sebelum mengunggah:"
echo "  1. grep -rniE 'C:..Users|@gmail|ghp_|BEGIN .* PRIVATE' \"$DST\"  -> harus kosong"
echo "  2. find \"$DST\" -type f -size +10M                             -> harus kosong"
echo "  3. pastikan tidak ada berkas dataset (*.csv flow, *.pcap, *.parquet)"
echo "  4. baca ulang paper/main_v10.tex: berisi alamat email penulis korespondensi"
