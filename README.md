# MemeBot 🚀

MemeBot is an experimental trading agent that listens to **social signals** (Twitter, Telegram, Discord) and **on-chain wallet activity** (via Helius), estimates liquidity routes, and simulates or executes swaps on **Solana** (Ethereum/BNB basics included).

It supports:
- ✅ **Simulation mode** – dry-run trades with detailed logs.  
- ✅ **Paper trading** – track entries/exits without sending real transactions.  
- ✅ **Live mode** – optional Solana devnet/mainnet trades via Jupiter aggregator.  
- ✅ **Testing suite** – `pytest` with mocked signals, quotes, and swaps.  

---

## Requirements

- **Operating system:** macOS / Linux / WSL2 recommended  
- **Python:** 3.11+ (3.13 supported)  
- **Git** installed  
- **Solana CLI** (for live trades / keypair handling)

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/YOURNAME/memebot.git
cd memebot
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

*(Windows PowerShell: `.\.venv\Scripts\Activate.ps1`)*

### 3. Install dependencies

```bash
pip install -e .
```

This installs MemeBot in “editable” mode so changes take effect immediately.

---

## Running Tests

To confirm everything is working:

```bash
pytest
```

Expected: **all tests pass**, with a few marked `skipped` (integration tests for optional networks).

---

## Simulation Mode

Run the bot in simulation:

```bash
python -m memebot.main --mode simulate --debug --enable-exits
```

---

## Paper Trading

Log trades without touching real chains:

```bash
ENABLE_MOCK=1 python -m memebot.main --mode paper --debug --enable-exits
```

Check PnL later:

```bash
python -m memebot.tools.pnl_cli --since today
```

---

## Live Trading (Solana)

⚠️ **Risk disclaimer:** This code is experimental. Do not use with significant funds.

### 1. Get a Solana keypair

```bash
solana-keygen new --outfile ~/.config/solana/devnet-keypair.json
solana airdrop 2 --url https://api.devnet.solana.com
```

### 2. Set environment variables

```bash
export SOLANA_CLUSTER=devnet
export ALLOW_LIVE=1
export SOLANA_PRIVATE_KEY_FILE=~/.config/solana/devnet-keypair.json
export SOLANA_OWNER=$(solana-keygen pubkey ~/.config/solana/devnet-keypair.json)
```

### 3. Run live mode

```bash
python -m memebot.main --mode live --debug --enable-exits
```

---

## Environment Variables (Quick Reference)

| Variable | Purpose | Example |
|----------|---------|---------|
| `NETWORK` | Which network | `solana` |
| `SOLANA_CLUSTER` | Cluster | `devnet` / `mainnet` |
| `ALLOW_LIVE` | Enable real trades | `1` |
| `ENABLE_MOCK` | Use mock signal streams | `1` |
| `MOCK_JUPITER` | Mock Jupiter quotes | `1` |
| `AUTO_DEVNET_MOCK` | Auto-fallback for devnet | `1` |
| `SOLANA_PRIVATE_KEY_FILE` | Path to Solana keypair JSON | `~/.config/solana/devnet-keypair.json` |
| `SOLANA_OWNER` | Override owner pubkey | `YourPubkey` |
| `BASE_SIZE_SOL` | Fixed size per buy | `0.05` |
| `TP_PCT` | Take profit % | `20` |
| `SL_PCT` | Stop loss % | `-30` |
| `TRAIL_PCT` | Trailing stop % | `10` |
| `MIN_HOLD_SEC` | Min hold time | `10` |
| `DAILY_LOSS_CAP_SOL` | Max daily loss | `1.0` |

---

## ✅ Verification Checklist

Before running MemeBot live, confirm the system works end-to-end.

### 1. Run all unit tests
```bash
pytest -q
```
Expected: all tests pass (some may be `skipped` if optional integrations not configured).

---

### 2. Verify integrations
Check your API credentials and connectivity:

```bash
python -m memebot.tools.verify telegram
python -m memebot.tools.verify discord
```

Twitter uses `snscrape` (no API key needed).

---

### 3. Backtest with exits
Use the included sample dataset:

```bash
python -m memebot.backtest.runner memebot/backtest/sample.jsonl --debug
python -m memebot.tools.pnl_cli --since all
```

Expected:
- ≥ 1 entry trade  
- ≥ 1 exit trade  
- PnL stats, including per-token breakdown

---

### 4. Simulation mode (with exits)
```bash
ENABLE_MOCK=1 python -m memebot.main --mode simulate --debug --enable-exits
```

Expected: Logs show `[signal]`, `[decision]`, `[simulate]`, and `[exit]`.

---

### 5. Paper trading
```bash
ENABLE_MOCK=1 python -m memebot.main --mode paper --debug --enable-exits
python -m memebot.tools.pnl_cli --since today
```

Expected: Trades recorded, PnL summary available.

---

### 6. Live devnet test
⚠️ **Only use devnet airdrop funds for this test.**

```bash
SOLANA_CLUSTER=devnet ALLOW_LIVE=1 \
SOLANA_PRIVATE_KEY_FILE=~/.config/solana/devnet-keypair.json \
python -m memebot.main --mode live --debug --enable-exits
```

Expected: Real swaps executed against Jupiter’s **devnet** liquidity.

---

If all these checks pass, MemeBot is fully functional in simulation, paper, backtest, and live (devnet) modes.  

---


## Roadmap

- [ ] Real Twitter sentiment stream  
- [ ] Position sizing + advanced risk engine  
- [ ] Docker support for deployment  

---

## Disclaimer

This software is **for educational purposes only**.  
Using it on mainnet may result in loss of funds.  
Use at your own risk.
