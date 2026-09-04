"""API routes for generating and approving suggested fixes.

POST /suggested-fix/generate  — generates a fix proposal for an exception
POST /suggested-fix/approve   — logs approval to audit trail (nothing external)
"""
import json
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from llm.suggested_fix import generate_suggested_fix
from engine.audit_log import append_event

router = APIRouter()


class FixRequest(BaseModel):
    settlement_id: str
    invoice_id: str = ""
    amount_paise: int = 0
    confidence: float = 0.0
    status: str = ""
    match_type: str = ""
    # Optional anomaly context
    anomaly_type: Optional[str] = None
    anomaly_severity: Optional[str] = None
    anomaly_impact_paise: Optional[int] = None
    anomaly_description: Optional[str] = None


class ApproveRequest(BaseModel):
    settlement_id: str
    run_id: str = "manual"
    fix_proposal: dict


@router.post('/suggested-fix/generate')
def generate_fix(req: FixRequest):
    """Generate a fix proposal for a reconciliation exception.

    The proposal is a structured JSON object, never executed automatically.
    Every number is cross-checked against the evidence before returning.
    """
    exception_data = {
        "settlement_id": req.settlement_id,
        "invoice_id": req.invoice_id,
        "amount_paise": req.amount_paise,
        "confidence": req.confidence,
        "status": req.status,
        "match_type": req.match_type,
    }

    anomaly_data = None
    if req.anomaly_type:
        anomaly_data = {
            "type_name": req.anomaly_type,
            "severity": req.anomaly_severity or "UNKNOWN",
            "estimated_impact_paise": req.anomaly_impact_paise or 0,
            "description": req.anomaly_description or "",
        }

    proposal = generate_suggested_fix(exception_data, anomaly_data)
    return proposal


@router.post('/suggested-fix/approve')
def approve_fix(req: ApproveRequest):
    """Log a human-approved fix to the audit trail.

    This does exactly ONE thing: writes to the append-only audit log.
    Nothing is sent externally. No API call, no write to a real ledger.
    The UI makes this explicit.
    """
    append_event(
        run_id=req.run_id,
        record_id=req.settlement_id,
        actor="human:dashboard",
        event_type="ADJUSTMENT_PROPOSED_AND_APPROVED",
        payload=req.fix_proposal,
    )
    return {
        "status": "ok",
        "message": (
            f"Fix for {req.settlement_id} logged to audit trail. "
            f"Nothing was sent externally."
        ),
    }
