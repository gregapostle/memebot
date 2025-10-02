import pytest
import types
from memebot.ingest import mock
from memebot.types import SocialSignal

def test_stream_mock_signals_yields_signals(monkeypatch):
    # Patch time.sleep so tests don’t actually wait
    monkeypatch.setattr(mock.time, "sleep", lambda s: None)

    # Collect all signals
    signals = list(mock.stream_mock_signals())

    # We expect two SocialSignal objects
    assert all(isinstance(sig, SocialSignal) for sig in signals)
    assert {sig.symbol for sig in signals} == {"USDC", "BONK"}
    assert signals[0].caller == "alpha"
    assert signals[1].caller == "beta"

def test_logger_output(monkeypatch, caplog):
    # Patch sleep again
    monkeypatch.setattr(mock.time, "sleep", lambda s: None)

    with caplog.at_level("DEBUG"):
        signals = list(mock.stream_mock_signals())
    # Ensure debug logs mention captured signals
    assert any("captured signal" in m for m in caplog.messages)
    assert len(signals) == 2