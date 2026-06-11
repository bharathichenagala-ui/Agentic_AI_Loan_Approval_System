#!/bin/bash
# ── Agentic AI Loan Approval System — Startup Script ──────────────────────────
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Validate environment
if [ -z "$ANTHROPIC_API_KEY" ]; then
    if [ -f .env ]; then
        export $(grep -v '^#' .env | xargs)
    fi
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY is not set."
    echo "Copy .env.example to .env and add your key."
    exit 1
fi

# Install dependencies if needed
if ! python -c "import fastmcp" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "=========================================="
echo "  Agentic AI Loan Approval System"
echo "=========================================="
echo ""

# Start FastAPI in background
echo "[1/2] Starting FastAPI server on port 8000..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!
echo "      API PID: $API_PID"

# Wait for API to be ready
sleep 3

# Start Streamlit
echo "[2/2] Starting Streamlit UI on port 8501..."
echo ""
echo "  API:  http://localhost:8000"
echo "  Docs: http://localhost:8000/docs"
echo "  UI:   http://localhost:8501"
echo ""
streamlit run ui/app.py --server.port 8501

# Cleanup on exit
trap "kill $API_PID 2>/dev/null" EXIT
