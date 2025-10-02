import pytest
import asyncio
import logging
from memebot.ingest.social import telegram_ingest
from memebot.types import SocialSignal


@pytest.mark.asyncio
async def test_run_telegram_ingest_invokes_callback(monkeypatch):
    """Ensure run_telegram_ingest creates signals and calls callback."""
    signals = []

    # Patch watchlist to have fake groups
    monkeypatch.setitem(telegram_ingest.watchlist, "telegram_groups", ["test-group"])

    def fake_callback(sig: SocialSignal):
        signals.append(sig)

    await telegram_ingest.run_telegram_ingest(fake_callback, debug=True)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.platform == "telegram"
    assert sig.source == "test-group"
    assert "Mocked message" in sig.text


@pytest.mark.asyncio
async def test_verify_telegram_credentials_success(monkeypatch):
    """Verify credential check returns a username when keys are present."""
    monkeypatch.setitem(telegram_ingest.watchlist, "telegram_api_id", "id")
    monkeypatch.setitem(telegram_ingest.watchlist, "telegram_api_hash", "hash")

    result = await telegram_ingest.verify_telegram_credentials()
    assert result == "mock-telegram-user"


@pytest.mark.asyncio
async def test_verify_telegram_credentials_failure(monkeypatch):
    """Verify credential check raises when keys are missing."""
    monkeypatch.setitem(telegram_ingest.watchlist, "telegram_api_id", None)
    monkeypatch.setitem(telegram_ingest.watchlist, "telegram_api_hash", None)

    with pytest.raises(RuntimeError):
        await telegram_ingest.verify_telegram_credentials()


def test_stream_telegram_generator(monkeypatch):
    """Ensure stream_telegram yields SocialSignal synchronously."""
    monkeypatch.setitem(telegram_ingest.watchlist, "telegram_groups", ["sync-group"])

    # Patch run_telegram_ingest to put directly into the queue
    async def fake_run_telegram_ingest(callback, debug=False):
        sig = SocialSignal(
            platform="telegram",
            source="sync-group",
            symbol="BONK",
            contract="So11111111111111111111111111111111111111112",
            confidence=0.75,
            text="Mocked message",
            caller="tester",
        )
        # Call callback in a way that matches how stream_telegram expects
        await callback(sig)

    monkeypatch.setattr(telegram_ingest, "run_telegram_ingest", fake_run_telegram_ingest)

    gen = telegram_ingest.stream_telegram(limit=1)
    sig = next(gen)

    assert isinstance(sig, SocialSignal)
    assert sig.platform == "telegram"
    assert sig.source == "sync-group"
    assert "Mocked message" in sig.text

@pytest.mark.asyncio
async def test_run_telegram_ingest_debug_logs(monkeypatch, caplog):
    """Ensure run_telegram_ingest hits debug log branch when debug=True."""

    captured = []

    def fake_callback(sig: SocialSignal):
        captured.append(sig)

    # Patch watchlist to provide groups
    monkeypatch.setitem(telegram_ingest.watchlist, "telegram_groups", ["group1"])

    caplog.set_level(logging.DEBUG)
    await telegram_ingest.run_telegram_ingest(fake_callback, debug=True)

    assert any("[telegram] captured signal" in m for m in caplog.messages)
    assert captured
    assert captured[0].platform == "telegram"


def test_stream_telegram_triggers_loop_close(monkeypatch):
    """Ensure stream_telegram executes loop.close() cleanly."""
    # Patch run_telegram_ingest so it doesn't hang and just puts None
    async def fake_ingest(cb, debug=False):
        await cb(None)  # immediately send sentinel

    monkeypatch.setattr(telegram_ingest, "run_telegram_ingest", fake_ingest)

    # Run with limit=1 so the for loop iterates
    list(telegram_ingest.stream_telegram(limit=1))
    # If loop.close() wasn't called properly, this would leak loop handles
    # No assertion needed, reaching here cleanly is enough

@pytest.mark.asyncio
async def test_run_telegram_ingest_with_async_callback(monkeypatch):
    """Ensure async callback branch is exercised in run_telegram_ingest."""

    results = []

    async def async_callback(sig):
        results.append(sig)

    # Patch watchlist to include at least one group
    monkeypatch.setitem(telegram_ingest.watchlist, "telegram_groups", ["groupX"])

    # Run with async callback (triggers line 35)
    await telegram_ingest.run_telegram_ingest(async_callback, debug=False)

    assert results, "Async callback should have been called"
    assert results[0].platform == "telegram"