"""figures_build.py — gambar PDF vektor, terbaca grayscale (abu + hatch/linestyle,
identitas tidak pernah hanya lewat warna)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)
E = json.load(open(os.path.join(HERE, "NUMBERS.json"), encoding="utf-8"))["entries"]
v = lambda k: E[k]["value"]

plt.rcParams.update({"font.size": 8, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150,
                     "axes.grid": True, "grid.color": "#dddddd",
                     "grid.linewidth": 0.5, "axes.axisbelow": True})
DARK, MID, LIGHT = "#1a1a1a", "#777777", "#c8c8c8"
MODELS = ["DT", "HGB", "KNN", "LR", "MLP", "RF"]
CLASSES = ["Benign", "HTTPFlood", "ICMPFlood", "SYNFlood", "SYNScan",
           "SlowrateDoS", "TCPConnectScan", "UDPFlood", "UDPScan"]


def save(fig, name):
    p = os.path.join(FIG, name)
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print("tulis", p)


# ---------- F1: akurasi protokol literatur, label asli vs terkoreksi ----------
# 6 model klasik (e2.*) + 5 model deep learning (dl.*) = 11 model
MODELS_DL = ["CNN1D", "LSTM", "MLP3", "TABICL", "TRF"]
SRC11 = [("e2", m) for m in MODELS] + [("dl", m) for m in MODELS_DL]
fig, ax = plt.subplots(figsize=(7.2, 2.8))
x = np.arange(len(SRC11))
a = [v(f"{s}.A.lit.{m}.acc_mean") for s, m in SRC11]
ak = [v(f"{s}.A.lit.{m}.acc_korr_mean") for s, m in SRC11]
ae = [v(f"{s}.A.lit.{m}.acc_ci95") for s, m in SRC11]
ake = [v(f"{s}.A.lit.{m}.acc_korr_ci95") for s, m in SRC11]
ax.bar(x - 0.19, a, 0.36, yerr=ae, color=DARK, edgecolor="black",
       linewidth=0.5, label="Original labels", capsize=2)
ax.bar(x + 0.19, ak, 0.36, yerr=ake, color=LIGHT, edgecolor="black",
       linewidth=0.5, hatch="///", label="Corrected labels", capsize=2)
for xi, (va, vk) in enumerate(zip(a, ak)):
    ax.text(xi - 0.19, va + 0.012, f"{va:.3f}", ha="center", fontsize=6)
    ax.text(xi + 0.19, vk + 0.012, f"{vk:.3f}", ha="center", fontsize=6)
ax.axvline(len(MODELS) - 0.5, color="#aaaaaa", linestyle="--", linewidth=0.8)
ax.text((len(MODELS) - 1) / 2, 1.07, "Classical", ha="center", fontsize=7,
        style="italic")
ax.text(len(MODELS) + (len(MODELS_DL) - 1) / 2, 1.07, "Deep learning",
        ha="center", fontsize=7, style="italic")
ax.set_xticks(x, [m for _, m in SRC11])
ax.set_ylim(0, 1.14)
ax.set_ylabel("Accuracy")
ax.set_title("Literature protocol (random 80/20, version A)", fontsize=8)
ax.legend(frameon=False, fontsize=7, ncol=2, loc="upper center",
          bbox_to_anchor=(0.5, -0.12))
save(fig, "F1_lit_asli_vs_terkoreksi.pdf")

# ---------- F2: recall per kelas lintas-BS, versi A vs B (model HGB) ----------
fig, axes = plt.subplots(2, 1, figsize=(5.4, 4.2), sharex=True)
x = np.arange(len(CLASSES))
for ax, p, judul in zip(axes, ("b12", "b21"),
                        ("Train BS1 $\\rightarrow$ test BS2", "Train BS2 $\\rightarrow$ test BS1")):
    ra = [v(f"e2.A.{p}.HGB.rec_{k}_mean") for k in CLASSES]
    rb = [v(f"e2.B.{p}.HGB.rec_{k}_mean") for k in CLASSES]
    ax.bar(x - 0.19, ra, 0.36, color=DARK, edgecolor="black", linewidth=0.5,
           label="Version A (original labels)")
    ax.bar(x + 0.19, rb, 0.36, color=LIGHT, edgecolor="black", linewidth=0.5,
           hatch="///", label="Version B (corrected labels)")
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Recall")
    ax.set_title(f"{judul} (HGB)", fontsize=8)
h, lbl = axes[0].get_legend_handles_labels()
fig.legend(h, lbl, frameon=False, fontsize=7, ncol=2, loc="upper center",
           bbox_to_anchor=(0.5, 1.03))
axes[1].set_xticks(x, CLASSES, rotation=35, ha="right")
save(fig, "F2_recall_lintasBS_AvsB.pdf")

# ---------- F3: flow per 10 dtk di BS1/UDPFlood1.csv ----------
RAW = os.path.join(ROOT, "pilot_audit", "cache", "bs1", "BS1_each_attack_csv",
                   "UDPFlood1.csv")
d = pd.read_csv(RAW, usecols=["StartTime", "SrcAddr", "Attack Type"])
mmss = d["StartTime"].astype(str).str.extract(r"^(\d+):([\d.]+)$")
sec = mmss[0].astype(float) * 60 + mmss[1].astype(float)
# unwrap pembungkusan jam (MM:SS berulang tiap 60 menit)
sec = sec.to_numpy()
wrap = np.concatenate([[0], np.cumsum(np.diff(sec) < -1800)]) * 3600
sec = sec + wrap
bin10 = ((sec - sec.min()) // 10).astype(int)
d = d.assign(bin=bin10)
n_bins = int(d["bin"].max()) + 1
t = np.arange(n_bins) * 10

atk = set(v("meta.ip_penyerang"))
vic = v("meta.ip_korban")


def grp(ip):
    if ip in atk:
        return f"attacker {ip}"
    if ip == vic:
        return f"victim {vic}"
    return "other IPs"


fig, axes = plt.subplots(2, 1, figsize=(5.4, 4.0), sharex=True)
styles = [("-", DARK, 1.4), ("--", DARK, 1.2), (":", MID, 1.6), ("-.", MID, 1.2)]
g1 = d.groupby([d["SrcAddr"].map(grp), "bin"]).size().unstack(fill_value=0)
order1 = g1.sum(1).sort_values(ascending=False).index
for (ls, col, lw), name in zip(styles, order1):
    y = np.zeros(n_bins)
    y[g1.columns.astype(int)] = 0  # noop, kolom = bin
    row = g1.loc[name].reindex(range(n_bins), fill_value=0)
    axes[0].plot(t, row.values, ls, color=col, linewidth=lw, label=name)
axes[0].set_ylabel("Flows / 10 s")
axes[0].set_title("By source IP", fontsize=8)
axes[0].legend(frameon=False, fontsize=6.5)

g2 = d.groupby(["Attack Type", "bin"]).size().unstack(fill_value=0)
for (ls, col, lw), name in zip(styles, g2.sum(1).sort_values(ascending=False).index):
    row = g2.loc[name].reindex(range(n_bins), fill_value=0)
    axes[1].plot(t, row.values, ls, color=col, linewidth=lw, label=f"label {name}")
axes[1].set_ylabel("Flows / 10 s")
axes[1].set_xlabel("Seconds since capture start (BS1/UDPFlood1.csv)")
axes[1].set_title("By original label", fontsize=8)
axes[1].legend(frameon=False, fontsize=6.5)
save(fig, "F3_flow_per10dtk_UDPFlood1.pdf")
print(f"F3: {len(d)} baris, {n_bins} bin 10 dtk "
      f"(c4_task4: rows={v('f3.rows')}, n_bin_10s={v('f3.n_bin_10s')})")

# ---------- F4: distribusi Seq per kelas (seluruh file BS1+BS2) ----------
frames = []
for bs, sub in (("bs1", "BS1_each_attack_csv"), ("bs2", "BS2_each_attack_csv")):
    base = os.path.join(ROOT, "pilot_audit", "cache", bs, sub)
    for fn in sorted(os.listdir(base)):
        if fn.endswith(".csv"):
            p = os.path.join(base, fn)
            hdr = {c.strip(): c for c in pd.read_csv(p, nrows=0).columns}
            # BS1/TCPConnect1.csv memakai "Attack Type " (spasi ekor)
            df = pd.read_csv(p, usecols=[hdr["Seq"], hdr["Attack Type"]])
            df.columns = [c.strip() for c in df.columns]
            frames.append(df)
seq = pd.concat(frames, ignore_index=True).dropna(subset=["Attack Type"])
data = [seq.loc[seq["Attack Type"] == k, "Seq"].to_numpy() for k in CLASSES]

fig, ax = plt.subplots(figsize=(5.0, 3.0))
bp = ax.boxplot(data, vert=False, tick_labels=CLASSES, showfliers=False,
                widths=0.6, patch_artist=True,
                medianprops=dict(color="black", linewidth=1.2),
                boxprops=dict(facecolor=LIGHT, edgecolor="black", linewidth=0.7),
                whiskerprops=dict(color="black", linewidth=0.7),
                capprops=dict(color="black", linewidth=0.7))
ax.set_xlabel("Seq (flow record sequence number within capture)")
ax.set_title("Distribution of Seq by class (original labels, BS1+BS2)", fontsize=8)
ax.invert_yaxis()
save(fig, "F4_distribusi_Seq_per_kelas.pdf")
print(f"F4: {len(seq)} baris dari {len(frames)} file.")
