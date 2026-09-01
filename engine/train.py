"""Standalone entry point: builds training candidates from bucketing and trains
the confidence model. Run directly (`python -m engine.train`) or imported by
the evaluation harness.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from engine.blocking import build_buckets
from engine.confidence_model import build_training_examples, save_model, train_confidence_model
from engine.exact_match import exact_key_match
from engine.ingestion import load_ledger_csv, load_settlement_csv
from engine.pipeline import gather_pairwise_candidates

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def train_and_save():
    settlements = load_settlement_csv(os.path.join(DATA_DIR, "settlement_report.csv"))
    ledgers = load_ledger_csv(os.path.join(DATA_DIR, "internal_ledger.csv"))
    ground_truth = pd.read_csv(os.path.join(DATA_DIR, "ground_truth.csv"), dtype=str, keep_default_na=False)
    ground_truth["should_match"] = ground_truth["should_match"].map(lambda v: v == "True")

    _exact, remaining_s, remaining_l = exact_key_match(settlements, ledgers)
    buckets = build_buckets(remaining_s, remaining_l)
    bucket_pairs = gather_pairwise_candidates(buckets)

    X, y = build_training_examples(remaining_s, remaining_l, ground_truth, bucket_pairs)
    model, report, _test_set = train_confidence_model(X, y)
    save_model(model)
    return model, report


if __name__ == "__main__":
    _model, report = train_and_save()
    print("Confidence model trained.")
    for k, v in report.items():
        print(f"  {k}: {v}")
