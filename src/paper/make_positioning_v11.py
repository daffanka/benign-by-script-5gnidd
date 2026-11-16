"""make_positioning_v11.py — matriks posisi v11.

Perbedaan dari v10: baris dan kolom dibatasi pada yang BISA diisi dari sumber
primer yang sudah dibuka (lihat RELATED_WORK_EVIDENCE.csv), sehingga tidak ada
sel "?" sama sekali. Kolom = kapabilitas pada kolom 3-6 Tabel perbandingan.

Nilai: 1.0 penuh, 0.5 sebagian, 0.0 "not reported in the record we opened".
Semua nilai diturunkan dari baris bukti yang sama dengan tabel; tidak ada
penilaian tambahan tanpa bukti.

python make_positioning_v11.py
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)

COLS = [("C1", "Defect\nreported"), ("C2", "Scale\nquantified"),
        ("C3", "Mechanism\nidentified"), ("C4", "Corrected data\nor scripts")]

# (label, C1, C2, C3, C4, alasan singkat -> CSV)
ROWS = [
 ("Engelen et al. 2021", 1.0, 1.0, 0.5, 1.0,
  "labelling flaws; >20% traces relabelled; causes traced; improved processing"),
 ("Liu et al. 2022 (gap)", None, None, None, None, "dikeluarkan: abstrak tidak terbuka"),
 ("Flood et al. 2024", 1.0, 0.5, 0.0, 0.0,
  "six design smells incl. murky labelling; heuristics per smell; no mechanism or release in abstract"),
 ("Jerabek et al. 2025", 1.0, 1.0, 0.5, 0.0,
  "over 50% redundant samples; splitting practice named; no release in abstract"),
 ("Chen et al. 2021", 1.0, 0.5, 0.0, 0.0,
  "data-quality impact; 11 datasets; no mechanism or release in abstract"),
 ("Luay et al. 2025", 1.0, 0.0, 0.0, 1.0,
  "missing temporal features; new NetFlow datasets released"),
 ("Northcutt et al. 2021", 1.0, 1.0, 0.5, 0.0,
  "label errors in 10 test sets; >=3.3% average; confident learning"),
 ("Galal 2026", 1.0, 1.0, 1.0, 1.0,
  "serialisation artifact; four columns at accuracy 1.0000; leakage-free benchmark"),
 ("Roy & Minu 2026", 1.0, 1.0, 0.5, 0.0,
  "shortcut from addresses/timestamps; 3.6M flows; no release in abstract"),
 ("Samarakoon et al. 2022", 0.0, 0.0, 0.0, 1.0,
  "dataset paper; no defect in abstract; dataset released"),
 ("Uccello & Nadjm-Tehrani 2026", 0.0, 0.0, 0.0, 0.0, "feature attribution on 5G-NIDD"),
 ("Ilias et al. 2024", 0.0, 0.0, 0.0, 0.0, "CNN+MoE detector on 5G-NIDD"),
 ("Moubayed 2024", 0.0, 0.0, 0.0, 0.0, "EDA+DL pipeline on 5G-NIDD"),
 ("Lassoued et al. 2026", 0.5, 0.0, 0.0, 0.0, "notes earlier work uses limited subsets"),
 ("Neto et al. 2023", 0.5, 0.0, 0.0, 1.0, "notes omitted attacks; dataset released"),
 ("This work", 1.0, 1.0, 1.0, 1.0,
  "labelling block + shortcut columns; 23.15% of rows; (session x source IP) rule; versions A/B/C"),
]


def write_csv():
    p = os.path.join(HERE, "positioning_matrix_v11.csv")
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["baris", "kolom", "nilai", "simbol", "dasar_bukti",
                    "rujukan_bukti"])
        sym = {1.0: "penuh", 0.5: "setengah", 0.0: "kosong", None: "dikeluarkan"}
        for r in ROWS:
            for (ck, _), v in zip(COLS, r[1:5]):
                w.writerow([r[0], ck, "" if v is None else v, sym[v], r[5],
                            "RELATED_WORK_EVIDENCE.csv"])
    print("tulis", p)


def draw():
    rows = [r for r in ROWS if r[1] is not None]
    nr, nc = len(rows), len(COLS)
    fig, ax = plt.subplots(figsize=(1.75 * nc + 3.6, 0.5 * nr + 2.0))
    ax.set_xlim(-0.5, nc - 0.5)
    ax.set_ylim(-0.5, nr - 0.5)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    for i, r in enumerate(rows):
        if r[0] == "This work":
            ax.axhspan(i - 0.5, i + 0.5, color="0.90", zorder=0)
        for j, v in enumerate(r[1:5]):
            ax.add_patch(plt.Circle((j, i), 0.18, fill=False, ec="0.15", lw=1.0, zorder=3))
            if v == 1.0:
                ax.add_patch(plt.Circle((j, i), 0.18, color="0.15", zorder=2))
            elif v == 0.5:
                ax.add_patch(matplotlib.patches.Wedge((j, i), 0.18, 90, 270,
                                                      color="0.15", zorder=2))
    ax.set_xticks(range(nc))
    ax.set_xticklabels([f"{k}\n{t}" for k, t in COLS], fontsize=8)
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks(range(nr))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    for t, r in zip(ax.get_yticklabels(), rows):
        if r[0] == "This work":
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
                  markeredgecolor="0.15", markersize=9, fillstyle="left", label="partial"),
           Line2D([], [], marker="o", color="none", markerfacecolor="white",
                  markeredgecolor="0.15", markersize=9,
                  label="not reported in the record we opened")]
    ax.legend(handles=leg, loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=3,
              frameon=False, fontsize=8)
    fig.tight_layout()
    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        p = os.path.join(FIG, f"fig_positioning.{ext}")
        fig.savefig(p, bbox_inches="tight", **kw)
        print("tulis", p)
    plt.close(fig)
    n_q = sum(1 for r in rows for v in r[1:5] if v is None)
    print(f"baris: {nr}, kolom: {nc}, sel: {nr*nc}, sel '?': {n_q} "
          f"({100*n_q/(nr*nc):.1f}%)")


if __name__ == "__main__":
    write_csv()
    draw()
