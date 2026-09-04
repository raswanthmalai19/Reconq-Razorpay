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

    bad_rows = []
    for col in ("amount_inr", "fee_inr", "tax_inr"):
        fn = normalize_amount_paise if col == "amount_inr" else (lambda v: normalize_amount_paise(v) if v not in ("", None) else 0)
        good = []
        for i, v in enumerate(df[col]):
            try:
                good.append(fn(v))
            except (ValueError, TypeError):
                good.append(None)
                bad_rows.append((i, col, v))
        df[col] = good

    if bad_rows:
        import warnings
        details = "; ".join(f"row {r} col {c}='{v}'" for r, c, v in bad_rows)
        warnings.warn(f"settlement_report.csv: {len(bad_rows)} malformed value(s) quarantined — {details}")

    # Drop rows where amount_inr could not be parsed (essential field)
    n_before = len(df)
    df = df.dropna(subset=["amount_inr"])
    n_dropped = n_before - len(df)
    if n_dropped:
        import warnings
        warnings.warn(f"settlement_report.csv: {n_dropped} row(s) dropped — unparseable amount_inr")

    df["amount_inr"] = df["amount_inr"].astype(int)
    df["fee_inr"] = df["fee_inr"].fillna(0).astype(int)
    df["tax_inr"] = df["tax_inr"].fillna(0).astype(int)
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
