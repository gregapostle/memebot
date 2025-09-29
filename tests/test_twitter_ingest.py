import pytest
import asyncio
from memebot.ingest.social import twitter_ingest

@pytest.mark.asyncio
async def test_twitter_signal_mock(monkeypatch):
    sample_tweet = {
        "id": "12345",
        "date": "2024-01-01T00:00:00+00:00",
        "content": "New CA: So11111111111111111111111111111111111111112",
    }

    async def fake_fetch(user):
        return [sample_tweet]

    monkeypatch.setattr(twitter_ingest, "fetch_tweets", fake_fetch)
    twitter_ingest.TRACK_USERS[:] = ["testuser"]

    async for sig in twitter_ingest.stream_twitter():
        assert sig["platform"] == "twitter"
        assert sig["source"] == "testuser"
        assert "CA:" in sig["mentions"]
        break
