import pytest
import asyncio
from memebot.ingest.social import stream_social
from memebot.types import SocialSignal


@pytest.mark.asyncio
async def test_stream_social_mock(monkeypatch):
    """Basic smoke test ensuring at least one social signal flows through."""

    async def fake_twitter():
        yield {
            "platform": "twitter",
            "type": "social",
            "source": "tester",
            "content": "CA: ...",
            "mentions": [],
            "confidence": 0.8,
            "ts": 123.0,
            "id": "tw1",
            "contract": "abc",
        }

    monkeypatch.setattr(stream_social, "stream_twitter", fake_twitter)
    monkeypatch.setattr(stream_social.settings, "enable_twitter", True)
    monkeypatch.setattr(stream_social.settings, "enable_telegram", False)
    monkeypatch.setattr(stream_social.settings, "enable_discord", False)

    results = []
    async for sig in stream_social.stream_social_signals():
        results.append(sig)
        break  # just check one signal

    assert results
    assert results[0].platform == "twitter"


@pytest.mark.asyncio
async def test_stream_social_all_branches(monkeypatch):
    """Ensure stream_social yields from twitter, telegram, and discord."""

    # ✅ Force all platform flags on
    monkeypatch.setattr(stream_social.settings, "enable_twitter", True)
    monkeypatch.setattr(stream_social.settings, "enable_telegram", True)
    monkeypatch.setattr(stream_social.settings, "enable_discord", True)

    async def fake_twitter():
        yield {
            "platform": "twitter",
            "type": "social",
            "source": "tester",
            "content": "CA: ...",
            "mentions": [],
            "confidence": 0.8,
            "ts": 123.0,
            "id": "tw1",
            "contract": "abc",
        }
        yield SocialSignal(
            platform="twitter",
            source="x",
            type="social",
            content="hi",
            mentions=[],
            confidence=0.5,
            ts=1.0,
            id="1",
            contract="abc",
        )

    def fake_telegram(limit=5):
        yield {
            "platform": "telegram",
            "type": "social",
            "source": "tester",
            "content": "CA: ...",
            "mentions": [],
            "confidence": 0.7,
            "ts": 124.0,
            "id": "tg1",
            "contract": "def",
        }
        yield SocialSignal(
            platform="telegram",
            source="y",
            type="social",
            content="hey",
            mentions=[],
            confidence=0.6,
            ts=2.0,
            id="2",
            contract="def",
        )

    def fake_discord(limit=5):
        yield {
            "platform": "discord",
            "type": "social",
            "source": "tester",
            "content": "CA: ...",
            "mentions": [],
            "confidence": 0.9,
            "ts": 125.0,
            "id": "dc1",
            "contract": "ghi",
        }
        yield SocialSignal(
            platform="discord",
            source="z",
            type="social",
            content="yo",
            mentions=[],
            confidence=0.7,
            ts=3.0,
            id="3",
            contract="ghi",
        )

    monkeypatch.setattr(stream_social, "stream_twitter", fake_twitter)
    monkeypatch.setattr(stream_social, "stream_telegram", fake_telegram)
    monkeypatch.setattr(stream_social, "stream_discord", fake_discord)

    results = []
    async for sig in stream_social.stream_social():
        results.append(sig)

    # Should have yielded 6 signals total (2 from each source)
    assert len(results) == 6
    platforms = {sig.platform for sig in results}
    assert platforms == {"twitter", "telegram", "discord"}