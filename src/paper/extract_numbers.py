"""numbers.py — bangun NUMBERS.json: satu sumber tunggal semua angka naskah K4.
Setiap entri: {"value": ..., "file": <path sumber>, "where": <kolom/field>}.
Tidak ada angka diketik manual; semua dibaca dari file hasil.
"""
import csv
import json
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
R5G = os.path.join(ROOT, "study_5gnidd_audit", "results")
RPA = os.path.join(ROOT, "pilot_audit", "results")
RPS = os.path.join(ROOT, "pilot_scan", "results")
RCP = os.path.join(ROOT, "study_cpla", "results")

N = {}
untraceable = []


def put(key, value, file, where):
    rel = os.path.relpath(file, ROOT).replace("\\", "/")
    N[key] = {"value": value, "file": rel, "where": where}


# ---------- T1: e1_counts.csv ----------
f = os.path.join(R5G, "e1_counts.csv")
c = pd.read_csv(f)
for _, r in c.iterrows():
    for col in ("BS1", "BS2", "total"):
        put(f"t1.{r.versi}.{r.kelas}.{col}", int(r[col]), f,
            f"baris versi={r.versi},kelas={r.kelas}, kolom {col}")
for v in c.versi.unique():
    sub = c[c.versi == v]
    for col in ("BS1", "BS2", "total"):
        put(f"t1.{v}.TOTAL.{col}", int(sub[col].sum()), f,
            f"jumlah kolom {col} semua kelas versi {v}")

# ---------- T2/T3/F1/F2: e2_summary.csv ----------
f = os.path.join(R5G, "e2_summary.csv")
s = pd.read_csv(f)
CLASSES = sorted(c.kelas.unique())
for _, r in s.iterrows():
    base = f"e2.{r.versi}.{r.protokol}.{r.model}"
    for m in ("f1_macro", "acc", "tpr", "fpr", "f1_macro_korr", "acc_korr",
              "tpr_korr", "fpr_korr"):
        put(f"{base}.{m}_mean", float(r[f"{m}_mean"]), f,
            f"baris versi={r.versi},protokol={r.protokol},model={r.model}, kolom {m}_mean")
        put(f"{base}.{m}_ci95", float(r[f"{m}_ci95"]), f,
            f"idem, kolom {m}_ci95")
    put(f"{base}.n_seed", int(r.n_seed), f, "kolom n_seed")
    for k in CLASSES:
        put(f"{base}.rec_{k}_mean", float(r[f"rec_{k}_mean"]), f,
            f"idem, kolom rec_{k}_mean")

# ---------- T4: e4_runs.csv (dosis) + e4_perm.json ----------
f = os.path.join(R5G, "e4_runs.csv")
e4 = pd.read_csv(f)
for sf, g in e4.groupby("set_fitur"):
    n = len(g)
    for m in ("acc", "f1_macro", "acc_korr", "f1_korr"):
        mean = float(g[m].mean())
        ci = float(1.96 * g[m].std(ddof=1) / n**0.5) if n > 1 else 0.0
        put(f"t4.dose.{sf}.{m}_mean", round(mean, 6), f,
            f"mean kolom {m} atas {n} seed, set_fitur={sf}")
        put(f"t4.dose.{sf}.{m}_ci95", round(ci, 6), f,
            f"1.96*sd/sqrt(n) kolom {m}, set_fitur={sf}")
    put(f"t4.dose.{sf}.n_feats", int(g.n_feats.iloc[0]), f,
        f"kolom n_feats, set_fitur={sf}")
    put(f"t4.dose.{sf}.n_seed", n, f, f"jumlah baris set_fitur={sf}")

f = os.path.join(R5G, "e4_perm.json")
perm = json.load(open(f, encoding="utf-8"))
put("t4.perm.baseline_acc", perm["baseline_acc"], f, "field baseline_acc")
put("t4.perm.n_repeats", perm["n_repeats"], f, "field n_repeats")
for col in ("Seq", "Offset"):
    put(f"t4.perm.{col}.drop_acc_mean", perm["per_kolom"][col]["drop_acc_mean"],
        f, f"per_kolom.{col}.drop_acc_mean")

# ---------- T5: e5_runs.csv (CSV cacat: n_flag menempel di kolom deskripsi) ----------
f = os.path.join(R5G, "e5_runs.csv")
with open(f, encoding="utf-8") as fh:
    rd = list(csv.reader(fh))
