import numpy as np

from engine.confidence_model import predict_confidence, train_confidence_model


def test_predict_confidence_fails_safe_when_model_missing():
    """No model loaded must never silently allow an auto-match."""
    feats = {"amount_delta_pct": 0.0, "date_delta_days": 0.0, "narration_similarity": 1.0,
              "reference_similarity": 1.0, "is_fee_pattern": 0.0}
    assert predict_confidence(None, feats) == 0.0


def test_model_separates_obviously_safe_from_obviously_unsafe_examples():
    rng = np.random.RandomState(0)
    safe = rng.normal(loc=[0.0, 0.0, 1.0, 1.0, 0.0], scale=0.02, size=(60, 5))
    unsafe = rng.normal(loc=[0.5, 10.0, 0.2, 0.2, 0.0], scale=0.05, size=(60, 5))
    X = np.vstack([safe, unsafe])
    y = np.array([1] * 60 + [0] * 60)
    model, report, (X_test, y_test) = train_confidence_model(X, y)
    assert report["test_acc"] > 0.85
