"""Optimal 1:1 assignment via the Hungarian algorithm.

Runs a single GLOBAL assignment over every remaining settlement/ledger row
(restricted to candidate pairs surfaced by bucketing) rather than one
assignment per bucket, so a row that appears in several overlapping buckets
still can't be double-claimed -- a naive "best match per row independently"
or "per-bucket" approach can double-assign across bucket boundaries.
"""
import numpy as np
from scipy.optimize import linear_sum_assignment

from engine.features import compute_features

NON_CANDIDATE_COST = 10.0  # sentinel cost, always worse than any real 0..1 confidence


def assign_candidates(remaining_settlements, remaining_ledgers, buckets, model):
    """remaining_settlements / remaining_ledgers: pandas DataFrames (post exact+group match).
    buckets: dict from engine.blocking.build_buckets, used only to restrict which
    (settlement, ledger) pairs are even considered -- keeps this near-linear instead
    of comparing every settlement against every ledger.

    Returns a list of {"settlement_id","invoice_id","confidence","features"}.
    """
    from engine.confidence_model import predict_confidence

    settlements = list(remaining_settlements.to_dict("records"))
    ledgers = list(remaining_ledgers.to_dict("records"))
    if not settlements or not ledgers:
        return []

    s_index = {s["settlement_id"]: i for i, s in enumerate(settlements)}
    l_index = {l["invoice_id"]: j for j, l in enumerate(ledgers)}

    candidate_pairs = set()
    for bucket in buckets.values():
        for srow in bucket["settlements"]:
            if srow["settlement_id"] not in s_index:
                continue
            for lrow in bucket["ledgers"]:
                if lrow["invoice_id"] not in l_index:
                    continue
                candidate_pairs.add((srow["settlement_id"], lrow["invoice_id"]))

    n, m = len(settlements), len(ledgers)
    cost_matrix = np.full((n, m), NON_CANDIDATE_COST)
    feat_cache = {}
    for sid, iid in candidate_pairs:
        i, j = s_index[sid], l_index[iid]
        feats = compute_features(settlements[i], ledgers[j])
        conf = predict_confidence(model, feats)
        cost_matrix[i, j] = 1.0 - conf
        feat_cache[(i, j)] = (conf, feats)

    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    results = []
    for i, j in zip(row_ind, col_ind):
        if (i, j) not in feat_cache:
            continue  # Hungarian had to fill a slot with a non-candidate pair; ignore it
        conf, feats = feat_cache[(i, j)]
        results.append({
            "settlement_id": settlements[i]["settlement_id"],
            "invoice_id": ledgers[j]["invoice_id"],
            "confidence": conf,
            "features": feats,
        })
    return results