hdr = rd[0]
assert hdr[:2] == ["prosedur", "deskripsi"]
for row in rd[1:]:
    if len(row) == 6:  # n_flag terserap ke deskripsi ber-kutip
        proc, desc = row[0], row[1]
        desc_txt, n_flag = desc.rsplit(",", 1)
        n_benar, prec, rec, rt = row[2], row[3], row[4], row[5]
    else:
        proc, desc_txt, n_flag, n_benar, prec, rec, rt = row[:7]
    put(f"t5.{proc}.n_flag", int(n_flag), f,
        "kolom n_flag (dipulihkan dari akhir field deskripsi; CSV sumber cacat kutip)")
    put(f"t5.{proc}.n_benar", int(n_benar), f, "kolom n_benar")
    put(f"t5.{proc}.precision", float(prec), f, "kolom precision")
    put(f"t5.{proc}.recall", float(rec), f, "kolom recall")
    put(f"t5.{proc}.deskripsi", desc_txt, f, "kolom deskripsi (teks)")

# ---------- T6: pilot_scan 4 dataset + profil 5G-NIDD ----------
for name in ("ciciot", "cictoniot", "cse", "unsw"):
    f = os.path.join(RPS, f"{name}.json")
    j = json.load(open(f, encoding="utf-8"))
    r = j["ringkasan"]
    put(f"t6.{name}.judul", j["judul"], f, "field judul")
    for k in ("n_baris", "pct_baris_duplikat", "pct_baris_konflik_label",
              "bayes_akurasi", "bayes_macro_f1"):
        put(f"t6.{name}.{k}", r[k], f, f"ringkasan.{k}")

f = os.path.join(RPA, "profile_5gnidd.json")
p = json.load(open(f, encoding="utf-8"))
put("t6.5gnidd.judul", "5G-NIDD (per-BS CSV)", f, "disusun dari field dataset")
put("t6.5gnidd.n_baris", p["rows"], f, "field rows")
put("t6.5gnidd.pct_baris_duplikat", p["dup_exact_pct_no_id"], f,
    "field dup_exact_pct_no_id (tanpa kolom identitas; definisi paling sebanding dgn scan)")
put("t6.5gnidd.pct_baris_konflik_label", p["same_feat_diff_label_pct_no_id"], f,
    "field same_feat_diff_label_pct_no_id")
# Batas atas Bayes 5G-NIDD: sebelum koreksi dari c2_task3.json,
# sesudah koreksi dari c4_task7.json (bayes_42_nonid.sesudah).
f = os.path.join(RPA, "c2_task3.json")
j = json.load(open(f, encoding="utf-8"))
put("t6.5gnidd.bayes_akurasi", j["bayes_upper_bound_full"]["accuracy"], f,
    "bayes_upper_bound_full.accuracy (label asli, sebelum koreksi)")
put("t6.5gnidd.bayes_macro_f1", j["bayes_upper_bound_full"]["macro_f1"], f,
    "bayes_upper_bound_full.macro_f1 (label asli, sebelum koreksi)")
put("t6.5gnidd.bayes_rows", j["bayes_upper_bound_full"]["rows"], f,
    "bayes_upper_bound_full.rows")
f = os.path.join(RPA, "c4_task7.json")
j = json.load(open(f, encoding="utf-8"))
put("t6.5gnidd.bayes_akurasi_korr", j["bayes_42_nonid"]["sesudah"][0], f,
    "bayes_42_nonid.sesudah[0] (format '(akurasi, macro_f1)'; sesudah koreksi label)")
put("t6.5gnidd.bayes_macro_f1_korr", j["bayes_42_nonid"]["sesudah"][1], f,
    "bayes_42_nonid.sesudah[1] (sesudah koreksi label)")

# ---------- T7/F1: lima model deep learning, study_5gnidd_dl/results/runs.csv ----------
f = os.path.join(ROOT, "study_5gnidd_dl", "results", "runs.csv")
dl = pd.read_csv(f)
for (versi, proto, model), g in dl.groupby(["versi", "protokol", "model"]):
    base = f"dl.{versi}.{proto}.{model}"
    n = len(g)
    put(f"{base}.n_seed", n, f,
        f"jumlah baris protokol={proto},versi={versi},model={model}")
    for m in ("f1_macro", "acc", "f1_macro_korr", "acc_korr", "pct_mis_benign"):
        col = g[m].dropna()
        if len(col) == 0:
            continue
        mean = float(col.mean())
        ci = float(1.96 * col.std(ddof=1) / len(col) ** 0.5) if len(col) > 1 else 0.0
        put(f"{base}.{m}_mean", round(mean, 6), f,
            f"mean kolom {m} atas {len(col)} seed, protokol={proto},versi={versi},model={model}")
        put(f"{base}.{m}_ci95", round(ci, 6), f,
            f"1.96*sd/sqrt(n) kolom {m}, idem")

# ---------- T8: ringkasan E8 (e8_summary.json + kontrol/replika dari e8_runs.csv) ----------
f = os.path.join(R5G, "e8_summary.json")
e8 = json.load(open(f, encoding="utf-8"))
put("t8.n_skenario", e8["n_skenario"], f, "field n_skenario")
for proc, d in e8["per_prosedur"].items():
    for m in ("f1_mean", "f1_median", "prec_mean", "rec_mean"):
        put(f"t8.{proc}.{m}", d[m], f, f"per_prosedur.{proc}.{m}")
