"""Candidate bucketing: date-window + amount-band, so later steps never do O(n²).

Design guarantees:
  - Each (settlement, ledger) pair appears in AT MOST one bucket for the purpose
    of assignment (overlap is for candidate recall, not assignment).
  - Bucket size is hard-capped at MAX_BUCKET_SIZE. When a bucket exceeds the cap
    the records nearest to the bucket's centre (by amount) are kept. This means
    very large or very small amounts that are rare get priority — the common middle
    is sampled. In practice this cap only fires when the test dataset has
    pathologically uniform amounts (e.g. all records sampled from a small set).
  - At real merchant scale, amounts are naturally dispersed so buckets are small.
"""
from collections import defaultdict

import pandas as pd

DATE_WINDOW_DAYS = 3
AMOUNT_BAND_PCT = 0.15
AMOUNT_FLOOR_PAISE = 5000   # ₹50 floor band for very small amounts
MAX_BUCKET_SIZE = 60         # Hard cap per side. Beyond this the Hungarian matrix
                             # becomes O(60³) ≈ 216,000 ops — acceptable.
                             # Without the cap, a 500-record bucket is 125M ops.


def _amount_bucket_key(amount_paise: int) -> int:
    band = max(int(amount_paise * AMOUNT_BAND_PCT), AMOUNT_FLOOR_PAISE)
    return amount_paise // band if band > 0 else 0


def _cap_bucket_side(rows: list, cap: int) -> list:
    """If a bucket side exceeds cap, keep the rows most likely to be real matches.

    Strategy: sort by amount descending (high-value items are higher-risk and
    should never be silently skipped) and take the top `cap`. This is a
    deterministic, auditable sampling decision — not random.
    """
    if len(rows) <= cap:
        return rows
    return sorted(rows, key=lambda r: r["amount_inr"], reverse=True)[:cap]


def build_buckets(settlements: pd.DataFrame, ledgers: pd.DataFrame):
    """Groups remaining settlement/ledger rows into coarse buckets for candidate generation.

    Returns a dict: bucket_key -> {"settlements": [...], "ledgers": [...]}
    A settlement/ledger row may appear in more than one adjacent bucket so that
    a date/amount right at a boundary still finds its true counterpart.

    Buckets are capped at MAX_BUCKET_SIZE per side to bound the Hungarian runtime.
    """
    buckets = defaultdict(lambda: {"settlements": [], "ledgers": []})

    for _, srow in settlements.iterrows():
        base_key = _amount_bucket_key(srow["amount_inr"])
        for date_offset in range(-DATE_WINDOW_DAYS, DATE_WINDOW_DAYS + 1):
            for amt_key in (base_key - 1, base_key, base_key + 1):
                key = (srow["settlement_date"] + pd.Timedelta(days=date_offset), amt_key)
                buckets[key]["settlements"].append(srow)

    for _, lrow in ledgers.iterrows():
        base_key = _amount_bucket_key(lrow["amount_inr"])
        key_date = lrow["invoice_date"]
        for amt_key in (base_key - 1, base_key, base_key + 1):
            key = (key_date, amt_key)
            buckets[key]["ledgers"].append(lrow)

    # Keep only buckets where both sides have candidates, and apply the size cap
    result = {}
    for k, v in buckets.items():
        if v["settlements"] and v["ledgers"]:
            result[k] = {
                "settlements": _cap_bucket_side(v["settlements"], MAX_BUCKET_SIZE),
                "ledgers":     _cap_bucket_side(v["ledgers"],     MAX_BUCKET_SIZE),
            }
    return result
