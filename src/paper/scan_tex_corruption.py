r"""scan_tex_corruption.py — pemeriksa regresi untuk kerusakan escape di sumber LaTeX.

Gagal (exit 1) bila sebuah berkas .tex memuat:
  * baris yang diawali  ef{ , extbf{ , oprule , ootnotesize , ewcommand , egin{
    (sisa "\r", "\t", "\b", "\f", "\n" yang termakan escape Python)
  * karakter kontrol CR, BS, FF, atau TAB di luar environment verbatim
dan bila teks hasil ekstraksi PDF memuat "eftab" (rujukan yang rusak terbawa ke
PDF).

Dipakai pada: semua .tex di v11_1/ dan github/paper/, serta teks kedua PDF.

python -I scan_tex_corruption.py
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STARTS = ("ef{", "extbf{", "oprule", "ootnotesize", "ewcommand", "egin{",
          "exttt{", "abel{", "ext{")
CTRL = {"\r": "CR", "\x08": "BS", "\x0c": "FF", "\t": "TAB"}
VERB = re.compile(r"\\begin\{(verbatim|lstlisting|minted)\}.*?\\end\{\1\}", re.S)

problems = []
files = sorted(set(glob.glob(os.path.join(HERE, "**", "*.tex"), recursive=True)
                   + glob.glob(os.path.join(HERE, "..", "github", "paper", "**", "*.tex"),
                               recursive=True)))
files = [f for f in files if "numbercheck" not in f and os.sep + "build" + os.sep not in f]

for f in files:
    raw = open(f, encoding="utf-8", newline="").read()
    body = VERB.sub(" ", raw)          # abaikan isi verbatim
    rel = os.path.relpath(f, HERE)
    for i, line in enumerate(body.split("\n"), 1):
        s = line.lstrip()
        for bad in STARTS:
            if s.startswith(bad):
                problems.append(f"{rel}:{i}: baris diawali '{bad}' -> {line.strip()[:60]}")
    # CRLF adalah akhir baris Windows yang sah; hanya CR tunggal yang dihitung
    body_nocrlf = body.replace("\r\n", "\n")
    for ch, name in CTRL.items():
        n = body_nocrlf.count(ch)
        if n:
            idx = body_nocrlf.index(ch)
            ln = body_nocrlf[:idx].count("\n") + 1
            problems.append(f"{rel}: {n} karakter {name} (pertama di baris {ln})")

pdfs = [os.path.join(HERE, "pdf", "main_v11_1.pdf"),
        os.path.join(HERE, "pdf", "main_v11_1_2col.pdf")]
for p in pdfs:
    if not os.path.exists(p):
        problems.append(f"{os.path.basename(p)}: PDF tidak ada (belum dibangun?)")
        continue
    try:
        from pypdf import PdfReader
        txt = " ".join((pg.extract_text() or "") for pg in PdfReader(p).pages)
    except Exception as e:                                   # noqa: BLE001
        problems.append(f"{os.path.basename(p)}: gagal diekstrak ({type(e).__name__})")
        continue
    flat = re.sub(r"\s+", "", txt)
    for bad in ("eftab", "exttt", "oprule", "ootnotesize"):
        if bad in flat:
            problems.append(f"{os.path.basename(p)}: teks PDF memuat '{bad}'")

print(f"berkas .tex diperiksa: {len(files)}; PDF diperiksa: "
      f"{len([p for p in pdfs if os.path.exists(p)])}")
if problems:
    print("GAGAL — kerusakan escape ditemukan:")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print("scan_tex_corruption: OK — tidak ada sisa escape yang rusak.")
