# ReconQ — Risk-Weighted Reconciliation Agent

**Track:** Razorpay AI Buildathon 2026 — AI Finance Controller

ReconQ reconciles a payment gateway's settlement report against an internal ledger automatically, but raises the bar for auto-clearing a match exactly as much as the money at stake demands — instant on routine cases, human-gated on high-value or structurally ambiguous ones, every decision explained and logged.

## The problem

Finance/ops teams reconcile settlements against ledgers by hand or with brittle exact-match scripts. Mismatches (fees, timing gaps, partial refunds, duplicates, split/merged settlements, corrupted references) need judgment. Most tools apply one confidence bar to every transaction regardless of size — a ₹200 mismatch and a ₹4,00,000 mismatch at the same 90% confidence do not carry the same risk if the system is wrong.

## What's different

Three concrete mechanisms:

1. **Risk-weighted (amount-banded) auto-match threshold** instead of one fixed number.
2. **Bounded subset-sum split/merge detection** — finds cases where one settlement equals the sum of 2–4 ledger rows (or vice versa), not just 1:1 pairs.
3. **Evidence-only LLM explanation layer** with a post-hoc numeric-fabrication check — the LLM can never state a number that isn't in the evidence it was given.

None of this is claimed as academically novel — amount-banded review thresholds are a known pattern in fraud/credit-risk systems generally. The claim is narrower: these three mechanisms, implemented and measured together, are genuinely more work than a "two CSVs + LLM narration" submission, and that gap is checkable in this repo's code and evaluation report.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python data/generate_data.py        # seeded synthetic settlement + ledger + ground truth
python -m pytest tests/ -q          # 16 unit tests
python eval/harness.py              # trains the model, runs both policies, writes eval/report.md
streamlit run dashboard/app.py      # interactive dashboard
```

No API key is required for any of the above. `ANTHROPIC_API_KEY` is optional — without it, the LLM explanation layer runs in template-fallback mode; the reconciliation engine itself is entirely unaffected either way (see `.env.example`).

## Measured results (from `eval/report.md`, regenerate anytime with `python eval/harness.py`)

Run on the seeded synthetic set (154 settlement records, `random.seed(42)`):

| Metric | ReconQ (risk-weighted) | Naive (fixed 0.85 threshold) |
|---|---|---|
| Match precision (of auto-matched) | 98.5% | 98.6% |
| Match recall (any status) | 97.5% | 97.5% |
| False-match rate | 1.5% | 1.4% |
| Human-review rate | 13.5% | 9.7% |

**The signature moment:** on this run, 8 (settlement, ledger) pairs received the *identical* confidence score from the shared model but a *different* final decision purely because of transaction amount — including a ₹4,14,477 pair at 95.6% confidence that ReconQ routes to human review and the naive fixed-threshold baseline would auto-clear. Full table in `eval/report.md`.

Confidence model (logistic regression): 91.4% held-out test accuracy (208/69/70 train/val/test split).

## Known limitations (stated honestly — see `eval/report.md` "Known Failure Modes")

- Measured false-match rate (1.5%) is above the pre-declared <1% target on this 154-record set — a small number of absolute misclassified records at this scale, reported as-is, not rounded away.
- Validation accuracy (79.7%) is noticeably lower than test accuracy (91.4%) — plausibly explained by the small held-out split (69 examples) at this dataset scale, not confirmed as a modeling bug.
- Trained and evaluated on synthetic data only; transfer to real settlement data is untested.
- Group detection is capped at 4 members per split/merge; a genuine 5+-way merge fails safely to `UNRESOLVED`, not a wrong partial match.

## Architecture, security, evaluation methodology

See [ARCHITECTURE.md](ARCHITECTURE.md), [SECURITY.md](SECURITY.md), [EVALUATION.md](EVALUATION.md), and the full build plan in [RECONQ_MASTER_SPEC.md](RECONQ_MASTER_SPEC.md).

## Tech stack

Python 3.11, pandas/scipy/rapidfuzz, scikit-learn (`LogisticRegression`), SQLite/SQLAlchemy (append-only audit log), Streamlit, `anthropic` SDK (optional, forced tool-use).

## What is explicitly NOT built

No live Razorpay API integration (this project reconciles synthetic CSVs, not live settlements — named as future work). No autonomous write-back to any ledger. No multi-tenant auth. No fine-tuning. No production credentials anywhere.
