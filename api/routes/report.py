"""Executive Report API route — generates Gemini-powered reconciliation intelligence reports."""
from fastapi import APIRouter, HTTPException

router = APIRouter()


def get_store():
    from api.main import results_store
    return results_store


@router.get("/report/{run_id}")
def generate_report(run_id: str):
    """Generate executive reconciliation report for a completed run."""
    store = get_store()

    # Resolve run_id
    if run_id == "default" and store:
        run_id = next(reversed(store))
    if run_id not in store:
        raise HTTPException(status_code=404, detail="Run not found. Run a reconciliation first.")

    entry = store[run_id]
    response = entry["response"] if isinstance(entry, dict) and "response" in entry else entry

    from llm.report_generator import generate_executive_report

    report = generate_executive_report(
        kpi=response.kpi.model_dump(),
        matches=[m.model_dump() for m in response.matches],
        anomalies=[a.model_dump() for a in response.anomalies],
        leakage_report=response.leakage_report.model_dump() if response.leakage_report else None,
        run_id=run_id,
    )
    return report
