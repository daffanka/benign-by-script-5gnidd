"""Step 04 — ablation: repeat protocols (a) and (c) after dropping the top-3
features from step 02 (union of binary-AUC top-3 and multiclass-F1 top-3) plus
every identity column."""
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

_spec = importlib.util.spec_from_file_location(
    "step03", os.path.join(os.path.dirname(os.path.abspath(__file__)), "03_split_gap.py"))
step03 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(step03)


def run(ds):
    sf = C.load_json(f"single_feature_{ds}.json")
    drop = set(sf["top3_bin"]) | set(sf["top3_multi"])
    df = C.load_sample(ds)
    _, id_cols, *_ = C.dataset_columns(ds, df)
    drop |= set(id_cols)
    step03.run_protocols(ds, "ablate", drop)


if __name__ == "__main__":
    run(sys.argv[1])