for proc, nb in e8["terbaik"].items():
    put(f"t8.{proc}.terbaik", nb, f, f"terbaik.{proc}")

f = os.path.join(R5G, "e8_runs.csv")
with open(f, encoding="utf-8") as fh:
    e8r = list(csv.DictReader(fh))
for r in e8r:
    if r["skenario"] == "kontrol_negatif":
        put(f"t8.{r['prosedur']}.kontrol_n_flag", int(r["n_flag"]), f,
            "kolom n_flag baris skenario=kontrol_negatif (n_poison=0; semua flag salah)")
    if r["skenario"] == "s12_atk2benign_full_BS1_UDPFlood":
        put(f"t8.{r['prosedur']}.replika_recall", float(r["recall"]), f,
            "kolom recall baris skenario=s12_atk2benign_full_BS1_UDPFlood "
            "(replika bug asli: UDPFlood IP penyerang di BS1/UDPFlood1.csv -> Benign, "
            "seluruh file)")
        put(f"t8.{r['prosedur']}.replika_f1", float(r["f1"]), f,
            "kolom f1 baris skenario=s12_atk2benign_full_BS1_UDPFlood")
        put("t8.replika_n_poison", int(r["n_poison"]), f,
            "kolom n_poison baris s12 (jumlah baris diracuni)")

# ---------- T9: evaluasi tingkat blok E9 (e9_summary.json + replika dari e9_runs.csv) ----------
f = os.path.join(R5G, "e9_summary.json")
e9 = json.load(open(f, encoding="utf-8"))
put("t9.n_skenario", e9["n_skenario"], f, "field n_skenario")
for proc, d in e9["per_prosedur"].items():
    for m in ("pct_rank1", "pct_top3", "mean_rank", "median_rank", "n_absen"):
        put(f"t9.{proc}.{m}", d[m], f, f"per_prosedur.{proc}.{m}")
w9 = e9["wilcoxon_rank_d_vs"]["c_global_noid"]
put("t9.wilcoxon_d_vs_c.p", round(w9["p_two_sided"], 4), f,
    "wilcoxon_rank_d_vs.c_global_noid.p_two_sided (dibulatkan 4 desimal)")
put("t9.wilcoxon_d_vs_c.mean_diff", w9["mean_diff_rank_d_minus"], f,
    "wilcoxon_rank_d_vs.c_global_noid.mean_diff_rank_d_minus")
mc9 = e9["mcnemar_top1_d_vs"]["c_global_noid"]
put("t9.mcnemar_d_vs_c.p", mc9["p_exact_two_sided"], f,
    "mcnemar_top1_d_vs.c_global_noid.p_exact_two_sided")
put("t9.mcnemar_d_vs_c.d_saja", mc9["d_saja"], f,
    "mcnemar_top1_d_vs.c_global_noid.d_saja")
put("t9.mcnemar_d_vs_c.lain_saja", mc9["lain_saja"], f,
    "mcnemar_top1_d_vs.c_global_noid.lain_saja")

