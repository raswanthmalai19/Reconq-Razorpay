"""Feature engineering for the confidence model.

5 features, computed per candidate (settlement, ledger) pair.
"""
from rapidfuzz import fuzz

FEE_BAND_LOW = 0.005
FEE_BAND_HIGH = 0.35  # generous upper bound; covers fees + partial refunds together


def compute_features(srow, lrow) -> dict:
    s_amt = int(srow["amount_inr"])
    l_amt = int(lrow["amount_inr"])
    amount_delta_pct = abs(s_amt - l_amt) / max(l_amt, 1)
    date_delta_days = abs((srow["settlement_date"] - lrow["invoice_date"]).days)
    narration_similarity = fuzz.token_sort_ratio(srow["narration_norm"], lrow["memo_norm"]) / 100.0
    reference_similarity = fuzz.partial_ratio(srow["utr_reference_norm"], lrow["invoice_id_norm"]) / 100.0
    is_fee_pattern = 1.0 if FEE_BAND_LOW <= amount_delta_pct <= FEE_BAND_HIGH else 0.0

    return {
        "amount_delta_pct": amount_delta_pct,
        "date_delta_days": float(date_delta_days),
        "narration_similarity": narration_similarity,
        "reference_similarity": reference_similarity,
        "is_fee_pattern": is_fee_pattern,
    }


FEATURE_ORDER = [
    "amount_delta_pct", "date_delta_days", "narration_similarity",
    "reference_similarity", "is_fee_pattern",
]


def features_to_vector(features: dict):
    return [features[k] for k in FEATURE_ORDER]
