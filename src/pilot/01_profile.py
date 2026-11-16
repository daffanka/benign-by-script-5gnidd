"""Step 01 — profile each dataset and build the <=1M-row stratified sample cache.

Per dataset reports: rows, columns, classes; % exact duplicate rows
(features+label); % rows whose features collide with a different label;
constant columns; available identity columns.

5G-NIDD is profiled in full (1.21M rows fit in RAM). CICIoT2023 is profiled in
a streaming pass over all 63 merged CSVs (exact duplicate stats via uint64 row
hashes), then sampled in a second pass.
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C


def dup_stats_from_hashes(h_full, h_feat, labels_codes):
    """h_full: hash(features+label); h_feat: hash(features only)."""
    n = len(h_full)
    n_unique_full = len(pd.unique(h_full))
    dup_pct = 100.0 * (n - n_unique_full) / n
    # rows whose feature-hash occurs with >1 distinct label
    df = pd.DataFrame({"h": h_feat, "y": labels_codes})
    nlab = df.groupby("h", sort=False)["y"].nunique()
    bad_hashes = nlab.index[nlab.to_numpy() > 1]
    conflict_rows = int(df["h"].isin(bad_hashes).sum())
    conflict_pct = 100.0 * conflict_rows / n
    return dup_pct, conflict_pct, n_unique_full


def profile_5gnidd():
    t0 = time.time()
    C.log("01: loading 5G-NIDD Combined.csv (full)")
    df = pd.read_csv(C.PATH_5GNIDD, low_memory=False)
    df = df.rename(columns={df.columns[0]: "row_id"})
    n, ncol = df.shape
    feats = [c for c in df.columns if c not in C.NIDD_LABEL_COLS + ["row_id"]]

    classes = df["Attack Type"].astype(str).value_counts().to_dict()
    lab_codes = pd.Categorical(df["Attack Type"].astype(str)).codes

    h_feat = pd.util.hash_pandas_object(df[feats], index=False).to_numpy()
    h_full = h_feat ^ (lab_codes.astype(np.uint64) * np.uint64(0x9E3779B97F4A7C15))
    dup_pct, conflict_pct, n_uniq = dup_stats_from_hashes(h_full, h_feat, lab_codes)

    # same stats with identity columns excluded (Seq/Offset/VLAN/TCP-base make
    # every row unique, hiding the real duplicate rate)
    feats_noid = [c for c in feats if c not in C.NIDD_ID_COLS]
    h_feat2 = pd.util.hash_pandas_object(df[feats_noid], index=False).to_numpy()
    h_full2 = h_feat2 ^ (lab_codes.astype(np.uint64) * np.uint64(0x9E3779B97F4A7C15))
    dup_pct2, conflict_pct2, _ = dup_stats_from_hashes(h_full2, h_feat2, lab_codes)

    const_cols = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    id_present = [c for c in df.columns if c in C.NIDD_ID_COLS]

    prof = {
        "dataset": "5gnidd", "rows": int(n), "cols": int(ncol),
        "n_classes_multi": int(len(classes)), "class_counts": classes,
        "dup_exact_pct": round(dup_pct, 4),
        "same_feat_diff_label_pct": round(conflict_pct, 4),
        "dup_exact_pct_no_id": round(dup_pct2, 4),
        "same_feat_diff_label_pct_no_id": round(conflict_pct2, 4),
        "constant_cols": const_cols,
        "identity_cols": id_present,
        "identity_cols_note": "row_id = indeks ekspor CSV (kolom pertama tanpa nama); "
                              "Seq = nomor urut record Argus; Offset = byte offset record; "
                              "sVid/dVid = VLAN id; SrcTCPBase/DstTCPBase = TCP seq awal. "
                              "Tidak ada kolom IP/port/timestamp di Combined.csv.",
        "runtime_s": round(time.time() - t0, 1),
    }
    C.save_json("profile_5gnidd.json", prof)

    # ---- sample cache (stratified by Attack Type, seed 0, cap 1M) ----
    idx = C.stratified_cap(df["Attack Type"].astype(str).to_numpy(), C.SAMPLE_CAP, seed=0)
    sub = df.iloc[np.sort(idx)].copy()
    sub["orig_idx"] = np.sort(idx)
    # 10 sequential blocks over the ORIGINAL row order (no timestamp column exists)
    sub["time_block"] = (sub["orig_idx"] * 10 // n).astype(np.int8)
    sub.to_parquet(C.sample_path("5gnidd"), index=False)
    C.log(f"01: 5gnidd done rows={n} dup%={dup_pct:.2f} conflict%={conflict_pct:.2f} "
          f"sample={len(sub)} ({time.time()-t0:.0f}s)")
    return prof


def profile_ciciot():
    t0 = time.time()
    files = C.ciciot_files()
    C.log(f"01: streaming CICIoT2023 pass 1 over {len(files)} files")
    hashes_feat, hashes_full, lab_list = [], [], []
    class_counts = {}
    per_file_counts = {}
    num_min, num_max = {}, {}
    ncols = None
    feat_cols = None
    total = 0
    n_label_na = 0
    for fi, path in enumerate(files):
        fname = os.path.basename(path)
        per_file_counts[fname] = 0
        for chunk in pd.read_csv(path, chunksize=C.CHUNK, low_memory=False):
            if feat_cols is None:
                ncols = chunk.shape[1]
                feat_cols = [c for c in chunk.columns if c != C.CICIOT_LABEL_COL]
            na = chunk[C.CICIOT_LABEL_COL].isna()
            if na.any():
                n_label_na += int(na.sum())
                chunk = chunk.loc[~na]
            lab = chunk[C.CICIOT_LABEL_COL].astype(str)
            vc = lab.value_counts()
            for k, v in vc.items():
                class_counts[k] = class_counts.get(k, 0) + int(v)
            per_file_counts[fname] += len(chunk)
            total += len(chunk)
            feats32 = chunk[feat_cols].astype(np.float32)  # hash on float32 so ties are stable
            hf = pd.util.hash_pandas_object(feats32, index=False).to_numpy()
            hashes_feat.append(hf)
            lab_list.append(lab.to_numpy())
            for c in feat_cols:
                col = feats32[c]
                mn, mx = col.min(), col.max()
                num_min[c] = min(num_min.get(c, np.inf), mn)
                num_max[c] = max(num_max.get(c, -np.inf), mx)
        C.log(f"01: pass1 {fi+1}/{len(files)} {fname} rows_total={total}")
    all_labels = sorted(class_counts)
    lab_codes = pd.Categorical(np.concatenate(lab_list), categories=all_labels).codes
    del lab_list
    h_feat = np.concatenate(hashes_feat)
    del hashes_feat
    h_full = h_feat ^ (lab_codes.astype(np.uint64) * np.uint64(0x9E3779B97F4A7C15))
    dup_pct, conflict_pct, n_uniq = dup_stats_from_hashes(h_full, h_feat, lab_codes)
    del h_feat, h_full

    const_cols = [c for c in feat_cols if num_min[c] == num_max[c]]
    # no IP/port/timestamp/ID columns exist in the merged CSVs; name-pattern
    # hits (Time_To_Live, IPv) are real protocol features, not identity
    id_present = []

    prof = {
        "dataset": "ciciot2023", "rows": int(total), "cols": int(ncols),
        "n_classes_multi": len(class_counts), "class_counts": class_counts,
        "dup_exact_pct": round(dup_pct, 4),
        "same_feat_diff_label_pct": round(conflict_pct, 4),
        "constant_cols": const_cols,
        "identity_cols": id_present,
        "identity_cols_note": "Tidak ada kolom IP/port/timestamp/ID di CSV merged; "
                              "satu-satunya kunci identitas adalah file asal (Merged01..63). "
                              "Duplikat dihitung pada fitur float32 (hash uint64, eksak).",
        "n_files": len(files),
        "label_na_rows_dropped": int(n_label_na),
        "runtime_s": round(time.time() - t0, 1),
    }
    C.save_json("profile_ciciot2023.json", prof)
    C.log(f"01: ciciot pass1 done rows={total} dup%={dup_pct:.2f} conflict%={conflict_pct:.2f}")

    # ---- pass 2: stratified sample, cap 1M, keep src_file ----
    rng = np.random.default_rng(0)
    frac = min(1.0, C.SAMPLE_CAP / total)
    target = {k: max(int(round(v * frac)), min(v, C.MIN_PER_CLASS))
              for k, v in class_counts.items()}
    scale = C.SAMPLE_CAP / max(sum(target.values()), 1)
    if scale < 1.0:
        target = {k: max(int(v * scale), 1) for k, v in target.items()}
    parts = []
    for fi, path in enumerate(files):
        fname = os.path.basename(path)
        for chunk in pd.read_csv(path, chunksize=C.CHUNK, low_memory=False):
            chunk = chunk.loc[chunk[C.CICIOT_LABEL_COL].notna()]
            lab = chunk[C.CICIOT_LABEL_COL].astype(str)
            p = lab.map(lambda k: target[k] / class_counts[k]).to_numpy()
            keep = rng.random(len(chunk)) < p
            if keep.any():
                sub = chunk.loc[keep].copy()
                for c in feat_cols:
                    sub[c] = sub[c].astype(np.float32)
                sub["src_file"] = fname
                parts.append(sub)
        C.log(f"01: pass2 {fi+1}/{len(files)} {fname}")
    sample = pd.concat(parts, ignore_index=True)
    del parts
    if len(sample) > C.SAMPLE_CAP:
        idx = C.stratified_cap(sample[C.CICIOT_LABEL_COL].to_numpy(), C.SAMPLE_CAP, seed=0)
        sample = sample.iloc[np.sort(idx)].reset_index(drop=True)
    sample["orig_idx"] = np.arange(len(sample))
    sample.to_parquet(C.sample_path("ciciot2023"), index=False)
    C.log(f"01: ciciot sample saved rows={len(sample)} ({time.time()-t0:.0f}s total)")
    return prof


if __name__ == "__main__":
    ds = sys.argv[1]
    if ds == "5gnidd":
        profile_5gnidd()
    elif ds == "ciciot2023":
        profile_ciciot()
    else:
        raise SystemExit(f"unknown dataset {ds}")
