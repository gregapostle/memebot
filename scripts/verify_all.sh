#!/bin/bash
set -euo pipefail

echo "🔍 MemeBot Verification Suite Starting..."
echo "========================================="

# 1. Static Analysis
echo "👉 Running Ruff lint..."
ruff check memebot
echo "👉 Running Ruff format check..."
ruff format --check memebot
echo "👉 Running mypy type checks..."
mypy memebot

# 2. Unit Tests
echo "👉 Running pytest suite..."
pytest -q --disable-warnings

# 3. Manual Mode Validations (Mock Streams)
echo "👉 Running Simulation Mode (mock)..."
ENABLE_MOCK=1 python -m memebot.main --mode simulate --debug --enable-exits || true

echo "👉 Running Paper Trading Mode (mock)..."
ENABLE_MOCK=1 python -m memebot.main --mode paper --debug --enable-exits || true

echo "👉 Checking PnL CLI..."
python -m memebot.tools.pnl_cli --since today || true

echo "👉 Running Backtest Runner with sample.jsonl..."
python -m memebot.backtest.runner memebot/backtest/sample.jsonl --debug || true
python -m memebot.tools.pnl_cli --since all || true

# 4. FastAPI Webhook Server (Helius) — short-lived test
echo "👉 Launching Helius Webhook FastAPI (background)..."
( python -m memebot.ingest.helius_webhook & ) 
HELIUS_PID=$!
sleep 3
echo "👉 Sending test webhook request..."
curl -s -X POST http://localhost:8787/helius \
    -H 'x-helius-signature: fake' \
    -d '{"transactions":[]}' || true
kill $HELIUS_PID || true

# 5. Env Sync
echo "👉 Validating .env with update_env.sh..."
bash scripts/update_env.sh

echo "✅ MemeBot verification completed!"

