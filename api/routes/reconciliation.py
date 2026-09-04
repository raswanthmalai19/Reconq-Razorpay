import os
import uuid
import tempfile
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from io import StringIO

from api.schemas import (
    ReconciliationResponse, KPISummary, MatchRecord,
    OverrideRequest
)
from engine.pipeline import run_reconciliation
from engine.audit_log import append_event, append_override, get_all_events
from engine.confidence_model import load_model
from engine.train import train_and_save

router = APIRouter()

# Import the results_store from main (lazy import to avoid circular dependency)
def get_store():
    from api.main import results_store
    return results_store

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")

def get_or_train_model():
    model = load_model()
    if model is None:
        model, _ = train_and_save()
    return model

def _amount_lookup(settlement_path, ledger_path):
    settlements = pd.read_csv(settlement_path, dtype=str, keep_default_na=False)
    ledgers = pd.read_csv(ledger_path, dtype=str, keep_default_na=False)
    s_amt = {r["settlement_id"]: int(r["amount_inr"]) for _, r in settlements.iterrows()}
    return s_amt

def process_reconciliation(run_id: str, settlement_path: str, ledger_path: str, bank_statement_path: str = None) -> ReconciliationResponse:
    model = get_or_train_model()
    
    # Run the pipeline (with optional bank statement)
    result = run_reconciliation(settlement_path, ledger_path, model, bank_statement_path=bank_statement_path)
    s_amt = _amount_lookup(settlement_path, ledger_path)
    
    # Log events
    for m in result["matched"]:
        append_event(run_id, m["settlement_id"], "system", "EXACT_MATCH", m)
    for gm in result["group_matches"]:
        append_event(run_id, ",".join(gm["settlement_ids"]), "system", "GROUP_MATCH", gm)
    for a in result["assigned"]:
        append_event(run_id, a["settlement_id"], "system", "DECISION",
                      {"invoice_id": a["invoice_id"], "confidence": a["confidence"], "status": a["status"]})

    # Build KPI summary
    n_auto = len(result["matched"]) + sum(1 for a in result["assigned"] if a["status"] == "AUTO_MATCHED")
    n_review = len(result["group_matches"]) + sum(1 for a in result["assigned"] if a["status"] == "HUMAN_REVIEW")
    n_unresolved = len(result["unresolved_settlements"])
    total_records = n_auto + n_review + n_unresolved
    match_rate = n_auto / total_records if total_records else 0.0

    auto_ids = [m["settlement_id"] for m in result["matched"]] + \
               [a["settlement_id"] for a in result["assigned"] if a["status"] == "AUTO_MATCHED"]
    rupees_auto = sum(s_amt.get(sid, 0) for sid in auto_ids) / 100.0
    
    review_ids = [a["settlement_id"] for a in result["assigned"] if a["status"] == "HUMAN_REVIEW"]
    rupees_review = sum(s_amt.get(sid, 0) for sid in review_ids) / 100.0

    # Bank result KPIs
    bank_confirmed_count = 0
    funds_in_transit_count = 0
    if result.get("bank_result"):
        br = result["bank_result"]
        bank_confirmed_count = len(br.get("bank_confirmed", []))
        funds_in_transit_count = len(br.get("funds_in_transit", []))

    kpi = KPISummary(
        total_records=total_records,
        auto_matched=n_auto,
        human_review=n_review,
        unresolved=n_unresolved,
        match_rate=match_rate,
        rupees_auto_cleared=rupees_auto,
        rupees_in_review=rupees_review,
        bank_confirmed=bank_confirmed_count,
        funds_in_transit=funds_in_transit_count
    )

    # Build matches
    matches = []
    for m in result["matched"]:
        matches.append(MatchRecord(
            settlement_id=m["settlement_id"], invoice_id=m["invoice_id"],
            status=m["status"], confidence=m.get("confidence"), match_type="exact",
            amount_paise=s_amt.get(m["settlement_id"])
        ))
    for gm in result["group_matches"]:
        sid = ",".join(gm["settlement_ids"])
        matches.append(MatchRecord(
            settlement_id=sid, invoice_id=",".join(gm["invoice_ids"]),
            status=gm["status"], confidence=gm.get("confidence"), match_type=gm.get("match_type", "group"),
            amount_paise=sum(s_amt.get(i, 0) for i in gm["settlement_ids"])
        ))
    for a in result["assigned"]:
        matches.append(MatchRecord(
            settlement_id=a["settlement_id"], invoice_id=a["invoice_id"],
            status=a["status"], confidence=a.get("confidence"), match_type="1:1",
            amount_paise=s_amt.get(a["settlement_id"])
        ))
    for sid in result["unresolved_settlements"]:
        matches.append(MatchRecord(
            settlement_id=sid, invoice_id="", status="UNRESOLVED",
            confidence=None, match_type="n/a", amount_paise=s_amt.get(sid)
        ))

    # Build anomaly items
    from api.schemas import AnomalyItem, LeakageReport as LeakageReportSchema
    anomaly_items = []
    for a in result.get("anomalies", []):
        anomaly_items.append(AnomalyItem(
            anomaly_type=a["type_name"],
            severity=a["severity"],
            estimated_impact_rupees=a["estimated_impact_paise"] / 100.0,
            description=a["description"],
            affected_records=a["affected_records"]
        ))

    leakage = None
    lr = result.get("leakage_report")
    if lr:
        leakage = LeakageReportSchema(
            total_leakage_rupees=lr["total_leakage_paise"] / 100.0,
            anomaly_count=len(anomaly_items),
            by_category={k: v / 100.0 for k, v in lr["by_category"].items()},
            recommendations=lr["recommendations"],
            anomalies=anomaly_items
        )

    response = ReconciliationResponse(
        run_id=run_id,
        kpi=kpi,
        matches=matches,
        anomalies=anomaly_items,
        leakage_report=leakage
    )
    
    # Store raw result + DataFrames for copilot access
    settlements_df = pd.read_csv(settlement_path, dtype=str, keep_default_na=False)
    ledgers_df = pd.read_csv(ledger_path, dtype=str, keep_default_na=False)
    get_store()[run_id] = {
        "response": response,
        "raw_result": result,
        "settlements_df": settlements_df,
        "ledgers_df": ledgers_df,
    }
    return response

