import pytest
import asyncio
from memebot.ingest.social import telegram_ingest

@pytest.mark.asyncio
async def test_telegram_signal_mock(monkeypatch):
    fake_event = type("FakeEvent", (), {
        "raw_text": "🚀 New CA: So11111111111111111111111111111111111111112",
        "chat_id": 1234,
        "date": "2024-01-01T00:00:00",
        "id": 99,
    })

    queue = asyncio.Queue()
    await queue.put({
        "type": "social",
        "platform": "telegram",
        "source": "1234",
        "content": fake_event.raw_text,
        "mentions": ["CA:"],
        "confidence": 0.7,
        "ts": fake_event.date,
        "id": str(fake_event.id),
    })

    # Patch queue into generator
    async def fake_stream():
        while not queue.empty():
            yield await queue.get()

    monkeypatch.setattr(telegram_ingest, "stream_telegram", fake_stream)

    async for sig in telegram_ingest.stream_telegram():
        assert sig["platform"] == "telegram"
        assert "CA:" in sig["mentions"]
        break
