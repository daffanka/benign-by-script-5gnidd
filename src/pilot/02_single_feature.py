"""Step 02 — single-feature probes.

For every feature: DecisionTree(max_depth=3) on a 200k-row stratified sample,
binary task (benign vs attack) scored by ROC-AUC and multiclass task scored by
macro-F1. Reports the top-10 features per task. Sample/model seed = 0.
"""
import os
import sys
import time

import numpy as np
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C


def run(ds):
    t0 = time.time()
    df = C.load_sample(ds)
    feats, id_cols, y_bin, y_multi, group, gkey = C.dataset_columns(ds, df)
    idx = C.stratified_cap(y_multi, C.SF_SAMPLE, seed=0)
    X = C.encode_features(df.iloc[idx], feats)
    yb, ym = y_bin[idx], y_multi[idx]
    C.log(f"02: {ds} probing {len(feats)} features on {len(idx)} rows")

    tr, te = train_test_split(np.arange(len(idx)), test_size=0.3,
                              random_state=0, stratify=ym)
    rows = []
    for c in feats:
        x = X[c].to_numpy().reshape(-1, 1)
        res = {"feature": c, "is_identity": c in id_cols}
        try:
            m = DecisionTreeClassifier(max_depth=3, random_state=0)
            m.fit(x[tr], yb[tr])
            p = m.predict_proba(x[te])
            auc = roc_auc_score(yb[te], p[:, 1]) if p.shape[1] > 1 else 0.5
            res["auc_bin"] = round(float(auc), 4)
        except Exception as e:
            res["auc_bin"] = None
            res["err_bin"] = str(e)
        try:
            m = DecisionTreeClassifier(max_depth=3, random_state=0)
            m.fit(x[tr], ym[tr])
            pred = m.predict(x[te])
            f1 = f1_score(ym[te], pred, average="macro", zero_division=0)
            res["f1_multi"] = round(float(f1), 4)
        except Exception as e:
            res["f1_multi"] = None
            res["err_multi"] = str(e)
        rows.append(res)

    top_bin = sorted([r for r in rows if r["auc_bin"] is not None],
                     key=lambda r: -r["auc_bin"])[:10]
    top_multi = sorted([r for r in rows if r["f1_multi"] is not None],
                       key=lambda r: -r["f1_multi"])[:10]
    out = {
        "dataset": ds, "n_rows_probe": int(len(idx)),
        "top10_auc_bin": top_bin, "top10_f1_multi": top_multi,
        "all_features": rows,
        "top3_bin": [r["feature"] for r in top_bin[:3]],
        "top3_multi": [r["feature"] for r in top_multi[:3]],
        "runtime_s": round(time.time() - t0, 1),
    }
    C.save_json(f"single_feature_{ds}.json", out)
    C.log(f"02: {ds} done top3_bin={out['top3_bin']} top3_multi={out['top3_multi']} "
          f"({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    run(sys.argv[1])
