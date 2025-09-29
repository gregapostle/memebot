import queue
from typing import Generator
from memebot.strategy.fusion import Signal

# Shared queue for webhook pushes
helius_queue: "queue.Queue[Signal]" = queue.Queue()


def enqueue_signal(sig: Signal):
    """Called by helius_webhook after parsing a Jupiter swap txn."""
    helius_queue.put(sig)


def stream_helius() -> Generator[Signal, None, None]:
    """
    Generator that yields signals from the helius_queue.
    Used inside main.py like other streams.
    """
    while True:
        sig = helius_queue.get()  # blocking until a signal arrives
        yield sig
