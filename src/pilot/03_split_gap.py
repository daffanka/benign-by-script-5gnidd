"""Step 03 — split-protocol gap, multiclass task.

Model: sklearn HistGradientBoostingClassifier (histogram-GBDT, the same
algorithm family as LightGBM; LightGBM itself is not installed in the frozen
experiment env and installs were not permitted). Settings mimic LightGBM
defaults: max_iter=100, lr=0.1, 255 bins, no early stopping, CPU only.

Protocols (seeds 0,1,2):
  (a) stratified random split 70/30
  (b) stratified random split after dropping exact duplicates (features+label)
  (c) grouped split: CICIoT2023 by source file; 5G-NIDD by 10 sequential row
      blocks (7 train / 3 test, blocks chosen per seed) since no time/file col.

Reports macro-F1 and per-class recall. Model rows capped at MODEL_CAP
(stratified) for the 3-hour CPU budget.
"""
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import f1_score, recall_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C


def make_model(seed):
    # l2_regularization=0.1: without it leaf values diverge (raw scores ~1e6)
    # on near-separable classes; LightGBM avoids this via its default
    # min_sum_hessian_in_leaf=1e-3, which sklearn's HGB lacks.
    return HistGradientBoostingClassifier(
        max_iter=100, learning_rate=0.1, max_bins=255,
        early_stopping=False, random_state=seed, l2_regularization=0.1)


def split_indices(protocol, X, ym, group, seed):
    n = len(ym)
    if protocol == "a":
        tr, te = train_test_split(np.arange(n), test_size=0.3,
                                  random_state=seed, stratify=ym)
        return tr, te, None
    if protocol == "b":
        h = pd.util.hash_pandas_object(X, index=False).to_numpy()
        h = h ^ (pd.Categorical(ym).codes.astype(np.uint64)
                 * np.uint64(0x9E3779B97F4A7C15))
        keep = ~pd.Series(h).duplicated().to_numpy()
        pos = np.flatnonzero(keep)
        ymk = ym[pos]
        # classes reduced to 1 member cannot be stratified; keep them in train
        vc = pd.Series(ymk).value_counts()
        ok = ymk_in = np.isin(ymk, vc.index[vc >= 2])
        tr2, te2 = train_test_split(np.arange(ok.sum()), test_size=0.3,
                                    random_state=seed, stratify=ymk[ok])
        base = pos[ok]
        tr = np.concatenate([base[tr2], pos[~ok]])
        te = base[te2]
        return tr, te, {"rows_after_dedup": int(len(pos)), "rows_before": int(n)}
    if protocol == "c":
        rng = np.random.default_rng(seed)
        groups = np.asarray(group)
        uniq = pd.unique(groups)
        k_test = max(1, int(round(len(uniq) * 0.3)))
        te_groups = rng.choice(uniq, size=k_test, replace=False)
        te_mask = np.isin(groups, te_groups)
        tr = np.flatnonzero(~te_mask)
        te = np.flatnonzero(te_mask)
        return tr, te, {"n_groups": int(len(uniq)), "n_test_groups": int(k_test),
                        "test_groups": [str(g) for g in te_groups]}
    raise ValueError(protocol)


def run_protocols(ds, tag, drop_features):
    """tag: 'full' (step 03, protocols a/b/c) or 'ablate' (step 04, a/c)."""
    t0 = time.time()
    df = C.load_sample(ds)
    feats, id_cols, y_bin, y_multi, group, gkey = C.dataset_columns(ds, df)
    feats = [c for c in feats if c not in drop_features]

    idx = C.stratified_cap(y_multi, C.MODEL_CAP, seed=0)
    idx = np.sort(idx)
    df = df.iloc[idx]
    X = C.encode_features(df, feats)
    # sklearn's HGB binner crashes on columns with <2 distinct non-NaN values
    degenerate = [c for c in X.columns if X[c].nunique(dropna=True) < 2]
    if degenerate:
        C.log(f"03/04[{tag}]: {ds} dropping degenerate cols {degenerate}")
        X = X.drop(columns=degenerate)
        feats = [c for c in feats if c not in degenerate]
    ym = y_multi[idx]
    grp = np.asarray(group)[idx]
    all_classes = np.unique(y_multi)
    C.log(f"03/04[{tag}]: {ds} rows={len(df)} feats={len(feats)} "
          f"dropped={sorted(drop_features)}")

    protocols = ["a", "b", "c"] if tag == "full" else ["a", "c"]
    results = []
    for proto in protocols:
        for seed in C.SEEDS:
            ts = time.time()
            tr, te, info = split_indices(proto, X, ym, grp, seed)
            m = make_model(seed)
            # guard: a column can still collapse to <2 distinct values inside
            # this particular train split
            Xtr = X.iloc[tr]
            bad = [c for c in Xtr.columns if Xtr[c].nunique(dropna=True) < 2]
            cols = [c for c in X.columns if c not in bad]
            try:
                m.fit(Xtr[cols], ym[tr])
            except Exception as e:
                results.append({"protocol": proto, "seed": seed,
                                "error": f"{type(e).__name__}: {e}"})
                C.log(f"03/04[{tag}]: {ds} proto={proto} seed={seed} FIT ERROR {e}")
                continue
            pred = m.predict(X.iloc[te][cols])
            f1 = f1_score(ym[te], pred, average="macro",
                          labels=all_classes, zero_division=0)
            rec = recall_score(ym[te], pred, average=None,
                               labels=all_classes, zero_division=0)
            res = {
                "protocol": proto, "seed": seed,
                "macro_f1": round(float(f1), 4),
                "recall_per_class": {str(c): round(float(r), 4)
                                     for c, r in zip(all_classes, rec)},
                "n_train": int(len(tr)), "n_test": int(len(te)),
                "classes_missing_in_train":
                    [str(c) for c in all_classes if c not in set(ym[tr])],
                "fit_s": round(time.time() - ts, 1),
            }
            if info:
                res["split_info"] = info
            results.append(res)
            C.log(f"03/04[{tag}]: {ds} proto={proto} seed={seed} "
                  f"macroF1={f1:.4f} ({time.time()-ts:.0f}s)")

    out = {
        "dataset": ds, "tag": tag, "group_key": gkey,
        "features_used": feats, "features_dropped": sorted(drop_features),
        "model": "HistGradientBoostingClassifier(max_iter=100, lr=0.1, "
                 "max_bins=255, early_stopping=False, l2_regularization=0.1) — "
                 "pengganti LightGBM (tidak terpasang; instalasi tidak diizinkan); "
                 "l2=0.1 mencegah divergensi nilai leaf (pengganti "
                 "min_sum_hessian_in_leaf LightGBM)",
        "model_rows_cap": C.MODEL_CAP,
        "results": results,
        "runtime_s": round(time.time() - t0, 1),
    }
    name = f"splitgap_{ds}.json" if tag == "full" else f"ablation_{ds}.json"
    C.save_json(name, out)
    C.log(f"03/04[{tag}]: {ds} done ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    run_protocols(sys.argv[1], "full", set())
