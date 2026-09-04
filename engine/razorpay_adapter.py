"""Razorpay Settlement Adapter — fetches live settlement data from Razorpay API
and normalises it into the exact same DataFrame shape that the reconciliation
engine expects from CSV ingestion.

Architecture:
    Razorpay API response  ─▶  normalise()  ─▶  Settlement[] DataFrame
    CSV rows               ─▶  csv_ingestor  ─▶  Settlement[] DataFrame
    
Both paths produce the same columns downstream. Nothing in the matching engine,
risk policy, or UI cares which path was used.

Test-mode behaviour:
    If the Razorpay test account has 0 settlements (fresh key, no transactions
    yet), this returns an honest empty result — count=0, source="razorpay_live".
    Nothing is fabricated under the Razorpay label. The caller (api/routes/
    razorpay_sync.py) surfaces this as a clear "no settlements yet" state and
    the UI offers the separately-labeled synthetic "Sample Data" path instead.
"""
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd

RAZORPAY_KEY_ID     = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def fetch_razorpay_settlements(
    key_id:     Optional[str] = None,
    key_secret: Optional[str] = None,
    count:      int = 100,
) -> dict:
    """Fetch settlements from Razorpay API and return as a normalised dict.

    Returns:
        {
            "settlements_df": pd.DataFrame,   # same schema as CSV path
            "source": "razorpay_live" | "razorpay_seeded",
            "count": int,
            "message": str,
            "raw_items": list,
        }
    """
    kid = (key_id or RAZORPAY_KEY_ID).strip()
    ksec = (key_secret or RAZORPAY_KEY_SECRET).strip()

    if not kid or not ksec:
        raise ValueError("Razorpay Key ID and Key Secret are required.")

    try:
        import razorpay
        client = razorpay.Client(auth=(kid, ksec))
        result = client.settlement.all({"count": min(count, 100)})
        items = result.get("items", [])
    except Exception as exc:
        raise RuntimeError(f"Razorpay API call failed: {exc}") from exc

    if items:
        df = _normalise_live(items)
        return {
            "settlements_df": df,
            "source": "razorpay_live",
            "count": len(df),
            "message": f"Fetched {len(df)} settlements from Razorpay live API.",
            "raw_items": items,
        }
    else:
        return {
            "settlements_df": pd.DataFrame(),
            "source": "razorpay_live",
            "count": 0,
            "message": (
                "Your Razorpay test account has no settlements yet. Run a test payment "
                "through Razorpay's test checkout to see live data here, or use Sample Data "
                "to see the full reconciliation pipeline on synthetic data instead."
            ),
            "raw_items": [],
        }


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def _normalise_live(items: list) -> pd.DataFrame:
    """Convert Razorpay settlement API objects into the engine's CSV schema."""
    rows = []
    for item in items:
        # Razorpay amounts are in paise
        amount_paise = int(item.get("amount", 0))
        fee_paise    = int(item.get("fees", 0))
        tax_paise    = int(item.get("tax", 0))
        net_paise    = amount_paise - fee_paise - tax_paise

        # Parse settlement date from Unix timestamp
        created_at = item.get("created_at") or item.get("settled_at") or 0
        if created_at:
            dt = datetime.fromtimestamp(created_at, tz=timezone.utc)
            date_str = dt.strftime("%Y-%m-%d")
        else:
            date_str = ""

        sid = item.get("id", "")
        rows.append({
            "settlement_id":    sid,
            "amount_inr":       amount_paise,
            "fee_inr":          fee_paise,
            "tax_inr":          tax_paise,
            "net_inr":          net_paise,
            "settlement_date":  date_str,
            "utr_reference":    item.get("utr", ""),
            "status":           item.get("status", "processed"),
            "invoice_id":       "",
            "narration":        f"Razorpay Settlement {sid}",
            "batch_id":         f"BATCH_{date_str.replace('-','')}",
        })
    return pd.DataFrame(rows)


def get_sample_ledger_for_api_mode() -> pd.DataFrame:
    """Return a minimal sample ledger for use when only the API path provides settlements."""
    random.seed(42)
    rows = []
    base_date = datetime.now(tz=timezone.utc) - timedelta(days=30)

    amounts = [
        45000, 12000, 8500, 230000, 67000, 1800, 990, 150000,
        33000, 4500, 78000, 25000, 5500, 320000, 11000, 9800,
        42000, 6700, 88000, 15000, 3200, 190000,
    ]

    for i, amt_paise in enumerate(amounts):
        if i % 5 == 0:
            ledger_amt = int(amt_paise * 0.98)
        else:
            ledger_amt = amt_paise

        day_offset = random.randint(0, 27)
        dt = base_date + timedelta(days=day_offset)

        rows.append({
            "invoice_id":    f"INV-API-{str(i+1).zfill(4)}",
            "amount_inr":    ledger_amt,
            "invoice_date":  dt.strftime("%Y-%m-%d"),
            "status":        "pending",
            "customer_ref":  f"CUST{random.randint(1000, 9999)}",
            "memo":          "Web sale",
        })

    return pd.DataFrame(rows)
