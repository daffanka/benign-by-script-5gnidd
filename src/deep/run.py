"""Replikasi deep learning K4 (audit 5G-NIDD) — GPU, <=3 jam.

Model: MLP3 (3 lapis tersembunyi 256/128/64), CNN1D, LSTM, TRF (Transformer encoder
2 lapis d=32), TABICL (TabICL v2, konteks 10.000 baris seimbang).
Protokol x versi: lit-A (semua kolom termasuk Seq/Offset, acak 80/20, dinilai vs label
asli DAN terkoreksi + % baris salah-label test yang diprediksi Benign);
noid-A/B (42 fitur non-identitas, acak 80/20); b12-A/B (BS1->BS2); b21-A/B (BS2->BS1).
Seed 0/1/2. Metrik identik e2: acc, macro-F1, TPR/FPR biner (pred != Benign),
recall per kelas. Data: study_5gnidd_audit/cache/full.parquet (HANYA DIBACA).

python run.py [--smoke] [--max-hours 2.8]
"""
import argparse
import json
import os
import sys
import time

NTHREAD = max(1, (os.cpu_count() or 4) - 3)
os.environ.setdefault("OMP_NUM_THREADS", str(NTHREAD))

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.join(os.path.dirname(HERE), "study_5gnidd_audit")
sys.path.insert(0, AUDIT)
sys.path.append(r"<PATH TO YOUR PYTHON ENV site-packages>")
import common_s as S  # noqa: E402  (hanya load_full/version_arrays/encode/stratified_cap)

BATCH, EPOCHS, LR = 8192, 10, 1e-3
TAB_CTX, TAB_EVAL, TAB_CHUNK = 10_000, 50_000, 4_000
PRED_CHUNK = 65_536
SEEDS = (0, 1, 2)
MODELS = ("MLP3", "CNN1D", "LSTM", "TRF", "TABICL")
COMBOS = (("lit", "A"), ("noid", "A"), ("noid", "B"),
          ("b12", "A"), ("b12", "B"), ("b21", "A"), ("b21", "B"))
T0 = time.time()


def log(*a):
    line = f"[{time.time() - T0:7.0f}s] " + " ".join(str(x) for x in a)
    print(line, flush=True)


def append_csv(path, row, cols):
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write(",".join(cols) + "\n")
        f.write(",".join(str(row.get(c, "")) for c in cols) + "\n")


