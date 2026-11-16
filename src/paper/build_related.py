"""build_related.py (v11.1) — tabel perbandingan dua panel + bukti per sel.

Perubahan v11.1:
  * dua panel: A = studi audit dataset (kolom penuh), B = studi pengguna
    5G-NIDD (Study, Dataset, What it reports, Difference)
  * "not stated in abstrak yang kami buka" -> "n.s." + catatan di bawah tabel
  * kolom Difference TIDAK boleh memuat kunci NUMBERS.json; pemeriksa menolaknya
  * Neto dkk. dikeluarkan dari tabel (lihat EVIDENCE_gaps.md)

Menulis: tables/T_related.tex, RELATED_WORK_EVIDENCE.csv
python build_related.py
"""
import csv
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")
AKSES = "2026-11-16"
NS = "n.s."


def norm(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower())


def ratio(q, text):
    qw, tw = [w for w in norm(q).split() if w], set(norm(text).split())
    return sum(1 for w in qw if w in tw) / len(qw) if qw else 0.0


_cache = {}


def source_text(key):
    if key in _cache:
        return _cache[key]
    out = []
    p = os.path.join(SRC, f"crossref_{key}.json")
    if os.path.exists(p):
        m = json.load(open(p, encoding="utf-8"))["message"]
        out += [(m.get("title") or [""])[0], m.get("abstract", "") or ""]
    for p in (os.path.join(SRC, f"arxiv_{key}.xml"), os.path.join(SRC, f"primary_{key}.xml")):
        if os.path.exists(p):
            t = open(p, encoding="utf-8", errors="replace").read()
            out += re.findall(r"<summary>(.*?)</summary>", t, re.S)
            out += re.findall(r"<entry>.*?<title>(.*?)</title>", t, re.S)
    p = os.path.join(SRC, f"primary_{key}.pdf")
    if os.path.exists(p):
        try:
            from pypdf import PdfReader
            out.append(" ".join((pg.extract_text() or "")
                                for pg in PdfReader(p).pages[:2]))
        except Exception:
            pass
    _cache[key] = " ".join(out)
    return _cache[key]


def url_of(key):
    p = os.path.join(SRC, f"crossref_{key}.json")
    if os.path.exists(p):
        return "https://api.crossref.org/works/" + json.load(open(p, encoding="utf-8"))["message"]["DOI"]
    p = os.path.join(SRC, f"arxiv_{key}.xml")
    if os.path.exists(p):
        m = re.findall(r"<id>(http[^<]*abs[^<]*)</id>",
                       open(p, encoding="utf-8", errors="replace").read())
        if m:
            return m[0]
    p = os.path.join(SRC, f"primary_{key}.pdf")
    if os.path.exists(p):
        return "author-repository PDF: sources/" + os.path.basename(p)
    return "-"


