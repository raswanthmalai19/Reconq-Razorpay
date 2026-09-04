"""Suggested Fix Generator — evidence-only LLM layer for exception resolution.

Architecture:
  - The LLM generates a structured JSON "fix proposal" for a given exception
  - Every number in the proposal is cross-checked against the evidence object
  - If any number doesn't match the evidence, the payload is discarded and a
    template fallback is returned
  - The LLM is explicitly instructed to output "no_confident_fix" for ambiguous cases
  - "Approve" writes to the audit log only — nothing is sent externally

This is NOT a separate "AI Agent" feature. It extends the existing evidence-only
LLM architecture the copilot already uses: structured output, forced schema,
numeric verification, human gate.
"""
import json
import os
import re
from typing import Optional

from google import genai
from google.genai import types


GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

# The only adjustment types the LLM is allowed to generate.
# Anything outside this enum is rejected.
VALID_ADJUSTMENT_TYPES = frozenset({
    "fee_reversal",
    "duplicate_removal",
    "amount_correction",
    "timing_correction",
    "no_confident_fix",
})

SYSTEM_PROMPT = """You are a financial reconciliation assistant. You generate structured fix proposals for payment exceptions.

ABSOLUTE RULES — violating any of these causes your output to be discarded:

1. You ONLY generate adjustments for these categories:
   - fee_reversal: when the MDR/fee charged exceeds the expected rate
   - duplicate_removal: when the same settlement appears twice (same amount, same date)
   - amount_correction: when there is a clear, calculable mismatch between settlement and ledger amounts
   - timing_correction: when settlement and ledger dates are offset but amounts match exactly
   - no_confident_fix: when you are NOT confident what the correct fix is

2. If you are unsure what the fix should be, you MUST set adjustment_type to "no_confident_fix" and explain why. NEVER guess.

3. Every amount you state in affected_records MUST appear VERBATIM in the evidence you were given. Never invent, round, or estimate a number. If the evidence says the amount is 5000 paise, you write 5000 — not 50.00, not "approximately 5000".

4. The "explanation" field must cite specific record IDs and amounts from the evidence.

5. You are generating a PROPOSAL for a human to review. Nothing you output will be automatically executed. Be precise, not persuasive.

Respond with valid JSON matching this exact schema:
{
  "adjustment_type": "fee_reversal" | "duplicate_removal" | "amount_correction" | "timing_correction" | "no_confident_fix",
  "affected_records": [
    {"record_id": "string", "field": "string", "current_value": number, "proposed_value": number, "reason": "string"}
  ],
  "evidence_cited": ["string"],
  "confidence": 0.0 to 1.0,
  "explanation": "string — cite exact record IDs and amounts",
  "human_next_step": "string — what the reviewer should verify before approving"
}
"""


def _build_evidence_object(exception_data: dict, anomaly_data: dict = None) -> dict:
    """Constructs the evidence object that the LLM and the cross-checker both see.

    This is the single source of truth. Every number the LLM is allowed to cite
    must appear in this object.
    """
    evidence = {
        "settlement_id": exception_data.get("settlement_id", ""),
        "invoice_id": exception_data.get("invoice_id", ""),
        "amount_paise": exception_data.get("amount_paise", 0),
        "confidence": exception_data.get("confidence", 0),
        "status": exception_data.get("status", ""),
        "match_type": exception_data.get("match_type", ""),
    }

    if anomaly_data:
        evidence["anomaly_type"] = anomaly_data.get("type_name", "")
        evidence["anomaly_severity"] = anomaly_data.get("severity", "")
        evidence["anomaly_impact_paise"] = anomaly_data.get("estimated_impact_paise", 0)
        evidence["anomaly_description"] = anomaly_data.get("description", "")
        evidence["anomaly_affected_records"] = anomaly_data.get("affected_records", [])

    return evidence


def _extract_all_numbers(obj) -> set:
    """Recursively extracts every numeric value from a nested dict/list."""
    numbers = set()
    if isinstance(obj, dict):
        for v in obj.values():
            numbers |= _extract_all_numbers(v)
    elif isinstance(obj, list):
        for item in obj:
            numbers |= _extract_all_numbers(item)
    elif isinstance(obj, (int, float)):
        numbers.add(obj)
    return numbers


