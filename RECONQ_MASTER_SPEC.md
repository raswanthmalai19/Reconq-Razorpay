# RECONQ_MASTER_SPEC.md
## ReconQ — Risk-Weighted Reconciliation Agent
### Razorpay AI Buildathon 2026 — Track 04: AI Finance Controller

**Status: BUILD COMPLETE.** All MUST-BUILD scope from §5 is implemented, tested (16/16 `pytest` passing), and evaluated (`eval/report.md` has real, reproducible numbers). This document remains the single source of truth for design rationale.

**Today: Tue Sep 1, 2026. Deadline: applications close Fri Sep 5, 2026.** That is **4 real build days** (Sep 1–4), submit Sep 5. The previous draft of this idea (`ReconIQ_Build_Specification-1.md`, now deleted) assumed a 6-day window starting Aug 30 — that assumption is stale and has been corrected everywhere in this document. Everything else useful from that draft is carried forward, tightened, and re-verified against the actual constraint.

The Bridle / agentic-commerce project (Track 01) has been **fully deleted** from this workspace per your decision. This is a clean-slate, single-project workspace. Product name is **ReconQ** (not ReconIQ).

---

## 1. Executive Summary

**Problem:** Merchant finance/ops teams reconcile a payment gateway's settlement report against their internal ledger by hand or with brittle exact-match scripts. Mismatches (fees, timing gaps, partial refunds, duplicates, split/merged settlements, corrupted references) need judgment. Existing tools — and the obvious first-draft hackathon answer — apply one match/no-match confidence bar to every transaction regardless of size. A ₹200 mismatch and a ₹4,00,000 mismatch at the same 90% confidence do not carry the same risk if the system is wrong, and treating them identically is the clearest tell of a project that hasn't thought about the actual cost of an error.

**The core product insight (the thing worth building around):**

> The cost of a wrong auto-match scales with the money involved. So the bar for "safe to auto-clear" should scale too — not be one fixed number.

**What ReconQ is:** a reconciliation engine that (1) matches settlement records to ledger records using deterministic exact-matching first, then bucketed fuzzy candidates, then a **bounded subset-sum search for split/merged transactions**, (2) scores every remaining candidate pair with a **trained logistic-regression confidence model**, (3) resolves 1:1 assignment with the **Hungarian algorithm** so no record is double-claimed, (4) applies a **risk-weighted (amount-banded) threshold policy** to decide AUTO_MATCHED / HUMAN_REVIEW / UNRESOLVED, and (5) generates an **evidence-only LLM explanation** for the review/unresolved minority, with a **numeric-fabrication cross-check** so the LLM can never invent a number that isn't in the evidence it was given.

**What ReconQ explicitly is not:** an LLM that reads two CSVs and free-associates a report. The LLM never touches the matching decision. It only narrates a decision the deterministic engine + trained classifier already made, for the minority of ambiguous cases, and only using numbers that are independently verified afterward.

---

## 2. Honesty Ground Rules (binding for this entire build)

These apply to every phase from here forward, not just this document:

