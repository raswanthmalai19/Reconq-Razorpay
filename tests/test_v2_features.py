"""Tests for bank matching, anomaly detection, Gemini client, and 3-way pipeline."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest


# --- Bank Matching Tests ---

def test_bank_match_confirms_exact_utr_and_amount():
    """A bank entry with the same UTR, same amount, same date should be BANK_CONFIRMED."""
    from engine.bank_matching import match_bank_to_settlements

    bank_df = pd.DataFrame([{
        "bank_txn_id": "BNK-001", "utr_reference": "UTR202208011234",
        "credit_amount_inr": 50000, "credit_date": "2026-08-01",
        "bank_narration": "Settlement", "balance_after": 100000
    }])
    settlements_df = pd.DataFrame([{
        "settlement_id": "STL-001", "utr_reference": "UTR202208011234",
        "amount_inr": 50000, "settlement_date": "2026-08-01",
        "fee_inr": 0, "tax_inr": 0, "narration": "test", "batch_id": "B1"
    }])
    result = match_bank_to_settlements(bank_df, settlements_df)
    assert len(result.bank_confirmed) == 1
    assert result.bank_confirmed[0]["status"] == "BANK_CONFIRMED"


def test_bank_match_detects_amount_discrepancy():
    """A bank entry with different amount should be BANK_DISCREPANCY."""
    from engine.bank_matching import match_bank_to_settlements

    bank_df = pd.DataFrame([{
        "bank_txn_id": "BNK-001", "utr_reference": "UTR202208011234",
        "credit_amount_inr": 49000, "credit_date": "2026-08-01",
        "bank_narration": "Settlement", "balance_after": 100000
    }])
    settlements_df = pd.DataFrame([{
        "settlement_id": "STL-001", "utr_reference": "UTR202208011234",
        "amount_inr": 50000, "settlement_date": "2026-08-01",
        "fee_inr": 0, "tax_inr": 0, "narration": "test", "batch_id": "B1"
    }])
    result = match_bank_to_settlements(bank_df, settlements_df)
    assert len(result.bank_discrepancies) == 1
    assert result.bank_discrepancies[0]["status"] == "BANK_DISCREPANCY"


def test_bank_match_detects_funds_in_transit():
    """A settlement with no bank entry should be FUNDS_IN_TRANSIT."""
    from engine.bank_matching import match_bank_to_settlements

    bank_df = pd.DataFrame(columns=["bank_txn_id", "utr_reference", "credit_amount_inr",
                                      "credit_date", "bank_narration", "balance_after"])
    settlements_df = pd.DataFrame([{
        "settlement_id": "STL-001", "utr_reference": "UTR202208011234",
        "amount_inr": 50000, "settlement_date": "2026-08-01",
        "fee_inr": 0, "tax_inr": 0, "narration": "test", "batch_id": "B1"
    }])
    result = match_bank_to_settlements(bank_df, settlements_df)
    assert len(result.funds_in_transit) == 1


# --- Anomaly Detection Tests ---

def test_anomaly_detects_fee_overcharge():
    """Fee significantly above expected MDR should be flagged."""
    from engine.anomaly_detector import detect_anomalies

    settlements = pd.DataFrame([{
        "settlement_id": "STL-001", "amount_inr": 100000,
        "fee_inr": 5000, "settlement_date": "2026-08-01"  # 5% fee on 2% expected
    }])
    ledgers = pd.DataFrame(columns=["invoice_id", "amount_inr"])
    result = {"unresolved_settlements": [], "unresolved_ledgers": []}
    anomalies = detect_anomalies(settlements, ledgers, result)
    fee_anomalies = [a for a in anomalies if a.type_name == "Fee Overcharge"]
    assert len(fee_anomalies) == 1


def test_anomaly_detects_missing_settlements():
    """Unresolved ledger entries should trigger missing settlement anomaly."""
    from engine.anomaly_detector import detect_anomalies

    settlements = pd.DataFrame(columns=["settlement_id", "amount_inr", "fee_inr", "settlement_date"])
    ledgers = pd.DataFrame([
        {"invoice_id": "INV-001", "amount_inr": 50000},
        {"invoice_id": "INV-002", "amount_inr": 30000},
    ])
    result = {"unresolved_settlements": [], "unresolved_ledgers": ["INV-001", "INV-002"]}
    anomalies = detect_anomalies(settlements, ledgers, result)
    missing = [a for a in anomalies if a.type_name == "Missing Settlement"]
    assert len(missing) == 1
    assert missing[0].severity == "CRITICAL"


def test_leakage_report_aggregates_correctly():
    """Leakage report should sum impacts across all anomaly types."""
    from engine.anomaly_detector import Anomaly, generate_leakage_report

    anomalies = [
        Anomaly("Fee Overcharge", "MEDIUM", 5000, "test", ["STL-001"]),
        Anomaly("Missing Settlement", "CRITICAL", 10000, "test", ["INV-001"]),
    ]
    report = generate_leakage_report(anomalies)
    assert report.total_leakage_paise == 15000
    assert len(report.by_category) == 2
    assert len(report.recommendations) >= 2


# --- Gemini Client Tests ---

def test_gemini_explain_falls_back_without_api_key():
    """Without GEMINI_API_KEY, gemini_explain should return template fallback."""
    old = os.environ.pop("GEMINI_API_KEY", None)
    try:
        from llm.gemini_client import gemini_explain
        result = gemini_explain({"amount_delta_pct": 0.02, "date_delta_days": 1})
        assert result["source"] == "template_fallback"
        assert "explanation" in result
    finally:
        if old:
            os.environ["GEMINI_API_KEY"] = old


def test_main_client_prefers_gemini_falls_to_template():
    """Main explain() should fall to template when both API keys are missing."""
    old_g = os.environ.pop("GEMINI_API_KEY", None)
    old_a = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        from llm.client import explain
        result = explain({"amount_delta_pct": 0.03, "date_delta_days": 2})
        assert result["source"] == "template_fallback"
    finally:
        if old_g:
            os.environ["GEMINI_API_KEY"] = old_g
        if old_a:
            os.environ["ANTHROPIC_API_KEY"] = old_a


# --- 3-Way Pipeline Integration Test ---

def test_pipeline_3way_returns_bank_result():
    """Pipeline with bank_statement_path should return bank_result."""
    from engine.pipeline import run_reconciliation
    from engine.confidence_model import load_model

    model = load_model()
    DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    result = run_reconciliation(
        os.path.join(DATA, "settlement_report.csv"),
        os.path.join(DATA, "internal_ledger.csv"),
        model,
        bank_statement_path=os.path.join(DATA, "bank_statement.csv")
    )
    assert result["bank_result"] is not None
    assert "bank_confirmed" in result["bank_result"]
    assert "funds_in_transit" in result["bank_result"]
    assert len(result["anomalies"]) > 0
    assert result["leakage_report"]["total_leakage_paise"] >= 0


def test_pipeline_2way_backward_compatible():
    """Pipeline without bank_statement_path should still work (backward compat)."""
    from engine.pipeline import run_reconciliation
    from engine.confidence_model import load_model

    model = load_model()
    DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    result = run_reconciliation(
        os.path.join(DATA, "settlement_report.csv"),
        os.path.join(DATA, "internal_ledger.csv"),
        model
    )
    assert result["bank_result"] is None
    assert "matched" in result
    assert "assigned" in result
