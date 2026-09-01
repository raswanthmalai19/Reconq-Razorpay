"""Naive fixed-threshold baseline agent.

Same trained confidence model, but a single global cutoff instead of
amount-banding -- used only inside the evaluation harness to produce a
measured comparison against the risk-weighted policy. Never used in the
live dashboard path.
"""

NAIVE_FIXED_THRESHOLD = 0.85  # a single "reasonable-looking" global cutoff
NAIVE_LOWER_BOUND = 0.40


def naive_decide(confidence: float) -> str:
    if confidence < NAIVE_LOWER_BOUND:
        return "UNRESOLVED"
    if confidence >= NAIVE_FIXED_THRESHOLD:
        return "AUTO_MATCHED"
    return "HUMAN_REVIEW"
