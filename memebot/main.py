import typer
import time
from memebot.config import settings
from memebot.strategy.simple import decide
from memebot.strategy.entry import plan_entry
from memebot.exec.paper import PaperTrade, append_trade
from memebot.exec.sim import simulate_swap
from memebot.ingest.mock import stream_mock_signals
from memebot.solana.trade import trade_live
from memebot.solana.jupiter import get_quote
from memebot.strategy.exits import ExitManager, ExitLoop

app = typer.Typer()


def handle_signal(sig, debug: bool = False, mode: str = "simulate"):
    ok, reason, size_native, out_amt, impact_bps = plan_entry(sig)
    decision = decide(sig, liq_ok=ok, est_price_impact_bps=impact_bps)
    if debug:
        typer.echo(
            f"[signal] {sig.source} {sig.symbol} {sig.contract} caller={getattr(sig, 'caller', None)} conf={sig.confidence:.2f}"
        )
        typer.echo(
            f"[entry] ok={ok} reason={reason} sized={size_native:.4f} impact={impact_bps}bps out_raw={out_amt}"
        )
        typer.echo(f"[decision] {decision.action} reason={decision.reason}")
    if decision.action == "buy":
        base = (
            "SOL"
            if settings.network == "solana"
            else ("ETH" if settings.network == "ethereum" else "BNB")
        )
        if mode == "live" and settings.network == "solana":
            lamports = max(1, int(size_native * 1_000_000_000))
            if sig.contract is None:
                return
            quote = get_quote(settings.wsol_mint, str(sig.contract), lamports)  # type: ignore[arg-type]

            if not quote.get("ok"):
                if debug:
                    typer.echo(f"[live] no_quote {quote}")
                return decision
            res = trade_live(quote)
            if debug:
                typer.echo(f"[live] {res}")
            return decision

        append_trade(
            PaperTrade(
                ts=time.time(),
                chain=settings.network,
                side="buy",
                base=base,
                quote=sig.contract or "",
                size_base=size_native,
                out_amount=float(out_amt),
                price_impact_bps=int(impact_bps),
                slippage_bps=int(decision.max_slippage_bps),
                reason=decision.reason,
            )
        )
        trade = simulate_swap(decision)
        if debug:
            typer.echo(f"[simulate] {trade}")
    return decision


@app.command()
def run(
    mode: str = typer.Option("simulate", help="simulate | paper | live"),
    debug: bool = typer.Option(False, help="verbose logs"),
    enable_exits: bool = typer.Option(False, help="enable exit loop"),
):
    typer.echo(
        f"Starting MemeBot in {mode} mode (network={settings.network}, chain_id={settings.chain_id})"
    )
    streams = []
    if settings.enable_mock:
        streams.append(stream_mock_signals())

    exit_loop = None
    if enable_exits:
        exit_manager = ExitManager()
        exit_loop = ExitLoop(exit_manager, mode=mode)
        exit_loop.start(debug=debug)

    try:
        for stream in streams:
            for sig in stream:
                handle_signal(sig, debug=debug, mode=mode)
                time.sleep(0.2)
    finally:
        if exit_loop:
            exit_loop.stop()


if __name__ == "__main__":
    app()
