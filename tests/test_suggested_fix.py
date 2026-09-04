"""Tests for the Suggested Fix generator — numeric cross-check and fallback behavior."""
import pytest
from llm.suggested_fix import (
    _build_evidence_object,
    _extract_all_numbers,
    _cross_check_numbers,
    _template_fallback,
    VALID_ADJUSTMENT_TYPES,
)


def _sample_evidence():
    return {
        "settlement_id": "STL-001",
        "invoice_id": "INV-001",
        "amount_paise": 500000,
        "confidence": 0.85,
        "status": "HUMAN_REVIEW",
        "match_type": "assigned",
    }


class TestEvidenceBuilder:
    def test_basic_evidence(self):
        data = {"settlement_id": "STL-001", "amount_paise": 100}
        ev = _build_evidence_object(data)
        assert ev["settlement_id"] == "STL-001"
        assert ev["amount_paise"] == 100

    def test_with_anomaly(self):
        data = {"settlement_id": "STL-001", "amount_paise": 100}
        anomaly = {"type_name": "Fee Overcharge", "severity": "MEDIUM",
                   "estimated_impact_paise": 5000, "description": "test"}
        ev = _build_evidence_object(data, anomaly)
        assert ev["anomaly_type"] == "Fee Overcharge"
        assert ev["anomaly_impact_paise"] == 5000


class TestNumberExtraction:
    def test_flat_dict(self):
        nums = _extract_all_numbers({"a": 10, "b": 20, "c": "text"})
        assert nums == {10, 20}

    def test_nested(self):
        nums = _extract_all_numbers({"a": [{"b": 5}, {"c": 10}], "d": 15})
        assert nums == {5, 10, 15}

    def test_empty(self):
        assert _extract_all_numbers({}) == set()


class TestCrossCheck:
    def test_valid_proposal(self):
        evidence = _sample_evidence()
        proposal = {
            "affected_records": [
                {"record_id": "STL-001", "field": "fee", "current_value": 500000, "proposed_value": 0}
            ]
        }
        passed, violations = _cross_check_numbers(proposal, evidence)
        assert passed is True
        assert violations == []

    def test_invalid_number_rejected(self):
        evidence = _sample_evidence()
        proposal = {
            "affected_records": [
                {"record_id": "STL-001", "field": "fee", "current_value": 999999, "proposed_value": 0}
            ]
        }
        passed, violations = _cross_check_numbers(proposal, evidence)
        assert passed is False
        assert len(violations) == 1
        assert "999999" in violations[0]

    def test_derivable_difference_allowed(self):
        evidence = _sample_evidence()  # has 500000 and 0.85
        proposal = {
            "affected_records": [
                {"record_id": "STL-001", "field": "amount",
                 "current_value": 500000,
                 "proposed_value": 500000}  # same value — valid
            ]
        }
        passed, _ = _cross_check_numbers(proposal, evidence)
        assert passed is True

    def test_empty_records_passes(self):
        evidence = _sample_evidence()
        proposal = {"affected_records": []}
        passed, violations = _cross_check_numbers(proposal, evidence)
        assert passed is True
        assert violations == []


class TestTemplateFallback:
    def test_fallback_structure(self):
        evidence = _sample_evidence()
        fb = _template_fallback(evidence, "test reason")
        assert fb["adjustment_type"] == "no_confident_fix"
        assert fb["affected_records"] == []
        assert fb["confidence"] == 0.0
        assert "test reason" in fb["explanation"]
        assert fb["validation"]["cross_check_passed"] is False

    def test_fallback_has_human_step(self):
        evidence = _sample_evidence()
        fb = _template_fallback(evidence, "any reason")
        assert "human_next_step" in fb
        assert len(fb["human_next_step"]) > 0


class TestValidAdjustmentTypes:
    def test_expected_types(self):
        assert "fee_reversal" in VALID_ADJUSTMENT_TYPES
        assert "duplicate_removal" in VALID_ADJUSTMENT_TYPES
        assert "amount_correction" in VALID_ADJUSTMENT_TYPES
        assert "timing_correction" in VALID_ADJUSTMENT_TYPES
        assert "no_confident_fix" in VALID_ADJUSTMENT_TYPES

    def test_invalid_type_not_present(self):
        assert "auto_execute" not in VALID_ADJUSTMENT_TYPES
        assert "send_email" not in VALID_ADJUSTMENT_TYPES
