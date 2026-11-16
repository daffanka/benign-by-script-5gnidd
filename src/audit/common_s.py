"""Studi penuh K4 (audit 5G-NIDD) — konfigurasi & helper bersama.

Memakai ulang kode pilot_audit/ (common.py, 07_c4.py dkk) via importlib.
Semua keluaran di study_5gnidd_audit/ (results/, cache/).
"""
import importlib.util
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.join(os.path.dirname(HERE), "pilot_audit")
sys.path.insert(0, PILOT)
import common as PC  # noqa: E402

RESULTS = os.path.join(HERE, "results")
CACHE = os.path.join(HERE, "cache")
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

FULL = os.path.join(CACHE, "full.parquet")
FEATS = os.path.join(CACHE, "feats.json")

N_TRUTH = 281_529   # baris salah-label (C4)
N_VER_C = 925_573   # baris versi C (C5)


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace(".py", ""), os.path.join(PILOT, name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pilot_c4():
    return _load("07_c4.py")


def log(msg, tag="study"):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(os.path.join(RESULTS, f"{tag}.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def save_json(name, obj):
    with open(os.path.join(RESULTS, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)


def append_jsonl(name, obj):
    with open(os.path.join(RESULTS, name), "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, default=str) + "\n")


def append_csv(name, row: dict, cols: list):
    p = os.path.join(RESULTS, name)
    new = not os.path.exists(p)
    with open(p, "a", encoding="utf-8") as f:
        if new:
            f.write(",".join(cols) + "\n")
        f.write(",".join(str(row.get(c, "")) for c in cols) + "\n")


def load_full():
    d = pd.read_parquet(FULL)
    with open(FEATS, "r", encoding="utf-8") as f:
        fj = json.load(f)
    return d, fj


def version_arrays(d, v):
    """Kembalikan (mask_keep, label) untuk versi A/B/C."""
    if v == "A":
        return np.ones(len(d), bool), d["__y"].to_numpy().astype(str)
    if v == "B":
        return np.ones(len(d), bool), d["__ycorr"].to_numpy().astype(str)
    if v == "C":
        return d["__keepC"].to_numpy(), d["__y"].to_numpy().astype(str)
    raise ValueError(v)


def make_model(name, seed):
    from sklearn.ensemble import (HistGradientBoostingClassifier,
                                  RandomForestClassifier)
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.tree import DecisionTreeClassifier
    imp = lambda: SimpleImputer(strategy="median")  # noqa: E731
    if name == "HGB":
        # setelan identik C1-C5 (pengganti LightGBM; l2=0.1 cegah divergensi leaf)
        return HistGradientBoostingClassifier(
            max_iter=100, learning_rate=0.1, max_bins=255,
            early_stopping=False, random_state=seed, l2_regularization=0.1)
    if name == "RF":
        return Pipeline([("imp", imp()),
                         ("m", RandomForestClassifier(n_estimators=100, n_jobs=-1,
                                                      random_state=seed))])
    if name == "DT":
        return Pipeline([("imp", imp()),
                         ("m", DecisionTreeClassifier(random_state=seed))])
    if name == "LR":
        return Pipeline([("imp", imp()), ("sc", StandardScaler()),
                         ("m", LogisticRegression(max_iter=100, random_state=seed))])
    if name == "KNN":
        return Pipeline([("imp", imp()), ("sc", StandardScaler()),
                         ("m", KNeighborsClassifier(n_neighbors=5,
                                                    algorithm="brute", n_jobs=-1))])
    if name == "MLP":
        return Pipeline([("imp", imp()), ("sc", StandardScaler()),
                         ("m", MLPClassifier(hidden_layer_sizes=(100,), max_iter=30,
                                             batch_size=2048, early_stopping=True,
                                             random_state=seed))])
    raise ValueError(name)


MODEL_DESC = {
    "HGB": "HistGradientBoosting(max_iter=100,lr=0.1,max_bins=255,l2=0.1,no early stop)",
    "RF": "RandomForest(n_estimators=100) + imputasi median",
    "DT": "DecisionTree(default) + imputasi median",
    "LR": "LogisticRegression(lbfgs,max_iter=100) + imputasi median + StandardScaler",
    "KNN": "kNN(k=5,brute) + imputasi median + StandardScaler; train disubsample 200k stratified",
    "MLP": "MLP(100,)(max_iter=30,batch=2048,early_stopping) + imputasi median + StandardScaler",
}

encode_features = PC.encode_features
stratified_cap = PC.stratified_cap
