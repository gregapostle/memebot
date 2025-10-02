import pytest
import asyncio
import json
import types
import runpy
from memebot.ingest.social import twitter_ingest


@pytest.mark.asyncio
async def test_fetch_tweets_parses_and_filters(monkeypatch):
    """Covers fetch_tweets: parsing valid JSON, filtering by last_seen."""
    sample_tweet = {"id": "111", "date": "2024-01-01", "content": "CA: something"}

    # Fake stdout that yields two tweets
    lines = [
        json.dumps(sample_tweet).encode(),
        json.dumps({"id": "222", "date": "2024-01-02", "content": "More CA:"}).encode(),
        b"",  # sentinel to stop
    ]
    it = iter(lines)

    class FakeStdout:
        def readline(self):
            return next(it)

    class FakeProc:
        stdout = FakeStdout()
        def terminate(self): pass

    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: FakeProc())

    twitter_ingest.last_seen.clear()
    tweets = await twitter_ingest.fetch_tweets("user1")
    assert any(t["id"] == "111" for t in tweets)
    assert "user1" in twitter_ingest.last_seen

    # Simulate already having last_seen to force filtering
    twitter_ingest.last_seen["user1"] = "200"
    tweets2 = await twitter_ingest.fetch_tweets("user1")
    assert tweets2 == []


@pytest.mark.asyncio
async def test_fetch_tweets_handles_bad_json(monkeypatch):
    """Covers fetch_tweets: invalid JSON lines are skipped."""
    lines = [b"{notjson}", b"", b""]

    class FakeStdout:
        def readline(self):
            return lines.pop(0)

    class FakeProc:
        stdout = FakeStdout()
        def terminate(self): pass

    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: FakeProc())

    out = await twitter_ingest.fetch_tweets("user2")
    assert out == []


@pytest.mark.asyncio
async def test_stream_twitter_yields_and_filters(monkeypatch):
    """Covers stream_twitter normal operation and keyword filter."""
    tweet = {"id": "123", "date": "2024-01-01", "content": "New CA: minted"}
    async def fake_fetch(user): return [tweet]

    monkeypatch.setattr(twitter_ingest, "fetch_tweets", fake_fetch)
    twitter_ingest.TRACK_USERS[:] = ["mockuser"]
    twitter_ingest.TRACK_KEYWORDS[:] = ["CA:"]

    # Patch sleep so the infinite loop breaks quickly
    called = {}
    async def fake_sleep(_): called["done"] = True; raise asyncio.CancelledError()
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    sigs = []
    try:
        async for sig in twitter_ingest.stream_twitter():
            sigs.append(sig)
    except asyncio.CancelledError:
        pass

    assert sigs
    assert sigs[0]["platform"] == "twitter"
    assert "CA:" in sigs[0]["mentions"]
    assert "done" in called


@pytest.mark.asyncio
async def test_stream_twitter_handles_no_users(monkeypatch):
    """Covers early return when TRACK_USERS empty."""
    twitter_ingest.TRACK_USERS[:] = [""]

    agen = twitter_ingest.stream_twitter()  # async generator
    result = await anext(agen, None)  # safely get first yielded value or None
    assert result is None


@pytest.mark.asyncio
async def test_stream_twitter_handles_fetch_exception(monkeypatch):
    """Covers error handling path in stream_twitter."""
    async def bad_fetch(user): raise RuntimeError("boom")
    monkeypatch.setattr(twitter_ingest, "fetch_tweets", bad_fetch)
    twitter_ingest.TRACK_USERS[:] = ["baduser"]

    # Patch sleep to stop loop
    async def fake_sleep(_): raise asyncio.CancelledError()
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    try:
        async for _ in twitter_ingest.stream_twitter():
            pass
    except asyncio.CancelledError:
        pass  # expected

@pytest.mark.asyncio
async def test_fetch_tweets_no_stdout(monkeypatch):
    """Covers case where proc.stdout is None."""
    class FakeProc:
        stdout = None
        def terminate(self): pass
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: FakeProc())

    out = await twitter_ingest.fetch_tweets("userX")
    assert out == []


@pytest.mark.asyncio
async def test_fetch_tweets_breaks_on_empty_line_explicit(monkeypatch):
    """Explicitly hit the `if not line: break` branch in fetch_tweets."""
    lines = [b"", b"something"]  # first iteration triggers `if not line:`
    class FakeStdout:
        def readline(self): return lines.pop(0)
    class FakeProc:
        stdout = FakeStdout()
        def terminate(self): pass
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: FakeProc())

    out = await twitter_ingest.fetch_tweets("userZ")
    assert out == []

@pytest.mark.asyncio
async def test_fetch_tweets_hits_break_branch(monkeypatch):
    """Force hitting the `if not line: break` line."""
    class FakeStdout:
        def readline(self): return None  # not b"", so loop body runs
    
    class FakeProc:
        stdout = FakeStdout()
        def terminate(self): pass
    
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: FakeProc())
    
    out = await twitter_ingest.fetch_tweets("userBreak")
    assert out == []