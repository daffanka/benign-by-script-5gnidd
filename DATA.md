# Data

This repository contains **no dataset**. It ships only code and summary results.

## 5G-NIDD

5G-NIDD is distributed by its authors (Samarakoon et al., arXiv:2212.01298).
Obtain it from the official source cited in that paper; we do not mirror it and
we do not redistribute any flow records.

The analysis expects the per-base-station CSV exports (the `*_each_attack_csv`
folders for BS1 and BS2) and/or `Combined.csv`. Point the scripts at your local
copy by editing the `<DATA_ROOT>` placeholder at the top of
`src/pilot/common.py`, `src/pilot/scan.py` and `preregistration/cpla.py`.

**Licence terms: BELUM TERVERIFIKASI / NOT VERIFIED.** We did not confirm the
redistribution terms of 5G-NIDD. Do not re-upload the dataset to this or any
other repository before checking them with the dataset authors.

## Derived versions built by this code

`src/audit/make_clean.py` rebuilds three versions deterministically from your
own copy:

- **A** — the original labelling, unchanged.
- **B** — relabels exactly the identified block: Benign rows from the attacker
  hosts to the victim, UDP, inside the UDPFlood capture files, become UDPFlood
  (281,529 rows).
- **C** — removes those rows instead, and additionally drops cross-file record
  copies on the eight-column key `[StartTime, SrcAddr, DstAddr, Sport, Dport,
  Proto, TotPkts, TotBytes]`, keeping the first occurrence (925,573 rows).

Row counts per class and version are in `results/study_5gnidd_audit/e1_counts.csv`.

## Other datasets used only for the cross-dataset scan

CSE-CIC-IDS2018, CICIoT2023, CIC-ToN-IoT-V2 and UNSW-NB15 are used only for the
model-free scan (duplicate rate, label-conflict rate, Bayes bounds) and for the
corrector study. They are likewise not redistributed here; obtain them from
their respective publishers. Summary outputs are in `results/pilot_scan/` and
`results/study_cpla/`.
