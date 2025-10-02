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
export OFFLINE=1
pytest -q --disable-warnings

# 3. Manual Mode Validations (Mock Streams)
echo "👉 Running Simulation Mode (mock)..."
ENABLE_MOCK=1 python -m memebot.main --mode simulate --debug --enable-exits --max-signals 5 || true

echo "👉 Running Paper Trading Mode (mock)..."
ENABLE_MOCK=1 python -m memebot.main --mode paper --debug --enable-exits --max-signals 5 || true

echo "👉 Checking PnL CLI..."
python -m memebot.tools.pnl_cli --since today || true

echo "👉 Running Backtest Runner with sample.jsonl..."
python -m memebot.backtest.runner memebot/backtest/sample.jsonl --debug || true
python -m memebot.tools.pnl_cli --since all || true

# 4. FastAPI Webhook Server (Helius) — short-lived test
echo "👉 Launching Helius Webhook FastAPI (background)..."
PORT=8788 python -m memebot.ingest.helius_webhook --port 8788 &
HELIUS_PID=$!
sleep 3

echo "👉 Sending test webhook request..."
PAYLOAD='{"transactions":[]}'
SECRET="${HELIUS_WEBHOOK_SECRET:-testsecret}"
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -binary | xxd -p -c 256)

curl -s -X POST http://localhost:8788/helius \
    -H "x-helius-signature: $SIGNATURE" \
    -d "$PAYLOAD" || true

if kill -0 $HELIUS_PID 2>/dev/null; then
  kill $HELIUS_PID >/dev/null 2>&1 || true
  wait $HELIUS_PID 2>/dev/null || true
fi

# 5. Env Sync
echo "👉 Validating .env with update_env.sh..."
bash scripts/update_env.sh

echo "✅ MemeBot verification completed!"
