import csv
import os
import time
from pathlib import Path
from typing import Dict, Any
import typer

DATA_DIR = Path(os.getenv("MEMEBOT_DATA_DIR", "./data"))
TRADES_FILE = DATA_DIR / "trades.csv"
CLOSED_FILE = DATA_DIR / "positions_closed.csv"


def load_trades() -> list[Dict[str, Any]]:
    if not TRADES_FILE.exists():
        return []
    with open(TRADES_FILE, newline="") as f:
        return list(csv.DictReader(f))


def load_closed_positions() -> list[Dict[str, Any]]:
    if not CLOSED_FILE.exists():
        return []
    with open(CLOSED_FILE, newline="") as f:
        return list(csv.DictReader(f))


def summarize_pnl(trades: list[Dict[str, Any]]) -> Dict[str, Any]:
    gross = sum(float(t.get("pnl_base", 0.0)) for t in trades)
    winners = sum(1 for t in trades if float(t.get("pnl_base", 0.0)) > 0)
    losers = sum(1 for t in trades if float(t.get("pnl_base", 0.0)) < 0)
    return {"trades": len(trades), "gross": gross, "winners": winners, "losers": losers}


def summarize_pnl_by_token(trades: list[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for t in trades:
        sym = t.get("quote", "UNKNOWN")
        pnl_val = float(t.get("pnl_base", 0.0))
        if sym not in grouped:
            grouped[sym] = {"trades": 0, "gross": 0.0}
        grouped[sym]["trades"] += 1
        grouped[sym]["gross"] += pnl_val
    return grouped


def daily_loss_exceeded(limit: float) -> bool:
    """Check if today's cumulative losses exceed the given cap (in base units)."""
    positions = load_closed_positions()
    today = time.strftime("%Y-%m-%d", time.gmtime())
    losses = 0.0
    for pos in positions:
        ts = float(pos.get("ts_close", 0) or 0)
        if ts == 0:
            continue
        day = time.strftime("%Y-%m-%d", time.gmtime(ts))
        if day == today:
            pnl = float(pos.get("pnl_base", 0.0))
            if pnl < 0:
                losses += abs(pnl)
    return losses >= limit


def main(since: str = typer.Option("today", help="Time filter: today|all")):
    trades = load_closed_positions()
    summary = summarize_pnl(trades)
    typer.echo(
        f"trades={summary['trades']} gross={summary['gross']:.4f} "
        f"winners={summary['winners']} losers={summary['losers']}"
    )

    per_token = summarize_pnl_by_token(trades)
    if per_token:
        typer.echo("Per-token summary:")
        for sym, stats in per_token.items():
            typer.echo(f" {sym}: {stats['trades']} trades gross={stats['gross']:.4f}")


if __name__ == "__main__":
    typer.run(main)
