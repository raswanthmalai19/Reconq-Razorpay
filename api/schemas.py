from pydantic import BaseModel
from typing import Optional
from enum import Enum

class ReconciliationStatus(str, Enum):
    AUTO_MATCHED = 'AUTO_MATCHED'
    HUMAN_REVIEW = 'HUMAN_REVIEW'
    UNRESOLVED = 'UNRESOLVED'
    BANK_CONFIRMED = 'BANK_CONFIRMED'
    BANK_DISCREPANCY = 'BANK_DISCREPANCY'
    FUNDS_IN_TRANSIT = 'FUNDS_IN_TRANSIT'

class MatchRecord(BaseModel):
    settlement_id: str
    invoice_id: str = ''
    status: str
    confidence: Optional[float] = None
    match_type: str = ''
    amount_paise: Optional[int] = None

class KPISummary(BaseModel):
    total_records: int
    auto_matched: int
    human_review: int
    unresolved: int
    match_rate: float
    rupees_auto_cleared: float
    rupees_in_review: float
    bank_confirmed: int = 0
    funds_in_transit: int = 0

class AnomalyItem(BaseModel):
    anomaly_type: str
    severity: str
    estimated_impact_rupees: float
    description: str
    affected_records: list[str]

class LeakageReport(BaseModel):
    total_leakage_rupees: float
    anomaly_count: int
    by_category: dict
    recommendations: list[str]
    anomalies: list[AnomalyItem]

class ReconciliationResponse(BaseModel):
    run_id: str
    kpi: KPISummary
    matches: list[MatchRecord]
    anomalies: list[AnomalyItem]
    leakage_report: Optional[LeakageReport] = None

class CopilotRequest(BaseModel):
    message: str
    run_id: str = 'default'

class CopilotResponse(BaseModel):
    reply: str
    sources: list[str] = []

class OverrideRequest(BaseModel):
    settlement_id: str
    decision: str  # 'accept' or 'override'
    note: str = ''

class PipelineProgress(BaseModel):
    stage: str
    detail: str
    progress_pct: float