- **Never fabricate metrics.** Every number in the final evaluation report must come from actually running the harness against held-out ground truth. Until the harness runs, every metrics table in this document is *labeled as a target*, not a result.
- **Never claim novelty without checking.** Risk-weighted/amount-banded auto-approval thresholds are a known pattern in fraud/AML and credit-risk systems generally (tiered review, aka "step-up" authorization) — this is **not** a claim to have invented the concept. The claim, precisely stated, is: *most reconciliation-focused hackathon submissions on this exact track are unlikely to implement it*, which is an inference about competitive positioning, not a claim of academic originality. Labeled `[INFERENCE]` wherever it appears.
- **Never claim Razorpay needs something unless evidence supports it.** Any statement about what Razorpay does/doesn't already have is labeled `[VERIFIED]` (fetched from an official source), `[INFERENCE]` (reasoned but not directly confirmed), or `[UNKNOWN]` (not checked). No unlabeled claims about Razorpay's internal tooling.
- **Never use AI merely to make the project look like AI.** Exact-key matching, bucketing, and the auto/review/unresolved decision are deliberately plain deterministic code — stated explicitly in the pitch as a strength, not hidden.
- **Never build unnecessary infrastructure.** No Kubernetes, no message queue, no vector DB, no multi-tenant auth, no cloud deployment. SQLite + a single-process app is the right scale for this MVP and the judging bar ("repo + video").
- **Never sacrifice correctness for complexity.** Logistic regression over 5 engineered features, not a deep model, because the labeled data is a few hundred rows and a bigger model would only add overfitting risk with no accuracy benefit at this scale.
- **Never sacrifice demo reliability for features.** The system must fully run and demo with **zero external API keys** (LLM calls degrade to template explanations; there is no payments API dependency in this project at all — see §3).
- **Never use production payment credentials.** N/A directly (ReconQ makes no live payment calls — it reconciles already-settled records from CSVs), but stated for completeness: nothing in this system ever touches a live key.
- **Never allow real autonomous money movement.** ReconQ never writes back to any ledger, never triggers a payment, never moves money. A human's Accept/Override click only updates an internal status field.
- **Never stop at planning.** Plan → build → test → evaluate → document, all the way through, in this same engagement.
- **If the original idea is weak, change it. If a feature is unnecessary, remove it. If a simpler implementation is stronger, use it. Prefer measured evidence over claims.** These are standing instructions for every remaining decision in this build.

---

## 3. Research Findings — What's Actually Verified vs. Inferred

