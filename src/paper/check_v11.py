"""check_v11.py — pemeriksaan statis main_v11.tex.

1. setiap kunci \cite ada di references.bib; tidak ada entri bib yang tidak disitasi
2. setiap \ref punya \label
3. setiap berkas \includegraphics dan \input ada
4. angka naskah TIDAK berubah dari main_v10.tex (perbandingan multiset token angka
   di luar Bagian 2, yang memang ditulis ulang)
5. jumlah referensi disitasi + sebaran kategori
python check_v11.py
"""
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
V11 = os.path.join(HERE, "main_v11_1.tex")
V10 = os.path.join(os.path.dirname(HERE), "main_v10.tex")
BIB = os.path.join(HERE, "references.bib")

t11 = open(V11, encoding="utf-8").read()
t10 = open(V10, encoding="utf-8").read()
bib = open(BIB, encoding="utf-8").read()
prob = []

bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
cited = set()
for c in re.findall(r"cite[tp]?\{([^}]+)\}", t11):
    cited.update(x.strip() for x in c.split(","))
missing = sorted(cited - bib_keys)
uncited = sorted(bib_keys - cited)
if missing:
    prob.append("kunci \\cite tanpa entri bib: " + ", ".join(missing))
if uncited:
    prob.append("entri bib tidak disitasi: " + ", ".join(uncited))

inputs = ""
for m in re.findall(r"\\input\{([^}]+)\}", t11):
    q = os.path.join(HERE, m if m.endswith(".tex") else m + ".tex")
    if os.path.exists(q):
        inputs += open(q, encoding="utf-8").read()
labels = set(re.findall(r"\\label\{([^}]+)\}", t11 + inputs))
refs = set(re.findall(r"\\(?:ref|autoref)\{([^}]+)\}", t11))
if refs - labels:
    prob.append("\\ref tanpa \\label: " + ", ".join(sorted(refs - labels)))

for m in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", t11):
    if not os.path.exists(os.path.join(HERE, m)):
        prob.append(f"berkas gambar tidak ada: {m}")
for m in re.findall(r"\\input\{([^}]+)\}", t11):
    p = os.path.join(HERE, m if m.endswith(".tex") else m + ".tex")
    if not os.path.exists(p):
        prob.append(f"berkas input tidak ada: {m}")


def nums(s):
    s = re.sub(r"(?<!\\)%.*", " ", s)
    s = s.replace("\\,", "")
    return Counter(re.findall(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?", s))


def cut_sec2(s):
    a = s.index(r"\section{Background and Related Work}")
    b = s.index(r"\section{The 5G-NIDD Dataset}")
    return s[:a] + s[b:]


d10, d11 = nums(cut_sec2(t10)), nums(cut_sec2(t11))
beda = {k: (d10.get(k, 0), d11.get(k, 0)) for k in set(d10) | set(d11)
        if d10.get(k, 0) != d11.get(k, 0)}
if beda:
    prob.append("angka di luar Bagian 2 berubah: " + str(beda))

KAT = {
 "audit dataset IDS": ["engelen2021_troubleshooting", "liu2022_errorprevalence",
   "lanvin2022_errors_cicids", "flood2024_badsmells", "goldschmidt2025_survey",
   "galal2026_edgeiiotset", "roy2026_shortcut", "jerabek2025_simplemodel",
   "chen2021_dataquality", "luay2025_temporal", "sarhan2022_standardfeature"],
 "label noise & kualitas data": ["northcutt2021_labelerrors",
   "northcutt2021_confidentlearning", "frenay2014_labelnoise", "song2023_noisylabels"],
 "jalan pintas / kebocoran / jebakan evaluasi": ["arp2022_dosdonts",
   "sommer2010_closedworld", "geirhos2020_shortcut", "kapoor2023_leakage",
   "galal2026_edgeiiotset", "roy2026_shortcut"],
 "5G: keamanan, dataset, IDS": ["samarakoon2022_5gnidd", "bouke2024_leakagefree",
   "uccello2026_featureattr", "ilias2024_cnnmoe", "harshdeep2025_deeptransids",
   "saranya2025_ibertroa", "moubayed2024_eda_pipeline",
   "lassoued2026_supervised_5gnidd", "olaniyi2026_slr_5g", "ahmad2018_5gsecurity"],
 "model / alat / statistik": ["pedregosa2011_sklearn", "virtanen2020_scipy",
   "wilcoxon1945_ranking", "mcnemar1947_sampling", "qu2025_tabicl"],
 "dataset lain yang dipindai": ["sharafaldin2018_cicids2017", "moustafa2015_unswnb15",
   "neto2023_ciciot2023", "booij2022_toniot"],
}
print(f"entri bib        : {len(bib_keys)}")
print(f"referensi disitasi: {len(cited)}")
for k, v in KAT.items():
    print(f"  - {k}: {len([x for x in v if x in cited])}")
arx = [k for k in cited if re.search(r"@\w+\{" + re.escape(k) + r",[^@]*?arXiv preprint", bib, re.S)]
print(f"preprint arXiv    : {len(arx)} ({100*len(arx)/len(cited):.1f}%)")
if prob:
    print("\nMASALAH:")
    for p in prob:
        print(" -", p)
else:
    print("\ncheck_v11: OK — sitasi, label, berkas, dan angka di luar Bagian 2 konsisten.")