@router.post('/reconcile', response_model=ReconciliationResponse)
async def reconcile(
    settlement: UploadFile = File(...),
    ledger: UploadFile = File(...),
    bank_statement: Optional[UploadFile] = File(None)
):
    run_id = str(uuid.uuid4())
    tmp_dir = tempfile.mkdtemp(prefix="reconq_api_")
    settlement_path = os.path.join(tmp_dir, "settlement_report.csv")
    ledger_path = os.path.join(tmp_dir, "internal_ledger.csv")
    
    content = await settlement.read()
    with open(settlement_path, "wb") as f:
        f.write(content)
        
    content = await ledger.read()
    with open(ledger_path, "wb") as f:
        f.write(content)
    
    bank_path = None
    if bank_statement:
        bank_path = os.path.join(tmp_dir, "bank_statement.csv")
        content = await bank_statement.read()
        with open(bank_path, "wb") as f:
            f.write(content)
        
    response = process_reconciliation(run_id, settlement_path, ledger_path, bank_statement_path=bank_path)
    return response

@router.post('/reconcile/sample', response_model=ReconciliationResponse)
def reconcile_sample():
    run_id = str(uuid.uuid4())
    settlement_path = os.path.join(DATA_DIR, "settlement_report.csv")
    ledger_path = os.path.join(DATA_DIR, "internal_ledger.csv")
    bank_path = os.path.join(DATA_DIR, "bank_statement.csv")
    bank_statement_path = bank_path if os.path.exists(bank_path) else None
    
    response = process_reconciliation(run_id, settlement_path, ledger_path, bank_statement_path=bank_statement_path)
    return response


