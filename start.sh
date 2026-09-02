#!/bin/bash
# AgentSetu — Start all services

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-3001}

echo ""
echo "⚡ AgentSetu — Starting Services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Backend ────────────────────────────────────────────────────────────────────
echo "🔧 Starting FastAPI backend (port $BACKEND_PORT)…"
cd "$ROOT/services/api"

# Use virtualenv if present, else system python
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# Install dependencies if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "  Installing Python dependencies…"
  pip3 install -r requirements.txt -q
fi

# Ensure .env exists
if [ ! -f ".env" ]; then
  echo "  ⚠️  No .env found — copying from .env.example"
  cp .env.example .env
  echo "  ✏️  Edit services/api/.env with your Razorpay + OpenAI keys"
fi

# Start backend
uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload &
BACKEND_PID=$!
echo "  ✓ Backend started (PID $BACKEND_PID)"
echo "  ✓ API:  http://localhost:$BACKEND_PORT"
echo "  ✓ Docs: http://localhost:$BACKEND_PORT/docs"
echo ""

# Wait for backend to be ready
sleep 3

# ── Frontend ───────────────────────────────────────────────────────────────────
echo "🎨 Starting Next.js frontend (port $FRONTEND_PORT)…"
cd "$ROOT/apps/web"

# Set API URL env var for frontend
export NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  echo "  Installing Node.js dependencies…"
  npm install --legacy-peer-deps -q
fi

# Start frontend
npm run dev -- -p $FRONTEND_PORT > /tmp/agentsetu-next.log 2>&1 &
FRONTEND_PID=$!
echo "  ✓ Frontend started (PID $FRONTEND_PID)"

# Wait for frontend to be ready
sleep 4

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 AgentSetu is running!"
echo ""
echo "   🛒 Buyer:     http://localhost:$FRONTEND_PORT/buyer"
echo "   🏪 Merchant:  http://localhost:$FRONTEND_PORT/merchant"
echo "   📋 Audit:     http://localhost:$FRONTEND_PORT/audit"
echo "   📚 API Docs:  http://localhost:$BACKEND_PORT/docs"
echo ""
echo "   Demo merchants: OrganicKart · TechMart · SpiceWorld"
echo ""
echo "   ⚠️  Add real API keys to services/api/.env for full AI + payment features"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Cleanup on exit
cleanup() {
  echo ""
  echo "Stopping services…"
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 0
}
trap cleanup INT TERM
wait
