import os
import asyncio
from telethon import TelegramClient, events  # type: ignore
from typing import AsyncGenerator, Dict, Any

# Env vars
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", "memebot")
TELEGRAM_CHANNELS = os.getenv("TELEGRAM_CHANNELS", "").split(",")
TRACK_KEYWORDS = os.getenv("TELEGRAM_TRACK_KEYWORDS", "CA:").split(",")

client = None  # lazy init


async def stream_telegram() -> AsyncGenerator[Dict[str, Any], None]:
    """
    Async generator that yields SocialSignal dicts from Telegram channels.
    """

    global client

    # Validate before starting
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise ValueError("Missing TELEGRAM_API_ID or TELEGRAM_API_HASH in env")
    if not TELEGRAM_CHANNELS or TELEGRAM_CHANNELS == [""]:
        raise ValueError("Missing TELEGRAM_CHANNELS in env")

    if client is None:
        client = TelegramClient(
            TELEGRAM_SESSION, int(TELEGRAM_API_ID), TELEGRAM_API_HASH
        )

    queue: asyncio.Queue = asyncio.Queue()

    @client.on(events.NewMessage(chats=TELEGRAM_CHANNELS))
    async def handler(event):
        text = event.raw_text
        if any(kw.lower() in text.lower() for kw in TRACK_KEYWORDS):
            signal = {
                "type": "social",
                "platform": "telegram",
                "source": str(event.chat_id),
                "content": text,
                "mentions": [kw for kw in TRACK_KEYWORDS if kw.lower() in text.lower()],
                "confidence": 0.7,
                "ts": str(event.date),
                "id": str(event.id),
            }
            await queue.put(signal)

    await client.start()

    while True:
        signal = await queue.get()
        yield signal
        queue.task_done()


async def verify_telegram_credentials():
    """
    Quick check that Telegram API ID/Hash are valid and login works.
    """
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise ValueError("Missing TELEGRAM_API_ID or TELEGRAM_API_HASH in env")

    client = TelegramClient(
        TELEGRAM_SESSION + "_verify", int(TELEGRAM_API_ID), TELEGRAM_API_HASH
    )
    await client.start()
    me = await client.get_me()
    await client.disconnect()
    return me.username or me.id
