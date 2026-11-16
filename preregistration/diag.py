"""Diagnostik mengapa blok R1 g5c 8% tak terdeteksi: distribusi prediksi OOF
lintas-partisi di dalam blok tersuntik, per ukuran blok dan seed.
Tidak mengubah hasil berskor; keluaran results/DIAG_G5C_R1.json.
python diag.py"""
import json
import os

import numpy as np
import pandas as pd

import cpla as C

HERE = os.path.dirname(os.path.abspath(__file__))
C.RES = os.path.join(HERE, "results")
C.TAG = "_diag"

d = C.build("g5c")
classes = sorted(set(d["ytr"]) | set(d["yte"]))
out = []
for size in C.SIZES:
    for seed in C.SEEDS:
        y, mask, info = C.inject(d, "R1", size, seed, seed, {})
        fx, kx = C.folds_xp(d["ptr"], seed)
        yhat, P, aud = C.oof(d["Xtr"], y, fx, kx, classes, seed)
        vc = pd.Series(yhat[mask]).value_counts()
        # replikasi keputusan CPLA untuk grup yang memuat blok tersuntik
        p0, s0 = info["blok"]["partisi"], info["blok"]["sumber"]
        gm = aud & (d["ptr"] == p0) & (d["str_"] == s0) & (y == d["benign"])
        n_g = int(gm.sum())
        qvc = pd.Series(yhat[gm & (y != yhat)]).value_counts()
        q = str(qvc.index[0]) if len(qvc) else None
        n_b = int(qvc.iloc[0]) if len(qvc) else 0
        rate = n_b / n_g if n_g else 0.0
        df = pd.DataFrame({"p": d["ptr"][aud], "s": d["str_"][aud],
                           "y": y[aud], "q": yhat[aud]})
        gsz = df.groupby(["p", "s", "y"], sort=False).size().rename("n_g")
        blk = df[df.y != df.q].groupby(["p", "s", "y", "q"], sort=False).size().rename("n_b")
        tt = blk.reset_index().merge(gsz.reset_index(), on=["p", "s", "y"], how="left")
        tt["rate"] = tt.n_b / tt.n_g
        bg = tt[(tt.n_g >= C.MIN_N) & (tt.y == d["benign"]) & (tt.q == q)
                & (tt.p != p0)].rate.to_numpy() if q else np.array([])
        med = float(np.median(bg)) if len(bg) else 0.0
        mad = float(np.median(np.abs(bg - med))) if len(bg) else 0.0
        z = (rate - med) / (1.4826 * mad + 0.01) if q else 0.0
        lolos = bool(n_b >= C.MIN_N and rate >= C.RATE_MIN
                     and z >= C.Z_MIN and med <= C.BG_MAX)
        row = dict(size=size, seed=seed, n_inj=int(mask.sum()),
                   grup_n_g=n_g, blok_q=q, blok_n_b=n_b, blok_rate=round(rate, 4),
                   latar_med=round(med, 4), z=(None if np.isinf(z) else round(z, 2)),
                   lolos_ambang_cpla=lolos,
                   kelas_asli=info["blok"]["kelas"], partisi=info["blok"]["partisi"],
                   sumber=info["blok"]["sumber"],
                   frac_auditable_blok=round(float(aud[mask].mean()), 4),
                   prediksi_oof_di_blok={k: int(v) for k, v in vc.head(5).items()},
                   frac_diprediksi_benign=round(float((yhat[mask] == d["benign"]).mean()), 4))
        out.append(row)
        print(json.dumps(row, default=C.jenc), flush=True)
with open(os.path.join(C.RES, "DIAG_G5C_R1.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, default=C.jenc)
print("tulis results/DIAG_G5C_R1.json")
