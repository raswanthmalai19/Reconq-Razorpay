# SECURITY.md

## Threat model and mitigations

| Threat | Mitigation |
|---|---|
| Malicious/adversarial narration or memo text (prompt injection) | Always treated as plain data, never `eval`'d or executed. `llm/injection_guard.py` pre-filters known injection markers before the text reaches any prompt. The system prompt (`llm/system_prompt.txt`) explicitly instructs the model to ignore embedded instructions in narration/memo fields. |
| LLM fabricating a number not supported by evidence | Every digit sequence in the LLM's `explanation` is parsed and cross-checked against the actual evidence object (`llm/client.py::_extract_numbers` / `_evidence_numbers`); a mismatch discards the explanation and substitutes a safe deterministic template, flagged `explanation_rejected=true`. |
| LLM returning free-form text instead of a structured verdict | `tool_choice` is forced to the single `reconciliation_verdict` tool (`llm/schema.py`) — the model cannot return plain prose. |
| Malformed/adversarial CSV input | Strict schema validation (`engine/ingestion.py`) rejects a file immediately, naming the specific missing/invalid column, before any processing begins. |
| A false auto-match (money reconciled to the wrong invoice) | The risk-weighted policy requires higher confidence as amount grows (up to 0.97 above ₹1,00,000); anything below 0.40 confidence at any amount is `UNRESOLVED`, never guessed into a status. |
| Component failure (LLM unreachable, missing model file, malformed row) | Every failure path degrades to `HUMAN_REVIEW` or `UNRESOLVED` — never a silent auto-match. `predict_confidence(model=None, ...)` explicitly returns `0.0`, which routes below every risk band. |
| Secrets exposure | `ANTHROPIC_API_KEY` is read from the environment only; `.env` is gitignored; `.env.example` ships with a placeholder; the key is never logged and never written into the audit trail payload. |
| Silent data tampering after a decision is made | The audit log (`engine/audit_log.py`) is append-only — no UPDATE/DELETE route exists anywhere in the codebase. Human Accept/Override actions are recorded as new rows, never as edits. |
| Autonomous money movement | ReconQ never calls any payment or settlement API and never writes to an external ledger. A human's Accept/Override click only updates an internal status field in the local SQLite database. |

## No production credentials anywhere

This project makes no live payment calls at all — it reconciles synthetic CSVs against a synthetic ledger. There is no Razorpay API key, no signing secret, and no live credential of any kind in this codebase. The only optional credential is `ANTHROPIC_API_KEY`, used solely for narrating already-made decisions.

## Data privacy

100% synthetic, seeded data (`random.seed(42)` in `data/generate_data.py`). No real PII, no real merchant data, no real payment instruments anywhere in this repository.

## Fail-safe principle (binding, checked in `tests/test_risk_policy.py` and `tests/test_confidence_model.py`)

No code path may silently authorize an auto-match. Every uncertain or failed state routes to `HUMAN_REVIEW` or `UNRESOLVED`.
