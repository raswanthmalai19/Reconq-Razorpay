from dotenv import load_dotenv
load_dotenv()  # Load .env BEFORE any other import reads environment variables

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title='ReconQ API', version='3.0')

# CORS
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

# In-memory store for reconciliation results (keyed by run_id)
results_store: dict = {}

@app.on_event('startup')
def startup():
    from engine.audit_log import init_db
    init_db()

# ── Routers ──────────────────────────────────────────────────────────────────
# Only routes that correspond to live UI pages are registered here.
# Anything without a frontend tab was removed to keep the surface honest.
from api.routes.reconciliation import router as recon_router
from api.routes.copilot import router as copilot_router
from api.routes.anomalies import router as anomaly_router
from api.routes.suggested_fix import router as fix_router

app.include_router(recon_router, prefix='/api')
app.include_router(copilot_router, prefix='/api')
app.include_router(anomaly_router, prefix='/api')
app.include_router(fix_router, prefix='/api')

@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': '3.0'}
