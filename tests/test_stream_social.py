import pytest
import asyncio
from memebot.ingest.social import stream_social

@pytest.mark.asyncio
async def test_stream_social_mock(monkeypatch):
    async def fake_twitter():
        yield {"type": "social", "platform": "twitter", "content": "CA: ..."}
    async def fake_telegram():
        yield {"type": "social", "platform": "telegram", "content": "CA: ..."}
    async def fake_discord():
        yield {"type": "social", "platform": "discord", "content": "CA: ..."}

    monkeypatch.setattr(stream_social, "stream_twitter", fake_twitter)
    monkeypatch.setattr(stream_social, "stream_telegram", fake_telegram)
    monkeypatch.setattr(stream_social, "stream_discord", fake_discord)

    async def run_once():
        async for sig in stream_social.stream_social_signals():
            assert sig["type"] == "social"
            assert sig["platform"] in ["twitter", "telegram", "discord"]
            break

    await run_once()
