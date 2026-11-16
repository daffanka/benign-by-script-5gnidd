# Reproducing the paper

CPU only. The full chain was run on Windows 11, Python 3.10 (conda env),
20 logical cores. Expect a few hours for the model experiments and about
15 seconds for the paper build.

```bash
pip install -r requirements.txt
```

## 0. Get the data

See [DATA.md](DATA.md). Then set the data root: edit the `<DATA_ROOT>`
placeholder in `src/pilot/common.py`, `src/pilot/scan.py` and
`preregistration/cpla.py` to the folder that holds your copy.

## 1. Build the dataset versions

```bash
python src/audit/make_clean.py
```

Produces versions A (original), B (block relabelled) and C (block removed +
cross-file deduplication) deterministically, and writes
`results/study_5gnidd_audit/e1_config.json` and `e1_counts.csv`
(281,529 relabelled rows; 925,573 rows in version C).

## 2. Audit experiments (E1-E9)

```bash
python src/audit/e2_run.py     # 6 classical models x 4 protocols x 3 versions
python src/audit/e3.py         # depth-2 labelling rule, leaf purity
python src/audit/e4.py         # shortcut dose-response + permutation importance
python src/audit/e5.py         # 7 audit procedures on the real error
python src/audit/e6.py         # SYNFlood generalisation gap
python src/audit/e8.py         # 40 injected block-label-error scenarios
python src/audit/e9.py         # block-level ranking of the same 40 scenarios
python src/audit/aggregate.py  # summary CSV/JSON used by the paper
```

`e8.py` also writes `e8_scenarios.json` (about 14 MB, the injected row indices).
That file is excluded from this repository by `.gitignore`; it is regenerated
deterministically by the same command.

## 3. Deep-learning and foundation models

```bash
python src/deep/run.py     # CNN1D, LSTM, MLP3, Transformer, TabICL
```

TabICL is evaluated on stratified 50k test subsets (cost); this is stated in the
paper's Threats to validity.

## 4. Pilots: profile, conflicts, twins, cross-dataset scan

```bash
python src/pilot/run_all.py    # c2-c5 tasks: duplicates, conflicts, twins, residuals
python src/pilot/scan.py       # CSE-CIC-IDS2018, CICIoT2023, CIC-ToN-IoT-V2, UNSW-NB15
```

## 5. Pre-registered corrector study (paper section 7.4)

```bash
python preregistration/cpla.py --tag _a      # 5G-NIDD + UNSW-NB15
python preregistration/cpla.py --tag _cse    # CSE-CIC-IDS2018
python preregistration/report.py             # -> PILOT_D_REPORT.md
python preregistration/diag.py               # failure-mechanism diagnostics
```

The scoring rules, thresholds and gates are frozen in the docstring of
`cpla.py`; see `preregistration/PREREG_HASH.md` for the hash recorded before the
scored run.

## 6. Build the paper's numbers, tables and figures

```bash
python src/paper/make_all.py
```

Runs, in order: `extract_numbers.py` (writes `NUMBERS.json`), `tables_build.py`
(writes `results/tables/*.tex`), `figures_build.py` (writes `figures/*.pdf`),
`check_numbers.py` (fails if any number in the manuscript or the tables cannot
be traced to `NUMBERS.json`).

Expected final line: `check_numbers: OK`.

## 7. Compile the manuscript

No LaTeX installation was available on the machine used, so the PDF was built
externally. Upload `paper/` (main_v10.tex, references.bib, tables/, figures/) to
Overleaf, or run locally:

```bash
latexmk -pdf paper/main_v10.tex     # needs elsarticle + elsarticle-num-names.bst
```

## 8. Compile the manuscript locally (tectonic)

The repository ships the v11.1 sources in `paper/`. With
[tectonic](https://tectonic-typesetting.github.io/) on the PATH, run from inside
`paper/` (relative paths only; the first run downloads LaTeX packages):

```bash
cd paper
tectonic --keep-intermediates main_v11_1.tex       > build_main_v11_1.log 2>&1
python make_2col_v11_1.py                          # writes main_v11_1_2col.tex
tectonic --keep-intermediates main_v11_1_2col.tex  > build_main_v11_1_2col.log 2>&1
```

`make_2col_v11_1.py` changes layout only: document class
(`final,5p,times,twocolumn`, numeric citations kept), `figure`/`table` floats
widened to `figure*`/`table*`, and the in-document highlights list removed.
Scientific text, numbers, citations and table contents are untouched.

Reference builds (tectonic 0.17.0, 2026-11-16): one column 36 pages, two columns
18 pages; no undefined references or citations in either.

## 9. Re-run the paper-side checks

```bash
python src/paper/verify_refs.py     # every bibliography entry vs stored sources/
python src/paper/build_related.py   # related-work table + per-cell evidence CSV
python src/paper/check_v11.py       # citations, labels, files, numbers outside Section 2
python src/paper/scan_language.py   # no stray non-English words in .tex/.bib
```

`verify_refs.py` and `prior_art_search.py` need the raw API responses, which are
kept outside the repository (`sources/` is git-ignored); re-fetch them with
`fetch_refs.py`, `fetch_abstracts.py` and `prior_art_search.py`.
