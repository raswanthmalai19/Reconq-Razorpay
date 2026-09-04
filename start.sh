#!/usr/bin/env bash
# ReconQ v2.0 — Start the full stack
# Usage: ./start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colours
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}"
echo "  ██████╗ ███████╗ ██████╗ ██████╗ ███╗  ██╗ ██████╗  "
echo "  ██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗ ██║██╔═══██╗ "
echo "  ██████╔╝█████╗  ██║     ██║   ██║██╔██╗██║██║   ██║ "
echo "  ██╔══██╗██╔══╝  ██║     ██║   ██║██║╚████║██║▄▄ ██║ "
echo "  ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚███║╚██████╔╝ "
echo "  ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚══╝ ╚══▀▀═╝  "
echo "  Risk-Weighted Reconciliation Agent v2.0"
echo -e "${NC}"

# Check .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Copying from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please add your GEMINI_API_KEY to .env for AI features.${NC}"
fi

# Activate venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
fi

# Generate sample data if not present
if [ ! -f "data/bank_statement.csv" ]; then
    echo -e "${BLUE}Generating sample data...${NC}"
    python data/generate_data.py
fi

# Train model if not present
if [ ! -f "models/confidence_model.joblib" ]; then
    echo -e "${BLUE}Training confidence model...${NC}"
    python engine/train.py
fi

echo -e "${GREEN}Starting FastAPI backend on http://localhost:8000${NC}"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo -e "${GREEN}Starting React frontend on http://localhost:3000${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅  ReconQ is running!${NC}"
echo -e "${GREEN}  🌐  Dashboard:  http://localhost:3000${NC}"
echo -e "${GREEN}  📡  API Docs:   http://localhost:8000/docs${NC}"
echo -e "${GREEN}  ⚡  Click 'Use Sample Data' to run your first reconciliation${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait and forward Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" INT TERM
wait
