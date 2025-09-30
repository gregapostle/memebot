import logging
import asyncio
from typing import Callable, Generator, Optional
from memebot.types import SocialSignal
from memebot.config.watchlist import watchlist

logger = logging.getLogger("memebot.telegram")


async def run_telegram_ingest(
    callback: Callable[[SocialSignal], None], debug: bool = False
):
    """Fake Telegram ingest (real impl would use Telethon)."""
    groups = watchlist.get("telegram_groups", [])
    logger.info(f"[telegram] monitoring groups: {groups}")

    # Example: replace with actual async client loop
    for group in groups:
        msg_text = f"Mocked message from {group}"
        sig = SocialSignal(
            platform="telegram",
            source=group,
            symbol="BONK",
            contract="So11111111111111111111111111111111111111112",
            confidence=0.75,
            text=msg_text,
            caller="tg-user",
        )
        if debug:
            logger.debug(f"[telegram] captured signal: {sig.model_dump()}")
        callback(sig)


async def verify_telegram_credentials() -> str:
    """
    Fake credential check for testing.
    Returns a dummy username if credentials exist.
    """
    if not (watchlist.get("telegram_api_id") and watchlist.get("telegram_api_hash")):
        raise RuntimeError("Missing Telegram API credentials")
    return "mock-telegram-user"


# --- Backward compatibility wrapper for tests ---
def stream_telegram(limit: int = 1) -> Generator[SocialSignal, None, None]:
    """
    Legacy generator interface for tests.
    Runs the async ingest in a blocking way and yields SocialSignal.
    Yields up to `limit` signals, then exits cleanly.
    """
    q: asyncio.Queue[Optional[SocialSignal]] = asyncio.Queue()

    async def runner():
        await run_telegram_ingest(q.put, debug=False)
        await q.put(None)  # sentinel

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(runner())

    for _ in range(limit):
        sig = loop.run_until_complete(q.get())
        if sig is None:
            break
        yield sig

    loop.close()
