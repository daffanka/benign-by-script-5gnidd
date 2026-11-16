"""E1 — dari file mentah per-BS, bangun tiga versi dataset:
A asli, B relabel 281.529 baris, C buang + dedup lintas-file (kunci 8 kolom).

Cetak jumlah baris per kelas per BS tiap versi; verifikasi cocok dengan C4/C5
(281.529 baris salah-label; 925.573 baris versi C). Simpan cache/full.parquet
(fitur Combined + meta) + cache/feats.json + results/e1_counts.csv +
results/e1_config.json.
"""
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common_s as S

KEY = ["StartTime", "SrcAddr", "DstAddr", "Sport", "Dport", "Proto",
       "TotPkts", "TotBytes"]


def main():
    t0 = time.time()
    c4 = S.pilot_c4()
    S.log("E1: memuat file mentah per-BS (cache pilot_audit)")
    d = c4.load_raw_files()
    feats_all, feats42 = c4.feats_sets()
    att = sorted(c4.attacker_ips(d))
    victim = c4.VICTIM

    # aturan koreksi C4
    mis = ((d["SrcAddr"].astype(str).isin(att))
           & (d["DstAddr"].astype(str) == victim)
           & (d["Proto"].astype(str) == "udp")
           & d["__file"].str.startswith("UDPFlood")
           & (d["__y"] == "Benign")).to_numpy()
    y_corr = d["__y"].to_numpy().copy()
    y_corr[mis] = "UDPFlood"

    # kunci 8 kolom + dedup lintas-file versi C (logika identik C5)
    k = pd.util.hash_pandas_object(d[KEY].astype(str), index=False).to_numpy()
    keep = ~mis
    order_file = {f: i for i, f in enumerate(
        [f"{bs}/{fn}" for bs in ["BS1", "BS2"]
         for fn in sorted(d.loc[d["__bs"] == bs, "__file"].unique())])}
    fileidx = (d["__bs"] + "/" + d["__file"]).map(order_file).to_numpy()
    g = pd.DataFrame({"k": k[keep], "fi": fileidx[keep]})
    first = g.groupby("k")["fi"].min()
    keep_c = keep.copy()
    keep_c[keep] = (g["fi"].to_numpy() == first.loc[g["k"]].to_numpy())

    n_mis, n_c = int(mis.sum()), int(keep_c.sum())
    S.log(f"E1: n_salah_label={n_mis} (harap {S.N_TRUTH}); "
          f"versi C={n_c} baris (harap {S.N_VER_C})")
    assert n_mis == S.N_TRUTH, f"salah-label {n_mis} != {S.N_TRUTH}"
    assert n_c == S.N_VER_C, f"versi C {n_c} != {S.N_VER_C}"

    # simpan parquet: fitur Combined + kolom kunci/meta
    extra = [c for c in ["StartTime", "SrcAddr", "DstAddr"] if c not in feats_all]
    out = d[feats_all + extra + ["__bs", "__file", "__y"]].copy()
    out["__ycorr"] = y_corr
    out["__mis"] = mis
    out["__keepC"] = keep_c
    out["__key"] = k
    for c in out.columns:
        if not (pd.api.types.is_numeric_dtype(out[c])
                or pd.api.types.is_bool_dtype(out[c])):
            out[c] = out[c].astype("string")
    out.to_parquet(S.FULL, index=False)

    with open(S.FEATS, "w", encoding="utf-8") as f:
        import json
        json.dump({"feats_all": feats_all, "feats42": feats42,
                   "id_cols": [c for c in feats_all if c not in feats42],
                   "classes": sorted(pd.unique(d["__y"]).tolist()),
                   "key": KEY}, f, indent=2)

    # hitungan per kelas per BS tiap versi
    rows = []
    for v in ["A", "B", "C"]:
        if v == "A":
            m, y = np.ones(len(d), bool), d["__y"].to_numpy()
        elif v == "B":
            m, y = np.ones(len(d), bool), y_corr
        else:
            m, y = keep_c, d["__y"].to_numpy()
        tab = (pd.DataFrame({"bs": d["__bs"].to_numpy()[m], "y": y[m]})
               .groupby(["y", "bs"]).size().unstack(fill_value=0))
        print(f"\n=== Versi {v}: total {int(m.sum())} baris ===")
        print(tab.to_string())
        for cls in tab.index:
            rows.append({"versi": v, "kelas": cls,
                         "BS1": int(tab.loc[cls].get("BS1", 0)),
                         "BS2": int(tab.loc[cls].get("BS2", 0)),
                         "total": int(tab.loc[cls].sum())})
    pd.DataFrame(rows).to_csv(os.path.join(S.RESULTS, "e1_counts.csv"), index=False)

    S.save_json("e1_config.json", {
        "sumber": "pilot_audit/cache/bs1|bs2 (CSV mentah per-BS, label NaN dibuang)",
        "aturan_relabel": "Benign & SrcAddr in IP penyerang & DstAddr=korban & "
                          "Proto=udp & file UDPFlood* -> UDPFlood",
        "ip_penyerang": att, "ip_korban": victim,
        "kunci_dedup": KEY,
        "versi_C": "buang baris salah-label + untuk kunci lintas-file simpan hanya "
                   "occurrence di file pertama (urutan BS1->BS2, nama file terurut)",
        "n_salah_label": n_mis, "n_versi_C": n_c, "n_total": int(len(d)),
        "runtime_s": round(time.time() - t0, 1)})
    S.log(f"E1 selesai ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