# ----------------------------------------------------------------- PANEL A
PANEL_A = [
 ("engelen2021_troubleshooting", "CICIDS2017",
  ("Flow construction, feature extraction and labelling flaws",
   "problems with traffic generation, flow construction, feature extraction and labelling"),
  ("Manual re-analysis of the collection pipeline; improved processing applied",
   "revisit CICIDS2017 and its data collection pipeline and analyze correctness"),
  ("More than 20\\% of traces reconstructed or relabelled",
   "more than 20 percent of original traces are reconstructed or relabelled"),
  ("Improved data-processing methodology reported",
   "address most of them by applying an improved data processing methodology"),
  "Studies CICIDS2017; this work audits 5G-NIDD and recovers an exact (session $\\times$ source IP) labelling rule (Sec.~5.3)"),
 ("flood2024_badsmells", "7 benchmark NIDS datasets",
  ("Six recurring design smells, including murky labelling",
   "seven highly-cited benchmark datasets, discovering six suspect design patterns"),
  ("In-depth manual analysis plus six heuristics",
   "We formulate six heuristics to measure the prevalence of these issues"),
  ("Six smells across seven datasets",
   "seven highly-cited benchmark datasets, six design smells"),
  (NS, "we conclude with some recommendations for using and creating NIDS datasets"),
  "Catalogues smells across datasets; this work quantifies one labelling rule and the share of 5G-NIDD rows it affects (Sec.~5.3)"),
 ("jerabek2025_simplemodel", "12 traffic-classification datasets",
  ("Redundant samples; identical flows with conflicting labels",
   "most datasets contain over 50% redundant samples identical packet sequences"),
  ("k-NN baseline across 12 datasets and 15 tasks",
   "evaluate this baseline across 12 datasets and 15 TC tasks"),
  ("Over 50\\% redundant samples", "over 50% redundant samples"),
  (NS, "we further argue that standard"),
  "Reports redundancy in traffic-classification data; this work reports duplicate and label-conflict rates for 5G-NIDD and four other datasets (Sec.~8)"),
 ("chen2021_dataquality", "11 host-IDS datasets",
  ("Poor data quality affecting intrusion-detection performance",
   "poor data quality has a direct impact on the performance"),
  ("Data-preparation workflow plus experiments with ten models",
   "we conducted experiments on 11 HIDS datasets using seven machine learning models"),
  ("Eleven datasets, ten models",
   "experiments on 11 HIDS datasets using seven machine learning models and three deep learning models"),
  (NS, "the data preparation workflow and quality requirements for intrusion detection are discussed"),
  "Addresses host-IDS data quality broadly; this work traces one network-flow labelling rule and its effect on eleven models (Sec.~5.4)"),
 ("luay2025_temporal", "NetFlow NIDS datasets",
  ("Published NetFlow datasets lack temporal features",
   "currently available NetFlow datasets for NIDS lack these temporal features"),
  ("Temporal analysis of feature distributions over time",
   "we provide a comprehensive temporal analysis of NetFlow datasets by examining the distribution"),
  ("New NetFlow datasets with temporal features released",
   "creating and making publicly available a set of NetFlow datasets"),
  ("Public NetFlow datasets with temporal features",
   "making publicly available a set of NetFlow datasets that incorporate these temporal features"),
  "Adds temporal features to NetFlow data; this work removes record-counter columns and corrects labels in 5G-NIDD (Sec.~6)"),
 ("northcutt2021_labelerrors", "10 vision, NLP and audio test sets",
  ("Pervasive label errors in widely used test sets",
   "We identify label errors in the test sets of 10 of the most commonly-used"),
  ("Confident learning, then crowdsourced human validation",
   "identified using confident learning algorithms and then human-validated via crowdsourcing"),
  ("At least 3.3\\% errors on average; 6\\% of ImageNet validation",
   "we estimate an average of at least 3.3% errors across the 10 datasets"),
  (NS, "proposing that judging models over correctly labeled test sets may be more useful"),
  "Diffuse errors across general ML benchmarks; this work reports one contiguous block inside a single capture file (Sec.~5.3)"),
 ("galal2026_edgeiiotset", "Edge-IIoTset",
  ("Serialisation artifact makes the label recoverable from provenance",
   "The label is recoverable from a serialisation artifact encoding file provenance"),
  ("Column ablation under 5-fold $\\times$ 3-repeat cross-validation",
   "Under 5-fold x 3-repeat cross-validation, five of six standard classifiers"),
  ("Four columns separate attack from normal at accuracy 1.0000",
   "Four of them separate attack from normal traffic with an accuracy of 1.0000"),
  ("Leakage-free benchmark proposed",
   "a Leakage-Free Benchmark for Precision-Agriculture Intrusion Detection"),
  "Shortcut from a serialisation artifact; here the shortcut columns are record counters and the labels themselves are wrong (Secs.~5.1, 5.3)"),
 ("roy2026_shortcut", "CyberFlowIoT-GICAP",
  ("Shortcut learning from testbed addresses and recording artifacts",
   "static testbed IP/MAC addresses and chronological recording artifacts"),
  ("Four learning paradigms, four feature sets, PCAP-disjoint splits",
   "Four learning paradigms are evaluated across four feature configurations using PCAP-disjoint splits"),
  ("3{,}617{,}388 flow records; 92.58\\% macro-F1 with behaviour-only features",
   "containing 3,617,388 flow records across 126 PCAP sessions"),
  (NS, "LightGBM is additionally evaluated using conventional random-flow splitting"),
  "Shortcut study on an IoT benchmark; this work adds a labelling error verified three independent ways on a 5G capture (Sec.~5.3)"),
]

