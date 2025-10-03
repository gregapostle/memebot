import time
import threading
import asyncio
import logging
import typer

from memebot.config.settings import settings
from memebot.config.watchlist import watchlist
from memebot.strategy.simple import decide
from memebot.strategy.entry import plan_entry
from memebot.exec.paper import PaperTrade, append_trade
from memebot.exec.sim import simulate_swap
from memebot.ingest.mock import stream_mock_signals
from memebot.solana.trade import trade_live
from memebot.solana.jupiter import get_quote
from memebot.strategy.exits import ExitManager, ExitLoop
from memebot.ingest.social.telegram_ingest import run_telegram_ingest
from memebot.ingest.social.discord_ingest import run_discord_ingest


app = typer.Typer()

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s - %(message)s",
)
logger = logging.getLogger("memebot")


def handle_signal(sig, debug: bool = False, mode: str = "simulate"):
    ok, reason, size_native, out_amt, impact_bps = plan_entry(sig)
    decision = decide(sig, liq_ok=ok, est_price_impact_bps=impact_bps)

    if debug:
        logger.info(
            f"[signal] {sig.platform} {sig.source} {sig.symbol or ''} {sig.contract or ''} "
            f"caller={getattr(sig, 'caller', None)} conf={sig.confidence:.2f}"
        )
        logger.info(
            f"[entry] ok={ok} reason={reason} sized={size_native:.4f} "
            f"impact={impact_bps}bps out_raw={out_amt}"
        )
        logger.info(f"[decision] {decision.action} reason={decision.reason}")

    if decision.action == "buy":
        base = (
            "SOL"
            if settings.network == "solana"
            else ("ETH" if settings.network == "ethereum" else "BNB")
        )
        if mode == "live" and settings.network == "solana":
            lamports = max(1, int(size_native * 1_000_000_000))
            if not settings.wsol_mint or sig.contract is None:
                return decision
            quote = get_quote(settings.wsol_mint, sig.contract, lamports)
            if not quote.get("ok"):
                if debug:
                    logger.warning(f"[live] no_quote {quote}")
                return decision
            res = trade_live(quote)
            if debug:
                logger.info(f"[live] {res}")
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
            logger.info(f"[simulate] {trade}")
    return decision


@app.command()
def run(
    mode: str = typer.Option("simulate", help="simulate | paper | live"),
    debug: bool = typer.Option(False, help="verbose logs"),
    enable_exits: bool = typer.Option(False, help="enable exit loop"),
    max_signals: int = typer.Option(0, help="limit signals for testing (0=unlimited)"),
):
    if debug:
        logger.setLevel(logging.DEBUG)

    logger.info(
        f"Starting MemeBot in {mode} mode (network={settings.network}, chain_id={settings.chain_id})"
    )

    streams = []
    threads = []

    # Mock data stream
    if settings.enable_mock:
        streams.append(stream_mock_signals())

    # Telegram ingest thread
    if (
        settings.enable_telegram
        and watchlist.get("telegram_groups")
        and watchlist.get("telegram_api_id")
        and watchlist.get("telegram_api_hash")
    ):

        def tg_runner():
            logger.info("[telegram] starting ingest")
            asyncio.run(
                run_telegram_ingest(
                    lambda sig: handle_signal(sig, debug, mode), debug=debug
                )
            )

        t = threading.Thread(target=tg_runner, daemon=True, name="TelegramThread")
        threads.append(t)
        t.start()

    # Discord ingest thread
    if (
        settings.enable_discord
        and watchlist.get("discord_channels")
        and watchlist.get("discord_token")
    ):

        def dc_runner():
            logger.info("[discord] starting ingest")
            run_discord_ingest(lambda sig: handle_signal(sig, debug, mode), debug=debug)

        t = threading.Thread(target=dc_runner, daemon=True, name="DiscordThread")
        threads.append(t)
        t.start()

    # Exit loop manager
    exit_loop = None
    if enable_exits:
        exit_manager = ExitManager()
        exit_loop = ExitLoop(exit_manager, mode=mode)
        exit_loop.start(debug=debug)

    count = 0
    try:
        for stream in streams:
            for sig in stream:
                handle_signal(sig, debug=debug, mode=mode)
                count += 1
                if max_signals and count >= max_signals:
                    logger.info(f"Reached max_signals={max_signals}, exiting...")
                    return
                time.sleep(0.2)
    finally:
        if exit_loop:
            exit_loop.stop()
        for t in threads:
            t.join(timeout=1)

@app.command()
def observe(debug: bool = False):
    """
    Run bot in observation mode.
    Tracks ingestion signals and prints scoring updates without trading.
    """
    import asyncio
    from memebot.ingest.social.stream_social import stream_social
    from memebot.strategy.fusion import SignalMemory

    async def run():
        memory = SignalMemory()
        async for sig in stream_social():
            fused = memory.fuse(sig)
            print(f"[observe] platform={sig.platform} source={sig.source} "
                  f"contract={sig.contract} score={fused.score:.2f}")
            if debug:
                print(" full signal:", sig)

    asyncio.run(run())

if __name__ == "__main__":
    app()
