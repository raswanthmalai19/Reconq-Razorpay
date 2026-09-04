"""Autonomous Recovery Action Generator — powered by Gemini.

Given an anomaly or exception, generates:
1. Bank dispute letter (RBI-compliant format)
2. Accounting journal entry (DR/CR)
3. Razorpay support ticket payload

This transforms ReconQ from 'finds problems' to 'fixes problems'.
"""
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")


def generate_recovery_actions(
    action_type: str,
    transaction_data: dict,
    anomaly_data: dict = None,
) -> dict:
    """Generate autonomous recovery actions for a transaction or anomaly.

    Args:
        action_type: 'exception' or 'anomaly'
        transaction_data: dict with settlement_id, invoice_id, amount_paise, confidence, status, match_type
        anomaly_data: dict with anomaly_type, severity, estimated_impact_rupees, description, affected_records
    """
    amount_rupees = (transaction_data.get("amount_paise") or 0) / 100
    settlement_id = transaction_data.get("settlement_id", "UNKNOWN")
    invoice_id = transaction_data.get("invoice_id", "UNKNOWN")
    status = transaction_data.get("status", "UNKNOWN")
    confidence = transaction_data.get("confidence", 0)
    today = datetime.now().strftime("%d %B %Y")

    # Build context for Gemini
    context = {
        "settlement_id": settlement_id,
        "invoice_id": invoice_id,
        "amount_rupees": amount_rupees,
        "status": status,
        "confidence": confidence,
        "match_type": transaction_data.get("match_type", ""),
        "date": today,
    }
    if anomaly_data:
        context["anomaly_type"] = anomaly_data.get("anomaly_type", "")
        context["severity"] = anomaly_data.get("severity", "")
        context["impact_rupees"] = anomaly_data.get("estimated_impact_rupees", 0)
        context["description"] = anomaly_data.get("description", "")
        context["affected_count"] = len(anomaly_data.get("affected_records", []))

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if api_key:
        try:
            return _generate_with_gemini(api_key, context, action_type)
        except Exception:
            pass

    # Fallback: template-based generation
    return _generate_template(context, action_type)


def _generate_with_gemini(api_key: str, context: dict, action_type: str) -> dict:
    client = genai.Client(api_key=api_key)

    prompt = f"""You are a senior finance operations specialist generating recovery actions for a payment reconciliation discrepancy.

TRANSACTION DATA:
{json.dumps(context, indent=2)}

ACTION TYPE: {action_type}

Generate a JSON response with exactly these 3 fields:

{{
  "dispute_letter": "A formal bank dispute letter (3-4 paragraphs). Include: Reference to settlement ID, exact amount in ₹, nature of discrepancy, request for investigation, timeline for resolution. Use formal business English. Include a subject line at the top.",
  "journal_entry": {{
    "description": "Brief description of the corrective journal entry",
    "entries": [
      {{"account": "Account Name", "debit_rupees": 0, "credit_rupees": 0}},
      {{"account": "Account Name", "debit_rupees": 0, "credit_rupees": 0}}
    ],
    "narration": "Accounting narration for the entry"
  }},
  "support_ticket": {{
    "subject": "Ticket subject line",
    "priority": "HIGH or MEDIUM or LOW",
    "category": "Settlement Discrepancy or Fee Dispute or Missing Transaction",
    "description": "Detailed ticket description with all relevant IDs and amounts",
    "resolution_requested": "Specific action requested from support team"
  }}
}}

Return ONLY valid JSON. No markdown fences."""

    chat = client.chats.create(
        model=GEMINI_MODEL,
        config=types.GenerateContentConfig(
            system_instruction="You are a JSON API for financial operations. Return only valid JSON.",
            max_output_tokens=8192,
            temperature=0.1,
        ),
    )
    resp = chat.send_message(prompt)
    raw = resp.text or ""
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    result = json.loads(raw)

    return {
        "settlement_id": context["settlement_id"],
        "generated_at": datetime.now().isoformat(),
        "source": "gemini",
        "dispute_letter": result.get("dispute_letter", ""),
        "journal_entry": result.get("journal_entry", {}),
        "support_ticket": result.get("support_ticket", {}),
    }


def _generate_template(context: dict, action_type: str) -> dict:
    sid = context["settlement_id"]
    iid = context["invoice_id"]
    amt = context["amount_rupees"]
    today = context["date"]
    anomaly_type = context.get("anomaly_type", "Reconciliation Discrepancy")
    impact = context.get("impact_rupees", amt)

    dispute_letter = f"""Subject: Dispute Regarding Settlement {sid} — Amount ₹{amt:,.2f}

Date: {today}

Dear Banking Operations Team,

We are writing to formally dispute settlement transaction {sid} dated {today}, involving an amount of ₹{amt:,.2f} (Invoice Reference: {iid}).

During our automated reconciliation process, this transaction was flagged as a {anomaly_type.lower()} with an estimated financial impact of ₹{impact:,.2f}. Our 3-way matching system (gateway ↔ ledger ↔ bank statement) has identified a discrepancy that requires immediate investigation.

We request that your team investigate this matter and provide a detailed breakdown of the settlement within 7 business days, in compliance with RBI circular RBI/2023-24/115 on payment settlement timelines.

Please contact our finance team for any clarifications required.

Regards,
Finance Operations Team"""

    journal_entry = {
        "description": f"Corrective entry for {anomaly_type} on {sid}",
        "entries": [
            {"account": "Bank Charges / Gateway Discrepancy", "debit_rupees": round(impact, 2), "credit_rupees": 0},
            {"account": "Gateway Settlement Receivable", "debit_rupees": 0, "credit_rupees": round(impact, 2)},
        ],
        "narration": f"To record {anomaly_type.lower()} discrepancy for settlement {sid}, invoice {iid}. Amount: ₹{impact:,.2f}. Auto-generated by ReconQ.",
    }

    support_ticket = {
        "subject": f"[{anomaly_type}] Settlement {sid} — ₹{amt:,.2f} discrepancy",
        "priority": "HIGH" if impact > 50000 else "MEDIUM",
        "category": "Settlement Discrepancy",
        "description": f"Settlement {sid} (Invoice: {iid}) flagged during automated reconciliation.\nType: {anomaly_type}\nAmount: ₹{amt:,.2f}\nImpact: ₹{impact:,.2f}\nConfidence: {context.get('confidence', 0)*100:.1f}%\nStatus: {context.get('status', 'UNKNOWN')}",
        "resolution_requested": f"Investigate and resolve the {anomaly_type.lower()} for settlement {sid}. Provide settlement breakdown and confirm correct amount.",
    }

    return {
        "settlement_id": sid,
        "generated_at": datetime.now().isoformat(),
        "source": "template",
        "dispute_letter": dispute_letter,
        "journal_entry": journal_entry,
        "support_ticket": support_ticket,
    }
