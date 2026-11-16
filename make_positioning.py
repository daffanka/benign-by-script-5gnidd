"""make_positioning.py — matriks kapabilitas "This work" vs literatur audit dataset.

Keluaran (relatif folder skrip):
  positioning_matrix.csv      bukti per sel (baris, kolom, nilai, bukti, sumber, status)
  figures/fig_positioning.pdf gambar vektor untuk naskah
  figures/fig_positioning.png 300 dpi

ATURAN ISI: nilai hanya dari bukti yang tercatat di kolom `bukti`+`sumber`.
  1.0  penuh    = ditunjukkan secara eksplisit
  0.5  setengah = sebagian / hanya sebagai gejala
  0.0  kosong   = tidak dilaporkan (bukti cukup untuk menyatakan tidak)
  None "?"      = belum dinilai (tidak ada bukti yang dibuka)
Sel tanpa bukti WAJIB None. Tidak ada karya yang dinilai lebih rendah daripada
yang bisa dibuktikan: bila ragu, dipakai None, bukan 0.0.

python make_positioning.py
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)

COLS = [
    ("C1", "Identifies\nlabel error"),
    ("C2", "Quantifies\nprevalence"),
    ("C3", "Verifies exact\nmechanism"),
    ("C4", "Identity /\nbookkeeping\nshortcut"),
    ("C5", "Releases fix\nor scripts"),
    ("C6", "Audits on\ninjected errors"),
    ("C7", "Targets a\n5G dataset"),
]

# (baris, {kolom: (nilai, bukti, sumber, status)})
P = "kalimat Bagian 2 naskah (paper_k4/main.tex)"
ROWS = [
    ("Engelen et al. 2021 [9]", {
        "C1": (1.0, "flaws in traffic generation, flow construction, feature extraction, and labelling",
               "ResearchPortal listing SPW/WTMC 2021", "TERVERIFIKASI (ringkasan resmi)"),
        "C2": (1.0, "more than 20 percent of original traffic traces reconstructed or relabelled",
               "ResearchPortal listing SPW/WTMC 2021", "TERVERIFIKASI (ringkasan resmi)"),
        "C3": (0.5, "uncover a series of problems and trace their causes",
               "ResearchPortal listing SPW/WTMC 2021", "TERVERIFIKASI (sebab, bukan aturan label eksak)"),
        "C4": (None, "", "", "BELUM DINILAI"),
        "C5": (1.0, "address most of them by applying an improved data processing methodology",
               "ResearchPortal listing + repo GintsEngelen/WTMC2021-Code", "TERVERIFIKASI"),
        "C6": (None, "", "", "BELUM DINILAI"),
        "C7": (0.0, "judul menyebut CICIDS2017 sebagai studi kasus", "references.bib", "TERVERIFIKASI (judul)"),
    }),
    ("Liu et al. 2022 [10]", {
        "C1": (1.0, "errors across the creation lifecycle, including attack orchestration, feature generation, documentation, and labeling",
               "abstrak CNS 2022 (aminer / CPS-VO)", "TERVERIFIKASI (abstrak)"),
        "C2": (0.5, "many previously undocumented errors",
               "abstrak CNS 2022", "TERVERIFIKASI (tanpa porsi numerik di abstrak)"),
        "C3": (1.0, "a recreated dataset with reverse-engineered, corrected labeling logic",
               "abstrak CNS 2022", "TERVERIFIKASI (abstrak)"),
        "C4": (None, "", "", "BELUM DINILAI"),
        "C5": (1.0, "release documentation of the issues and a recreated dataset",
               "abstrak CNS 2022", "TERVERIFIKASI (abstrak)"),
        "C6": (None, "", "", "BELUM DINILAI"),
        "C7": (0.0, "judul menyebut CIC-IDS-2017 dan CSE-CIC-IDS-2018", "references.bib", "TERVERIFIKASI (judul)"),
    }),
    ("Lanvin et al. 2022 [11]", {
        "C1": (1.0, "attacks that were carried out but not labeled correctly",
               "abstrak HAL hal-03775466 (CRiSIS 2022)", "TERVERIFIKASI (abstrak)"),
        "C2": (None, "", "", "BELUM DINILAI"),
        "C3": (0.5, "flaws in how the dataset labels events and how its traffic was captured",
               "abstrak HAL hal-03775466", "TERVERIFIKASI (jenis cacat, bukan aturan eksak)"),
        "C4": (None, "", "", "BELUM DINILAI"),
        "C5": (None, "", "", "BELUM DINILAI"),
        "C6": (None, "", "", "BELUM DINILAI"),
        "C7": (0.0, "judul menyebut CICIDS2017", "references.bib", "TERVERIFIKASI (judul)"),
    }),
    ("Flood et al. 2024 [12]", {
        "C1": (0.5, "six recurring data design smells ... correlate with ... murky labelling",
               "abstrak/draf final EuroS&P 2024", "TERVERIFIKASI (smell, bukan kesalahan label konkret)"),
        "C2": (0.5, "a heuristic measure for each [smell]",
               "draf final EuroS&P 2024", "TERVERIFIKASI (ukuran smell, bukan porsi kesalahan label)"),
        "C3": (None, "", "", "BELUM DINILAI"),
        "C4": (None, "", "", "BELUM DINILAI"),
        "C5": (None, "", "", "BELUM DINILAI"),
        "C6": (None, "", "", "BELUM DINILAI"),
        "C7": (None, "daftar 7 dataset yang dianalisis tidak terbuka dari abstrak", "", "BELUM DINILAI"),
    }),
    ("Goldschmidt & Chuda 2025 [13]", {
        "C1": (0.5, "synthesizes findings on flaws of existing datasets",
               "abstrak arXiv 2502.06688", "TERVERIFIKASI (sintesis temuan orang lain)"),
        "C2": (None, "", "", "BELUM DINILAI"),
        "C3": (None, "", "", "BELUM DINILAI"),
        "C4": (None, "", "", "BELUM DINILAI"),
        "C5": (None, "katalog 89 dataset dirilis, bukan dataset terkoreksi", "github.com/xGoldy/nid-datasets", "BELUM DINILAI"),
        "C6": (None, "", "", "BELUM DINILAI"),
        "C7": (None, "89 dataset disurvei; tidak terverifikasi apakah 5G-NIDD termasuk", "", "BELUM DINILAI"),
    }),
    ("Galal 2026 [14]", {
        "C1": (None, "", "", "BELUM DINILAI"),
        "C2": (None, "", "", "BELUM DINILAI"),
        "C3": (0.5, "a serialisation artifact ... lets a model recover labels from file provenance",
               "arXiv 2608.15761 (judul + fragmen)", "TERVERIFIKASI SEBAGIAN (abstrak penuh tidak terbuka)"),
        "C4": (1.0, "Provenance, Not Behaviour: A Serialisation Artifact in Edge-IIoTset",
               "judul arXiv 2608.15761", "TERVERIFIKASI (judul)"),
        "C5": (1.0, "and a Leakage-Free Benchmark for Precision-Agriculture Intrusion Detection",
               "judul arXiv 2608.15761", "TERVERIFIKASI (judul)"),
        "C6": (None, "", "", "BELUM DINILAI"),
        "C7": (0.0, "dataset sasaran Edge-IIoTset", "judul arXiv 2608.15761", "TERVERIFIKASI (judul)"),
    }),
    ("Roy & Minu 2026 [15]", {
        "C1": (None, "", "", "BELUM DINILAI"),
        "C2": (None, "", "", "BELUM DINILAI"),
        "C3": (None, "", "", "BELUM DINILAI"),
        "C4": (1.0, "Unmasking Shortcut Learning ... Feature Dependence and Data Leakage",
               "judul arXiv 2609.28725 + " + P, "TERVERIFIKASI (judul)"),
        "C5": (None, "", "", "BELUM DINILAI"),
        "C6": (None, "", "", "BELUM DINILAI"),
        "C7": (0.0, "domain sasaran IoT intrusion detection", "judul arXiv 2609.28725", "TERVERIFIKASI (judul)"),
    }),
    ("Jerabek et al. 2025 [16]", {
        "C1": (0.5, "identical flows [with] conflicting labels",
               "arXiv 2506.08655 (fragmen HTML)", "TERVERIFIKASI SEBAGIAN"),
        "C2": (0.5, "attribute the strong performance of simple models partly to redundancy in the data",
               "arXiv 2506.08655 (fragmen HTML)", "TERVERIFIKASI SEBAGIAN (angka >50% duplikat hanya dari ringkasan AI: BELUM TERVERIFIKASI)"),
        "C3": (None, "", "", "BELUM DINILAI"),
        "C4": (None, "", "", "BELUM DINILAI"),
        "C5": (None, "", "", "BELUM DINILAI"),
        "C6": (None, "", "", "BELUM DINILAI"),
        "C7": (None, "12 dataset klasifikasi trafik; tidak terverifikasi apakah ada dataset 5G", "", "BELUM DINILAI"),
    }),
    ("Arp et al. 2022 [17]", {
        "C1": (None, "", "", "BELUM DINILAI"),
        "C2": (None, "", "", "BELUM DINILAI"),
        "C3": (None, "", "", "BELUM DINILAI"),
        "C4": (0.5, "catalogue pitfalls of machine learning in security - including sampling bias and data snooping",
               P, "TERVERIFIKASI (kalimat naskah; pitfall umum, bukan kolom identitas)"),
        "C5": (None, "", "", "BELUM DINILAI"),
        "C6": (None, "", "", "BELUM DINILAI"),
        "C7": (0.0, "cakupan keamanan ML secara umum", P, "TERVERIFIKASI (kalimat naskah)"),
    }),
    ("Northcutt et al. 2021 [18]", {
        "C1": (1.0, "label errors in test sets destabilise benchmarks in general",
               P + " + judul NeurIPS D&B 2021", "TERVERIFIKASI (judul)"),
        "C2": (None, "", "", "BELUM DINILAI"),
        "C3": (None, "", "", "BELUM DINILAI"),
        "C4": (None, "", "", "BELUM DINILAI"),
        "C5": (None, "", "", "BELUM DINILAI"),
        "C6": (None, "", "", "BELUM DINILAI"),
        "C7": (0.0, "benchmark ML umum (vision/NLP), bukan dataset 5G", P, "TERVERIFIKASI (kalimat naskah)"),
    }),
    ("This work", {
        "C1": (1.0, "281529 UDP flood flows carry the wrong label in the BS1 capture",
               "main.tex Bagian 5.3; NUMBERS meta.n_salah_label", "TERVERIFIKASI (berkas hasil)"),
        "C2": (1.0, "23.15% dari dataset dan 58.93% dari kelas Benign",
               "NUMBERS n.derived.pct_salah_total, n.konflik.pct_dari_benign", "TERVERIFIKASI (berkas hasil)"),
        "C3": (1.0, "depth-2 decision tree reproduces the labels with 100% pure leaves; rule = (capture session x source IP)",
               "main.tex Bagian 5.3; study_5gnidd_audit/results", "TERVERIFIKASI (berkas hasil)"),
        "C4": (1.0, "Seq/Offset shortcut: permutation accuracy drop 0.3012; dose-response Tabel T4",
               "NUMBERS t4.perm.Seq.drop_acc_mean, t4.dose.*", "TERVERIFIKASI (berkas hasil)"),
        "C5": (1.0, "make_clean.py membangun versi A/B/C secara deterministik",
               "study_5gnidd_audit/make_clean.py", "TERVERIFIKASI (berkas ada)"),
        "C6": (1.0, "40 skenario injeksi (E8/E9) + studi korektor pra-registrasi (Bagian 7.4)",
               "NUMBERS t8.*, t9.*, t10.*", "TERVERIFIKASI (berkas hasil)"),
        "C7": (1.0, "dataset sasaran 5G-NIDD", "main.tex judul", "TERVERIFIKASI"),
    }),
]


def write_csv():
    p = os.path.join(HERE, "positioning_matrix.csv")
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["baris", "kolom", "kolom_judul", "nilai", "simbol", "bukti", "sumber",
                    "status_verifikasi"])
        sym = {1.0: "penuh", 0.5: "setengah", 0.0: "kosong", None: "?"}
        for nama, cells in ROWS:
            for ck, cj in COLS:
                v, bukti, sumber, status = cells[ck]
                w.writerow([nama, ck, cj.replace("\n", " "),
                            "" if v is None else v, sym[v], bukti, sumber, status])
    print("tulis", p)


def draw():
    nr, nc = len(ROWS), len(COLS)
    fig, ax = plt.subplots(figsize=(1.55 * nc + 3.6, 0.78 * nr + 2.2))
    ax.set_xlim(-0.5, nc - 0.5)
    ax.set_ylim(-0.5, nr - 0.5)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    for i, (nama, cells) in enumerate(ROWS):
        if nama == "This work":
            ax.axhspan(i - 0.5, i + 0.5, color="0.90", zorder=0)
        for j, (ck, _) in enumerate(COLS):
            v = cells[ck][0]
            if v is None:
                ax.text(j, i, "?", ha="center", va="center", fontsize=11, color="0.35")
                continue
            ax.add_patch(plt.Circle((j, i), 0.19, fill=False, ec="0.15", lw=1.0, zorder=3))
            if v == 1.0:
                ax.add_patch(plt.Circle((j, i), 0.19, color="0.15", zorder=2))
            elif v == 0.5:
                ax.add_patch(matplotlib.patches.Wedge((j, i), 0.19, 90, 270,
                                                      color="0.15", zorder=2))
    ax.set_xticks(range(nc))
    ax.set_xticklabels([f"{k}\n{t}" for k, t in COLS], fontsize=8)
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks(range(nr))
    labels = [n for n, _ in ROWS]
    ax.set_yticklabels(labels, fontsize=9)
    for t, (n, _) in zip(ax.get_yticklabels(), ROWS):
        if n == "This work":
            t.set_fontweight("bold")
    for s in ("top", "right", "bottom", "left"):
        ax.spines[s].set_visible(False)
    ax.set_xticks([x - 0.5 for x in range(1, nc)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, nr)], minor=True)
    ax.grid(which="minor", color="0.85", lw=0.6)
    ax.tick_params(which="both", length=0)
    leg = [Line2D([], [], marker="o", color="none", markerfacecolor="0.15",
                  markeredgecolor="0.15", markersize=9, label="demonstrated"),
           Line2D([], [], marker="o", color="none", markerfacecolor="0.15",
                  markeredgecolor="0.15", markersize=9, fillstyle="left",
                  label="partial"),
           Line2D([], [], marker="o", color="none", markerfacecolor="white",
                  markeredgecolor="0.15", markersize=9, label="not reported"),
           Line2D([], [], marker="$?$", color="none", markerfacecolor="0.35",
                  markeredgecolor="0.35", markersize=9, label="not assessed")]
    ax.legend(handles=leg, loc="upper center", bbox_to_anchor=(0.5, -0.06),
              ncol=4, frameon=False, fontsize=8)
    fig.tight_layout()
    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        p = os.path.join(FIG, f"fig_positioning.{ext}")
        fig.savefig(p, bbox_inches="tight", **kw)
        print("tulis", p)
    plt.close(fig)


if __name__ == "__main__":
    write_csv()
    draw()