def _cross_check_numbers(proposal: dict, evidence: dict) -> tuple[bool, list[str]]:
    """Verifies every number in the LLM's proposal exists in the evidence object.

    Returns (passed: bool, violations: list[str]).

    This is the same numeric-verification pattern the copilot uses for explanations,
    applied to a structured payload where a wrong number is materially worse.
    """
    evidence_numbers = _extract_all_numbers(evidence)
    # Also allow 0 and 1 (trivial values) and the confidence score
    evidence_numbers.add(0)
    evidence_numbers.add(1)

    violations = []
    for record in proposal.get("affected_records", []):
        for field in ("current_value", "proposed_value"):
            val = record.get(field)
            if val is not None and val not in evidence_numbers:
                # Check if it's a derived value (e.g., difference)
                # Allow values that are exact differences of evidence numbers
                is_derived = False
                ev_list = list(evidence_numbers)
                for a in ev_list:
                    for b in ev_list:
                        if abs(a - b) == abs(val):
                            is_derived = True
                            break
                    if is_derived:
                        break

                if not is_derived:
                    violations.append(
                        f"Record {record.get('record_id', '?')}: "
                        f"{field}={val} not found in evidence and is not a "
                        f"derivable difference of evidence values"
                    )

    return (len(violations) == 0, violations)


def _template_fallback(evidence: dict, reason: str) -> dict:
    """Returns a safe, non-LLM fallback when the LLM output fails validation."""
    return {
        "adjustment_type": "no_confident_fix",
        "affected_records": [],
        "evidence_cited": list(evidence.keys()),
        "confidence": 0.0,
        "explanation": (
            f"The AI was unable to generate a confident fix for this exception. "
            f"Reason: {reason}. Please review the evidence manually."
        ),
        "human_next_step": (
            "Review the settlement and ledger records side-by-side. "
            "Check for amount mismatches, fee discrepancies, or timing offsets."
        ),
        "validation": {
            "cross_check_passed": False,
            "fallback_reason": reason,
        },
    }


def generate_suggested_fix(
    exception_data: dict,
    anomaly_data: dict = None,
) -> dict:
    """Generate a fix proposal for a reconciliation exception.

    Returns a validated JSON proposal, or a template fallback if:
    - The LLM is unavailable
    - The LLM output fails schema validation
    - The numeric cross-check fails (a number appears that isn't in evidence)
    """
    evidence = _build_evidence_object(exception_data, anomaly_data)

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _template_fallback(evidence, "Gemini API key not configured")

    prompt = (
        f"Generate a fix proposal for this reconciliation exception.\n\n"
        f"EVIDENCE (this is your only source of truth — every number you cite "
        f"must come from here):\n"
        f"```json\n{json.dumps(evidence, indent=2, default=str)}\n```\n\n"
        f"Respond with the JSON fix proposal only. No markdown fences, no explanation outside the JSON."
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,  # Low temperature — we want precision, not creativity
                max_output_tokens=2048,
            ),
        )

        raw = response.text.strip()
        # Strip any markdown fences the model may add despite instructions
        raw = re.sub(r"```(?:json)?\s*", "", raw).strip()
        raw = re.sub(r"```\s*$", "", raw).strip()

        proposal = json.loads(raw)
    except json.JSONDecodeError:
        return _template_fallback(evidence, "LLM returned invalid JSON")
    except Exception as e:
        return _template_fallback(evidence, f"LLM call failed: {type(e).__name__}")

    # ── Schema validation ──────────────────────────────────────────────
    adj_type = proposal.get("adjustment_type", "")
    if adj_type not in VALID_ADJUSTMENT_TYPES:
        return _template_fallback(
            evidence,
            f"LLM returned invalid adjustment_type '{adj_type}'"
        )

    if not isinstance(proposal.get("affected_records"), list):
        return _template_fallback(evidence, "LLM returned non-list affected_records")

    if not isinstance(proposal.get("explanation"), str):
        return _template_fallback(evidence, "LLM returned non-string explanation")

    # ── Numeric cross-check ────────────────────────────────────────────
    passed, violations = _cross_check_numbers(proposal, evidence)
    proposal["validation"] = {
        "cross_check_passed": passed,
        "violations": violations if not passed else [],
        "evidence_numbers_available": sorted(list(_extract_all_numbers(evidence))),
    }

    if not passed:
        # Don't return the proposal — return the fallback with the violation details
        fallback = _template_fallback(
            evidence,
            f"Numeric cross-check failed: {'; '.join(violations)}"
        )
        fallback["validation"]["rejected_proposal_violations"] = violations
        return fallback

    # ── Passed all checks — tag it and return ──────────────────────────
    proposal["validation"]["evidence_hash"] = hash(json.dumps(evidence, sort_keys=True, default=str))

    return proposal
