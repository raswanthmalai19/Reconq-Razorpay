from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# Singleton agent instance
from engine.autonomous_agent import ReconAgent
agent = ReconAgent()

@router.post('/agent/run/{run_id}')
def run_agent(run_id: str):
    """Run the autonomous agent on a completed reconciliation."""
    from api.main import results_store
    if run_id not in results_store:
        from fastapi import HTTPException
        raise HTTPException(404, 'Run not found. Run reconciliation first.')
    entry = results_store[run_id]
    raw = entry['raw_result'] if isinstance(entry, dict) and 'raw_result' in entry else entry
    resp = entry['response'] if isinstance(entry, dict) and 'response' in entry else None
    
    # Build the data the agent needs
    recon_data = {}
    if resp:
        recon_data['kpi'] = resp.dict().get('kpi', {})
        recon_data['matches'] = [m.dict() for m in resp.matches] if hasattr(resp, 'matches') else []
    if raw:
        recon_data['anomalies'] = raw.get('anomalies', [])
        recon_data['leakage_report'] = raw.get('leakage_report', {})
    if not recon_data.get('kpi') and raw:
        recon_data['kpi'] = raw
    
    actions = agent.analyze_and_act(recon_data, run_id)
    return {'run_id': run_id, 'actions_taken': len(actions), 'actions': actions}

@router.get('/agent/activity')
def get_activity():
    """Get the agent's activity log and stats."""
    return agent.get_activity()

@router.post('/agent/clear')
def clear_agent():
    """Clear agent activity."""
    agent.clear()
    return {'status': 'cleared'}

class WebhookConfig(BaseModel):
    webhook_url: str

@router.post('/agent/configure')
def configure_agent(config: WebhookConfig):
    """Configure the agent's Discord webhook URL."""
    agent.webhook_url = config.webhook_url
    return {'status': 'configured', 'webhook_url': config.webhook_url}