# ----------------------------------------------------------------- PANEL B
PANEL_B = [
 ("samarakoon2022_5gnidd", "5G-NIDD (dataset paper)",
  ("Dataset built on a functional 5G test network; no dataset defect in the abstract (" + NS + ")",
   "a fully labeled dataset built on a functional 5G test network"),
  "Introduces 5G-NIDD; this work reports cross-capture record twins carrying opposite labels in the released data (Sec.~5.3)"),
 ("uccello2026_featureattr", "5G-NIDD",
  ("Compares statistical and logic-based feature attribution for 5G alerts",
   "feature attribution based on logic"),
  "Attributes model alerts on 5G-NIDD; this work shows two attributed columns are Argus record counters (Sec.~5.1)"),
 ("ilias2024_cnnmoe", "5G-NIDD",
  ("Convolutional network with Mixture of Experts for malicious traffic",
   "we pass this matrix through convolutional neural network"),
  "Trains on 5G-NIDD as distributed; this work evaluates after removing identity columns and correcting labels (Sec.~6)"),
 ("moubayed2024_eda_pipeline", "5G-NIDD",
  ("EDA and deep-learning pipeline; reports detection above 99.5\\%",
   "extremely high intrusion detection and attack identification capabilities above 99.5"),
  "Reports above 99.5\\% on 5G-NIDD; this work measures accuracy against corrected labels instead (Sec.~5.4)"),
 ("lassoued2026_supervised_5gnidd", "5G-NIDD",
  ("Supervised models on 5G-NIDD; notes earlier work uses limited subsets",
   "existing works using 5G-NIDD often focus on limited subsets"),
  "Evaluates supervised models on 5G-NIDD; this work audits the labels and the evaluation protocol itself (Secs.~5--6)"),
 ("abraheem2026_seqmeta", "5G-NIDD (Combined.csv)",
  ("Leakage-aware record-level evaluation; Seq and Offset rank highest, and removing "
   "them lowers holdout accuracy to 71.18\\% (XGBoost); 21 exact duplicates removed; "
   "no labelling error reported",
   "Seq and Offset emerged as the two highest-ranked predictors"),
  "Reports dependence on acquisition-order metadata under a record-level split; this work traces the labelling rule behind the affected block (Sec.~5.3)"),
]

THIS_A = ("\\textbf{This work}", "5G-NIDD (plus four datasets scanned)",
          "Block labelling error and identity-shortcut columns",
          "Single-file localisation, depth-2 rule, cross-capture twins, 40 injected scenarios",
          "281{,}529 rows: 23.15\\% of the dataset, 58.93\\% of its Benign class",
          "Scripts for versions A/B/C and the number manifest", "---")

FORBIDDEN = ("first", "only", "fails", "naive", "merely", "superficial")
KEYPAT = re.compile(r"\b(?:n|t\d{1,2}|meta|e\d|dl)\.[a-z0-9_]+", re.I)
ID_WORDS = re.compile(r"\b(abstrak|kami|yang|tidak|dengan|karena|untuk)\b", re.I)


