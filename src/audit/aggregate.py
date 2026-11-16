"""Agregasi hasil E2 (mean, sd, CI95% t-dist) -> results/e2_summary.csv +
cetak tabel ringkas untuk REPORT.md."""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common_s as S


def ci95(x):
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return 0.0
    return float(stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n))


def main():
    parts = []
    for lane in ["lane1", "lane2"]:
        p = os.path.join(S.RESULTS, f"e2_runs_{lane}.csv")
        if os.path.exists(p):
            parts.append(pd.read_csv(p))
    d = pd.concat(parts, ignore_index=True)
    print(f"total run: {len(d)}")
    metrics = [c for c in d.columns if c.startswith(("acc", "f1", "tpr", "fpr",
                                                     "rec"))]
    g = d.groupby(["versi", "protokol", "model"])
    rows = []
    for (v, p, m), gg in g:
        r = {"versi": v, "protokol": p, "model": m, "n_seed": len(gg)}
        for met in metrics:
            x = pd.to_numeric(gg[met], errors="coerce").dropna()
            if len(x) == 0:
                continue
            r[f"{met}_mean"] = round(float(x.mean()), 4)
            r[f"{met}_sd"] = round(float(x.std(ddof=1)), 5) if len(x) > 1 else 0.0
            r[f"{met}_ci95"] = round(ci95(x), 5)
        rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(S.RESULTS, "e2_summary.csv"), index=False)

    for proto in ["lit", "noid", "b12", "b21"]:
        print(f"\n### protokol {proto}: f1_macro mean (sd) [vs korr untuk A]")
        piv = out.loc[out["protokol"] == proto]
        for m in ["LR", "DT", "RF", "HGB", "KNN", "MLP"]:
            line = [m]
            for v in ["A", "B", "C"]:
                row = piv.loc[(piv["versi"] == v) & (piv["model"] == m)]
                if len(row) == 0:
                    line.append("-")
                    continue
                r = row.iloc[0]
                s = f"{r.get('f1_macro_mean', np.nan):.4f}±{r.get('f1_macro_sd', 0):.4f}"
                if v == "A" and not pd.isna(r.get("f1_macro_korr_mean", np.nan)):
                    s += f" | korr {r['f1_macro_korr_mean']:.4f}"
                line.append(s)
            print(" | ".join(str(x) for x in line))
        print(f"\n### protokol {proto}: acc / tpr / fpr")
        for m in ["LR", "DT", "RF", "HGB", "KNN", "MLP"]:
            line = [m]
            for v in ["A", "B", "C"]:
                row = piv.loc[(piv["versi"] == v) & (piv["model"] == m)]
                if len(row) == 0:
                    line.append("-")
                    continue
                r = row.iloc[0]
                line.append(f"acc {r.get('acc_mean', np.nan):.4f} "
                            f"tpr {r.get('tpr_mean', np.nan):.4f} "
                            f"fpr {r.get('fpr_mean', np.nan):.4f}")
            print(" | ".join(str(x) for x in line))
    # recall per kelas HGB lintas-BS versi A vs B
    print("\n### recall per kelas (HGB, b12/b21)")
    for proto in ["b12", "b21"]:
        for v in ["A", "B", "C"]:
            row = out.loc[(out["versi"] == v) & (out["protokol"] == proto)
                          & (out["model"] == "HGB")]
            if len(row):
                r = row.iloc[0]
                recs = {c.replace("rec_", "").replace("_mean", ""):
                        r[c] for c in out.columns
                        if c.startswith("rec_") and c.endswith("_mean")
                        and "korr" not in c and not pd.isna(r.get(c, np.nan))}
                print(proto, v, recs)


if __name__ == "__main__":
    main()
