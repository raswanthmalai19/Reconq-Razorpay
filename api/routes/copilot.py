"""Copilot API route — connects the Gemini ReconCopilot to the FastAPI layer."""
import os
import pandas as pd
from fastapi import APIRouter
from api.schemas import CopilotRequest, CopilotResponse
from typing import Dict, Any

router = APIRouter()
copilots: Dict[str, Any] = {}


def get_store():
    from api.main import results_store
    return results_store


def _get_or_create_copilot(run_id: str) -> "ReconCopilot":
    """Get existing copilot for a run or create a new one with live data."""
    from llm.copilot import ReconCopilot

    if run_id in copilots:
        return copilots[run_id]

    store = get_store()
    entry = store.get(run_id)

    raw_result = {}
    settlements_df = pd.DataFrame()
    ledgers_df = pd.DataFrame()

    if entry and isinstance(entry, dict):
        raw_result = entry.get("raw_result", {})
        # Use stored DataFrames (works for both custom uploads and sample data)
        if "settlements_df" in entry:
            settlements_df = entry["settlements_df"]
        if "ledgers_df" in entry:
            ledgers_df = entry["ledgers_df"]

        # Fallback: load sample data from disk if DataFrames weren't stored
        if settlements_df.empty or ledgers_df.empty:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
            s_path = os.path.join(data_dir, "settlement_report.csv")
            l_path = os.path.join(data_dir, "internal_ledger.csv")
            if settlements_df.empty and os.path.exists(s_path):
                settlements_df = pd.read_csv(s_path, dtype=str, keep_default_na=False)
            if ledgers_df.empty and os.path.exists(l_path):
                ledgers_df = pd.read_csv(l_path, dtype=str, keep_default_na=False)

    copilot = ReconCopilot(
        reconciliation_result=raw_result,
        settlements_df=settlements_df,
        ledgers_df=ledgers_df,
        anomalies=raw_result.get("anomalies", []),
    )
    copilots[run_id] = copilot
    return copilot


@router.post("/copilot/chat", response_model=CopilotResponse)
def copilot_chat(req: CopilotRequest):
    """Send a message to the Gemini-powered reconciliation copilot."""
    store = get_store()

    # Try to get run_id — fall back to the most recent run if 'default'
    run_id = req.run_id
    if run_id == "default" and store:
        run_id = next(reversed(store))  # most recently inserted

    if run_id not in store and store:
        run_id = next(reversed(store))

    if not store:
        return CopilotResponse(
            reply=(
                "No reconciliation has been run yet. "
                "Click 'Use Sample Data' on the Dashboard to run a reconciliation first, "
                "then come back to ask me questions!"
            )
        )

    try:
        copilot = _get_or_create_copilot(run_id)
        reply = copilot.chat(req.message)
        return CopilotResponse(reply=str(reply), sources=[run_id])
    except Exception as exc:
        return CopilotResponse(reply=f"Copilot encountered an error: {exc}. Please try again.")


@router.post("/copilot/reset/{run_id}")
def reset_copilot(run_id: str):
    """Reset the chat history for a given run."""
    if run_id in copilots:
        copilots[run_id].reset()
    return {"status": "reset"}
