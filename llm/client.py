"""Evidence-only LLM explanation layer.

The LLM never sees a blank slate and never decides a match -- it only
narrates a decision the deterministic engine + confidence model already made,
using a forced tool schema, with every number in its explanation cross-checked
against the evidence object afterward. On any failure (no API key, network
error, schema violation, numeric fabrication) it falls back to a safe
template -- the reconciliation numbers themselves are never affected.
"""
import os
import re

from llm.injection_guard import scan_text
from llm.schema import RECONCILIATION_VERDICT_TOOL

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_prompt.txt")
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")


def _load_system_prompt() -> str:
    with open(SYSTEM_PROMPT_PATH) as f:
        return f.read()


def _template_verdict(evidence: dict, reason: str) -> dict:
    """Deterministic, always-safe fallback -- never fabricates a number."""
    amt_pct = evidence.get("amount_delta_pct", 0)
    category = "fee_or_rounding" if 0 < amt_pct < 0.05 else "unclear"
    return {
        "category": category,
        "confidence_in_category": 0.5,
        "explanation": f"Rule-based summary ({reason}): amounts differ, dates differ, "
                        f"routed for human review since AI explanation is unavailable.",
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
                nums.add(str(round(v * 100)))  # percentage rendering, e.g. 0.02 -> "2"
                nums.add(str(round(v * 100, 1)))
    return nums


def explain(evidence: dict, narration_a: str = "", narration_b: str = "") -> dict:
    """evidence: dict of already-computed values (amount_delta_pct, date_delta_days,
    narration_similarity, reference_similarity, confidence_score, amount_inr).
    Returns a verdict dict matching the reconciliation_verdict tool schema, plus
    explanation_rejected/source bookkeeping fields.
    """
    injected_a = scan_text(narration_a)
    injected_b = scan_text(narration_b)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return _template_verdict(evidence, "no API key configured")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        user_content = (
            f"EVIDENCE = {evidence}\n"
            f"untrusted_text_a = {narration_a!r}\n"
            f"untrusted_text_b = {narration_b!r}"
        )
        resp = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=300,
            system=_load_system_prompt(),
            tools=[RECONCILIATION_VERDICT_TOOL],
            tool_choice={"type": "tool", "name": "reconciliation_verdict"},
            messages=[{"role": "user", "content": user_content}],
        )
        tool_use = next((b for b in resp.content if b.type == "tool_use"), None)
        if tool_use is None:
            return _template_verdict(evidence, "LLM returned no tool call")

        verdict = dict(tool_use.input)
        verdict["explanation_rejected"] = False
        verdict["source"] = "llm"

        claimed_numbers = _extract_numbers(verdict.get("explanation", ""))
        allowed_numbers = _evidence_numbers(evidence)
        fabricated = claimed_numbers - allowed_numbers
        if fabricated:
            fallback = _template_verdict(evidence, "numeric cross-check failed")
            fallback["explanation_rejected"] = True
            fallback["category"] = verdict.get("category", fallback["category"])
            fallback["recommended_action"] = verdict.get("recommended_action", fallback["recommended_action"])
            return fallback

        if injected_a or injected_b:
            verdict["injection_marker_detected"] = True
        return verdict

    except Exception as exc:  # noqa: BLE001 -- any LLM failure must degrade safely
        fallback = _template_verdict(evidence, f"LLM call failed ({type(exc).__name__})")
        return fallback
