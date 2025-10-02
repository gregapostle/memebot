import typer
import sys
import time
import json
from pathlib import Path
from typing import List, Dict

from memebot.strategy.fusion import Signal, SignalMemory
from memebot.strategy.entry import plan_entry
from memebot.strategy.simple import decide
from memebot.exec.paper import PaperTrade, append_trade, reset_trades, get_all_trades
from memebot.strategy.exits import ExitManager
from memebot.config import settings
from memebot.types import SocialSignal


app = typer.Typer(add_completion=False)


def load_signals(path: Path) -> List[Signal]:
    signals: List[Signal] = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw: Dict = json.loads(line)
            sig = Signal(
                platform=raw.get("platform", "unknown"),
                type=raw.get("type", "social"),
                source=raw.get("source", ""),
                content=raw.get("content", ""),
                mentions=raw.get("mentions", []),
                confidence=raw.get("confidence", 0.0),
                ts=float(raw.get("ts", time.time())),
                id=raw.get("id"),
                contract=raw.get("contract"),
            )
            signals.append(sig)
    return signals


@app.command()
def run(
    file: str = typer.Argument(..., help="Path to signals JSONL file"),
    debug: bool = typer.Option(False, help="Verbose logging"),
    ignore_decay: bool = typer.Option(False, help="Ignore score decay"),
    ignore_allowlist: bool = typer.Option(False, help="Ignore caller allowlist"),
    enable_exits: bool = typer.Option(True, help="Run exits inline during backtest"),
):
    path = Path(file)
    if not path.exists():
        raise typer.BadParameter(f"File {file} not found")

    signals = load_signals(path)
    typer.echo(f"Loaded {len(signals)} signals from {file}")

    memory = SignalMemory(decay_seconds=0 if ignore_decay else 60)
    reset_trades()
    exit_manager = ExitManager() if enable_exits else None

    buys = 0
    for sig in signals:
        fused = memory.fuse(sig)

        if debug:
            typer.echo(
                f"[fuse] {fused.platform} src={fused.source} score={fused.score:.2f}"
            )

        if fused.score < 1.0:
            continue

        base_size = float(settings.base_size_sol or 0.05)
        ok, reason, _, out_amt, impact_bps = plan_entry(fused)
        size_native = base_size

        if not ignore_allowlist and not ok:
            continue

        decision = decide(
            SocialSignal(**fused.__dict__), liq_ok=ok, est_price_impact_bps=impact_bps
        )
        if decision.action == "buy":
            trade = PaperTrade(
                ts=fused.ts,
                chain=settings.network,
                side="buy",
                base="SOL",
                quote=fused.contract or "",
                size_base=size_native,
                out_amount=float(out_amt),
                price_impact_bps=int(impact_bps),
                slippage_bps=int(decision.max_slippage_bps),
                reason=decision.reason,
            )
            append_trade(trade)
            buys += 1
            if debug:
                typer.echo(f"[trade] {trade}")

        if enable_exits:
            if exit_manager is not None:
                exits = exit_manager.tick_exits(mode="paper", debug=debug)
            if exits and debug:
                typer.echo(f"[exits] Triggered {len(exits)} exits")

    typer.echo(f"Completed {buys} buys")
    typer.echo(f"Total trades recorded: {len(get_all_trades())}")
    typer.echo("Use `python -m memebot.tools.pnl_cli` to analyse PnL in detail.")


def main(argv=None):
    """Entry point so tests and external callers can invoke runner programmatically."""
    argv = argv or sys.argv[1:]
    app(argv)


if __name__ == "__main__":  # pragma: no cover
    app()
