"""Razorpay direct API sync route.

POST /api/razorpay/sync    — fetch settlements from Razorpay API → run reconciliation
GET  /api/razorpay/status  — check if keys are configured
"""
import os
import uuid
import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class RazorpaySync(BaseModel):
    key_id:     Optional[str] = None   # if provided, overrides .env
    key_secret: Optional[str] = None
    count:      int = 100


@router.get("/razorpay/status")
def razorpay_status():
    """Check if Razorpay keys are configured."""
    kid = os.environ.get("RAZORPAY_KEY_ID", "").strip()
    return {
        "configured": bool(kid),
        "key_id_prefix": kid[:12] + "..." if kid else None,
        "mode": "test" if kid.startswith("rzp_test_") else "live" if kid else None,
    }


@router.post("/razorpay/sync")
async def razorpay_sync(req: RazorpaySync = None):
    """Fetch settlements from Razorpay API and run reconciliation.

    This is the 'Connect Razorpay' path. It produces the exact same output
    as POST /api/reconcile — same pipeline, same risk scoring, same decisions.

    Note: Razorpay's API only ever provides the gateway/settlement side.
    The internal ledger (the merchant's own ERP/accounting record) is not
    something any payment gateway API can provide — it lives in the
    merchant's own systems. So this route reconciles real, live Razorpay
    settlements against a synthetic sample ledger, and says so explicitly
    in the response (`ledger_source` / `ledger_message`) and in the UI.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from engine.razorpay_adapter import fetch_razorpay_settlements, get_sample_ledger_for_api_mode
    from engine.audit_log import append_event

    if req is None:
        req = RazorpaySync()

    kid   = req.key_id   or os.environ.get("RAZORPAY_KEY_ID", "")
    ksec  = req.key_secret or os.environ.get("RAZORPAY_KEY_SECRET", "")

    if not kid or not ksec:
        return {"error": "Razorpay API keys not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to .env"}

    # Fetch settlements in thread (network call)
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        try:
            adapter_result = await asyncio.wait_for(
                loop.run_in_executor(
                    pool,
                    lambda: fetch_razorpay_settlements(kid, ksec, req.count)
                ),
                timeout=15.0,
            )
        except asyncio.TimeoutError:
            return {"error": "Razorpay API request timed out (>15s). Check your network connection."}
        except Exception as exc:
            return {"error": str(exc)}

    settlements_df = adapter_result["settlements_df"]

    if settlements_df.empty:
        return {
            "status": "no_settlements",
            "razorpay_source": adapter_result["source"],
            "razorpay_message": adapter_result["message"],
        }

    ledgers_df = get_sample_ledger_for_api_mode()

    # Save to temp CSVs to match the existing pipeline expectations
    import tempfile
    from api.routes.reconciliation import process_reconciliation

    run_id = str(uuid.uuid4())
    
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as s_file, \
         tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as l_file:
        settlement_path = s_file.name
        ledger_path = l_file.name
        
    try:
        settlements_df.to_csv(settlement_path, index=False)
        ledgers_df.to_csv(ledger_path, index=False)

        # Run the full reconciliation pipeline (same as CSV path)
        response = process_reconciliation(run_id, settlement_path, ledger_path)
    except Exception as exc:
        if os.path.exists(settlement_path): os.remove(settlement_path)
        if os.path.exists(ledger_path): os.remove(ledger_path)
        return {"error": f"Reconciliation failed: {exc}"}

    # Cleanup temp files
    if os.path.exists(settlement_path): os.remove(settlement_path)
    if os.path.exists(ledger_path): os.remove(ledger_path)

    # Write to audit log
    try:
        append_event(
            run_id=run_id,
            record_id="razorpay_sync",
            actor="system",
            event_type="RAZORPAY_API_SYNC",
            payload={
                "source": adapter_result["source"],
                "settlement_count": adapter_result["count"],
                "message": adapter_result["message"],
            },
        )
    except Exception:
        pass  # audit log failure never blocks the response

    result = response.model_dump() if hasattr(response, "model_dump") else dict(response)
    result["razorpay_source"] = adapter_result["source"]
    result["razorpay_message"] = adapter_result["message"]
    result["ledger_source"] = "synthetic_sample"
    result["ledger_message"] = (
        "Razorpay's API only provides settlement data, not your internal ledger "
        "(that lives in your own ERP/accounting system). This run reconciles the "
        "real settlements fetched above against a synthetic sample ledger so the "
        "matching pipeline has a counterpart to reconcile against."
    )
    return result
