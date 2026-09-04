"""Recovery Actions API — generates autonomous dispute letters, journal entries, and support tickets."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class RecoveryRequest(BaseModel):
    action_type: str = "exception"  # 'exception' or 'anomaly'
    settlement_id: str = ""
    invoice_id: str = ""
    amount_paise: int = 0
    confidence: float = 0
    status: str = ""
    match_type: str = ""
    anomaly_type: Optional[str] = None
    severity: Optional[str] = None
    estimated_impact_rupees: Optional[float] = None
    description: Optional[str] = None
    affected_records: Optional[list] = None


@router.post("/recovery/generate")
def generate_recovery(req: RecoveryRequest):
    """Generate autonomous recovery actions for a transaction or anomaly."""
    from llm.recovery_actions import generate_recovery_actions

    transaction_data = {
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
            "anomaly_type": req.anomaly_type,
            "severity": req.severity or "MEDIUM",
            "estimated_impact_rupees": req.estimated_impact_rupees or 0,
            "description": req.description or "",
            "affected_records": req.affected_records or [],
        }

    result = generate_recovery_actions(req.action_type, transaction_data, anomaly_data)
    return result
