import pytest
import asyncio
from memebot.ingest.social import discord_ingest

@pytest.mark.asyncio
async def test_discord_signal_mock(monkeypatch):
    # Mock a message event payload
    fake_message = {
        "type": "social",
        "platform": "discord",
        "source": "test_user",
        "content": "New CA: So11111111111111111111111111111111111111112",
        "mentions": ["CA:"],
        "confidence": 0.7,
        "ts": "2024-01-01T00:00:00",
        "id": "123",
    }

    queue = asyncio.Queue()
    await queue.put(fake_message)

    async def fake_stream():
        while not queue.empty():
            yield await queue.get()

    monkeypatch.setattr(discord_ingest, "stream_discord", fake_stream)

    async for sig in discord_ingest.stream_discord():
        assert sig["platform"] == "discord"
        assert "CA:" in sig["mentions"]
        break
