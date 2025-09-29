import threading
import time


def check_exits(prices):
    # placeholder for test purposes
    return []


class ExitManager:
    def __init__(self, prices=None):
        self.prices = prices or {}

    def tick(self, mode="simulate", debug=False):
        exits = check_exits(self.prices)
        if debug and exits:
            print(f"[exit-manager] {len(exits)} exits triggered in {mode} mode")
        return exits

    def tick_exits(self, mode="simulate", debug=False):
        return self.tick(mode=mode, debug=debug)


class ExitLoop:
    def __init__(
        self, manager: ExitManager, mode="simulate", interval=2.0, tick_sec=None
    ):
        self.interval = tick_sec or interval
        self.manager = manager
        self.mode = mode
        self.thread = None
        self._stop = threading.Event()

    def _run(self, debug=False):
        while not self._stop.is_set():
            self.manager.tick_exits(mode=self.mode, debug=debug)
            time.sleep(self.interval)

    def start(self, debug=False):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, args=(debug,), daemon=True)
        self.thread.start()

    def stop(self):
        self._stop.set()
        if self.thread:
            self.thread.join(timeout=2)
