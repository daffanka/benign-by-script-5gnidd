"""apply_v11.py — bangun main_v11.tex dari main_v10.tex.

Perubahan HANYA pada: Bagian 2 (Related Work), penyisipan Tabel perbandingan,
caption/rujukan gambar posisi, dan kalimat klaim kebaruan. Tidak ada angka
hasil, tabel hasil, atau kesimpulan yang disentuh.
"""
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
V10 = os.path.join(os.path.dirname(HERE), "main_v10.tex")
V11 = os.path.join(HERE, "main_v11.tex")
shutil.copyfile(V10, V11)
t = open(V11, encoding="utf-8", newline="").read()

# ---------------------------------------------------------------- Bagian 2.1
start = t.index(r"\subsection{Correcting IDS benchmark datasets}")
end = t.index(r"\subsection{How 5G-NIDD is used}")
NEW21 = r"""\subsection{Benchmark datasets and their defects}

Doubts about machine learning for intrusion detection are older than the
datasets we audit here: \citet{sommer2010_closedworld} argued that the field's
evaluation practice, not its algorithms, is the binding constraint. More
recently the critique has become concrete. \citet{arp2022_dosdonts} catalogue
pitfalls in the design, implementation and evaluation of learning-based security
systems; \citet{kapoor2023_leakage} show that leakage undermines reproducibility
across machine-learning-based science; and \citet{geirhos2020_shortcut} name the
underlying failure mode, shortcut learning, in which a model solves a benchmark
through a cue that will not exist in deployment.

Auditing the benchmarks themselves has a short but consequential history.
\citet{engelen2021_troubleshooting} re-examined CICIDS2017 together with its
collection pipeline and reported flaws in traffic generation, flow construction,
feature extraction and labelling, relabelling or reconstructing a large share of
the data. \citet{liu2022_errorprevalence} quantified error prevalence in
CICIDS2017 and CSE-CIC-IDS2018, and \citet{lanvin2022_errors_cicids} showed that
correcting CICIDS2017 changes measured detection performance.
\citet{flood2024_badsmells} catalogue recurring ``data design smells'' across
benchmark NIDS datasets and give a heuristic for each, while
\citet{goldschmidt2025_survey} survey intrusion datasets and their limitations
at the level of the field. \citet{chen2021_dataquality} argue that data quality,
rather than model choice, bounds intrusion-detection performance;
\citet{sarhan2022_standardfeature} propose a standard NetFlow feature set so
that results become comparable across datasets; and \citet{luay2025_temporal}
show that published NetFlow datasets omit temporal features and release versions
that restore them. \citet{jerabek2025_simplemodel} report that a simple baseline
matches deep models across traffic-classification benchmarks, because identical
flows recur across training and test splits and sometimes carry conflicting
labels. Closest to our shortcut findings, \citet{galal2026_edgeiiotset} trace a
serialisation artifact in Edge-IIoTset that makes the label recoverable from
file provenance, and \citet{roy2026_shortcut} document shortcut learning from
testbed addresses and recording artifacts in an IoT benchmark.

Table~\ref{tab:related} places these studies side by side along the dimensions
that matter for the present case: which dataset is audited, which defect is
reported, how it is evidenced, at what scale, and what is released.
Figure~\ref{fig:positioning} summarises the same evidence as a capability
matrix. Two patterns are visible. First, the audited datasets are almost all
from the CICIDS and IoT families; the 5G captures that carry the 5G-NIDD label
are used as given. Second, studies that report a defect rarely recover the
mechanism that produced it: most report symptoms, such as duplicate flows or
inflated scores, rather than the rule that generated the wrong labels. Our work
differs in scale and specificity rather than in kind: we identify a single
mechanical labelling rule, verify it three independent ways, and quantify both
the affected share of the dataset and its effect on eleven models.

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{figures/fig_positioning.pdf}
\caption{Positioning of this work against the closest dataset-audit
literature, using the same evidence as Table~\ref{tab:related}. Filled:
demonstrated; half: partial; empty: not reported in the record we opened.
Cell-level evidence, with quotations and the URLs consulted, is in the
supplementary files \texttt{positioning\_matrix\_v11.csv} and
\texttt{RELATED\_WORK\_EVIDENCE.csv}.}
\label{fig:positioning}
\end{figure}


\input{tables/T_related}

\subsection{Label noise as a modelling assumption}

Label noise is a mature subject in its own right. \citet{frenay2014_labelnoise}
survey classification under label noise, and \citet{song2023_noisylabels} survey
the deep-learning variants of the problem; \citet{northcutt2021_labelerrors}
show that label errors in widely used test sets are numerous enough to change
benchmark rankings, which they identify with confident learning
\citep{northcutt2021_confidentlearning}. That method, like most of the
literature it summarises, assumes a class-conditional noise process: whether a
label is corrupted depends on its class, not on where the record came from.
Block-structured label noise, where whole (session $\times$ source) groups are
wrong, violates exactly that assumption, and we quantify the consequences for
audit procedures in Section~\ref{sec:audits}.

"""
t = t[:start] + NEW21 + t[end:]

# ------------------------------------------------- tambahan di akhir 2.2
anchor = (r"To our knowledge, no prior work reports the" + "\n"
          r"labelling error or the identity-shortcut mechanism we describe.")
NEWCLAIM = (r"In the sources we searched (Supplement~S1), we found no prior work"
            + "\n" + r"reporting the labelling error or the identity-shortcut "
            r"mechanism we describe." + "\n\n"
            r"Finally, this paper also touches four other benchmark datasets and a "
            r"standard" + "\n"
            r"software stack. The datasets scanned in Section~\ref{sec:beyond} are "
            r"CICIDS2017" + "\n"
            r"\citep{sharafaldin2018_cicids2017}, UNSW-NB15 "
            r"\citep{moustafa2015_unswnb15}," + "\n"
            r"CICIoT2023 \citep{neto2023_ciciot2023} and the ToN-IoT family "
            r"\citep{booij2022_toniot}," + "\n"
            r"whose authors already note heterogeneity and feature-standardisation "
            r"problems." + "\n"
            r"Our models and tests use scikit-learn "
            r"\citep{pedregosa2011_sklearn} and SciPy" + "\n"
            r"\citep{virtanen2020_scipy}; the paired tests reported in "
            r"Section~\ref{sec:audits} are" + "\n"
            r"those of \citet{wilcoxon1945_ranking} and "
            r"\citet{mcnemar1947_sampling}; and the" + "\n"
            r"tabular foundation model we evaluate is TabICL "
            r"\citep{qu2025_tabicl}. Security" + "\n"
            r"requirements specific to 5G, which motivate a 5G-specific benchmark in "
            r"the" + "\n"
            r"first place, are surveyed by \citet{ahmad2018_5gsecurity}.")
assert anchor in t, "pola klaim kebaruan tidak ditemukan"
t = t.replace(anchor, NEWCLAIM, 1)

open(V11, "w", encoding="utf-8", newline="").write(t)
print("main_v11.tex ditulis")

cited = set()
for c in re.findall(r"cite[tp]?\{([^}]+)\}", t):
    cited.update(x.strip() for x in c.split(","))
print("kunci \\cite unik:", len(cited))