# ---------------- model torch ----------------
def make_net(name, F, C, seed):
    import torch
    import torch.nn as nn
    torch.manual_seed(seed)
    if name == "MLP3":
        return nn.Sequential(nn.Linear(F, 256), nn.ReLU(), nn.Linear(256, 128),
                             nn.ReLU(), nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, C))
    if name == "CNN1D":
        class CNN(nn.Module):
            def __init__(self):
                super().__init__()
                self.c1 = nn.Conv1d(1, 32, 5, padding=2)
                self.c2 = nn.Conv1d(32, 64, 3, padding=1)
                self.p = nn.MaxPool1d(2)
                self.fc1 = nn.Linear(64 * (F // 4), 128)
                self.fc2 = nn.Linear(128, C)
                self.r = nn.ReLU()

            def forward(self, x):
                h = self.p(self.r(self.c1(x.unsqueeze(1))))
                h = self.p(self.r(self.c2(h)))
                h = self.r(self.fc1(h.flatten(1)))
                return self.fc2(h)
        return CNN()
    if name == "LSTM":
        class LSTMNet(nn.Module):
            def __init__(self):
                super().__init__()
                self.lstm = nn.LSTM(1, 64, batch_first=True)
                self.fc = nn.Linear(64, C)

            def forward(self, x):
                o, _ = self.lstm(x.unsqueeze(-1))
                return self.fc(o[:, -1])
        return LSTMNet()
    if name == "TRF":
        class TrfNet(nn.Module):
            def __init__(self, d=32):
                super().__init__()
                self.proj = nn.Linear(1, d)
                self.pos = nn.Parameter(torch.zeros(1, F, d))
                lay = nn.TransformerEncoderLayer(d, 4, 64, dropout=0.1,
                                                 batch_first=True)
                self.enc = nn.TransformerEncoder(lay, 2)
                self.fc = nn.Linear(d, C)

            def forward(self, x):
                h = self.proj(x.unsqueeze(-1)) + self.pos
                return self.fc(self.enc(h).mean(1))
        return TrfNet()
    raise ValueError(name)


ARCH_DESC = {
    "MLP3": "MLP 3 lapis tersembunyi 256-128-64 ReLU",
    "CNN1D": "Conv1d(1->32,k5)-MaxPool2-Conv1d(32->64,k3)-MaxPool2-FC128",
    "LSTM": "LSTM(input=1,hidden=64) atas urutan fitur, keluaran langkah terakhir",
    "TRF": "Transformer encoder 2 lapis d=32 h=4 ff=64 + pos-embedding, mean-pool",
    "TABICL": "TabICL v2 (checkpoint lokal), konteks seimbang <=10.000 baris train",
}


def train_torch(name, Ztr, ycode, C, seed, epochs, dev):
    import torch
    import torch.nn as nn
    net = make_net(name, Ztr.shape[1], C, seed).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    lossf = nn.CrossEntropyLoss()
    X = torch.from_numpy(Ztr).to(dev)
    Y = torch.from_numpy(ycode).to(dev)
    n = len(X)
    g = torch.Generator().manual_seed(seed)
    for ep in range(epochs):
        perm = torch.randperm(n, generator=g).to(dev)
        for i in range(0, n, BATCH):
            b = perm[i:i + BATCH]
            opt.zero_grad()
            loss = lossf(net(X[b]), Y[b])
            loss.backward()
            opt.step()
    del X, Y
    return net


def pred_torch(net, Zte, dev):
    import torch
    net.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(Zte), PRED_CHUNK):
            x = torch.from_numpy(Zte[i:i + PRED_CHUNK]).to(dev)
            out.append(net(x).argmax(1).cpu().numpy())
    return np.concatenate(out)


def balanced_ctx(ytr, cap, seed):
    rng = np.random.default_rng(seed)
    classes, counts = np.unique(ytr, return_counts=True)
    quota = cap // len(classes)
    takes = []
    for c in classes:
        pos = np.flatnonzero(ytr == c)
        takes.append(rng.permutation(pos)[:quota])
    taken = np.concatenate(takes)
    rest = cap - len(taken)
    if rest > 0:
        pool = np.setdiff1d(np.arange(len(ytr)), taken)
        takes_r = rng.permutation(pool)[:rest]
        taken = np.concatenate([taken, takes_r])
    return np.sort(taken)


# ---------------- metrik (identik e2) ----------------
def metrics(row, tag, yref, pred, classes):
    from sklearn.metrics import accuracy_score, f1_score, recall_score
    row[f"acc{tag}"] = round(float(accuracy_score(yref, pred)), 6)
    row[f"f1_macro{tag}"] = round(float(f1_score(
        yref, pred, average="macro", labels=classes, zero_division=0)), 6)
    pb = (pred != "Benign")
    yb = (yref != "Benign")
    row[f"tpr{tag}"] = round(float(pb[yb].mean()), 6) if yb.any() else ""
    row[f"fpr{tag}"] = round(float(pb[~yb].mean()), 6) if (~yb).any() else ""
    rec = recall_score(yref, pred, average=None, labels=classes, zero_division=0)
    for c, r in zip(classes, rec):
        row[f"rec{tag}_{c}"] = round(float(r), 6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--max-hours", type=float, default=2.8)
    a = ap.parse_args()
    import torch
    torch.set_num_threads(NTHREAD)
    dev = "cuda"
    assert torch.cuda.is_available()
    res = os.path.join(HERE, "results_smoke" if a.smoke else "results")
    os.makedirs(res, exist_ok=True)
    runs_csv = os.path.join(res, "runs.csv")
    cfg_jsonl = os.path.join(res, "configs.jsonl")
    seeds = (0,) if a.smoke else SEEDS
    epochs = 2 if a.smoke else EPOCHS
    tab_eval = 5_000 if a.smoke else TAB_EVAL
    tab_ctx0 = 2_000 if a.smoke else TAB_CTX

    done = set()
    if os.path.exists(runs_csv):
        done = set(pd.read_csv(runs_csv)["run_id"].astype(str))
        log(f"resume: {len(done)} run sudah ada")

    d, fj = S.load_full()
    feats_all, feats42, classes = fj["feats_all"], fj["feats42"], fj["classes"]
    if a.smoke:
        idx = np.sort(S.stratified_cap(d["__y"].to_numpy().astype(str), 40_000, 0))
        d = d.iloc[idx].reset_index(drop=True)
    ycorr_full = d["__ycorr"].to_numpy().astype(str)
    mis_full = d["__mis"].to_numpy().astype(bool)
    classes_arr = np.array(classes)

    csv_cols = ["run_id", "protokol", "versi", "model", "seed", "n_train",
                "n_test", "n_test_eval", "n_feats", "n_ctx", "epochs",
                "fit_s", "pred_s", "baris_per_detik", "pct_mis_benign",
                "n_mis_test_eval"]
    for t in ("", "_korr"):
        csv_cols += [f"acc{t}", f"f1_macro{t}", f"tpr{t}", f"fpr{t}"]
        csv_cols += [f"rec{t}_{c}" for c in classes]

    from sklearn.model_selection import train_test_split
    for proto, version in COMBOS:
        mask, y = S.version_arrays(d, version)
        dv = d.loc[mask]
        yv = y[mask]
        ycorr_v = ycorr_full[mask]
        mis_v = mis_full[mask]
        bs = dv["__bs"].to_numpy()
        feats = feats_all if proto == "lit" else feats42
        t0 = time.time()
        Xall = S.encode_features(dv, feats).to_numpy(np.float32)
        log(f"{proto}-{version}: n={len(dv)} F={len(feats)} encode {time.time()-t0:.0f}s")
        i_bs1 = np.flatnonzero(bs == "BS1")
        i_bs2 = np.flatnonzero(bs == "BS2")
        for seed in seeds:
            if time.time() - T0 > a.max_hours * 3600:
                log(f"STOP batas waktu sebelum {proto}-{version} s{seed}")
                return
            if proto in ("lit", "noid"):
                tr, te = train_test_split(np.arange(len(dv)), test_size=0.2,
                                          random_state=seed, stratify=yv)
            elif proto == "b12":
                tr, te = i_bs1, i_bs2
            else:
                tr, te = i_bs2, i_bs1
            # praproses sekali per (combo, seed): inf->NaN, imputasi median train,
            # lalu standardisasi (mu/sd train) untuk jaringan torch
            t0 = time.time()
            Xtr = Xall[tr].copy()
            Xte = Xall[te].copy()
            Xtr[np.isinf(Xtr)] = np.nan
            Xte[np.isinf(Xte)] = np.nan
            med = np.nanmedian(Xtr, 0)
            med = np.where(np.isnan(med), 0.0, med).astype(np.float32)
            ii = np.where(np.isnan(Xtr))
            Xtr[ii] = np.take(med, ii[1])
            ii = np.where(np.isnan(Xte))
            Xte[ii] = np.take(med, ii[1])
            mu = Xtr.mean(0)
            sd = Xtr.std(0) + 1e-6
            Ztr = ((Xtr - mu) / sd).astype(np.float32)
            Zte = ((Xte - mu) / sd).astype(np.float32)
            ytr, yte = yv[tr], yv[te]
            ycode = np.searchsorted(classes_arr, ytr).astype(np.int64)
            ycorr_te = ycorr_v[te]
            mis_te = mis_v[te]
            log(f"{proto}-{version} s{seed}: praproses {time.time()-t0:.0f}s "
                f"(train {len(tr)}, test {len(te)}, mis di test {int(mis_te.sum())})")

            for model in MODELS:
                run_id = f"{proto}|{version}|{model}|s{seed}"
                if run_id in done:
                    continue
                if time.time() - T0 > a.max_hours * 3600:
                    log(f"STOP batas waktu sebelum {run_id}")
                    return
                try:
                    row = {"run_id": run_id, "protokol": proto, "versi": version,
                           "model": model, "seed": seed, "n_train": len(tr),
                           "n_test": len(te), "n_feats": len(feats),
                           "epochs": "" if model == "TABICL" else epochs,
                           "n_ctx": ""}
                    if model == "TABICL":
                        from tabicl import TabICLClassifier
                        sub = S.stratified_cap(yte, tab_eval, seed)
                        sub = np.sort(sub)
                        ctx = tab_ctx0
                        t0 = time.time()
                        while True:
                            try:
                                ci = balanced_ctx(ytr, ctx, seed)
                                tclf = TabICLClassifier(
                                    device="cuda", random_state=seed,
                                    allow_auto_download=False)
                                tclf.fit(Xtr[ci], ytr[ci])
                                fit_s = round(time.time() - t0, 1)
                                t0 = time.time()
                                preds = []
                                for i in range(0, len(sub), TAB_CHUNK):
                                    p = tclf.predict_proba(Xte[sub[i:i + TAB_CHUNK]])
                                    preds.append(
                                        tclf.classes_.astype(str)[p.argmax(1)])
                                pred = np.concatenate(preds)
                                break
                            except torch.cuda.OutOfMemoryError:
                                torch.cuda.empty_cache()
                                ctx //= 2
                                log(f"  {run_id}: OOM -> konteks {ctx}")
                                if ctx < 1000:
                                    raise
                        pred_s = round(time.time() - t0, 1)
                        row.update(n_ctx=len(ci), n_test_eval=len(sub))
                        yref, ycorr_ref, mis_ref = yte[sub], ycorr_te[sub], mis_te[sub]
                        del tclf
                        torch.cuda.empty_cache()
                    else:
                        t0 = time.time()
                        net = train_torch(model, Ztr, ycode, len(classes), seed,
                                          epochs, dev)
                        fit_s = round(time.time() - t0, 1)
                        t0 = time.time()
                        pred = classes_arr[pred_torch(net, Zte, dev)]
                        pred_s = round(time.time() - t0, 1)
                        row["n_test_eval"] = len(te)
                        yref, ycorr_ref, mis_ref = yte, ycorr_te, mis_te
                        del net
                        torch.cuda.empty_cache()
                    row["fit_s"] = fit_s
                    row["pred_s"] = pred_s
                    row["baris_per_detik"] = round(len(yref) / max(pred_s, 1e-9), 1)
                    metrics(row, "", yref, pred, classes)
                    if version == "A":
                        metrics(row, "_korr", ycorr_ref, pred, classes)
                        if mis_ref.any():
                            row["pct_mis_benign"] = round(
                                100 * float((pred[mis_ref] == "Benign").mean()), 4)
                            row["n_mis_test_eval"] = int(mis_ref.sum())
                    append_csv(runs_csv, row, csv_cols)
                    with open(cfg_jsonl, "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "run_id": run_id, "arsitektur": ARCH_DESC[model],
                            "fitur": "semua kolom (termasuk Seq/Offset)"
                            if proto == "lit" else "42 non-identitas",
                            "split": "acak 80/20 stratified" if proto in
                            ("lit", "noid") else {"b12": "latih BS1, uji BS2",
                                                  "b21": "latih BS2, uji BS1"}[proto],
                            "praproses": "inf->NaN; imputasi median train; "
                            "standardisasi mu/sd train (torch); TabICL dapat "
                            "matriks imputasi tanpa standardisasi",
                            "opt": f"Adam lr={LR} batch={BATCH} epoch={epochs} "
                                   "CE tanpa bobot kelas, tanpa early stopping"
                            if model != "TABICL" else
                            f"konteks seimbang {row['n_ctx']}; eval subset "
                            f"stratified {row['n_test_eval']}",
                            "seed": seed}) + "\n")
                    log(f"{run_id} f1={row['f1_macro']} acc={row['acc']} "
                        f"fit={fit_s}s pred={pred_s}s"
                        + (f" misBenign={row.get('pct_mis_benign', '')}%"
                           if version == "A" else ""))
                except Exception as e:  # noqa: BLE001
                    import traceback
                    traceback.print_exc()
                    log(f"GAGAL {run_id}: {type(e).__name__}: {e}")
            del Xtr, Xte, Ztr, Zte
        del Xall
    log("RUN SELESAI")


if __name__ == "__main__":
    main()
