from fastapi import APIRouter

router = APIRouter()


def get_store():
    from api.main import results_store
    return results_store


@router.get('/anomalies/{run_id}')
def get_anomalies(run_id: str):
    """Return anomalies and leakage report for a given run."""
    store = get_store()
    if run_id not in store:
        return {"anomalies": [], "leakage_report": None}

    entry = store[run_id]
    # Store now contains {"response": ReconciliationResponse, "raw_result": dict}
    if isinstance(entry, dict) and "response" in entry:
        response = entry["response"]
    else:
        response = entry

    return {
        "anomalies": [a.dict() if hasattr(a, 'dict') else a for a in (response.anomalies or [])],
        "leakage_report": response.leakage_report.dict() if response.leakage_report and hasattr(response.leakage_report, 'dict') else response.leakage_report,
    }
