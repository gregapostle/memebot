import logging
import queue
import threading
from typing import Callable, Generator, Optional
from memebot.types import SocialSignal
from memebot.config.watchlist import watchlist

logger = logging.getLogger("memebot.discord")


def run_discord_ingest(callback: Callable[[SocialSignal], None], debug: bool = False):
    """Fake Discord ingest (real impl would use discord.py)."""
    channels = watchlist.get("discord_channels", [])
    logger.info(f"[discord] monitoring channels: {channels}")

    # Example: replace with actual async client loop
    for channel in channels:
        msg_text = f"Mocked message from {channel}"
        sig = SocialSignal(
            platform="discord",
            source=channel,
            symbol="USDC",
            contract="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            confidence=0.82,
            text=msg_text,
            caller="dc-user",
        )
        if debug:
            logger.debug(f"[discord] captured signal: {sig.model_dump()}")
        callback(sig)


async def verify_discord_credentials() -> str:
    """
    Fake credential check for testing.
    Returns a dummy user if credentials exist.
    """
    if not watchlist.get("discord_token"):
        raise RuntimeError("Missing Discord bot token")
    return "mock-discord-user"


# --- Backward compatibility wrapper for tests ---
def stream_discord(limit: int = 1) -> Generator[SocialSignal, None, None]:
    """
    Legacy generator interface for tests.
    Runs Discord ingest in a background thread and yields SocialSignal.
    Yields up to `limit` signals, then exits cleanly.
    """
    q: "queue.Queue[Optional[SocialSignal]]" = queue.Queue()

    def runner():
        run_discord_ingest(q.put, debug=False)
        q.put(None)  # sentinel

    t = threading.Thread(target=runner, daemon=True)
    t.start()

    for _ in range(limit):
        sig = q.get()
        if sig is None:
            break
        yield sig
