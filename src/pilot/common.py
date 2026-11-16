"""Shared config & helpers for Pilot C (K4) shortcut/leakage audit.

Datasets expected on this laptop (never downloaded here):
  - 5G-NIDD   : metpen\\data\\5G\\5GNIDD\\extracted\\Combined.csv
  - CICIoT2023: metpen\\data\\CICIoT2023\\MERGED_CSV\\Merged*.csv (63 files)
  - CICIoMT2024: NOT FOUND on this machine -> skipped (recorded as deviation).

All outputs stay inside pilot_audit/ (results/ and cache/).
"""
import json
import os
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
CACHE = os.path.join(HERE, "cache")
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

METPEN = r"<DATA_ROOT>"
PATH_5GNIDD = os.path.join(METPEN, "data", "5G", "5GNIDD", "extracted", "Combined.csv")
DIR_CICIOT = os.path.join(METPEN, "data", "CICIoT2023", "MERGED_CSV")

SEEDS = [0, 1, 2]
SAMPLE_CAP = 1_000_000      # max rows kept per dataset (stratified, seed 0)
MODEL_CAP = 300_000         # max rows used for model training/eval in steps 03/04
SF_SAMPLE = 200_000         # rows for single-feature probes (step 02)
MIN_PER_CLASS = 100         # sampling floor per class (if available)
CHUNK = 400_000

DATASETS = ["5gnidd", "ciciot2023"]
MISSING_DATASETS = {
    "ciciomt2024": "CICIoMT2024 tidak ditemukan di laptop (dicari 'iomt' di "
                   r"<DATA_ROOT>, D:\, E:\; hanya ada PDF paper). Dilewati."
}

# 5G-NIDD column roles (header verified from the CSV).
NIDD_LABEL_COLS = ["Label", "Attack Type", "Attack Tool"]
# Identity / bookkeeping columns: export row index, Argus record sequence number,
# byte offset of the record in the capture file, VLAN ids, raw TCP initial
# sequence numbers (per-connection identifiers).
NIDD_ID_COLS = ["row_id", "Seq", "Offset", "sVid", "dVid", "SrcTCPBase", "DstTCPBase"]
# The export row index is an artifact of the CSV export (unnamed first column);
# it is excluded from features everywhere but still reported as an identity column.
NIDD_DROP_ALWAYS = ["row_id"]

CICIOT_LABEL_COL = "Label"

ID_NAME_PATTERNS = ["ip", "port", "time", "date", "mac", "seq", "offset", "vid",
                    "tcpbase", "flow_id", "session", "src_file", "row_id"]


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(os.path.join(RESULTS, "run.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def save_json(name, obj):
    with open(os.path.join(RESULTS, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)


def load_json(name):
    with open(os.path.join(RESULTS, name), "r", encoding="utf-8") as f:
        return json.load(f)


def ciciot_files():
    return sorted(
        os.path.join(DIR_CICIOT, f) for f in os.listdir(DIR_CICIOT)
        if f.lower().endswith(".csv")
    )


def sample_path(ds):
    return os.path.join(CACHE, f"{ds}_sample.parquet")


def load_sample(ds):
    df = pd.read_parquet(sample_path(ds))
    return df


def dataset_columns(ds, df):
    """Return (feature_cols, id_cols_present, y_bin, y_multi, group_col)."""
    if ds == "5gnidd":
        meta = NIDD_LABEL_COLS + ["orig_idx", "time_block"]
        feats = [c for c in df.columns if c not in meta + NIDD_DROP_ALWAYS]
        id_cols = [c for c in NIDD_ID_COLS if c in df.columns and c != "row_id"]
        y_bin = (df["Label"].astype(str) != "Benign").astype(np.int8).to_numpy()
        y_multi = df["Attack Type"].astype(str).to_numpy()
        group = df["time_block"].to_numpy()
        gkey = "10 blok berurutan berdasarkan urutan baris Combined.csv (tidak ada kolom waktu/file asal)"
    else:
        meta = [CICIOT_LABEL_COL, "src_file", "orig_idx"]
        feats = [c for c in df.columns if c not in meta]
        id_cols = []  # no identity columns present in the merged CICIoT2023 CSVs
        y_bin = (~df[CICIOT_LABEL_COL].astype(str).str.upper()
                 .str.startswith("BENIGN")).astype(np.int8).to_numpy()
        y_multi = df[CICIOT_LABEL_COL].astype(str).to_numpy()
        group = df["src_file"].to_numpy()
        gkey = "file CSV asal (Merged01..Merged63)"
    return feats, id_cols, y_bin, y_multi, group, gkey


def encode_features(df, feats):
    """Numeric passthrough (float32); object columns -> integer category codes."""
    out = pd.DataFrame(index=df.index)
    for c in feats:
        col = df[c]
        if pd.api.types.is_numeric_dtype(col) or pd.api.types.is_bool_dtype(col):
            out[c] = pd.to_numeric(col, errors="coerce").astype(np.float32)
        else:
            # object / category / pandas-3 'str' dtype -> integer category codes
            codes = pd.Categorical(col.astype(str)).codes.astype(np.float32)
            codes[pd.isna(col).to_numpy()] = np.nan
            out[c] = codes
    return out


def stratified_cap(y, cap, seed, min_per_class=MIN_PER_CLASS):
    """Return positional indices for a stratified sample of at most `cap` rows."""
    n = len(y)
    if n <= cap:
        return np.arange(n)
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    classes, counts = np.unique(y, return_counts=True)
    frac = cap / n
    take = np.maximum(np.floor(counts * frac).astype(int),
                      np.minimum(counts, min_per_class))
    # trim overshoot from the biggest classes
    over = take.sum() - cap
    order = np.argsort(-take)
    i = 0
    while over > 0:
        j = order[i % len(order)]
        cut = min(over, max(take[j] - min_per_class, 0))
        take[j] -= cut
        over -= cut
        i += 1
        if i > 10 * len(order):
            break
    idx = []
    for cls, k in zip(classes, take):
        pos = np.flatnonzero(y == cls)
        if k < len(pos):
            pos = rng.choice(pos, size=k, replace=False)
        idx.append(pos)
    idx = np.concatenate(idx)
    rng.shuffle(idx)
    return idx
