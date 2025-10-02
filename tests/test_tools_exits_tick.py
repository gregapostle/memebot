import runpy, sys, pytest, time, subprocess, importlib, memebot.tools.exits_tick as exits_tick
from typer.testing import CliRunner
import memebot.tools.exits_tick as exits_tick

runner = CliRunner()

def test_exits_tick_runs_as_module():
    """
    Ensure `python -m memebot.tools.exits_tick` starts and exits quickly.
    Run it in a subprocess with a timeout to avoid hanging due to the infinite loop.
    """
    start = time.time()
    proc = subprocess.Popen(
        [sys.executable, "-m", "memebot.tools.exits_tick", "--every", "1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Let it run briefly
        time.sleep(2)
        proc.terminate()
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError("exits_tick did not stop in time")

    out, err = proc.communicate()
    assert b"Starting exit loop" in out
    assert proc.returncode in (0, -15)  # normal exit or terminated
    assert time.time() - start < 10

def test_exits_tick_cli_once(monkeypatch):
    """Run the CLI once and exit cleanly with KeyboardInterrupt."""
    class FakeExitManager:
        def tick_exits(self, mode="simulate", debug=False):
            return []

    monkeypatch.setattr(exits_tick, "ExitManager", FakeExitManager)
    monkeypatch.setattr(exits_tick.time, "sleep", lambda _: (_ for _ in ()).throw(KeyboardInterrupt()))

    result = runner.invoke(
        exits_tick.app,
        ["--every=1", "--mode=simulate"],
    )
    assert result.exit_code in (0, 1, 130)
    assert "Starting exit loop" in result.output


def test_exits_tick_debug_and_interrupt(monkeypatch):
    """Covers debug logging and KeyboardInterrupt handling."""
    class FakeExitManager:
        def __init__(self):
            self.calls = 0
        def tick_exits(self, mode="simulate", debug=False):
            self.calls += 1
            if self.calls == 1:
                return ["exit1"]
            raise KeyboardInterrupt()

    monkeypatch.setattr(exits_tick, "ExitManager", FakeExitManager)
    monkeypatch.setattr(exits_tick.time, "sleep", lambda _: None)

    result = runner.invoke(
        exits_tick.app,
        ["--every=1", "--mode=simulate", "--debug"],
    )

    assert result.exit_code in (0, 1, 130)
    assert "Starting exit loop" in result.output
    assert "[loop] Triggered" in result.output or "Stopped." in result.output
