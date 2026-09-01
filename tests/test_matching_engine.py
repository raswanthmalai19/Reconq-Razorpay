import pandas as pd

from engine.exact_match import exact_key_match
from engine.group_matching import find_split_merge_candidates
from engine.normalize import normalize_date, normalize_reference


def test_normalize_reference_strips_punctuation_and_uppercases():
    assert normalize_reference("inv-2291") == "INV2291"
    assert normalize_reference(" INV_2291 ") == "INV2291"


def test_normalize_date_parses_iso_string():
    assert str(normalize_date("2026-08-14")) == "2026-08-14"


def _settlement_row(sid, amount, narration, date="2026-08-14"):
    return {
        "settlement_id": sid, "utr_reference": "UTR1", "amount_inr": amount,
        "settlement_date": normalize_date(date), "fee_inr": 0, "tax_inr": 0,
        "narration": narration, "batch_id": "B1",
        "utr_reference_norm": normalize_reference("UTR1"), "narration_norm": narration.lower(),
    }


def _ledger_row(iid, amount, memo="paid", date="2026-08-14"):
    return {
        "invoice_id": iid, "customer_ref": "C1", "amount_inr": amount,
        "invoice_date": normalize_date(date), "memo": memo, "status": "paid",
        "invoice_id_norm": normalize_reference(iid), "memo_norm": memo.lower(),
    }


def test_exact_key_match_finds_obvious_pair():
    settlements = pd.DataFrame([_settlement_row("STL-1", 100000, "Settlement for INV-2291 batch")])
    ledgers = pd.DataFrame([_ledger_row("INV-2291", 100000)])
    matched, remaining_s, remaining_l = exact_key_match(settlements, ledgers)
    assert len(matched) == 1
    assert matched[0]["confidence"] == 1.0
    assert len(remaining_s) == 0 and len(remaining_l) == 0


def test_exact_key_match_does_not_match_wrong_amount():
    settlements = pd.DataFrame([_settlement_row("STL-1", 100000, "Settlement for INV-2291 batch")])
    ledgers = pd.DataFrame([_ledger_row("INV-2291", 500000)])
    matched, remaining_s, remaining_l = exact_key_match(settlements, ledgers)
    assert len(matched) == 0
    assert len(remaining_s) == 1 and len(remaining_l) == 1


def test_split_merge_detects_settlement_equal_to_sum_of_two_ledger_rows():
    from engine.blocking import build_buckets

    settlements = pd.DataFrame([_settlement_row("STL-1", 100000, "Settlement misc")])
    ledgers = pd.DataFrame([
        _ledger_row("INV-A", 60000), _ledger_row("INV-B", 40000),
    ])
    buckets = build_buckets(settlements, ledgers)
    group_matches, consumed_s, consumed_l = find_split_merge_candidates(buckets)
    assert len(group_matches) == 1
    assert group_matches[0]["match_type"] == "split"
    assert set(group_matches[0]["invoice_ids"]) == {"INV-A", "INV-B"}
    assert "STL-1" in consumed_s
