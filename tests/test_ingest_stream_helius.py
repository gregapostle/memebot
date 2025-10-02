import pytest
import queue
import threading
import time

import memebot.ingest.stream_helius as stream_helius
from memebot.strategy.fusion import Signal


def test_enqueue_and_stream_single_signal():
    """Ensure enqueue_signal puts into queue and stream yields it."""
    sig = Signal(
        platform="helius",
        type="wallet",
        source="test",
        content="hello",
        mentions=["mint"],
        confidence=1.0,
        contract="mint",
    )

    # Enqueue a signal
    stream_helius.enqueue_signal(sig)

    # Grab it from the generator
    gen = stream_helius.stream_helius()
    out = next(gen)
    assert isinstance(out, Signal)
    assert out.contract == "mint"


def test_stream_blocks_until_signal(monkeypatch):
    """Simulate blocking get with background thread pushing a signal."""

    # Ensure queue is empty before test
    while not stream_helius.helius_queue.empty():
        stream_helius.helius_queue.get_nowait()

    gen = stream_helius.stream_helius()

    sig = Signal(
        platform="helius",
        type="wallet",
        source="thread",
        content="world",
        mentions=["mint"],
        confidence=0.9,
        contract="mint2",
    )

    def delayed_put():
        time.sleep(0.1)
        stream_helius.enqueue_signal(sig)

    t = threading.Thread(target=delayed_put)
    t.start()

    out = next(gen)  # now guaranteed to get the new signal
    assert out.contract == "mint2"

    t.join(timeout=1)
    assert not t.is_alive()