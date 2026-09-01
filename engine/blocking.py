"""Candidate bucketing: date-window + amount-band, so later steps never do O(n^2)."""
from collections import defaultdict

import pandas as pd

DATE_WINDOW_DAYS = 3
AMOUNT_BAND_PCT = 0.15
AMOUNT_FLOOR_PAISE = 5000  # Rs 50 floor band for very small amounts


def _amount_bucket_key(amount_paise: int) -> int:
    band = max(int(amount_paise * AMOUNT_BAND_PCT), AMOUNT_FLOOR_PAISE)
    return amount_paise // band if band > 0 else 0


def build_buckets(settlements: pd.DataFrame, ledgers: pd.DataFrame):
    """Groups remaining settlement/ledger rows into coarse buckets for candidate generation.

    Returns a dict: bucket_key -> {"settlements": [...], "ledgers": [...]}
    A settlement/ledger row may appear in more than one adjacent bucket so that
    a date/amount right at a boundary still finds its true counterpart.
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

    # keep only buckets where both sides have candidates
    return {k: v for k, v in buckets.items() if v["settlements"] and v["ledgers"]}
