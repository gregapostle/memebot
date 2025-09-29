import os
import asyncio
import discord
from typing import AsyncGenerator, Dict, Any

# Env vars
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_CHANNELS = os.getenv("DISCORD_CHANNELS", "").split(",")
TRACK_KEYWORDS = os.getenv("DISCORD_TRACK_KEYWORDS", "CA:").split(",")


async def stream_discord() -> AsyncGenerator[Dict[str, Any], None]:
    """
    Async generator yielding SocialSignal dicts from Discord channels.
    """
    if not DISCORD_TOKEN or not DISCORD_CHANNELS:
        return

    intents = discord.Intents.default()
    intents.messages = True
    intents.guilds = True
    intents.message_content = True

    client = discord.Client(intents=intents)
    queue: asyncio.Queue = asyncio.Queue()

    @client.event
    async def on_ready():
        print(f"[discord_ingest] Logged in as {client.user}")

    @client.event
    async def on_message(message):
        if str(message.channel.id) not in DISCORD_CHANNELS:
            return
        text = message.content
        if any(kw.lower() in text.lower() for kw in TRACK_KEYWORDS):
            signal = {
                "type": "social",
                "platform": "discord",
                "source": str(message.author),
                "content": text,
                "mentions": [kw for kw in TRACK_KEYWORDS if kw.lower() in text.lower()],
                "confidence": 0.7,
                "ts": str(message.created_at),
                "id": str(message.id),
            }
            await queue.put(signal)

    # Run Discord client in a background task
    loop = asyncio.get_event_loop()
    loop.create_task(client.start(DISCORD_TOKEN))

    while True:
        signal = await queue.get()
        yield signal
        queue.task_done()


async def verify_discord_credentials():
    """
    Quick check that Discord bot token works.
    """
    from discord import Client, Intents

    if not DISCORD_TOKEN:
        raise ValueError("Missing DISCORD_TOKEN in env")

    intents = Intents.default()
    client = Client(intents=intents)

    try:
        # Just login, don’t connect full websocket
        await client.login(DISCORD_TOKEN)
        user = client.user
        await client.close()
        return str(user) if user else "Unknown"
    except Exception as e:
        raise RuntimeError(f"Discord login failed: {e}")


if __name__ == "__main__":

    async def test():
        async for sig in stream_discord():
            print(sig)

    asyncio.run(test())