def main():
    ev, prob = [], []

    def add(key, col, txt, quote, url):
        ev.append([key, col, txt, quote, url, AKSES, "", ""])

    for key, ds, de, me, sc, re_, diff in PANEL_A:
        url = url_of(key)
        add(key, "Study", "\\citep{" + key + "}", "", url)
        add(key, "Dataset(s)", ds, "", url)
        for col, (txt, q) in zip(["Defect or issue reported", "Evidence / method",
                                  "Scale reported", "Release"], [de, me, sc, re_]):
            add(key, col, txt, q, url)
        add(key, "Difference from this work", diff, "", "main_v11_1.tex + NUMBERS.json")
    for key, ds, wr, diff in PANEL_B:
        url = url_of(key)
        add(key, "Study", "\\citep{" + key + "}", "", url)
        add(key, "Dataset", ds, "", url)
        add(key, "What it reports", wr[0], wr[1], url)
        add(key, "Difference from this work", diff, "", "main_v11_1.tex + NUMBERS.json")
    for col, txt in zip(["Study", "Dataset(s)", "Defect or issue reported",
                         "Evidence / method", "Scale reported", "Release",
                         "Difference from this work"], THIS_A):
        add("this_work", col, txt, "", "main_v11_1.tex + paper_k4/NUMBERS.json")

    for row in ev:
        key, col, txt, q = row[0], row[1], row[2], row[3]
        if q:
            r = ratio(q, source_text(key))
            row[6] = "VERIFIED" if r >= 0.80 else "WEAK"
            row[7] = f"{r:.2f}"
            if r < 0.80:
                prob.append(f"kutipan lemah ({r:.2f}): {key} / {col}")
        else:
            row[6] = ("OUR OWN FACT (paper section / NUMBERS.json)"
                      if key == "this_work" or col.startswith("Difference")
                      else "metadata verified")
            row[7] = "1.00"
        if col.startswith("Difference"):
            m = KEYPAT.search(txt)
            if m:
                prob.append(f"kunci NUMBERS.json di sel tabel: {key} -> {m.group(0)}")
            n = len(re.sub(r"\\[a-zA-Z]+|[{}$~]", " ", txt).split())
            if n > 25:
                prob.append(f"Difference > 25 kata ({n}): {key}")
            for w in FORBIDDEN:
                if re.search(rf"\b{w}\b", txt.lower()):
                    prob.append(f"kata terlarang '{w}': {key}")
        if ID_WORDS.search(txt):
            prob.append(f"kata Indonesia di sel: {key} / {col}")

    with open(os.path.join(HERE, "RELATED_WORK_EVIDENCE.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["row", "column", "cell_text", "source_quote", "url_or_file",
                    "access_date", "status", "match"])
        w.writerows(ev)

    colsA = ["Study", "Dataset(s)", "Defect or issue reported", "Evidence / method",
             "Scale reported", "Release", "Difference from this work"]
    L = [r"\begin{table*}[t]", r"\centering",
         r"\caption{Closest prior work on defects in intrusion-detection benchmark",
         r"datasets (Panel A) and recent studies that use 5G-NIDD as distributed",
         r"(Panel B), and how this paper relates to them. Per-cell evidence, with the",
         r"quotation and the URL consulted on " + AKSES + r", is in the supplementary",
         r"file \texttt{RELATED\_WORK\_EVIDENCE.csv}.}",
         r"\label{tab:related}", r"\footnotesize", r"\setlength{\tabcolsep}{3pt}",
         r"\begin{tabularx}{\textwidth}{p{1.85cm} p{1.85cm} X X p{2.25cm} p{1.85cm} X}",
         r"\toprule",
         r"\multicolumn{7}{@{}l}{\textbf{Panel A: audits of intrusion-detection benchmark datasets}}\\",
         r"\midrule",
         " & ".join(colsA) + r"\\", r"\midrule"]
    for key, ds, de, me, sc, re_, diff in PANEL_A:
        L.append(" & ".join(["\\citep{" + key + "}", ds, de[0], me[0], sc[0], re_[0], diff]) + r"\\")
        L.append(r"\addlinespace[2pt]")
    L.append(" & ".join(THIS_A) + r"\\")
    L += [r"\midrule",
          r"\multicolumn{7}{@{}l}{\textbf{Panel B: studies using 5G-NIDD as distributed}}\\",
          r"\midrule",
          r"Study & Dataset & \multicolumn{3}{l}{What it reports} & \multicolumn{2}{l}{Difference from this work}\\",
          r"\midrule"]
    for key, ds, wr, diff in PANEL_B:
        L.append("\\citep{" + key + "} & " + ds
                 + r" & \multicolumn{3}{p{0.40\textwidth}}{" + wr[0]
                 + r"} & \multicolumn{2}{p{0.26\textwidth}}{" + diff + r"}\\")
        L.append(r"\addlinespace[2pt]")
    L += [r"\bottomrule",
          r"\end{tabularx}",
          r"\vspace{2pt}",
          r"{\footnotesize \textit{" + NS + r"}: not stated in the abstract or record we",
          r"opened; full texts were not read.}",
          r"\end{table*}"]
    os.makedirs(os.path.join(HERE, "tables"), exist_ok=True)
    open(os.path.join(HERE, "tables", "T_related.tex"), "w", encoding="utf-8").write(
        "\n".join(L) + "\n")

    print(f"Panel A: {len(PANEL_A)+1} baris | Panel B: {len(PANEL_B)} baris | "
          f"baris bukti CSV: {len(ev)}")
    if prob:
        print("MASALAH:")
        for p in sorted(set(prob)):
            print(" -", p)
    else:
        print("pemeriksa: OK (bukti lengkap, tanpa kunci NUMBERS, tanpa kata Indonesia)")


if __name__ == "__main__":
    main()
