import logging
import queue
import threading
import time
import asyncio
from typing import Callable, Generator, Optional
from memebot.types import SocialSignal
from memebot.config.watchlist import watchlist
from memebot.ingest.llm_filter import filter_signal_with_llm  # ✅ Correct LLM filter

logger = logging.getLogger("memebot.discord")


def _process_signal(sig: SocialSignal, callback: Callable[[SocialSignal], None], debug: bool = False):
    """Run LLM filter before passing to callback."""
    filtered = asyncio.run(filter_signal_with_llm(sig))
    if not filtered or not filtered.get("valuable"):
        if debug:
            logger.info(f"[discord] dropped noise: {sig.text[:60]}")
        return

    sig.symbol = filtered.get("token")
    sig.contract = filtered.get("token")
    sig.confidence = filtered.get("confidence", sig.confidence)

    if debug:
        logger.info(f"[discord] accepted signal: {sig.model_dump()}")
    callback(sig)


def run_discord_ingest(callback: Callable[[SocialSignal], None], debug: bool = False):
    """Fake Discord ingest (real impl would use discord.py)."""
    channels = watchlist.get("discord_channels", [])
    logger.info(f"[discord] monitoring channels: {channels}")

    for channel in channels:
        msg_text = f"Mocked message from {channel}"
        sig = SocialSignal(
            platform="discord",
            source=channel,
            symbol=None,
            contract=None,
            confidence=0.5,
            text=msg_text,
            caller="dc-user",
        )
        _process_signal(sig, callback, debug=debug)


async def verify_discord_credentials() -> str:
    """Fake credential check for testing."""
    if not watchlist.get("discord_token"):
        raise RuntimeError("Missing Discord bot token")
    return "mock-discord-user"


def stream_discord(limit: int = 1) -> Generator[SocialSignal, None, None]:
    """Legacy generator for tests."""
    q: "queue.Queue[Optional[SocialSignal]]" = queue.Queue()

    def runner():
        run_discord_ingest(q.put, debug=False)
        q.put(None)

    t = threading.Thread(target=runner, daemon=True)
    t.start()

    for _ in range(limit):
        sig = q.get()
        if sig is None:
            break
        yield sig


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("[discord] starting ingest loop...")

    def _printer(sig: SocialSignal):
        print("[DISCORD]", sig)

    while True:
        run_discord_ingest(_printer, debug=True)
        logger.info("[discord] alive, still monitoring...")
        time.sleep(30)