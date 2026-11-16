"""E6 — SYNFlood BS2->BS1 (recall ~0,71): fitur mana yang berbeda antar BS untuk
kelas ini, dan menjadi kelas apa salah prediksinya.

Versi B (label terkoreksi), 42 fitur non-identitas, HGB seed 0-2.
Keluaran: results/e6.json, e6_feature_diff.csv.
"""
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common_s as S


def main():
    t0 = time.time()
    d, fj = S.load_full()
    feats42 = fj["feats42"]
    y = d["__ycorr"].to_numpy().astype(str)
    bs = d["__bs"].to_numpy()
    X = S.encode_features(d, feats42)

    # perbedaan fitur SYNFlood BS1 vs BS2 (Cohen's d pada fitur ter-encode)
    syn1 = X.loc[(bs == "BS1") & (y == "SYNFlood")]
    syn2 = X.loc[(bs == "BS2") & (y == "SYNFlood")]
    rows = []
    for c in feats42:
        a, b = syn1[c].to_numpy(), syn2[c].to_numpy()
        ma, mb = np.nanmean(a), np.nanmean(b)
        sa, sb = np.nanstd(a), np.nanstd(b)
        sp = np.sqrt((sa ** 2 + sb ** 2) / 2)
        dcoh = (ma - mb) / sp if sp > 0 else (0.0 if ma == mb else np.inf)
        rows.append({"fitur": c,
                     "mean_BS1": round(float(ma), 4), "mean_BS2": round(float(mb), 4),
                     "sd_BS1": round(float(sa), 4), "sd_BS2": round(float(sb), 4),
                     "nan_BS1_pct": round(100 * float(np.isnan(a).mean()), 2),
                     "nan_BS2_pct": round(100 * float(np.isnan(b).mean()), 2),
                     "cohen_d": round(float(dcoh), 4),
                     "abs_d": round(float(abs(dcoh)), 4)})
    diff = pd.DataFrame(rows).sort_values("abs_d", ascending=False)
    diff.to_csv(os.path.join(S.RESULTS, "e6_feature_diff.csv"), index=False)

    # latih BS2 -> prediksi BS1; ke kelas apa SYNFlood BS1 jatuh
    i2 = np.flatnonzero(bs == "BS2")
    i1syn = np.flatnonzero((bs == "BS1") & (y == "SYNFlood"))
    pred_dist = []
    for seed in range(3):
        cols = [c for c in feats42 if X.iloc[i2][c].nunique(dropna=True) >= 2]
        m = S.make_model("HGB", seed)
        m.fit(X.iloc[i2][cols], y[i2])
        p = m.predict(X.iloc[i1syn][cols])
        vc = pd.Series(p).value_counts(normalize=True)
        pred_dist.append(vc)
        S.log(f"E6 seed {seed}: recall SYNFlood="
              f"{float(vc.get('SYNFlood', 0)):.4f}", tag="e6")
    mean_dist = (pd.concat(pred_dist, axis=1).fillna(0).mean(axis=1)
                 .sort_values(ascending=False))

    S.save_json("e6.json", {
        "setup": "versi B (label terkoreksi), 42 fitur non-ID, HGB seed 0-2; "
                 "latih seluruh BS2, prediksi baris SYNFlood BS1 "
                 f"(n={len(i1syn)})",
        "prediksi_synflood_bs1_mean": {k: round(float(v), 4)
                                       for k, v in mean_dist.items()},
        "top10_fitur_beda": diff.head(10).to_dict("records"),
        "catatan": "cohen_d dihitung pada fitur ter-encode (kolom kategorikal = "
                   "kode kategori); NaN diabaikan dalam mean/sd",
        "runtime_s": round(time.time() - t0, 1)})
    S.log(f"E6 selesai ({(time.time()-t0)/60:.1f} menit)", tag="e6")


if __name__ == "__main__":
    main()
