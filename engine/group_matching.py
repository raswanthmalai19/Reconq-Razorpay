"""Bounded subset-sum search for split/merged transaction detection.

Looks, within each bucket, for N ledger rows summing to one settlement row
(or vice versa), within a small rounding tolerance. Group size capped at 4
and the number of candidate subsets considered per bucket is capped, so this
never becomes an unbounded combinatorial search.
"""
from itertools import combinations

MAX_GROUP_SIZE = 4
MAX_SUBSETS_PER_BUCKET = 20
AMOUNT_TOLERANCE_PAISE = 200  # +/- Rs 2 rounding tolerance across the group


def find_split_merge_candidates(buckets: dict):
    """Returns (group_matches, consumed_settlement_ids, consumed_invoice_ids).

    group_matches: list of {"settlement_ids": [...], "invoice_ids": [...],
                             "match_type": "split"|"merge", "confidence": float}
    """
    group_matches = []
    consumed_settlement_ids = set()
    consumed_invoice_ids = set()

    for _key, bucket in buckets.items():
        settlements = [s for s in bucket["settlements"] if s["settlement_id"] not in consumed_settlement_ids]
        ledgers = [l for l in bucket["ledgers"] if l["invoice_id"] not in consumed_invoice_ids]

        # Case: 1 settlement == sum of N ledger rows (a split settlement)
        for srow in settlements:
            if srow["settlement_id"] in consumed_settlement_ids:
                continue
            target = int(srow["amount_inr"])
            group = _find_summing_subset(ledgers, target, key="amount_inr", id_key="invoice_id",
                                          exclude=consumed_invoice_ids)
            if group:
                group_matches.append({
                    "settlement_ids": [srow["settlement_id"]],
                    "invoice_ids": [g["invoice_id"] for g in group],
                    "match_type": "split",
                    "confidence": _group_confidence(group, target, key="amount_inr"),
                })
                consumed_settlement_ids.add(srow["settlement_id"])
                consumed_invoice_ids.update(g["invoice_id"] for g in group)

        # Case: 1 ledger row == sum of N settlement rows (a merged settlement)
        ledgers = [l for l in bucket["ledgers"] if l["invoice_id"] not in consumed_invoice_ids]
        settlements = [s for s in bucket["settlements"] if s["settlement_id"] not in consumed_settlement_ids]
        for lrow in ledgers:
            if lrow["invoice_id"] in consumed_invoice_ids:
                continue
            target = int(lrow["amount_inr"])
            group = _find_summing_subset(settlements, target, key="amount_inr", id_key="settlement_id",
                                          exclude=consumed_settlement_ids)
            if group:
                group_matches.append({
                    "settlement_ids": [g["settlement_id"] for g in group],
                    "invoice_ids": [lrow["invoice_id"]],
                    "match_type": "merge",
                    "confidence": _group_confidence(group, target, key="amount_inr"),
                })
                consumed_invoice_ids.add(lrow["invoice_id"])
                consumed_settlement_ids.update(g["settlement_id"] for g in group)

    return group_matches, consumed_settlement_ids, consumed_invoice_ids


def _find_summing_subset(rows, target, key, id_key, exclude):
    candidates = [r for r in rows if r[id_key] not in exclude]
    if len(candidates) < 2:
        return None  # a subset must have >=2 members to count as a split/merge
    candidates = candidates[:MAX_SUBSETS_PER_BUCKET]
    for size in range(2, min(MAX_GROUP_SIZE, len(candidates)) + 1):
        for combo in combinations(candidates, size):
            total = sum(int(c[key]) for c in combo)
            if abs(total - target) <= AMOUNT_TOLERANCE_PAISE:
                return list(combo)
    return None


def _group_confidence(group, target, key) -> float:
    """Confidence derived from how tight the subset sum is against tolerance,
    not a fixed constant -- a sum off by Re 0 scores near 1.0, a sum at the
    edge of AMOUNT_TOLERANCE_PAISE scores near the floor."""
    total = sum(int(g[key]) for g in group)
    delta = abs(total - target)
    floor = 0.75
    tightness = 1.0 - (delta / AMOUNT_TOLERANCE_PAISE if AMOUNT_TOLERANCE_PAISE else 0)
    return round(floor + (1.0 - floor) * max(0.0, tightness), 4)
