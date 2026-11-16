"""tables_build.py — bangun tabel LaTeX (booktabs) HANYA dari NUMBERS.json."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TAB = os.path.join(HERE, "tables")
os.makedirs(TAB, exist_ok=True)
E = json.load(open(os.path.join(HERE, "NUMBERS.json"), encoding="utf-8"))["entries"]


def v(key):
    return E[key]["value"]


def num(x):      # bilangan bulat dengan pemisah ribuan LaTeX-aman
    return f"{x:,}".replace(",", "\\,")


def f4(x):
    return f"{x:.4f}"


def f2(x):
    return f"{x:.2f}"


def pm(m, ci):
    return f"{f4(m)} $\\pm$ {f4(ci)}"


def write(name, lines):
    p = os.path.join(TAB, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("tulis", p)


MODELS = ["DT", "HGB", "KNN", "LR", "MLP", "RF"]
PROTOS = ["lit", "noid", "b12", "b21"]
CLASSES = ["Benign", "HTTPFlood", "ICMPFlood", "SYNFlood", "SYNScan",
           "SlowrateDoS", "TCPConnectScan", "UDPFlood", "UDPScan"]

# ---------- T1 ----------
L = [r"\begin{tabular}{l rr rr rr}", r"\toprule",
     r"& \multicolumn{2}{c}{Version A} & \multicolumn{2}{c}{Version B} & \multicolumn{2}{c}{Version C}\\",
     r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}",
     r"Class & BS1 & BS2 & BS1 & BS2 & BS1 & BS2\\", r"\midrule"]
for k in CLASSES:
    row = [k.replace("Flood", "Flood").replace("_", r"\_")]
    for ver in "ABC":
        row += [num(v(f"t1.{ver}.{k}.BS1")), num(v(f"t1.{ver}.{k}.BS2"))]
    L.append(" & ".join(row) + r"\\")
L.append(r"\midrule")
row = ["Total"]
for ver in "ABC":
    row += [num(v(f"t1.{ver}.TOTAL.BS1")), num(v(f"t1.{ver}.TOTAL.BS2"))]
L += [" & ".join(row) + r"\\", r"\bottomrule", r"\end{tabular}"]
write("T1_jumlah_baris.tex", L)

# ---------- T2 ----------
L = [r"\begin{tabular}{ll llll}", r"\toprule",
     r"Protocol & Model & A (original labels) & A (corrected labels) & B & C\\",
     r"\midrule"]
for p in PROTOS:
    for i, m in enumerate(MODELS):
        cells = [p if i == 0 else "", m]
        cells.append(pm(v(f"e2.A.{p}.{m}.f1_macro_mean"), v(f"e2.A.{p}.{m}.f1_macro_ci95")))
        cells.append(pm(v(f"e2.A.{p}.{m}.f1_macro_korr_mean"), v(f"e2.A.{p}.{m}.f1_macro_korr_ci95")))
        cells.append(pm(v(f"e2.B.{p}.{m}.f1_macro_mean"), v(f"e2.B.{p}.{m}.f1_macro_ci95")))
        cells.append(pm(v(f"e2.C.{p}.{m}.f1_macro_mean"), v(f"e2.C.{p}.{m}.f1_macro_ci95")))
        L.append(" & ".join(cells) + r"\\")
    if p != PROTOS[-1]:
        L.append(r"\midrule")
L += [r"\bottomrule", r"\end{tabular}"]
write("T2_macroF1_model_protokol.tex", L)

# ---------- T3 ----------
L = [r"\begin{tabular}{ll llll}", r"\toprule",
     r"& & \multicolumn{2}{c}{Original labels} & \multicolumn{2}{c}{Corrected labels}\\",
     r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}",
     r"Direction & Model & TPR & FPR & TPR & FPR\\", r"\midrule"]
for p in ("b12", "b21"):
    for i, m in enumerate(MODELS):
        cells = [p if i == 0 else "", m,
                 pm(v(f"e2.A.{p}.{m}.tpr_mean"), v(f"e2.A.{p}.{m}.tpr_ci95")),
                 pm(v(f"e2.A.{p}.{m}.fpr_mean"), v(f"e2.A.{p}.{m}.fpr_ci95")),
                 pm(v(f"e2.A.{p}.{m}.tpr_korr_mean"), v(f"e2.A.{p}.{m}.tpr_korr_ci95")),
                 pm(v(f"e2.A.{p}.{m}.fpr_korr_mean"), v(f"e2.A.{p}.{m}.fpr_korr_ci95"))]
        L.append(" & ".join(cells) + r"\\")
    if p == "b12":
        L.append(r"\midrule")
L += [r"\bottomrule", r"\end{tabular}"]
write("T3_tprfpr_lintasBS.tex", L)

# ---------- T4 ----------
DOSE = ["semua", "minus_Seq", "minus_Offset", "minus_Seq_Offset", "minus_semua_identitas"]
LBL = {"semua": "All features", "minus_Seq": "Without Seq", "minus_Offset": "Without Offset",
       "minus_Seq_Offset": "Without Seq+Offset", "minus_semua_identitas": "Without all identity columns"}
L = [r"\begin{tabular}{l r ll}", r"\toprule",
     r"Feature set & $n_{\text{feat}}$ & Accuracy (original labels) & Accuracy (corrected labels)\\",
     r"\midrule"]
for d in DOSE:
    L.append(" & ".join([LBL[d], str(v(f"t4.dose.{d}.n_feats")),
                         pm(v(f"t4.dose.{d}.acc_mean"), v(f"t4.dose.{d}.acc_ci95")),
                         pm(v(f"t4.dose.{d}.acc_korr_mean"), v(f"t4.dose.{d}.acc_korr_ci95"))])
             + r"\\")
L += [r"\midrule",
      " & ".join(["Permutation: accuracy drop", "",
                  f"Seq: {f4(v('t4.perm.Seq.drop_acc_mean'))}",
                  f"Offset: {f4(v('t4.perm.Offset.drop_acc_mean'))}"]) + r"\\",
      r"\bottomrule", r"\end{tabular}"]
write("T4_dosis_shortcut.tex", L)

# ---------- T5 ----------
NAMA = {"a_perfile_id": "(a) Per-file OOF, with identity columns",
        "b_perfile_noid": "(b) Per-file OOF, without identity columns",
        "c_global_noid": "(c) Global OOF, without identity columns",
        "c_global_noid_conf95": r"(c$'$) Global OOF, confidence $\geq 0.95$",
        "d_latihBS2_tandaiBS1": "(d) Cross-capture: train BS2, flag Benign in BS1",
        "d_latihBS1_tandaiBS2": r"(d$'$) Cross-capture: train BS1, flag Benign in BS2",
        "e_kunci8": "(e) Cross-file 8-column key match (both sides flagged)"}
L = [r"\begin{tabular}{l rrrr}", r"\toprule",
     r"Audit procedure & Flagged & Correct & Precision & Recall\\", r"\midrule"]
for k, nama in NAMA.items():
    L.append(" & ".join([nama, num(v(f"t5.{k}.n_flag")), num(v(f"t5.{k}.n_benar")),
                         f4(v(f"t5.{k}.precision")), f4(v(f"t5.{k}.recall"))]) + r"\\")
L += [r"\bottomrule", r"\end{tabular}"]
write("T5_prosedur_audit.tex", L)

# ---------- T6 ----------
ORDER = ["5gnidd", "ciciot", "cictoniot", "cse", "unsw"]
L = [r"\begin{tabular}{l r rr rr}", r"\toprule",
     r"Dataset & Rows & Duplicates (\%) & Label conflicts (\%) & Bayes acc.\ & Bayes macro-F1\\",
     r"\midrule"]
for d in ORDER:
    jud = v(f"t6.{d}.judul").replace("_", r"\_")
    cells = [jud, num(v(f"t6.{d}.n_baris")),
             f2(v(f"t6.{d}.pct_baris_duplikat")),
             f2(v(f"t6.{d}.pct_baris_konflik_label")),
             f4(v(f"t6.{d}.bayes_akurasi")), f4(v(f"t6.{d}.bayes_macro_f1"))]
    L.append(" & ".join(cells) + r"\\")
    if d == "5gnidd":
        L.append(" & ".join([r"\quad after label correction", "--", "--", "--",
                             f4(v("t6.5gnidd.bayes_akurasi_korr")),
                             f4(v("t6.5gnidd.bayes_macro_f1_korr"))]) + r"\\")
L += [r"\bottomrule", r"\end{tabular}"]
write("T6_pindaian_dataset.tex", L)

# ---------- T7: lima model deep learning ----------
MODELS_DL = ["CNN1D", "LSTM", "MLP3", "TABICL", "TRF"]


def cell_dl(versi, p, m, metric, fmt=pm):
    km = f"dl.{versi}.{p}.{m}.{metric}_mean"
    if km not in E:
        return "--"
    return fmt(v(km), v(f"dl.{versi}.{p}.{m}.{metric}_ci95"))


L = [r"\begin{tabular}{ll lll ll l}", r"\toprule",
     r"& & \multicolumn{3}{c}{macro-F1} & \multicolumn{2}{c}{Accuracy (version A)} & \\",
     r"\cmidrule(lr){3-5}\cmidrule(lr){6-7}",
     r"Protocol & Model & A (original) & A (corrected) & B & Original & "
     r"Corrected & Mislabelled $\to$ Benign (\%)\\",
     r"\midrule"]
for p in PROTOS:
    for i, m in enumerate(MODELS_DL):
        cells = [p if i == 0 else "", m,
                 cell_dl("A", p, m, "f1_macro"),
                 cell_dl("A", p, m, "f1_macro_korr"),
                 cell_dl("B", p, m, "f1_macro"),
                 cell_dl("A", p, m, "acc"),
                 cell_dl("A", p, m, "acc_korr"),
                 cell_dl("A", p, m, "pct_mis_benign",
                         fmt=lambda a, c: f"{f2(a)} $\\pm$ {f2(c)}")]
        L.append(" & ".join(cells) + r"\\")
    if p != PROTOS[-1]:
        L.append(r"\midrule")
L += [r"\bottomrule", r"\end{tabular}"]
write("T7_model_deeplearning.tex", L)

# ---------- T8: ringkasan E8 (injeksi salah-label terkontrol) ----------
NAMA8 = {"a_perfile_id": "(a) Per-file OOF, with IDs",
         "b_perfile_noid": "(b) Per-file OOF, no IDs",
         "c_global_noid": "(c) Global OOF, no IDs",
         "d_lintas_capture": "(d) Cross-capture disagreement",
         "f_confident": "(f) Confident learning"}
nsk = v("t8.n_skenario")
L = [r"\begin{tabular}{l rr rr r r rr}", r"\toprule",
     r"& \multicolumn{2}{c}{F1} & & & & Neg.\ control & "
     r"\multicolumn{2}{c}{Real-bug replica}\\",
     r"\cmidrule(lr){2-3}\cmidrule(lr){8-9}",
     r"Audit procedure & mean & median & Precision & Recall & "
     rf"Best/{nsk} & (flags) & Recall & F1\\",
     r"\midrule"]
for k, nama in NAMA8.items():
    L.append(" & ".join([nama,
                         f4(v(f"t8.{k}.f1_mean")), f4(v(f"t8.{k}.f1_median")),
                         f4(v(f"t8.{k}.prec_mean")), f4(v(f"t8.{k}.rec_mean")),
                         str(v(f"t8.{k}.terbaik")),
                         num(v(f"t8.{k}.kontrol_n_flag")),
                         f4(v(f"t8.{k}.replika_recall")),
                         f4(v(f"t8.{k}.replika_f1"))]) + r"\\")
L += [r"\bottomrule", r"\end{tabular}"]
write("T8_ringkasan_e8.tex", L)

# ---------- T9: evaluasi tingkat blok E9 ----------
def f1(x):
    return f"{x:.1f}"


nsk9 = v("t9.n_skenario")
L = [r"\begin{tabular}{l rrr r rr}", r"\toprule",
     r"& & & & & \multicolumn{2}{c}{Replica block rank}\\",
     r"\cmidrule(lr){6-7}",
     r"Audit procedure & Rank-1 (\%) & Top-3 (\%) & Mean rank & "
     rf"Missed blocks/{nsk9} & s12 & s28\\",
     r"\midrule"]
for k, nama in NAMA8.items():
    L.append(" & ".join([nama,
                         f1(v(f"t9.{k}.pct_rank1")), f1(v(f"t9.{k}.pct_top3")),
                         f2(v(f"t9.{k}.mean_rank")), str(v(f"t9.{k}.n_absen")),
                         str(v(f"t9.{k}.replika_s12_rank")),
                         str(v(f"t9.{k}.replika_s28_rank"))]) + r"\\")
L += [r"\midrule",
      r"Paired tests (d) vs (c) & \multicolumn{3}{l}{Wilcoxon signed-rank on ranks: "
      rf"$p$ = {f4(v('t9.wilcoxon_d_vs_c.p'))}}} & "
      r"\multicolumn{3}{l}{McNemar on rank-1: "
      rf"$p$ = {f4(v('t9.mcnemar_d_vs_c.p'))}}}\\",
      r"\bottomrule", r"\end{tabular}"]
write("T9_tingkat_blok_e9.tex", L)

# ---------- T10: Pilot D — audit lintas-partisi sebagai korektor (pemulihan hilir) ----------
def sg(x, p=4):   # bertanda, untuk selisih
    return f"{x:+.{p}f}".replace("-", "$-$")


NAMA10 = {"noop": "No correction", "cl": "Confident learning (global OOF)",
          "cl_xp": "Confident learning (cross-partition OOF)",
          "oof": "Global OOF filter", "oof_xp": "Cross-partition OOF filter",
          "cpla": "CPLA (cross-partition block audit)"}
nsel10, nrusak10 = v("t10.n_sel_suntik"), v("t10.n_sel_rusak")
L = [r"\begin{tabular}{l rrr r rrr}", r"\toprule",
     r"& \multicolumn{3}{c}{Clean control (no injection)} & "
     rf"\multicolumn{{4}}{{c}}{{Injected cells ($n$ = {nsel10})}}\\",
     r"\cmidrule(lr){2-4}\cmidrule(lr){5-8}",
     r"Corrector & $\Delta$macro-F1 & $\Delta$FPR & Dropped (\%) & "
     rf"Recovery ($n$ = {nrusak10}) & $\Delta$F1 (CPLA$-$X) & W/T/L & $p$\\",
     r"\midrule"]
for k, nama in NAMA10.items():
    cells = [nama, sg(v(f"t10.{k}.ctl_df1")), sg(v(f"t10.{k}.ctl_dfpr")),
             f2(v(f"t10.{k}.ctl_pct_buang")), f2(v(f"t10.{k}.recov_median"))]
    if k == "cpla":
        cells += ["--", "--", "--"]
        L.append(r"\midrule")
    else:
        cells += [sg(v(f"t10.vs_{k}.med_df1")),
                  "/".join(str(v(f"t10.vs_{k}.n_{x}")) for x in ("win", "tie", "lose")),
                  f4(v(f"t10.vs_{k}.p"))]
    L.append(" & ".join(cells) + r"\\")
L += [r"\bottomrule", r"\end{tabular}"]
write("T10_korektor_cpla.tex", L)

print("Selesai: 10 tabel.")
