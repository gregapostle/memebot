import pytest
import logging
import queue
from memebot.ingest.social import discord_ingest
from memebot.types import SocialSignal


def test_run_discord_ingest_basic(monkeypatch, caplog):
    """Ensure run_discord_ingest creates signals and calls the callback."""
    monkeypatch.setitem(discord_ingest.watchlist, "discord_channels", ["chan1", "chan2"])

    captured = []
    caplog.set_level(logging.DEBUG)

    discord_ingest.run_discord_ingest(captured.append, debug=True)

    # Two signals should be captured, one per channel
    assert len(captured) == 2
    for sig in captured:
        assert isinstance(sig, SocialSignal)
        assert sig.platform == "discord"
    # Debug logging should appear
    assert any("[discord] captured signal" in rec.message for rec in caplog.records)


def test_run_discord_ingest_no_channels(monkeypatch):
    """Ensure no signals are emitted when no channels are configured."""
    monkeypatch.setitem(discord_ingest.watchlist, "discord_channels", [])

    captured = []
    discord_ingest.run_discord_ingest(captured.append, debug=True)
    assert captured == []


@pytest.mark.asyncio
async def test_verify_discord_credentials_success(monkeypatch):
    """Ensure verify_discord_credentials succeeds with token set."""
    monkeypatch.setitem(discord_ingest.watchlist, "discord_token", "fake-token")
    user = await discord_ingest.verify_discord_credentials()
    assert user == "mock-discord-user"


@pytest.mark.asyncio
async def test_verify_discord_credentials_failure(monkeypatch):
    """Ensure verify_discord_credentials raises without token."""
    monkeypatch.setitem(discord_ingest.watchlist, "discord_token", None)
    with pytest.raises(RuntimeError):
        await discord_ingest.verify_discord_credentials()


def test_stream_discord(monkeypatch):
    """Ensure stream_discord yields SocialSignal objects using real threading/queue."""
    monkeypatch.setitem(discord_ingest.watchlist, "discord_channels", ["chanA"])

    gen = discord_ingest.stream_discord(limit=1)
    sigs = list(gen)
    assert len(sigs) == 1
    sig = sigs[0]
    assert isinstance(sig, SocialSignal)
    assert sig.platform == "discord"
    assert sig.source == "chanA"

def test_stream_discord_handles_sentinel(monkeypatch):
    """Ensure stream_discord gracefully stops when sentinel None is received."""
    # Patch run_discord_ingest to immediately push sentinel
    def fake_runner(callback, debug=False):
        callback(None)

    monkeypatch.setattr(discord_ingest, "run_discord_ingest", fake_runner)

    gen = discord_ingest.stream_discord(limit=1)
    results = list(gen)
    assert results == []  # should stop cleanly without yielding anything