from typing import AsyncGenerator
from memebot.ingest.social.twitter_ingest import stream_twitter
from memebot.ingest.social.telegram_ingest import stream_telegram
from memebot.ingest.social.discord_ingest import stream_discord
from memebot.config import settings


async def stream_social() -> AsyncGenerator:
    if settings.enable_twitter:
        async for sig in stream_twitter():
            yield sig
    if settings.enable_telegram:
        async for sig in stream_telegram():
            yield sig
    if settings.enable_discord:
        async for sig in stream_discord():
            yield sig


async def stream_social_signals() -> AsyncGenerator:
    """Alias kept for backward compatibility in tests."""
    async for sig in stream_social():
        yield sig
