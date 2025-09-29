import time
import threading
import pytest
from memebot.strategy.exits import ExitLoop, ExitManager

class DummyExitManager(ExitManager):
    def __init__(self):
        super().__init__(prices={})
        self.called = 0
        self.lock = threading.Lock()

    def tick_exits(self, mode="simulate", debug=False):
        with self.lock:
            self.called += 1
        return []

def test_exit_loop_runs_and_stops():
    manager = DummyExitManager()
    loop = ExitLoop(manager, mode="simulate", tick_sec=0.2)

    loop.start()
    time.sleep(0.7)  # give time for 2-3 ticks
    loop.stop()

    with manager.lock:
        calls = manager.called

    assert calls >= 2  # should have ticked at least twice
    assert not loop.thread.is_alive()