**[VERIFIED — from Razorpay's own Track 04 framing, as captured in the original brief research]:** The AI Finance Controller track exists because "verification capacity, not generation speed, is the real bottleneck" for finance/ops teams, and "multi-source reconciliation" is named as an example direction. This is a direct, stated match for what ReconQ builds — no interpretation or stretch needed to justify track fit.

**[VERIFIED — general Razorpay developer convention, not specific to this track]:** Razorpay issues a Settlements API and settlement reports in production for real merchants; a Settlements API integration is realistic future work, not part of this MVP (no live credentials are available or needed — §3 of the MVP scope below runs entirely on synthetic CSVs).

**[UNKNOWN]:** Whether any other Track 04 submission implements amount-banded auto-match thresholds, split/merge detection via bounded subset-sum, or a naive-baseline comparison. No competing repos were found or searched for this track (unlike Track 01, where three were found). This is stated as `[UNKNOWN]`, not claimed as "no competition exists" — that would be an unverifiable claim.

**[INFERENCE]:** A "two CSVs in, fuzzy-match, LLM narrates" submission is a plausible default answer many applicants will independently arrive at, because it's the literal example direction named in the brief. This is reasoning about incentive structure, not a verified fact about actual submissions.

**What this means for scope:** the differentiation strategy is not "nobody else could think of this" — it's "the specific mechanisms (bounded subset-sum group matching, a trained-not-hand-tuned confidence model, a held-out precision/recall table, a numeric-fabrication check, and a measured naive-baseline comparison) are genuinely more implementation work than a top-level description suggests, and are the parts most time-constrained builds skip." That claim is checkable by anyone who reads the code and the evaluation report — which is the point.

---

## 4. Product Definition

| | |
|---|---|
| **Product name** | **ReconQ** |
| **One-line pitch** | ReconQ reconciles settlements against ledgers automatically, but raises the bar for auto-clearing a match exactly as much as the money at stake demands — instant on routine cases, human-gated on high-value or structurally ambiguous ones, every decision explained and logged. |
| **Target user** | A merchant finance/ops analyst reconciling gateway settlements against internal books; equally applicable to an internal Razorpay settlement-ops team reconciling across rails. |
| **Problem today** | Export both files → Excel/VLOOKUP → eyeball discrepancies → manually chase each one → no consistent policy for what's "safe" → redone from scratch every cycle, no institutional memory. |
| **What's different** | Three concrete mechanisms, no more: (1) risk-weighted (amount-banded) auto-match threshold instead of one fixed number, (2) bounded subset-sum split/merge group detection instead of 1:1-only matching, (3) evidence-only LLM explanation layer with a numeric-fabrication cross-check instead of free-form LLM narration. |
| **Where AI is genuinely used** | A small trained classifier (logistic regression) converts match features into a calibrated probability, replacing hand-tuned weights; an LLM (evidence-only, forced schema) explains and categorizes the human-review/unresolved minority. |
| **Where AI is explicitly NOT used** | The matching decision for the majority of records (exact-key + bucketed candidates = deterministic code, a hash join and a lookup table, not a model). Saying this plainly, out loud, is a stated strength of the design, not a gap. |
| **Success condition** | Pipeline runs end-to-end on a synthetic labeled set, produces a real (not cherry-picked) precision/recall table against held-out ground truth, and the risk-weighted policy visibly makes a different call than a fixed-threshold baseline on at least one high-value example — measured, not asserted. |
| **Failure condition (what must never happen)** | Any component failing *open* — i.e., silently auto-matching something it shouldn't. Every uncertain/failed code path routes to human review or unresolved, never to an auto-match. |

---

## 5. MVP Scope

### MUST BUILD
- Synthetic data generator, seeded (`random.seed(42)`), producing a settlement-report CSV + internal-ledger CSV with 8 labeled mismatch classes and a held-out `ground_truth.csv` the engine never sees.
- Deterministic exact-key matching (hash join) — clears the majority of records at confidence 1.0, instantly.
- Candidate bucketing (date-window + amount-band) so later steps never do O(n²) comparison.
- Bounded subset-sum split/merge group detection (group size ≤ 4).
- Feature engineering (5 features) + trained logistic-regression confidence scorer, self-labeled from the synthetic ground truth, with a real held-out 60/20/20 train/val/test split.
- Hungarian optimal 1:1 assignment (`scipy.optimize.linear_sum_assignment`) over the remaining candidate pairs.
- Risk-weighted (amount-banded) threshold policy: AUTO_MATCHED / HUMAN_REVIEW / UNRESOLVED.
- Naive fixed-threshold baseline agent (same confidence model, single global threshold, no amount-banding) — built specifically to produce a measured comparison, not just described.
- Evidence-only LLM explanation layer (Claude, forced tool schema) with a **post-hoc numeric cross-check**: every digit sequence in the explanation must appear verbatim in the evidence object, or the explanation is discarded and replaced with a safe template, flagged in the audit log.
- Injection-guard pre-filter on narration/memo text before it ever reaches the LLM prompt.
- Full append-only audit log (every match, decision, override, LLM verdict, rejected-explanation event).
- Evaluation harness: runs the full pipeline against the labeled set, computes precision/recall/false-match-rate/false-unmatch-rate/etc., and the naive-baseline comparison — writes a real `eval/report.md`.
- Streamlit dashboard: upload/sample-data, staged processing view, KPI cards, record table with status badges, exception drill-down (Accept/Override), audit log view, CSV export.
- `pytest` suite: matching engine correctness, confidence model sanity, LLM schema validator, risk policy monotonicity.
- Documentation: `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `EVALUATION.md`, this master spec kept accurate throughout.

### SHOULD BUILD (only once MUST is fully green)
- A second synthetic dataset "flavor" (e.g., subscriptions) to show the approach generalizes beyond one schema.
- A thin FastAPI layer in front of the engine, so the dashboard calls HTTP endpoints instead of importing Python directly (stronger "would you trust it" signal) — optional, not required for the core story.

### ONLY IF TIME REMAINS
- PDF export in addition to CSV.
- React/Tailwind frontend instead of Streamlit.
- A 5,000+ record stress-test run reporting wall-clock time only (never mixed with the accuracy claims from the 150-record labeled set).

### EXPLICITLY DO NOT BUILD
- Any live Razorpay API integration (Settlements API access requires a real merchant account with real settlement history — not available, not needed for this MVP; named as future work only).
- Any autonomous write-back to an external ledger.
- Multi-tenant auth, user accounts, public deployment.
- Kubernetes, message queues, vector databases, microservices.
- Fine-tuning any model.

---

## 6. Non-Functional Requirements

- **Fail-safe by construction:** any component failure (LLM unreachable, malformed input row, a subset-sum search that would blow up on an oversized bucket) degrades to HUMAN_REVIEW or UNRESOLVED, never to a silent AUTO_MATCHED. No code path may guess its way into an auto-match.
- **Reproducibility:** the synthetic generator is seeded; a judge who clones the repo and re-runs it gets the same evaluation numbers.
- **Portability:** the full pipeline and dashboard run with zero external credentials — `ANTHROPIC_API_KEY` absent means template-based explanations, not a crash.
- **Data integrity:** amounts are stored and compared as integer paise, never floats, to avoid rounding-drift bugs.
- **Auditability:** the audit log is append-only — no UPDATE/DELETE route exists anywhere in the code path.
- **Latency:** the deterministic engine (exact match → bucketing → group detection → confidence scoring → assignment → policy) must never depend on an LLM call being on its critical path; the LLM only narrates after the decision is already made.
- **Testability:** the matching engine, confidence model, and LLM schema validator all have unit tests runnable with plain local `pytest`, no network required.
- **Data privacy:** 100% synthetic data, no real PII, no real merchant data, ever.

---

## 7. System Architecture

```
                    ┌───────────────────────┐
                    │  Streamlit Dashboard   │
                    │ (upload, KPIs, drill-  │
                    │  down, audit, export)  │
                    └───────────┬────────────┘
                                │ direct Python calls (MVP) /
                                │ HTTP (should-build FastAPI layer)
       ┌────────────────────────┼─────────────────────────┐
       │                        │                          │
┌──────▼───────┐      ┌─────────▼─────────┐      ┌─────────▼─────────┐
│  Ingestion &  │      │  Matching Engine   │      │  Storage / Audit   │
│  Validation   │─────▶│  exact → bucket →  │─────▶│      (SQLite)      │
│ (schema check,│      │  group → confidence│      │ runs / records /   │
│  normalize)   │      │  → Hungarian assign│      │ evidence / audit   │
└───────────────┘      └─────────┬─────────┘      └─────────▲─────────┘
                                  │                           │
                        ┌─────────▼─────────┐                 │
                        │  Risk-Weighted     │                 │
                        │  Threshold Policy  │                 │
                        │ (amount-banded)    │                 │
                        └─────────┬─────────┘                 │
                         human-review / unresolved only         │
                        ┌─────────▼─────────┐                   │
                        │  LLM Evidence Layer │────────────────────┘
                        │ (Claude, forced tool│
                        │ schema, numeric     │
                        │ cross-check)        │
                        └─────────┬─────────┘
                                  │
                        ┌─────────▼─────────┐
                        │ Report / Export     │
                        │   (CSV)             │
                        └────────────────────┘

Parallel, offline: Naive fixed-threshold baseline agent (same confidence
model, single global cutoff) — run only inside the evaluation harness,
never in the live dashboard path, to produce the comparison number.

NOT IN MVP: live Settlements API ingestion; active-learning retraining
loop from human overrides; multi-currency/format auto-detection.
```

**Component responsibilities:**
- **Ingestion & Validation** — rejects malformed files immediately with a specific error; normalizes amounts to integer paise and dates to ISO format.
- **Matching Engine** — the deterministic core. Exact-key matches clear instantly at confidence 1.0. Everything else is bucketed by date-window + amount-band. Group detection runs a bounded subset-sum search inside each bucket for split/merge cases. Hungarian assignment guarantees a globally consistent 1:1 mapping for whatever's left.
- **Confidence Model** — only touches candidates that survive bucketing; converts 5 engineered features into a calibrated match probability.
- **Risk-Weighted Threshold Policy** — pure lookup logic, no AI; decides AUTO_MATCHED / HUMAN_REVIEW / UNRESOLVED as a function of both the confidence score and the transaction amount.
- **LLM Evidence Layer** — invoked only for the review/unresolved minority; narrates a decision already made, never makes one.
- **Storage/Audit** — append-only; the reconstructable record of everything the system did.
- **Naive baseline** — a separate, simpler decision function (same confidence model, one global threshold) run only inside the evaluation harness to produce the comparison metric.

---

## 8. Matching / Reconciliation Algorithm

**Pipeline, in order:**

1. **Normalization** — amounts → integer paise; dates → ISO date; reference strings → uppercase, punctuation/whitespace stripped; narration → lowercased for similarity comparison.
2. **Exact-key matching** — hash-index both sides on normalized reference id; a hit with amount within ±₹1 matches immediately at confidence 1.0 and is removed from further processing.
3. **Candidate bucketing** — remaining records bucketed by date (±3 days) AND amount (±15% band, with an absolute floor for very small amounts) so no later step compares every pair against every other pair.
4. **Group / split-merge detection** — within each bucket, a bounded subset-sum search (group size capped at 4, a capped number of candidate subsets considered per bucket) looks for N ledger rows summing to one settlement row, or vice versa, within a small rounding tolerance.
5. **Pairwise feature computation**, for remaining 1:1 candidates:
   - `amount_delta_pct` = |amount_a − amount_b| / amount_a
   - `date_delta_days` = |date_a − date_b|
   - `narration_similarity` = RapidFuzz `token_sort_ratio` / 100
   - `reference_similarity` = RapidFuzz `partial_ratio` / 100
   - `is_fee_pattern` = 1 if `amount_delta_pct` falls in a plausible gateway-fee band, else 0
6. **Confidence scoring** — the 5 features feed a trained `LogisticRegression`, output = P(true match).
7. **Optimal 1:1 assignment** — cost matrix (cost = 1 − confidence), solved via Hungarian algorithm within each bucket, guaranteeing no ledger row is claimed twice.
8. **Duplicate flagging** — a remaining record near-identical (same amount+date, reference off by ~1 character) to an already-matched record is flagged as a probable duplicate, not a fresh unmatched item.
9. **Risk-weighted decision** — apply the amount-banded threshold table (§10) to the final confidence.
10. **Fail-safe fallback** — anything the pipeline can't confidently place lands in UNRESOLVED, never AUTO_MATCHED.

---

## 9. Dataset Strategy

**No real Razorpay or merchant data anywhere.** Fully synthetic, seeded.

**`settlement_report.csv`:** `settlement_id, utr_reference, amount_inr(paise), settlement_date, fee_inr, tax_inr, narration, batch_id`

**`internal_ledger.csv`:** `invoice_id, customer_ref, amount_inr(paise), invoice_date, memo, status`

**8 labeled mismatch classes (target mix, ~150-record MVP set):**

| Class | Target share |
|---|---|
| Exact match | 65% |
| Fee / rounding difference | 10% |
| Timing difference (1–3 days) | 8% |
| Partial refund | 5% |
| Split or merged transaction | 4% |
| Duplicate entry | 3% |
| Genuinely missing (no counterpart) | 3% |
| Incorrect / corrupted reference | 2% |

`ground_truth.csv` is written separately and never read by the matching engine at inference time — used only for scoring. Train/val/test split for the confidence model is 60/20/20, stratified by class so rare classes appear in every split.

---

## 10. AI / Model Design — Exact Deterministic/ML/LLM Boundary

| Decision point | Approach | Why |
|---|---|---|
| Exact-key matching | Deterministic (hash join) | Free, instant, reproducible — an LLM here would be slower and non-deterministic for zero benefit |
| Candidate bucketing | Deterministic (indexing) | Pure performance optimization, not a judgment call |
| Split/merge detection | Algorithm (bounded subset-sum) | A combinatorial search problem, not a learning problem |
| Confidence scoring | **ML — logistic regression** | 5 numeric features, a few hundred labeled rows — right-sized, interpretable, low overfitting risk; a bigger model buys nothing at this data scale |
| Auto/review/unresolved decision | Deterministic (risk-weighted lookup) | A policy choice, not a prediction — a lookup table is auditable and tunable by a real finance team |
| Exception explanation & categorization | **LLM, evidence-only, forced schema** | Turning pre-verified numeric evidence into a short human-readable rationale is a genuine language task; a classifier can't write prose and a static template alone reads robotic on nuanced cases |

**Risk-weighted (amount-banded) policy — starting point, explicitly labeled as tunable, not fit from real loss data:**

| Transaction amount (₹) | Auto-match requires confidence ≥ |
|---|---|
| ≤ 1,000 | 0.75 |
| 1,000 – 25,000 | 0.85 |
| 25,000 – 1,00,000 | 0.93 |
| > 1,00,000 | 0.97 |

Below 0.40 confidence at any amount → UNRESOLVED, never guessed into a status. Between the lower bound and the amount's threshold → HUMAN_REVIEW.

**LLM tool schema (forced, single tool, no free text):**
```json
{
  "name": "reconciliation_verdict",
  "input_schema": {
    "type": "object",
    "properties": {
      "category": {"type": "string", "enum": ["timing_difference","fee_or_rounding","partial_refund","duplicate","split_or_merged","incorrect_reference","genuinely_missing","unclear"]},
      "confidence_in_category": {"type": "number", "minimum": 0, "maximum": 1},
      "explanation": {"type": "string", "maxLength": 240},
      "recommended_action": {"type": "string", "enum": ["auto_clear_safe","route_to_human_review","escalate_high_value","flag_possible_duplicate","no_action_insufficient_evidence"]},
      "cites_evidence_fields": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["category","confidence_in_category","explanation","recommended_action","cites_evidence_fields"]
  }
}
```

**Anti-hallucination / anti-injection controls, all enforced in code:**
- `tool_choice` forced to this one tool — the model cannot return free text.
- Every digit sequence in `explanation` is parsed and cross-checked against the actual evidence object; a mismatch discards the explanation, substitutes a safe generic template, and logs `explanation_rejected = true`.
- Narration/memo text is always labeled untrusted data in the system prompt, with an explicit instruction never to treat it as a command.
- A lightweight regex pre-filter flags obvious injection markers in narration text before it reaches the prompt, logged when it fires.
- The LLM's output never triggers a status write directly — the risk-weighted policy already decided AUTO/REVIEW/UNRESOLVED before the LLM is even called; a human must click Accept/Override for anything in review.

**What must NEVER be delegated to an LLM:** the matching decision, the confidence score, and the final AUTO/REVIEW/UNRESOLVED status. All three are deterministic/ML code on purpose.

---

## 11. Evaluation Methodology & Metrics

**Metrics (real, measured after the harness runs — every cell below is a target until then):**

| Metric | Target | Measured |
|---|---|---|
| Match precision (of everything auto-matched, % correct) | ≥ 98% | *(fill in after running)* |
| Match recall (of all true pairs, % found at any status) | ≥ 90% | |
| False-match rate (auto-matches that are wrong) | < 1% | |
| False-unmatch rate (true pairs landing Unresolved) | < 5% | |
| Exception classification accuracy (LLM category vs. ground truth) | ≥ 85% | |
| LLM schema-validity rate | ~100% | |
| Human-review rate | 10–20% | |
| Naive fixed-threshold false-match rate (comparison) | — | |
| Risk-weighted false-match rate (this system) | — | |
| Processing time (150-record set) | < 5s | |
| Cost per 1,000 records (LLM calls only) | < $0.20 | |

**Reporting discipline:** the final `eval/report.md` — generated by the harness, never hand-written — includes the full metrics table with real numbers, a per-class breakdown, the naive-baseline comparison, and a "Known Failure Modes" section listing every metric that misses its target, honestly, with the real number shown.

---

## 12. Security & Reliability Model

- **Input validation:** strict schema check (required columns + types) before any processing; a specific error naming the missing/invalid column, never a generic failure.
- **Untrusted text handling:** narration/memo fields are never `eval`'d or executed; always plain data, always labeled untrusted in any LLM-facing prompt.
- **Secrets:** `ANTHROPIC_API_KEY` via environment variable only; `.env` gitignored; `.env.example` committed with placeholders; never logged, never written into the audit trail payload.
- **No autonomous money movement:** the system never writes to any external ledger or triggers a payment. A human's Accept/Override click only updates an internal status field.
- **Audit immutability:** append-only table, no update/delete route exposed anywhere in the code.
- **Fail-safe on any component failure:** LLM down, malformed row, an oversized bucket that would make subset-sum too slow — all degrade to HUMAN_REVIEW with a clear reason, never to a silent auto-match.

---

## 13. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 | One language across data gen, ML, backend |
| Frontend | Streamlit | Fastest path to a working, demoable UI with zero frontend engineering risk in 4 days |
| Database | SQLite + SQLAlchemy | Zero-setup, matches this MVP's scale; a future Postgres swap is a connection-string change |
| Matching libs | pandas, numpy, scipy (`linear_sum_assignment`), rapidfuzz | Standard, fast, well-documented |
| ML | scikit-learn `LogisticRegression` | Right-sized for 5 features and a few hundred labeled rows; interpretable, low overfitting risk |
| LLM SDK | `anthropic` Python SDK, Claude (forced tool-use) | Hard schema guarantee via forced `tool_choice`; bounded classification-plus-explanation, not open-ended reasoning |
| Testing | `pytest` | Unit tests independent of any network call |
| Env/secrets | `python-dotenv`, `.env.example` committed, `.env` gitignored | Standard, zero-cost |
| Version control | Git + GitHub, small daily commits | Evidence of real, incremental process |

---

## 14. Repository Structure

```
reconq/
├── README.md
├── ARCHITECTURE.md
├── SECURITY.md
├── EVALUATION.md
├── RECONQ_MASTER_SPEC.md          # this file
├── .env.example
├── .gitignore
├── requirements.txt
├── data/
│   ├── generate_data.py           # seeded synthetic data generator
│   ├── settlement_report.csv
│   ├── internal_ledger.csv
│   └── ground_truth.csv           # held out — scoring only
├── engine/
│   ├── normalize.py
│   ├── exact_match.py
│   ├── blocking.py
│   ├── group_matching.py          # bounded subset-sum split/merge
│   ├── features.py
│   ├── confidence_model.py        # trains + loads the logistic regression
│   ├── assignment.py              # Hungarian algorithm wrapper
│   ├── risk_policy.py             # amount-banded threshold lookup
│   ├── naive_baseline.py          # single fixed-threshold comparison agent
│   └── audit_log.py
├── llm/
│   ├── system_prompt.txt
│   ├── schema.py                  # forced tool input_schema
│   ├── client.py                  # anthropic wrapper + numeric cross-check + fallback
│   └── injection_guard.py         # pre-filter for suspicious narration text
├── dashboard/
│   └── app.py                     # Streamlit UI
├── eval/
│   ├── harness.py                 # runs pipeline + naive baseline, computes metrics
│   └── report.md                  # generated, not hand-written
├── tests/
│   ├── test_matching_engine.py
│   ├── test_confidence_model.py
│   ├── test_risk_policy.py
│   └── test_llm_schema.py
└── demo/
    └── screenshots/
```

---

## 15. Environment Variables

```
# Anthropic API key for the evidence-only explanation layer.
# Leave blank to run in template-fallback mode — the reconciliation engine
# itself is entirely unaffected either way.
ANTHROPIC_API_KEY=
```

That's the entire credential surface. No payments API, no signing secret — this project makes no payment calls and issues no signed authorization objects, so there is nothing else to configure.

---

## 16. Build Plan — 4 Real Days (Sep 1 → Sep 4), Submit Sep 5

| Day | Date | Build | Test | End-of-day artifact | Fallback if behind |
|---|---|---|---|---|---|
| 1 | Tue Sep 1 | `generate_data.py`, `normalize.py`, `exact_match.py`, `blocking.py` | Exact-match rate matches injected exact-class % | v0: CLI script printing a real match-rate number | Ship v0 as the whole demo core |
| 2 | Tue Sep 1 – Wed Sep 2 | `features.py`, `confidence_model.py`, `assignment.py`, `group_matching.py`, `risk_policy.py`, `naive_baseline.py` | Precision/recall on held-out split; split/merge cases caught; naive-vs-risk-weighted comparison produces expected divergence | v1: full deterministic+ML pipeline with real accuracy numbers and both differentiators functionally real | Cap group size at 2 instead of 4, document the cut |
| 3 | Wed Sep 2 – Thu Sep 3 | `llm/` module (schema, prompt, client, injection guard, numeric cross-check), `audit_log.py`, `dashboard/app.py` | Schema-validity rate on the exception set; manual spot-check of 15–20 explanations; one adversarial narration string test; full manual demo run-through, timed | v2: demoable end to end, LLM optional/graceful, dashboard functional | Ship template-based canned explanations if LLM quality is weak, say so in README |
| 4 | Thu Sep 3 – Fri Sep 4 | `eval/harness.py`, populate real metrics table, security pass, README/ARCHITECTURE/SECURITY/EVALUATION docs, screenshots | Full evaluation table populated with real numbers; full `pytest` pass | Submission-ready repo | If a metric misses target, document it honestly as a known limitation |
| — | Sat Sep 5 | **Submit mid-day, not at the deadline hour.** Repo public, `.env` absent from history, form filled with track = AI Finance Controller. | — | — | — |

---

## 17. Demo Plan (for the eventual pitch video — not built yet)

1. Problem: a spreadsheet treats a ₹50 mismatch and a ₹5,00,000 mismatch identically — that's backwards.
2. Upload/sample data → staged processing → KPI dashboard.
3. **The wow moment:** same confidence score, two records — a small transaction auto-clears, a large one at identical confidence routes to human review, because the threshold is risk-weighted, not fixed.
4. Split/merge exception detail panel — Accept/Override made literal.
5. One honestly-reported case the system got wrong.
6. Real evaluation table on screen, including the naive-baseline comparison.
7. Architecture diagram walkthrough.
8. Limitations + future work, stated plainly.

---

## 18. Build Checklist / Definition of Done

- [x] Data generator produces reproducible output on a clean clone (`python data/generate_data.py`, seeded, verified across multiple reruns).
- [x] Matching engine unit tests pass (`pytest`) — 16/16 passing.
- [x] Confidence model trains in seconds, reports a real precision/recall table (91.4% held-out test accuracy).
- [x] Split/merge detection catches at least the injected split/merge class (verified in `test_matching_engine.py` and live on the full dataset).
- [x] Risk-weighted policy demonstrably diverges from the naive baseline on at least one high-value case (8 divergent pairs measured, incl. a ₹4,14,477 example — see `eval/report.md`).
- [x] LLM explanation layer runs with **and** without an API key set, without crashing either way (verified: template fallback confirmed in `tests/test_llm_schema.py`).
- [x] Every decision in a full pipeline run appears in the audit log (`engine/audit_log.py`, append-only, wired into the dashboard).
- [x] `eval/report.md` has real numbers, including at least one honestly-reported shortfall (false-match rate 1.5% vs <1% target, reported as-is).
- [x] README, ARCHITECTURE.md, SECURITY.md, EVALUATION.md all present and accurate.
- [x] `.env` never committed; `.env.example` present with placeholders only.
- [ ] Application form filled with track = **AI Finance Controller**, submitted before Sep 5 mid-day — **remaining human action**: create a public GitHub repo, push this code, record the 5-minute pitch video, and submit the form. Not something I can do on your behalf.

---

## 19. Go / No-Go

Planning is complete. The workspace has been fully cleared of the prior Bridle project. No ReconQ application code exists yet.

**Say "start" and the build begins at Day 1 of §16** — data generator, normalization, exact-match, bucketing — and continues through the build order in this document, testing at every stage, until the checklist in §18 is real and green, with a real evaluation report and a fully working, demoable product.
