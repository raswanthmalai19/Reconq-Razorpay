# ARCHITECTURE.md

## System diagram

```
                    Streamlit Dashboard
                    (upload/sample, KPIs, drill-down, audit, export)
                                |
                                v
        Ingestion & Validation  -->  Matching Engine  -->  Storage/Audit (SQLite)
        (schema check,               exact -> bucket ->
         normalize to paise/ISO)      group -> confidence ->
                                      Hungarian assignment
                                          |
                                          v
                              Risk-Weighted Threshold Policy
                              (amount-banded lookup, no AI)
                                          |
                          human-review / unresolved only
                                          v
                              LLM Evidence Layer
                              (forced tool schema, numeric cross-check)
                                          |
                                          v
                                  Report / Export (CSV)

Parallel, offline only: Naive fixed-threshold baseline (same confidence
model, single global cutoff) -- runs only inside eval/harness.py to produce
the comparison metric, never in the live dashboard path.
```

## Component-by-component

- **Ingestion & Validation** (`engine/ingestion.py`, `engine/normalize.py`) — rejects malformed CSVs with a specific named-column error; converts all amounts to integer paise (never floats) and dates to Python `date` objects.
- **Exact-key matching** (`engine/exact_match.py`) — extracts an `INV-####` style reference from the settlement narration, hash-joins against ledger invoice IDs, and clears any match within ±₹1 at confidence 1.0.
- **Bucketing** (`engine/blocking.py`) — buckets remaining records by (date ± 3 days) × (amount ± 15% band, floored at ₹50) so later steps never do O(n²) comparison. A row can appear in multiple overlapping buckets so a boundary case still finds its counterpart.
- **Split/merge detection** (`engine/group_matching.py`) — a bounded subset-sum search (group size ≤ 4, ≤20 candidates considered per bucket) looks for N ledger rows summing to one settlement row, or vice versa, within a ₹2 tolerance.
- **Feature engineering** (`engine/features.py`) — 5 features per candidate pair: `amount_delta_pct`, `date_delta_days`, `narration_similarity` (RapidFuzz token-sort), `reference_similarity` (RapidFuzz partial-ratio), `is_fee_pattern`.
- **Confidence model** (`engine/confidence_model.py`, `engine/train.py`) — a `LogisticRegression` trained on features from bucketed candidate pairs, self-labeled from the synthetic ground truth (true pair = positive, every other same-bucket pair = hard negative). 60/20/20 train/val/test split, `random_state=42`.
- **Assignment** (`engine/assignment.py`) — builds a **single global** cost matrix (cost = 1 − confidence) over all remaining settlements × ledgers, restricted to candidate pairs surfaced by bucketing (non-candidates get a sentinel cost), and solves with `scipy.optimize.linear_sum_assignment`. This is deliberately global, not per-bucket, so a row appearing in several overlapping buckets still can't be double-claimed.
- **Risk-weighted policy** (`engine/risk_policy.py`) — pure lookup table, no AI: required confidence rises from 0.75 (≤₹1,000) to 0.97 (>₹1,00,000). Below 0.40 at any amount → `UNRESOLVED`, never guessed.
- **Naive baseline** (`engine/naive_baseline.py`) — the same trained model, one fixed 0.85 cutoff — used only by `eval/harness.py` to produce the measured comparison.
- **LLM evidence layer** (`llm/client.py`, `llm/schema.py`, `llm/system_prompt.txt`) — Claude, `tool_choice` forced to a single schema, called only for `HUMAN_REVIEW`/`UNRESOLVED` pairs. Every digit sequence in the returned explanation is cross-checked against the evidence object; a mismatch discards the explanation and substitutes a safe template, flagged `explanation_rejected=true`. Falls back to a deterministic template with zero crash risk whenever `ANTHROPIC_API_KEY` is unset or the API call fails for any reason.
- **Injection guard** (`llm/injection_guard.py`) — a regex pre-filter flags obvious prompt-injection markers in narration/memo text before it reaches the LLM prompt; the system prompt additionally instructs the model to treat all narration/memo text as untrusted data, never as commands.
- **Audit log** (`engine/audit_log.py`) — append-only SQLite tables (`audit_log`, `overrides`); no UPDATE/DELETE route exists anywhere in the code.
- **Dashboard** (`dashboard/app.py`) — Streamlit: staged processing view, KPI cards, record table, exception drill-down with Accept/Override, audit log view, CSV export.

## One record traced end to end (a real `HUMAN_REVIEW` case from the evaluation run)

Settlement `STL-100125` (₹4,14,477) is bucketed against ledger `INV-2125` on date/amount proximity. `compute_features` yields a confidence of 0.9555 from the trained model — high, but not certain. `engine/risk_policy.decide(amount_paise=41447700, confidence=0.9555)` looks up the >₹1,00,000 band, which requires ≥0.97 — 0.9555 falls short, so the record is `HUMAN_REVIEW`, not `AUTO_MATCHED`. The naive baseline (`engine/naive_baseline.naive_decide`), given the identical 0.9555 confidence, only needs ≥0.85 and auto-clears it. Both facts are recorded in `eval/report.md`'s "Signature Moment" table. In the dashboard, this record surfaces in the Exception Drill-Down tab with an LLM (or template) explanation and Accept/Override buttons.

## Design decisions & tradeoffs

- **Logistic regression, not a deep model** — 5 numeric features and a few hundred labeled synthetic rows is exactly right-sized for logistic regression; a bigger model would add overfitting risk with no accuracy benefit at this scale.
- **Streamlit, not React** — fastest path to a working, demoable UI without frontend engineering risk in a 4-day build.
- **SQLite, not Postgres** — zero setup, matches this MVP's scale; a future Postgres swap is a connection-string change via SQLAlchemy.
- **Claude with forced tool-use, not a bigger/pricier model** — the task is bounded classification-plus-short-explanation over pre-computed features, not open-ended reasoning; the hard schema guarantee from forced `tool_choice` matters more here than raw model capability.
- **Global Hungarian assignment, not per-bucket** — bucketing is only used to restrict which pairs are considered (for performance); the actual 1:1 assignment must be solved once, globally, or a row present in two overlapping buckets could be assigned twice.

## What's implemented now vs. future architecture

Implemented: everything in the diagram above. **Not implemented, named as future work only:** a live Razorpay Settlements API ingestion adapter (would require a real merchant account with real settlement history, which we do not have); an active-learning loop that retrains the confidence model from human overrides; multi-currency/multi-format auto-detection.
