from typing import AsyncGenerator, Any, cast
from memebot.ingest.social.twitter_ingest import stream_twitter
from memebot.ingest.social.telegram_ingest import stream_telegram
from memebot.ingest.social.discord_ingest import stream_discord
from memebot.config import settings
from memebot.types import SocialSignal


async def stream_social() -> AsyncGenerator[SocialSignal, None]:
    """
    Unified async generator for all social platforms.
    Always yields SocialSignal objects.
    """
    if settings.enable_twitter:
        async for raw_twitter in stream_twitter():
            if isinstance(raw_twitter, SocialSignal):
                yield raw_twitter
            else:
                yield SocialSignal(**cast(dict[str, Any], raw_twitter))

    if settings.enable_telegram:
        for raw_tg in stream_telegram(limit=5):
            if isinstance(raw_tg, SocialSignal):
                yield raw_tg
            else:
                yield SocialSignal(**cast(dict[str, Any], raw_tg))

    if settings.enable_discord:
        for raw_dc in stream_discord(limit=5):
            if isinstance(raw_dc, SocialSignal):
                yield raw_dc
            else:
                yield SocialSignal(**cast(dict[str, Any], raw_dc))


async def stream_social_signals() -> AsyncGenerator[SocialSignal, None]:
    """Alias kept for backward compatibility in tests."""
    async for sig in stream_social():
        yield sig
