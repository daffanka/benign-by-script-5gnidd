# Supplement S1 — verification of references and search for prior work

All queries were executed on **2026-11-16** from one machine, with no
subscription databases. Every raw API response and every downloaded document is
stored under `v11_1/sources/` so that the steps below can be re-checked offline.
Search-engine result pages and AI-generated summaries were used **only** to
locate candidate URLs; they are never cited as evidence.

---

## S1a. Verification of the reference list

| interface | requests | what was taken | stored as |
|---|---|---|---|
| Crossref REST API, `api.crossref.org/works/<DOI>` | 26 | title, authors, venue, year, pages, DOI | `sources/crossref_*.json` |
| Crossref REST API, `works?query.bibliographic=` | 4 | DOIs for four older entries that had none | same files |
| arXiv API, `export.arxiv.org/api/query?id_list=` | 16 | title, authors, submission date, full abstract, `journal_ref` | `sources/arxiv_*.xml` |
| Author or institutional repositories | 2 | full abstracts absent from Crossref: KU Leuven Lirias PDF (Engelen et al.), authors' final-draft PDF (Flood et al.) | `sources/primary_*.pdf` |

`verify_refs.py` re-checks every bibliography entry against those files: title
similarity at least 0.80, matching year (allowing a preprint to predate the
published version), identical DOI, and a supporting quotation that must occur in
the stored source text at a word-match of at least 0.85. Result at the time of
writing: **38 of 38 entries pass, none fail**; preprints are 9 of 38 (23.7%).
Per-entry results are in `REFERENCE_AUDIT.md`.

One correction worth recording: an arXiv identifier initially fetched for
Frénay and Verleysen turned out to be an unrelated mathematics paper. That file
was discarded and the entry now rests on its Crossref record alone.

---

## S1b. Search for prior work on the 5G-NIDD defects

### (i) Forward citations of the 5G-NIDD dataset paper

Seed record: OpenAlex `W4310746777`, *5G-NIDD: A Comprehensive Network Intrusion
Detection Dataset Generated over 5G Wireless Network*, DOI
`10.48550/arXiv.2212.01298`, `cited_by_count` = 125.

```
https://api.openalex.org/works?filter=doi:10.48550/arxiv.2212.01298
https://api.openalex.org/works?filter=cites:W4310746777&per-page=200&cursor=*
```

**119 citing works** were returned (the index reports 125; the difference is not
explained by the API response and we did not reconcile it). Titles and
abstracts were screened for: *label, mislabel, mislabelled, mislabeled, error,
noise, leakage, shortcut, duplicate, audit, quality, artifact*. **29 of 119
passed the screen**; the full citer list is in
`sources/prior_art/citers_list.json` and the screened subset in
`prior_art_log.json`.

Reading the abstracts of the screened subset, two records bear on our claims:

1. **A leakage-aware evaluation of 5G-NIDD that ranks Seq and Offset highest.**
   OpenAlex lists *"Feature-Selected Machine Learning for 5G Intrusion
   Detection: Leakage-Aware Evaluation and Sensitivity to Sequence Metadata in
   5G-NIDD"* (2026, Wadi Alshatti University Journal of Pure and Applied
   Sciences, authors listed as Abraheem, Arhoumah, Fokla, Basheer). Its abstract
   states that Seq and Offset emerge as the two highest-ranked predictors and
   that removing them lowers holdout accuracy from about 99.97% to about 71%,
   concluding that near-perfect record-level results depend on acquisition-order
   metadata. **Status: the DOI (`10.63318/waujpasv4i2_14`) does not resolve at
   doi.org, Crossref returns 404, and we could not open the publisher's version.
   BELUM TERVERIFIKASI as a citable source**, so it is not in our bibliography.
   It is, however, enough to stop us claiming the identity-shortcut mechanism as
   unreported: the novelty sentence in Section 2.2 was weakened accordingly.
2. **An empirical leakage-free assessment** (Bouke and Abdullah, 2024,
   DOI `10.1016/j.prime.2024.100590`), already cited in the manuscript, which
   audits preprocessing leakage rather than labels.

None of the 29 screened abstracts reports a labelling error in 5G-NIDD.

### (ii) Keyword queries

```
arXiv:    https://export.arxiv.org/api/query?search_query=all:"5G-NIDD"&max_results=100
          -> 6 entries; 1 passed the keyword screen (the dataset paper itself)
Crossref: https://api.crossref.org/works?rows=100&query.bibliographic=
          5G-NIDD label error leakage shortcut duplicate audit quality
          -> 100 rows returned; 5 of them carry "5G-NIDD" in the title:
             10.3390/computers15060362, 10.1109/cscloud66326.2025.00055,
             10.1109/ieeedata.2025.3592888, 10.1016/j.rineng.2025.104826,
             10.1109/iccsdfai70505.2026.11647924
```

Two of those five are already in our bibliography; `10.1109/ieeedata.2025.3592888`
is the IEEE Data Descriptions descriptor of 5G-NIDD by its own authors, and the
remaining two are application papers. None of their titles mentions a labelling
error.

### (iii) An unpublished presentation that audits 5G-NIDD

`https://sola.kau.se/swits/wp-content/uploads/sites/257/2026/06/2026_Karim_Khalil.pdf`
(downloaded, 10 slides, stored as `sources/prior_art/khalil2026.pdf`).

We opened the file before summarising it, and the result differs from the
description we were given. The slides report a structural "bad smell" audit
(WhiffSuite) of 5G-NIDD with: class balance about 61% malicious, "80% of
malicious flows use background ports. Port is a weak separator", backward-packet
shares of 72% and 90%, zero-variance in 28 of 69 features, and **"0 duplicate
rows"**, with the explicit takeaway *"5G-NIDD is structurally clean"*. The
figure *"dst\_port alone achieves F1 = 0.997. Trivial shortcut"* belongs to the
**authors' own synthetic dataset (DDoSimu5G)**, not to 5G-NIDD. We therefore do
not describe this presentation as reporting a shortcut in 5G-NIDD.

### Limits of this search

- No Google Scholar, no Scopus, no Web of Science, no IEEE Xplore or ACM Digital
  Library full-text search: no institutional access from this machine.
- Screening used titles and abstracts only; no full texts of citing works were
  read.
- OpenAlex coverage is not complete, and its citation count (125) exceeded the
  records returned (119).
- Only English-language records were examined.

### Effect on the novelty claim

The manuscript says: *"In the sources we searched (Supplement S1), we found no
prior work reporting the labelling error we describe"*, and adds that the
dependence of 5G-NIDD scores on Seq and Offset has been observed independently
in an indexed record we could not verify. We make no claim of priority for the
shortcut observation itself.
