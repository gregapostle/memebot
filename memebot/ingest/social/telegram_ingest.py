import logging
import asyncio
import inspect
from typing import Callable, Generator, Optional
from memebot.types import SocialSignal
from memebot.config.watchlist import watchlist
from memebot.ingest.llm_filter import filter_signal_with_llm

logger = logging.getLogger("memebot.telegram")

USE_REAL_TELEGRAM = bool(
    watchlist.get("telegram_api_id") and watchlist.get("telegram_api_hash")
)

if USE_REAL_TELEGRAM:
    from telethon import TelegramClient, events


async def _process_signal(sig: SocialSignal, callback, debug: bool = False):
    """Run a signal through the LLM filter before forwarding."""
    result = await filter_signal_with_llm(sig)
    if result["valuable"]:
        sig.symbol = result.get("token") or sig.symbol
        sig.confidence = result.get("confidence", sig.confidence)
        if debug:
            logger.info(f"[telegram][LLM] accepted {result}")
        if inspect.iscoroutinefunction(callback):
            await callback(sig)
        else:
            callback(sig)
    else:
        if debug:
            logger.info(f"[telegram][LLM] dropped as noise: {result.get('reason')}")


async def run_telegram_ingest(
    callback: Callable[[SocialSignal], None], debug: bool = False
):
    groups = watchlist.get("telegram_groups", [])
    logger.info(f"[telegram] starting... monitoring groups: {groups or '[ALL]'}")

    if not USE_REAL_TELEGRAM:
        # --- Mock Mode ---
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
            await _process_signal(sig, callback, debug)
        return

    # --- Real Mode (Telethon) ---
    api_id = int(watchlist.get("telegram_api_id"))
    api_hash = watchlist.get("telegram_api_hash")
    session_name = watchlist.get("telegram_session", "memebot")

    client = TelegramClient(session_name, api_id, api_hash)

    @client.on(events.NewMessage)
    async def handler(event):
        entity = await event.get_chat()
        source_name = (
            getattr(entity, "title", None)
            or getattr(entity, "username", None)
            or str(event.chat_id)
        )

        allowed_groups = set(groups)
        if source_name not in allowed_groups and str(event.chat_id) not in allowed_groups:
            if debug:
                logger.debug(f"[telegram] skipping message from {source_name}")
            return

        msg_text = event.raw_text
        sig = SocialSignal(
            platform="telegram",
            source=source_name,
            symbol=None,
            contract=None,
            confidence=0.5,
            text=msg_text,
            caller="tg-user",
        )

        await _process_signal(sig, callback, debug)

    await client.start()
    logger.info("[telegram] listening for messages...")
    await client.run_until_disconnected()


async def verify_telegram_credentials() -> str:
    if not USE_REAL_TELEGRAM:
        return "mock-telegram-user"
    if not (watchlist.get("telegram_api_id") and watchlist.get("telegram_api_hash")):
        raise RuntimeError("Missing Telegram API credentials")
    return "telegram-user"


def stream_telegram(limit: int = 1) -> Generator[SocialSignal, None, None]:
    if not USE_REAL_TELEGRAM:
        q: asyncio.Queue[Optional[SocialSignal]] = asyncio.Queue()

        async def runner():
            await run_telegram_ingest(q.put, debug=False)
            await q.put(None)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(runner())

        for _ in range(limit):
            sig = loop.run_until_complete(q.get())
            if sig is None:
                break
            yield sig

        loop.close()
    else:
        raise RuntimeError("stream_telegram() is not supported in real mode")


if __name__ == "__main__":
    async def consume(sig):
        print("[TELEGRAM]", sig)

    async def main():
        print("[telegram] starting ingest…")

        async def heartbeat():
            while True:
                print("[telegram] alive, still monitoring groups...")
                await asyncio.sleep(30)

        asyncio.create_task(heartbeat())
        await run_telegram_ingest(consume, debug=True)

    asyncio.run(main())