f = os.path.join(R5G, "e9_runs.csv")
with open(f, encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        if r["skenario"] == "s12_atk2benign_full_BS1_UDPFlood":
            put(f"t9.{r['prosedur']}.replika_s12_rank", int(r["rank_blok"]), f,
                "kolom rank_blok baris skenario=s12_atk2benign_full_BS1_UDPFlood "
                "(replika bug asli konvensi T8: file BS1/UDPFlood1.csv & IP "
                "penyerang asli, 175.811 baris)")
        if r["skenario"] == "s28_atk2benign_full_BS2_UDPFlood":
            put(f"t9.{r['prosedur']}.replika_s28_rank", int(r["rank_blok"]), f,
                "kolom rank_blok baris skenario=s28_atk2benign_full_BS2_UDPFlood "
                "(replika ukuran penuh 281.529 baris, konvensi laporan E8/E9)")

# ---------- Angka caption gambar ----------
f = os.path.join(RPA, "results", "c4_task4.json") if False else os.path.join(RPA, "c4_task4.json")
j = json.load(open(f, encoding="utf-8"))
for k in ("rows", "n_udpflood", "n_benign_konflik_di_file", "n_bin_10s", "pearson_r"):
    put(f"f3.{k}", j[k], f, f"field {k}")
f = os.path.join(R5G, "e1_config.json")
cfg = json.load(open(f, encoding="utf-8"))
put("meta.ip_penyerang", cfg["ip_penyerang"], f, "field ip_penyerang")
put("meta.ip_korban", cfg["ip_korban"], f, "field ip_korban")
put("meta.n_salah_label", cfg["n_salah_label"], f, "field n_salah_label")
put("meta.n_versi_C", cfg["n_versi_C"], f, "field n_versi_C")
put("meta.n_total", cfg["n_total"], f, "field n_total")

# ---------- Angka naratif inline main.tex (kunci n.*) ----------
# Semua dibaca dari file hasil; entri "derived" dihitung dari entri lain dan
# formulanya didokumentasikan di field where.
f = os.path.join(RPA, "c3_task1.json")
j = json.load(open(f, encoding="utf-8"))
put("n.konflik.n_vektor", j["n_vektor_konflik_ben_udp"], f, "field n_vektor_konflik_ben_udp")
put("n.konflik.pct_dari_benign", j["pct_benign_konflik_dari_semua_benign"], f,
    "field pct_benign_konflik_dari_semua_benign")

f = os.path.join(RPA, "c2_task3.json")
j = json.load(open(f, encoding="utf-8"))
put("n.konflik.n_baris_benudp", j["top10_shared_class_pairs"][0]["n_baris_terlibat"], f,
    "top10_shared_class_pairs[0].n_baris_terlibat (pasangan Benign-UDPFlood)")

f = os.path.join(RPA, "c2_task1.json")
j = json.load(open(f, encoding="utf-8"))
put("n.idonly.f1_seq_offset", j["variants"]["iii_hanya_seq_offset"]["mean"], f,
    "variants.iii_hanya_seq_offset.mean (macro-F1 hanya Seq+Offset, split acak)")

f = os.path.join(RPA, "c3_task2.json")
j = json.load(open(f, encoding="utf-8"))
put("n.bayes_raw.acc", j["bayes_accuracy"], f, "field bayes_accuracy (90 fitur mentah non-ID)")
put("n.bayes_raw.f1", j["bayes_macro_f1"], f, "field bayes_macro_f1")
put("n.bayes_raw.pct_konflik", j["pct_baris_vektor_konflik"], f, "field pct_baris_vektor_konflik")
put("n.bayes_raw.n_fitur", j["n_fitur_mentah_nonid"], f, "field n_fitur_mentah_nonid")

f = os.path.join(RPA, "c5_task1.json")
j = json.load(open(f, encoding="utf-8"))
put("n.kembar.n_kunci_cocok", j["lintas_bs"]["n_kunci_cocok"], f, "lintas_bs.n_kunci_cocok")
put("n.kembar.n_kunci_label_beda", j["lintas_bs"]["n_kunci_label_beda"], f,
    "lintas_bs.n_kunci_label_beda (semuanya Benign BS1 -> UDPFlood BS2)")

f = os.path.join(RPA, "c5_task3.json")
j = json.load(open(f, encoding="utf-8"))
put("n.lit_hgb.pct_benign", j["pct_diprediksi_benign_multi"], f,
    "pct_diprediksi_benign_multi (HGB protokol literatur, baris salah-label di test)")

f = os.path.join(RPA, "c5_task4.json")
j = json.load(open(f, encoding="utf-8"))
put("n.noid_hgb.pct_benign", j["pct_diprediksi_benign_multi"], f,
    "pct_diprediksi_benign_multi (HGB tanpa kolom identitas)")

f = os.path.join(RPA, "c5_task5.json")
j = json.load(open(f, encoding="utf-8"))
put("n.residu.n_oof", j["n_salah_label_vs_oof"], f, "field n_salah_label_vs_oof")
put("n.residu.n_conf95", j["n_keyakinan_95"], f, "field n_keyakinan_95")
put("n.residu.pct", j["pct_keyakinan_95"], f, "field pct_keyakinan_95")

f = os.path.join(R5G, "e6.json")
j = json.load(open(f, encoding="utf-8"))
put("n.synflood.recall", j["prediksi_synflood_bs1_mean"]["SYNFlood"], f,
    "prediksi_synflood_bs1_mean.SYNFlood")
put("n.synflood.ke_tcpconnectscan", j["prediksi_synflood_bs1_mean"]["TCPConnectScan"], f,
    "prediksi_synflood_bs1_mean.TCPConnectScan")
put("n.synflood.ke_synscan", j["prediksi_synflood_bs1_mean"]["SYNScan"], f,
    "prediksi_synflood_bs1_mean.SYNScan")
rate = [x for x in j["top10_fitur_beda"] if x["fitur"] == "Rate"][0]
put("n.synflood.rate_bs1", rate["mean_BS1"], f, "top10_fitur_beda[fitur=Rate].mean_BS1")
put("n.synflood.rate_bs2", rate["mean_BS2"], f, "top10_fitur_beda[fitur=Rate].mean_BS2")
put("n.synflood.cohen_d_load", abs(j["top10_fitur_beda"][0]["cohen_d"]), f,
    "abs(top10_fitur_beda[0].cohen_d) (fitur Load)")
_dw = [x for x in j["top10_fitur_beda"] if x["fitur"] == "DstWin"][0]
put("n.synflood.pct_nan_dstwin_bs1", _dw["nan_BS1_pct"], f,
    "top10_fitur_beda[fitur=DstWin].nan_BS1_pct (flow SYNFlood BS1 tanpa jendela TCP korban)")

f = os.path.join(RPA, "c4_task2.json")
j = json.load(open(f, encoding="utf-8"))
put("n.ip7.bs2_benign", j["fokus"]["10.155.15.7"]["BS2"]["per_label"]["Benign"], f,
    "fokus.10.155.15.7.BS2.per_label.Benign")

f = os.path.join(R5G, "e3_top_features.json")
j = json.load(open(f, encoding="utf-8"))
for feat in j["top25"]:
    if feat["fitur"] in ("Seq", "Offset"):
        put(f"n.anova.rank_{feat['fitur']}", feat["rank"], f,
            f"top25[fitur={feat['fitur']}].rank")

f = os.path.join(R5G, "e8_summary.json")
j = json.load(open(f, encoding="utf-8"))
put("n.e8.wilcoxon_c_p", round(j["wilcoxon_d_vs"]["c_global_noid"]["p_two_sided"], 4), f,
    "wilcoxon_d_vs.c_global_noid.p_two_sided (dibulatkan 4 desimal)")
for tipe, d in j["f1_mean_per_tipe"].items():
    for proc, val in d.items():
        put(f"n.e8.f1_tipe.{tipe}.{proc}", round(val, 4), f,
            f"f1_mean_per_tipe.{tipe}.{proc} (dibulatkan 4 desimal)")

# derived: persentase dan rentang lintas-model (formula di where)
put("n.derived.pct_salah_total",
    round(N["meta.n_salah_label"]["value"] / N["meta.n_total"]["value"] * 100, 2),
    os.path.join(R5G, "e1_config.json"),
    "derived: n_salah_label / n_total * 100, dibulatkan 2 desimal")
_lit11 = [("e2", m) for m in ("DT", "HGB", "KNN", "LR", "MLP", "RF")] + \
         [("dl", m) for m in ("CNN1D", "LSTM", "MLP3", "TABICL", "TRF")]
_f1 = [N[f"{s}.A.lit.{m}.f1_macro_mean"]["value"] for s, m in _lit11]
_ak = [N[f"{s}.A.lit.{m}.acc_korr_mean"]["value"] for s, m in _lit11]
_a = [N[f"{s}.A.lit.{m}.acc_mean"]["value"] for s, m in _lit11]
_src = "study_5gnidd_audit/results/e2_summary.csv + study_5gnidd_dl/results/runs.csv"
put("n.derived.lit11.f1_min", round(min(_f1), 4), _src, "derived: min f1_macro_mean, protokol lit versi A, 11 model")
put("n.derived.lit11.f1_max", round(max(_f1), 4), _src, "derived: max f1_macro_mean, idem")
put("n.derived.lit11.acc_min", round(min(_a), 4), _src, "derived: min acc_mean, idem")
put("n.derived.lit11.acc_korr_min", round(min(_ak), 4), _src, "derived: min acc_korr_mean, idem")
put("n.derived.lit11.acc_korr_max", round(max(_ak), 4), _src, "derived: max acc_korr_mean, idem")
_pmb = [N[f"dl.A.lit.{m}.pct_mis_benign_mean"]["value"]
        for m in ("CNN1D", "LSTM", "MLP3", "TABICL", "TRF")]
put("n.derived.dl.pct_mis_benign_min", round(min(_pmb), 2),
    "study_5gnidd_dl/results/runs.csv", "derived: min pct_mis_benign_mean 5 model DL, lit versi A")
put("n.derived.dl.pct_mis_benign_max", round(max(_pmb), 2),
    "study_5gnidd_dl/results/runs.csv", "derived: max pct_mis_benign_mean, idem")
_xf1 = [N[f"e2.{ver}.{p}.{m}.f1_macro_mean"]["value"]
        for ver in "BC" for p in ("b12", "b21")
        for m in ("DT", "HGB", "KNN", "LR", "MLP", "RF")]
put("n.derived.crossbs_corr.f1_min", round(min(_xf1), 4),
    "study_5gnidd_audit/results/e2_summary.csv",
    "derived: min f1_macro_mean, protokol b12/b21, versi B dan C, 6 model")
put("n.derived.crossbs_corr.f1_max", round(max(_xf1), 4),
    "study_5gnidd_audit/results/e2_summary.csv", "derived: max idem")
put("n.derived.kembar_sisa",
    N["meta.n_salah_label"]["value"] - N["n.kembar.n_kunci_label_beda"]["value"],
    os.path.join(RPA, "c5_task1.json"),
    "derived: n_salah_label - n_kunci_label_beda (baris salah-label tanpa kembar kunci penuh)")
put("n.derived.n_dedup_extra",
    N["meta.n_total"]["value"] - N["meta.n_salah_label"]["value"] - N["meta.n_versi_C"]["value"],
    os.path.join(R5G, "e1_config.json"),
    "derived: n_total - n_salah_label - n_versi_C (salinan lintas-file yang dibuang dedup versi C)")
put("n.derived.e5_d21_fp",
    N["t5.d_latihBS2_tandaiBS1.n_flag"]["value"] - N["t5.d_latihBS2_tandaiBS1.n_benar"]["value"],
    os.path.join(R5G, "e5_runs.csv"), "derived: n_flag - n_benar prosedur d (latih BS2)")

# ---------- T10 + n.cpla.*: Pilot D (study_cpla), audit lintas-partisi sebagai KOREKTOR ----------
# Hanya dua berkas run berskor dipakai (runs_*.csv.bak = partial run pertama yang
# dibatalkan, DIPARKIR, tidak dipakai; lihat study_cpla/REPORT.md penyimpangan 13).
import numpy as np  # noqa: E402
from scipy.stats import wilcoxon  # noqa: E402

CPSRC = "study_cpla/results/runs_a.csv + study_cpla/results/runs_cse.csv"
cp = pd.concat([pd.read_csv(os.path.join(RCP, x))
                for x in ("runs_a.csv", "runs_cse.csv")], ignore_index=True)
BASE_CP = ["noop", "cl", "cl_xp", "oof", "oof_xp"]


def _piv(d, metric):
    return d.pivot_table(index=["ds", "regime", "size_frac", "seed"],
                         columns="corrector", values=metric, aggfunc="first")


cp_inj, cp_ctl = cp[cp.regime != "R0"], cp[cp.regime == "R0"]
pf, pfpr = _piv(cp_inj, "f1_macro"), _piv(cp_inj, "fpr")
p0, p0f = _piv(cp_ctl, "f1_macro"), _piv(cp_ctl, "fpr")
put("t10.n_sel_suntik", int(len(pf)), CPSRC,
    "jumlah sel unik (ds x rezim x ukuran x seed) dengan regime != R0")
put("t10.n_sel_kontrol", int(len(p0)), CPSRC, "jumlah sel kontrol (regime == R0)")
put("t10.n_sel_total", int(len(pf) + len(p0)), CPSRC, "jumlah seluruh sel")
gap_cp = (pf["oracle_drop"] - pf["noop"]).dropna()
ok_cp = gap_cp >= 0.01
put("t10.n_sel_rusak", int(ok_cp.sum()), CPSRC,
    "jumlah sel tersuntik dengan f1_macro(oracle_drop) - f1_macro(noop) >= 0.01")
tr_cp = float(cp_ctl[cp_ctl.corrector == "noop"].n_train.mean())
put("t10.n_train_kontrol_mean", int(round(tr_cp)), CPSRC,
    "mean kolom n_train atas sel kontrol, korektor noop")

for c in BASE_CP + ["cpla"]:
    put(f"t10.{c}.ctl_df1", round(float(np.median((p0[c] - p0["noop"]).dropna())), 6), CPSRC,
        f"median f1_macro({c}) - f1_macro(noop) atas sel kontrol R0")
    put(f"t10.{c}.ctl_dfpr", round(float(np.median((p0f[c] - p0f["noop"]).dropna())), 6), CPSRC,
        f"median fpr({c}) - fpr(noop) atas sel kontrol R0")
    nd = float(cp_ctl[cp_ctl.corrector == c].n_dibuang.mean())
    put(f"t10.{c}.ctl_n_buang", int(round(nd)), CPSRC,
        f"mean kolom n_dibuang, korektor {c}, sel kontrol R0")
    put(f"t10.{c}.ctl_pct_buang", round(100 * nd / tr_cp, 4), CPSRC,
        f"derived: 100 * mean n_dibuang({c}) / mean n_train, sel kontrol R0")
    r = ((pf.loc[ok_cp, c] - pf.loc[ok_cp, "noop"]) / gap_cp[ok_cp]).dropna()
    put(f"t10.{c}.recov_median", round(float(np.median(r)), 4), CPSRC,
        f"median (f1({c})-f1(noop))/(f1(oracle_drop)-f1(noop)) atas sel dengan selisih >= 0.01")

for c in BASE_CP:
    d = (pf["cpla"] - pf[c]).dropna()
    s, p = wilcoxon(d.to_numpy(), alternative="greater", zero_method="wilcox")
    put(f"t10.vs_{c}.med_df1", round(float(np.median(d)), 6), CPSRC,
        f"median f1_macro(cpla) - f1_macro({c}) atas sel tersuntik")
    put(f"t10.vs_{c}.n_win", int((d > 0).sum()), CPSRC, f"jumlah sel cpla > {c}")
    put(f"t10.vs_{c}.n_tie", int((d == 0).sum()), CPSRC, f"jumlah sel cpla == {c}")
    put(f"t10.vs_{c}.n_lose", int((d < 0).sum()), CPSRC, f"jumlah sel cpla < {c}")
    put(f"t10.vs_{c}.p", round(float(p), 6), CPSRC,
        f"wilcoxon satu sisi (cpla > {c}), zero_method=wilcox, atas sel tersuntik")
    dd = (pfpr["cpla"] - pfpr[c]).dropna()
    put(f"t10.vs_{c}.med_dfpr", round(float(np.median(dd)), 6), CPSRC,
        f"median fpr(cpla) - fpr({c}) atas sel tersuntik")

# sel paling merusak: 5G-NIDD versi C, R1, blok 8% (mean atas 3 seed)
w = cp[(cp.ds == "g5c") & (cp.regime == "R1") & (cp.size_frac == 0.08)]
for c in ("noop", "cpla", "oracle_drop", "cl", "oof"):
    put(f"n.cpla.g5c_r1_8.{c}.f1", round(float(w[w.corrector == c].f1_macro.mean()), 4), CPSRC,
        f"mean f1_macro korektor {c}, ds=g5c regime=R1 size_frac=0.08 (3 seed)")
put("n.cpla.g5c_r1_8.n_inj", int(w.n_inj.max()), CPSRC,
    "max kolom n_inj, ds=g5c regime=R1 size_frac=0.08")

# fraksi baris yang TIDAK bisa diaudit lintas-partisi (penjaga dukungan)
ijl = []
for x in ("inject_a.jsonl", "inject_cse.jsonl"):
    with open(os.path.join(RCP, x), encoding="utf-8") as fh:
        ijl += [json.loads(line) for line in fh if line.strip()]
ij = pd.DataFrame(ijl)
for ds in ("g5c", "unsw", "cse"):
    put(f"n.cpla.pct_nonauditable.{ds}",
        int(round(100 * (1 - float(ij[ij.ds == ds].frac_auditable_xp.mean())))),
        "study_cpla/results/inject_a.jsonl + inject_cse.jsonl",
        f"derived: 100*(1 - mean frac_auditable_xp) ds={ds}, dibulatkan ke bilangan bulat")

# diagnostik mekanisme (diag.py, 9 sel R1 g5c)
fd = os.path.join(RCP, "DIAG_G5C_R1.json")
dg = pd.DataFrame(json.load(open(fd, encoding="utf-8")))
inv = dg[dg.kelas_asli == "TCPConnectScan"]     # blok tak terlihat
sat = dg[dg.kelas_asli == "SYNScan"]            # latar jenuh
pas = dg[dg.lolos_ambang_cpla]                  # lolos ambang
put("n.cpla.diag.n_sel", int(len(dg)), fd, "jumlah baris DIAG_G5C_R1.json")
put("n.cpla.diag.n_lolos", int(len(pas)), fd, "jumlah baris dengan lolos_ambang_cpla=true")
put("n.cpla.diag.inv_benign_pct_min", round(100 * float(inv.frac_diprediksi_benign.min()), 1),
    fd, "min frac_diprediksi_benign x100, baris kelas_asli=TCPConnectScan")
put("n.cpla.diag.inv_benign_pct_max", round(100 * float(inv.frac_diprediksi_benign.max()), 1),
    fd, "max frac_diprediksi_benign x100, idem")
put("n.cpla.diag.inv_rate_min", round(float(inv.blok_rate.min()), 3), fd,
    "min blok_rate, baris kelas_asli=TCPConnectScan")
put("n.cpla.diag.inv_rate_max", round(float(inv.blok_rate.max()), 3), fd,
    "max blok_rate, idem")
put("n.cpla.diag.sat_rate_pct_min", round(100 * float(sat.blok_rate.min()), 1), fd,
    "min blok_rate x100, baris kelas_asli=SYNScan (auditor TIDAK sepakat)")
put("n.cpla.diag.sat_rate_pct_max", round(100 * float(sat.blok_rate.max()), 1), fd,
    "max blok_rate x100, idem")
put("n.cpla.diag.sat_latar_med", round(float(sat.latar_med.median()), 3), fd,
    "median latar_med, baris kelas_asli=SYNScan")
put("n.cpla.diag.sat_z_min", round(float(sat.z.min()), 2), fd,
    "min z, baris kelas_asli=SYNScan")
put("n.cpla.diag.sat_z_max", round(float(sat.z.max()), 2), fd, "max z, idem")
put("n.cpla.diag.pas_z_min", round(float(pas.z.min()), 2), fd,
    "min z, baris lolos_ambang_cpla=true")
put("n.cpla.diag.pas_latar_med", round(float(pas.latar_med.max()), 3), fd,
    "max latar_med, baris lolos_ambang_cpla=true")

# presisi/recall deteksi CPLA HANYA pada sel yang lolos ambang menurut diagnostik
sl = cp[(cp.ds == "g5c") & (cp.regime == "R1") & (cp.corrector == "cpla")
        & cp.set_index(["size_frac", "seed"]).index.isin(
            list(zip(pas["size"], pas.seed)))]
_pas_sel = ", ".join(f"({a}, seed {b})" for a, b in zip(pas["size"], pas.seed))
put("n.cpla.lolos.det_prec_min", round(float(sl.det_prec.min()), 4), CPSRC,
    f"min det_prec cpla, ds=g5c regime=R1 pada sel lolos ambang {_pas_sel}")
put("n.cpla.lolos.det_prec_max", round(float(sl.det_prec.max()), 4), CPSRC, "max det_prec, idem")
put("n.cpla.lolos.det_rec_min", round(float(sl.det_rec.min()), 4), CPSRC, "min det_rec, idem")

# ambang & konfigurasi CPLA yang dipra-registrasi (dibaca dari cpla.py, bukan diketik)
fsrc = os.path.join(ROOT, "study_cpla", "cpla.py")
_txt = open(fsrc, encoding="utf-8").read()
_m = re.search(r"MIN_N,\s*RATE_MIN,\s*Z_MIN,\s*BG_MAX\s*=\s*([\d.]+),\s*([\d.]+),"
               r"\s*([\d.]+),\s*([\d.]+)", _txt)
for nm, val in zip(("min_n", "rate_min", "z_min", "bg_max"), _m.groups()):
    put(f"n.cpla.ambang.{nm}", float(val) if "." in val else int(val), fsrc,
        f"konstanta {nm.upper()} di baris 'MIN_N, RATE_MIN, Z_MIN, BG_MAX = ...'")
put("n.cpla.sha256_12", open(os.path.join(RCP, "SCRIPT.sha256")).read().split()[0][:12],
    "study_cpla/results/SCRIPT.sha256", "12 heksadesimal pertama sha256 cpla.py")
_m = re.search(r"N_TRAIN,\s*N_TEST\s*=\s*([\d_]+),\s*([\d_]+)", _txt)
put("n.cpla.n_train_cap", int(_m.group(1).replace("_", "")), fsrc, "konstanta N_TRAIN")
put("n.cpla.n_test_cap", int(_m.group(2).replace("_", "")), fsrc, "konstanta N_TEST")
put("n.cpla.gerbang.recov_min",
    float(re.search(r"G2 PEMULIHAN:.*?>=\s*([\d.]+)", _txt, re.S).group(1)), fsrc,
    "ambang G2 di docstring bagian F ('median fraksi pemulihan ... >= ...')")
put("n.cpla.gerbang.g3_batas",
    float(re.search(r"G3 TIDAK MERUSAK:.*?>=\s*-([\d.]+)", _txt, re.S).group(1)), fsrc,
    "batas G3 di docstring bagian F (ΔF1 >= -x dan ΔFPR <= +x)")
put("n.cpla.cse_n_sumber",
    int(json.load(open(os.path.join(RCP, "preflight_cse.json"), encoding="utf-8"))
        ["cse"]["n_sumber_train"]),
    "study_cpla/results/preflight_cse.json", "cse.n_sumber_train (proksi sidik-jari TCP)")
put("t10.n_sel_tanpa_rusak", int(len(pf)) - int(ok_cp.sum()), CPSRC,
    "derived: t10.n_sel_suntik - t10.n_sel_rusak")

# uji asap v1 (SEBELUM penjaga dukungan) — dasar angka di Threats to validity
sv = pd.read_csv(os.path.join(ROOT, "study_cpla", "results_smoke_v1", "runs.csv"))
sv0 = sv[sv.regime == "R0"]
_svsrc = "study_cpla/results_smoke_v1/runs.csv"
put("n.cpla.smoke_v1.noop_f1", round(float(sv0[sv0.corrector == "noop"].f1_macro.iloc[0]), 4),
    _svsrc, "f1_macro korektor noop, sel kontrol R0 uji asap v1")
put("n.cpla.smoke_v1.oof_xp_f1", round(float(sv0[sv0.corrector == "oof_xp"].f1_macro.iloc[0]), 4),
    _svsrc, "f1_macro korektor oof_xp, idem (korektor lintas-partisi terburuk)")
_svp = 100 * sv0[sv0.corrector.isin(["cl_xp", "oof_xp"])].n_dibuang \
    / float(sv0[sv0.corrector == "noop"].n_train.iloc[0])
put("n.cpla.smoke_v1.pct_buang_min", round(float(_svp.min()), 1), _svsrc,
    "min 100*n_dibuang/n_train atas cl_xp & oof_xp, sel kontrol R0 uji asap v1")
put("n.cpla.smoke_v1.pct_buang_max", round(float(_svp.max()), 1), _svsrc, "max idem")

out = {"entries": N, "tak_tertelusur": untraceable,
       "catatan": "ci95 e2 = kolom *_ci95 sumber; ci95 e4 dihitung 1.96*sd/sqrt(n)."}
with open(os.path.join(HERE, "NUMBERS.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, ensure_ascii=False)
print(f"NUMBERS.json: {len(N)} entri; tak tertelusur: {len(untraceable)}")
