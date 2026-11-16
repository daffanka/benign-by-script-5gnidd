"""scan_language.py — cari kata Indonesia di berkas .tex/.bib DI LUAR komentar LaTeX."""
import glob
import re

ID = re.compile(r"\b(abstrak|kami|yang|tidak|dengan|karena|untuk|pada|dari|adalah)\b", re.I)
CMT = re.compile(r"(?<!\\)%.*")
hits = 0
for f in sorted(set(glob.glob("**/*.tex", recursive=True) + glob.glob("**/*.bib", recursive=True))):
    if "numbercheck" in f or "zipstage" in f:
        continue
    for i, line in enumerate(open(f, encoding="utf-8", errors="replace"), 1):
        code = CMT.sub("", line)
        m = ID.search(code)
        if m:
            hits += 1
            print(f"{f}:{i}: '{m.group(0)}' | {code.strip()[:95]}")
print("total kata Indonesia di luar komentar:", hits)
