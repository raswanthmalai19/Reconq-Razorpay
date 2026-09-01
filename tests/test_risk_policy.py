from engine.risk_policy import LOWER_BOUND, decide, required_confidence


def test_required_confidence_is_non_decreasing_with_amount():
    amounts = [50_000, 500_000, 5_000_000, 50_000_000]
    thresholds = [required_confidence(a) for a in amounts]
    assert thresholds == sorted(thresholds), "risk-weighted thresholds must not decrease with amount"


def test_low_confidence_always_unresolved_regardless_of_amount():
    for amount in (10_000, 10_000_000):
        assert decide(amount, LOWER_BOUND - 0.01) == "UNRESOLVED"


def test_high_confidence_small_amount_auto_matches():
    assert decide(50_000, 0.90) == "AUTO_MATCHED"


def test_same_confidence_large_amount_requires_review_not_auto_match():
    """The signature behavior: identical confidence, different amount, different decision."""
    small_amount_decision = decide(50_000, 0.90)
    large_amount_decision = decide(50_000_000, 0.90)
    assert small_amount_decision == "AUTO_MATCHED"
    assert large_amount_decision in ("HUMAN_REVIEW", "UNRESOLVED")
    assert small_amount_decision != large_amount_decision
