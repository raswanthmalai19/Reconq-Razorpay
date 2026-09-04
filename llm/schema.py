from typing import List, Literal
from pydantic import BaseModel, Field

class ReconciliationVerdict(BaseModel):
    category: Literal[
        "timing_difference", "fee_or_rounding", "partial_refund",
        "duplicate", "split_or_merged", "incorrect_reference",
        "genuinely_missing", "unclear"
    ]
    confidence_in_category: float = Field(ge=0, le=1)
    explanation: str = Field(max_length=240)
    recommended_action: Literal[
        "auto_clear_safe", "route_to_human_review",
        "escalate_high_value", "flag_possible_duplicate",
        "no_action_insufficient_evidence"
    ]
    cites_evidence_fields: List[str]

RECONCILIATION_VERDICT_TOOL = {
    "name": "reconciliation_verdict",
    "description": "Structured verdict for one reconciliation exception, based only on the supplied computed evidence.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": [
                    "timing_difference", "fee_or_rounding", "partial_refund",
                    "duplicate", "split_or_merged", "incorrect_reference",
                    "genuinely_missing", "unclear",
                ],
            },
            "confidence_in_category": {"type": "number", "minimum": 0, "maximum": 1},
            "explanation": {"type": "string", "maxLength": 240},
            "recommended_action": {
                "type": "string",
                "enum": [
                    "auto_clear_safe", "route_to_human_review",
                    "escalate_high_value", "flag_possible_duplicate",
                    "no_action_insufficient_evidence",
                ],
            },
            "cites_evidence_fields": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["category", "confidence_in_category", "explanation",
                      "recommended_action", "cites_evidence_fields"],
    },
}
