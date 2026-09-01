"""Exact-key matching: hash-index both sides on the invoice/settlement reference.

Clears the majority of clean records in O(n), at confidence 1.0, before any
fuzzy/ML logic ever runs.
"""
import re

import pandas as pd


def _extract_invoice_ref(narration: str) -> str:
    """Pull an INV-#### style token out of a settlement narration string."""
    m = re.search(r"INV[-]?(\d+)", narration.upper())
    return f"INV{m.group(1)}" if m else ""


def exact_key_match(settlements: pd.DataFrame, ledgers: pd.DataFrame):
    """Returns (matched_pairs, remaining_settlements, remaining_ledgers).

    matched_pairs is a list of dicts: settlement_id, invoice_id, confidence=1.0.
    """
    ledger_by_ref = {}
    for _, row in ledgers.iterrows():
        ledger_by_ref.setdefault(normalize_ref(row["invoice_id"]), []).append(row)

    matched = []
    matched_settlement_ids = set()
    matched_invoice_ids = set()

    for _, srow in settlements.iterrows():
        ref = _extract_invoice_ref(srow["narration"])
        ref_norm = normalize_ref(ref)
        candidates = ledger_by_ref.get(ref_norm, [])
        for lrow in candidates:
            if lrow["invoice_id"] in matched_invoice_ids:
                continue
            if abs(int(srow["amount_inr"]) - int(lrow["amount_inr"])) <= 100:  # +/- Re 1
                matched.append({
                    "settlement_id": srow["settlement_id"],
                    "invoice_id": lrow["invoice_id"],
                    "confidence": 1.0,
                    "match_type": "1:1",
                    "status": "AUTO_MATCHED",
                })
                matched_settlement_ids.add(srow["settlement_id"])
                matched_invoice_ids.add(lrow["invoice_id"])
                break

    remaining_settlements = settlements[~settlements["settlement_id"].isin(matched_settlement_ids)]
    remaining_ledgers = ledgers[~ledgers["invoice_id"].isin(matched_invoice_ids)]
    return matched, remaining_settlements, remaining_ledgers


def normalize_ref(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())
