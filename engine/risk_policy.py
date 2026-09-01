"""Risk-weighted (amount-banded) threshold policy -- pure lookup, no AI.

The confidence required to auto-clear a match scales with the transaction
amount, not a fixed number. This is the signature differentiator.
"""

# (amount upper bound in paise, required confidence) -- checked in ascending order
BANDS = [
    (100_000, 0.75),        # <= Rs 1,000
    (2_500_000, 0.85),      # Rs 1,000 - 25,000
    (10_000_000, 0.93),     # Rs 25,000 - 1,00,000
    (float("inf"), 0.97),   # > Rs 1,00,000
]

LOWER_BOUND = 0.40  # below this, at any amount -> UNRESOLVED, never guessed


def required_confidence(amount_paise: int) -> float:
    for upper, threshold in BANDS:
        if amount_paise <= upper:
            return threshold
    return BANDS[-1][1]


def decide(amount_paise: int, confidence: float) -> str:
    """Returns 'AUTO_MATCHED' | 'HUMAN_REVIEW' | 'UNRESOLVED'."""
    if confidence < LOWER_BOUND:
        return "UNRESOLVED"
    threshold = required_confidence(amount_paise)
    if confidence >= threshold:
        return "AUTO_MATCHED"
    return "HUMAN_REVIEW"
