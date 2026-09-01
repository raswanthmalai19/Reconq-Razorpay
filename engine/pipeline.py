"""Top-level orchestration: ingestion -> exact match -> bucket -> group match ->
confidence scoring -> Hungarian assignment -> risk-weighted decision.

This is the one place that calls every engine module in sequence. The
dashboard, evaluation harness and naive-baseline comparison all call into
this module so there is exactly one reconciliation code path.
"""
import pandas as pd

from engine.assignment import assign_candidates
from engine.blocking import build_buckets
from engine.exact_match import exact_key_match
from engine.group_matching import find_split_merge_candidates
from engine.ingestion import load_ledger_csv, load_settlement_csv
from engine.naive_baseline import naive_decide
from engine.risk_policy import decide


def gather_pairwise_candidates(buckets):
    """Dedups (settlement_id, invoice_id) candidate pairs across overlapping buckets,
    returning (srow, lrow) tuples -- used both by assignment and by training-data
    construction for the confidence model."""
    seen = set()
    pairs = []
    for bucket in buckets.values():
        for srow in bucket["settlements"]:
            for lrow in bucket["ledgers"]:
                key = (srow["settlement_id"], lrow["invoice_id"])
                if key in seen:
                    continue
                seen.add(key)
                pairs.append((srow, lrow))
    return pairs


def run_reconciliation(settlement_path: str, ledger_path: str, model, naive_mode: bool = False):
    """Runs the full pipeline. If naive_mode=True, uses the single fixed-threshold
    baseline decision instead of the risk-weighted amount-banded policy -- used only
    by the evaluation harness to produce the comparison metric.

    Returns a dict with keys: matched (list), group_matches (list), assigned (list),
    unresolved_settlements (list of ids), unresolved_ledgers (list of ids).
    """
    settlements = load_settlement_csv(settlement_path)
    ledgers = load_ledger_csv(ledger_path)

    exact_matches, remaining_s, remaining_l = exact_key_match(settlements, ledgers)
    for m in exact_matches:
        m["status"] = "AUTO_MATCHED"  # exact matches are always safe to auto-clear

    buckets = build_buckets(remaining_s, remaining_l)
    group_matches, consumed_s_ids, consumed_l_ids = find_split_merge_candidates(buckets)
    for gm in group_matches:
        gm["status"] = "HUMAN_REVIEW"  # split/merge always gets a human look, even at high confidence

    remaining_s = remaining_s[~remaining_s["settlement_id"].isin(consumed_s_ids)]
    remaining_l = remaining_l[~remaining_l["invoice_id"].isin(consumed_l_ids)]

    remaining_buckets = build_buckets(remaining_s, remaining_l)
    assigned = assign_candidates(remaining_s, remaining_l, remaining_buckets, model)

    matched_s_ids, matched_l_ids = set(), set()
    for pair in assigned:
        amount = int(remaining_s[remaining_s["settlement_id"] == pair["settlement_id"]].iloc[0]["amount_inr"])
        if naive_mode:
            pair["status"] = naive_decide(pair["confidence"])
        else:
            pair["status"] = decide(amount, pair["confidence"])
        matched_s_ids.add(pair["settlement_id"])
        matched_l_ids.add(pair["invoice_id"])

    unresolved_settlements = [
        sid for sid in remaining_s["settlement_id"].tolist() if sid not in matched_s_ids
    ]
    unresolved_ledgers = [
        iid for iid in remaining_l["invoice_id"].tolist() if iid not in matched_l_ids
    ]

    return {
        "matched": exact_matches,
        "group_matches": group_matches,
        "assigned": assigned,
        "unresolved_settlements": unresolved_settlements,
        "unresolved_ledgers": unresolved_ledgers,
    }
