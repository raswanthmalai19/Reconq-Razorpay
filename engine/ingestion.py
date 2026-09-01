"""Deterministic record loading + validation for ReconQ.

Rejects malformed CSVs immediately with a specific, named error rather than
a generic exception -- required by the spec's fail-fast input validation.
"""
import pandas as pd

from engine.normalize import normalize_amount_paise, normalize_date, normalize_reference, normalize_text

SETTLEMENT_REQUIRED_COLUMNS = [
    "settlement_id", "utr_reference", "amount_inr", "settlement_date",
    "fee_inr", "tax_inr", "narration", "batch_id",
]
LEDGER_REQUIRED_COLUMNS = [
    "invoice_id", "customer_ref", "amount_inr", "invoice_date", "memo", "status",
]


class SchemaValidationError(ValueError):
    pass


def _check_columns(df: pd.DataFrame, required, file_label: str):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SchemaValidationError(
            f"{file_label} is missing required column(s): {', '.join(missing)}"
        )


def load_settlement_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    _check_columns(df, SETTLEMENT_REQUIRED_COLUMNS, "settlement_report.csv")
    df["amount_inr"] = df["amount_inr"].map(normalize_amount_paise)
    df["fee_inr"] = df["fee_inr"].map(lambda v: normalize_amount_paise(v) if v not in ("", None) else 0)
    df["tax_inr"] = df["tax_inr"].map(lambda v: normalize_amount_paise(v) if v not in ("", None) else 0)
    df["settlement_date"] = df["settlement_date"].map(normalize_date)
    df["utr_reference_norm"] = df["utr_reference"].map(normalize_reference)
    df["narration_norm"] = df["narration"].map(normalize_text)
    return df


def load_ledger_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    _check_columns(df, LEDGER_REQUIRED_COLUMNS, "internal_ledger.csv")
    df["amount_inr"] = df["amount_inr"].map(normalize_amount_paise)
    df["invoice_date"] = df["invoice_date"].map(normalize_date)
    df["invoice_id_norm"] = df["invoice_id"].map(normalize_reference)
    df["memo_norm"] = df["memo"].map(normalize_text)
    return df