@router.post('/reconcile/compare')
def reconcile_compare(
    settlement: Optional[UploadFile] = File(None),
    ledger: Optional[UploadFile] = File(None),
):
    """Run same dataset through BOTH naive flat-threshold and risk-weighted policy.
    Returns exact rupees the naive policy would have auto-cleared wrongly.
    """
    from engine.naive_baseline import naive_decide, NAIVE_FIXED_THRESHOLD
    from engine.risk_policy import decide as risk_decide

    model = get_or_train_model()

    if settlement is None or ledger is None:
        s_path = os.path.join(DATA_DIR, "settlement_report.csv")
        l_path = os.path.join(DATA_DIR, "internal_ledger.csv")
    else:
        tmp = tempfile.mkdtemp(prefix="reconq_compare_")
        s_path = os.path.join(tmp, "settlement_report.csv")
        l_path = os.path.join(tmp, "internal_ledger.csv")
        with open(s_path, "wb") as f:
            f.write(settlement.file.read())
        with open(l_path, "wb") as f:
            f.write(ledger.file.read())

    result = run_reconciliation(s_path, l_path, model, naive_mode=False)
    s_amt = _amount_lookup(s_path, l_path)
    all_pairs = list(result.get("assigned", []))

    naive_auto, naive_review, naive_unresolved = [], [], []
    risk_auto, risk_review, risk_unresolved = [], [], []
    dangerous_auto_cleared = []

    for pair in all_pairs:
        sid = pair["settlement_id"]
        conf = pair.get("confidence", 0.0)
        amt_paise = s_amt.get(sid, 0)
        amt_rupees = amt_paise / 100.0
        naive_status = naive_decide(conf)
        risk_status = risk_decide(amt_paise, conf)
        record = {
            "settlement_id": sid,
            "invoice_id": pair.get("invoice_id", ""),
            "confidence": round(conf, 4),
            "amount_rupees": round(amt_rupees, 2),
            "naive_decision": naive_status,
            "risk_decision": risk_status,
        }
        if naive_status == "AUTO_MATCHED": naive_auto.append(record)
        elif naive_status == "HUMAN_REVIEW": naive_review.append(record)
        else: naive_unresolved.append(record)
        if risk_status == "AUTO_MATCHED": risk_auto.append(record)
        elif risk_status == "HUMAN_REVIEW": risk_review.append(record)
        else: risk_unresolved.append(record)
        if naive_status == "AUTO_MATCHED" and risk_status != "AUTO_MATCHED":
            dangerous_auto_cleared.append(record)

    exact_count = len(result.get("matched", []))
    exact_rupees = sum(s_amt.get(m["settlement_id"], 0) for m in result.get("matched", [])) / 100.0
    naive_total = sum(r["amount_rupees"] for r in naive_auto) + exact_rupees
    risk_total  = sum(r["amount_rupees"] for r in risk_auto)  + exact_rupees
    wrong_rupees = sum(r["amount_rupees"] for r in dangerous_auto_cleared)

    return {
        "total_records": len(all_pairs) + exact_count,
        "naive_policy": {
            "threshold": NAIVE_FIXED_THRESHOLD,
            "description": f"Flat {int(NAIVE_FIXED_THRESHOLD*100)}% confidence — same cutoff for ₹100 and ₹10,00,000",
            "auto_matched": len(naive_auto) + exact_count,
            "human_review": len(naive_review),
            "unresolved": len(naive_unresolved),
            "total_auto_cleared_rupees": round(naive_total, 2),
        },
        "risk_weighted_policy": {
            "description": "Banded: 75% for <₹1K · 85% for ₹1K–25K · 93% for ₹25K–1L · 97% for >₹1L",
            "auto_matched": len(risk_auto) + exact_count,
            "human_review": len(risk_review),
            "unresolved": len(risk_unresolved),
            "total_auto_cleared_rupees": round(risk_total, 2),
        },
        "headline": {
            "rupees_naive_would_clear_wrong": round(wrong_rupees, 2),
            "transactions_caught": len(dangerous_auto_cleared),
            "explanation": (
                f"The naive 85% policy would have auto-cleared ₹{wrong_rupees:,.2f} across "
                f"{len(dangerous_auto_cleared)} high-value transaction(s) that the risk-weighted "
                f"policy correctly stopped for human review."
            ),
        },
        "caught_transactions": sorted(dangerous_auto_cleared, key=lambda x: x["amount_rupees"], reverse=True)[:20],
    }


@router.get('/results/{run_id}', response_model=ReconciliationResponse)
def get_results(run_id: str):
    store = get_store()
    if run_id not in store:
        raise HTTPException(status_code=404, detail="Run not found")
    entry = store[run_id]
    return entry["response"] if isinstance(entry, dict) and "response" in entry else entry

@router.get('/results/{run_id}/export')
def export_results(run_id: str):
    store = get_store()
    if run_id not in store:
        raise HTTPException(status_code=404, detail="Run not found")
    
    entry = store[run_id]
    response = entry["response"] if isinstance(entry, dict) and "response" in entry else entry
    
    data = []
    for m in response.matches:
        data.append({
            "id": m.settlement_id,
            "invoice": m.invoice_id,
            "status": m.status,
            "confidence": m.confidence,
            "type": m.match_type
        })
    df = pd.DataFrame(data)
    
    stream = StringIO()
    df.to_csv(stream, index=False)
    stream.seek(0)
    
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reconq_results_{run_id}.csv"}
    )

@router.post('/override')
def override_decision(req: OverrideRequest):
    append_override("api-session", req.settlement_id, "human:api", req.decision, req.note)
    return {"status": "ok"}

@router.get('/audit/{run_id}')
def get_audit(run_id: str):
    from datetime import datetime, timezone
    events = get_all_events(run_id)
    # Fix timestamp: DB stores Unix seconds (float), JS Date() needs ISO string
    for e in events:
        ts = e.get("timestamp")
        if isinstance(ts, (int, float)) and ts > 0:
            e["timestamp"] = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        elif not ts:
            e["timestamp"] = None
        # Rename payload_json → payload for frontend
        if "payload_json" in e:
            try:
                import json as _json
                e["payload"] = _json.loads(e.pop("payload_json"))
            except Exception:
                e["payload"] = e.pop("payload_json")
    return events
