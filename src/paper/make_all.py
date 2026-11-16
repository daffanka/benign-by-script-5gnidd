"""make_all.py — bangun ulang semuanya: NUMBERS.json -> tabel -> gambar -> cek."""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = ["extract_numbers.py", "tables_build.py", "figures_build.py", "check_numbers.py"]

for s in STEPS:
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(HERE, s)], cwd=HERE)
    print(f"[{s}] rc={r.returncode}, {time.time()-t0:.1f}s")
    if r.returncode != 0:
        sys.exit(r.returncode)
print("make_all: selesai.")
