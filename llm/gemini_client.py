"""Gemini-powered explanation client for ReconQ.

Uses the Chat API (as recommended by the SDK) for full-length responses.
Evidence-only architecture: the LLM sees only the reconciliation features,
never raw narration that could cause hallucination of specific amounts.
Numeric cross-check: any numbers the LLM mentions must appear in the evidence.
"""
import os
import re
import json
from google import genai
from google.genai import types

from llm.injection_guard import scan_text

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_prompt.txt")

EXPLANATION_SYSTEM = (
    "You are a financial reconciliation expert. Given reconciliation evidence between a payment gateway "
    "settlement and an internal ledger entry, you produce a concise JSON analysis.\n\n"
    "RULES:\n"
    "1. Only reference numbers that appear in the EVIDENCE — never invent figures.\n"
    "2. Keep explanation under 200 characters.\n"
    "3. Return ONLY valid JSON — no markdown, no preamble.\n"
    "4. Choose category from: timing_difference, fee_or_rounding, partial_refund, duplicate, "
    "split_or_merged, incorrect_reference, genuinely_missing, unclear\n"
    "5. Choose recommended_action from: auto_clear_safe, route_to_human_review, "
    "escalate_high_value, flag_possible_duplicate, no_action_insufficient_evidence\n\n"
    "RETURN exactly this JSON structure:\n"
    '{"category": "...", "confidence_in_category": 0.0, "explanation": "...", '
    '"recommended_action": "...", "cites_evidence_fields": ["..."]}'
)


def _load_system_prompt() -> str:
    try:
        with open(SYSTEM_PROMPT_PATH) as f:
            return f.read()
    except FileNotFoundError:
        return EXPLANATION_SYSTEM


def _template_verdict(evidence: dict, reason: str) -> dict:
    """Deterministic, always-safe fallback — never fabricates a number."""
    amt_pct = evidence.get("amount_delta_pct", 0)
    category = "fee_or_rounding" if 0 < amt_pct < 0.05 else "unclear"
    return {
        "category": category,
        "confidence_in_category": 0.5,
        "explanation": f"Rule-based fallback ({reason}): amounts differ, routed for human review.",
        "recommended_action": "route_to_human_review",
        "cites_evidence_fields": ["amount_delta_pct", "date_delta_days"],
        "explanation_rejected": False,
        "source": "template_fallback",
    }


def _extract_numbers(text: str):
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def _evidence_numbers(evidence: dict):
    nums = set()
    for v in evidence.values():
        if isinstance(v, (int, float)):
            nums.add(str(v))
            if isinstance(v, float):
                nums.add(f"{v:.2f}")
                nums.add(f"{v:.1f}")
                nums.add(str(round(v * 100)))
                nums.add(str(round(v * 100, 1)))
    return nums


def gemini_explain(evidence: dict, narration_a: str = "", narration_b: str = "") -> dict:
    """Generate an evidence-grounded explanation using Gemini chat API."""
    _ = scan_text(narration_a)  # injection guard — discard injected content
    _ = scan_text(narration_b)

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _template_verdict(evidence, "no API key configured")

    try:
        client = genai.Client(api_key=api_key)
        chat = client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction="You are a JSON API. Return ONLY valid JSON. No text before or after.",
                max_output_tokens=8192,
                temperature=0,
            ),
        )
        user_content = (
            f"Evidence: {json.dumps(evidence)}\n"
            "Return exactly this JSON (fill in the values based on the evidence):\n"
            '{"category": "fee_or_rounding", "confidence_in_category": 0.85, '
            '"explanation": "...", "recommended_action": "route_to_human_review", '
            '"cites_evidence_fields": ["amount_delta_pct"]}'
        )
        response = chat.send_message(user_content)
        raw = response.text or ""

        # Strip markdown code fences if present
        raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()

        verdict = json.loads(raw)
        verdict["explanation_rejected"] = False
        verdict["source"] = "llm"

        # Numeric cross-check
        claimed = _extract_numbers(verdict.get("explanation", ""))
        allowed = _evidence_numbers(evidence)
        fabricated = claimed - allowed

        if fabricated:
            fallback = _template_verdict(evidence, "numeric cross-check failed")
            fallback["explanation_rejected"] = True
            fallback["category"] = verdict.get("category", fallback["category"])
            fallback["recommended_action"] = verdict.get("recommended_action", fallback["recommended_action"])
            return fallback

        return verdict

    except json.JSONDecodeError:
        return _template_verdict(evidence, "invalid JSON from LLM")
    except Exception as exc:
        return _template_verdict(evidence, f"LLM call failed ({type(exc).__name__})")
