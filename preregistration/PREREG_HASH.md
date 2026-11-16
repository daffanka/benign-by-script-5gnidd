# Pre-registration of the corrector study (paper section 7.4)

The scoring rules, noise regimes, CPLA thresholds, metrics and gates are frozen
in the docstring of `cpla.py` (sections A-G). The script was hashed BEFORE the
scored run; the paper quotes the first 12 hex characters.

| item | value |
|---|---|
| hash recorded before the scored run (`SCRIPT.sha256`) | `599d2aeef79dfd1cbb95df4070052819a36fdc812b5cb9d0359e9a21c010270e` |
| quoted in the manuscript | `599d2aeef79d` |
| verified against the original working copy on 2026-11-16 | **MATCHES** |
| sha256 of `preregistration/cpla.py` as published here | `a46f094b3f2eb37c872157691800525d9ccea851e9c89090c0aa675be0e7c23b` |

## Why the published copy has a different hash

The published copy differs from the hashed original in **one line only**: the
data-root constant, which in the original contained a machine-specific absolute
path including the operating-system user name. It was replaced by the
placeholder `<DATA_ROOT>` during privacy cleaning:

```
-DATA = r"C:\Users\<user>\Documents\metpen\data"
+DATA = r"<DATA_ROOT>\data"
```

Nothing else was touched: thresholds (MIN_N=30, RATE_MIN=0.60, Z_MIN=5.0,
BG_MAX=0.30), regimes, metrics, gates and the docstring are byte-identical. A
reviewer who substitutes their own data path back into that line will obtain a
file whose only difference from the hashed original is that same path.

## Gates and their outcome (from `PILOT_D_REPORT.md`)

- G1 dominance over every comparator: **failed**.
- G2 median recovery fraction >= 0.50: **failed** (0.33 over 13 qualifying cells).
- G3 harmlessness on clean data: **met**.
- Main gate (G1 and G2 and G3): **FAILED** - reported as such in the paper.
