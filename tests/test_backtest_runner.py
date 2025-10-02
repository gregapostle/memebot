import subprocess
import sys
import json
from pathlib import Path
import pytest
import importlib
import typer
from typer.testing import CliRunner

import memebot.backtest.runner as runner

runner_runner = CliRunner()


def make_signal_file(tmp_path: Path, signals: list[dict]) -> Path:
    """Helper to create a JSONL file with signals."""
    f = tmp_path / "signals.jsonl"
    with f.open("w") as fh:
        for sig in signals:
            fh.write(json.dumps(sig) + "\n")
    return f


def test_runner_with_sample_jsonl(tmp_path):
    """Ensure runner executes with a valid sample JSONL file."""
    f = make_signal_file(tmp_path, [{"platform": "mock", "source": "src", "symbol": "BONK"}])

    result = subprocess.run(
        [sys.executable, "-m", "memebot.backtest.runner", str(f)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Loaded 1 signals" in result.stdout


def test_runner_runs_as_module(tmp_path):
    """Run runner as a module with a dummy empty file path."""
    f = make_signal_file(tmp_path, [])
    result = subprocess.run(
        [sys.executable, "-m", "memebot.backtest.runner", str(f)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_load_signals_and_low_score(tmp_path, monkeypatch):
    """Patch SignalMemory to force low score, ensuring no trades are made."""

    class FakeSig:
        def __init__(self):
            self.platform = "mock"
            self.source = "tester"
            self.contract = "abc"
            self.ts = 123.0
            self.score = 0.5
            self.__dict__.update(vars(self))

    # Patch fuse to always return a low-score signal
    monkeypatch.setattr(runner.SignalMemory, "fuse", lambda self, sig: FakeSig())

    f = make_signal_file(tmp_path, [{"platform": "mock", "source": "tester"}])

    # ✅ Positional arg for file, explicitly cast to str
    result = runner_runner.invoke(
        runner.app,
        [str(f)],   # just the positional file arg
        standalone_mode=False,
    )

    assert result.exit_code == 0
    assert "Completed 0 buys" in result.stdout


def test_run_with_trade_and_exits(tmp_path, monkeypatch):
    """Simulate a trade being executed and exits being ticked."""
    class FakeSig:
        def __init__(self):
            self.platform = "mock"
            self.source = "tester"
            self.contract = "abc"
            self.ts = 123.0
            self.score = 2.0
            self.__dict__.update(vars(self))

    monkeypatch.setattr(runner.SignalMemory, "fuse", lambda self, sig: FakeSig())
    monkeypatch.setattr(runner, "plan_entry", lambda sig: (True, "ok", None, 100, 5))

    class FakeDecision:
        action = "buy"
        max_slippage_bps = 50
        reason = "test"

    monkeypatch.setattr(runner, "decide", lambda sig, liq_ok, est_price_impact_bps: FakeDecision())
    monkeypatch.setattr(runner.ExitManager, "tick_exits", lambda self, mode, debug=False: [])

    f = make_signal_file(tmp_path, [{"platform": "mock", "source": "tester"}])
    result = runner_runner.invoke(
        runner.app,
        [str(f)],   # just the positional file arg
        standalone_mode=False,
    )
    assert result.exit_code == 0
    assert "Completed 1 buys" in result.stdout


def test_run_disable_exits(tmp_path, monkeypatch):
    """Ensure exits can be disabled."""
    monkeypatch.setattr(runner.SignalMemory, "fuse", lambda self, s: s)
    monkeypatch.setattr(runner, "plan_entry", lambda sig: (True, "ok", None, 100, 5))

    class NoDecision:
        action = "hold"
        max_slippage_bps = 0
        reason = "skip"

    monkeypatch.setattr(runner, "decide", lambda sig, liq_ok, est_price_impact_bps: NoDecision())

    f = make_signal_file(tmp_path, [{"platform": "mock", "source": "tester"}])
    result = runner_runner.invoke(
        runner.app,
        [str(f)],   # just the positional file arg
        standalone_mode=False,
    )
    assert result.exit_code == 0
    assert "Completed 0 buys" in result.stdout


def test_main_entrypoint(monkeypatch, tmp_path):
    """Ensure runner.main() entrypoint works without error."""
    f = make_signal_file(tmp_path, [{"platform": "mock", "source": "tester"}])

    # Patch run so we don’t execute full backtest
    monkeypatch.setattr(runner, "run", lambda file, **kwargs: None)

    result = runner_runner.invoke(
        runner.app,
        [str(f)],   # just the positional file arg
        standalone_mode=False,
    )
    assert result.exit_code == 0



def test_load_signals_skips_blank(tmp_path):
    """Ensure blank lines in the JSONL file are ignored."""
    f = make_signal_file(tmp_path, [{"platform": "mock"}])
    with f.open("a") as fh:
        fh.write("\n")  # add a blank line
        fh.write(json.dumps({"platform": "mock2"}) + "\n")
    signals = runner.load_signals(f)
    assert len(signals) == 2  # blank line skipped


def test_run_bad_file_raises():
    """Ensure missing file raises a BadParameter."""
    result = runner_runner.invoke(
        runner.app,
        ["nonexistent.jsonl"],
        standalone_mode=False,
    )
    assert result.exit_code != 0
    assert isinstance(result.exception, typer.BadParameter)
    assert "not found" in str(result.exception)


def test_run_skips_low_score(tmp_path, monkeypatch):
    """Force a signal with low score so it's skipped."""
    f = make_signal_file(tmp_path, [{"platform": "mock"}])

    class FakeSig:
        platform = "m"
        source = "s"
        contract = "c"
        ts = 1.0
        score = 0.5
        __dict__ = {}

    monkeypatch.setattr(runner.SignalMemory, "fuse", lambda self, sig: FakeSig)

    result = runner_runner.invoke(
        runner.app,
        [str(f)],
        standalone_mode=False,
    )
    assert "Completed 0 buys" in result.stdout


def test_run_skips_allowlist(tmp_path, monkeypatch):
    """Force plan_entry to return not ok so trade is skipped by allowlist."""
    f = make_signal_file(tmp_path, [{"platform": "mock"}])

    class FakeSig:
        platform = "m"
        source = "s"
        contract = "c"
        ts = 1.0
        score = 2.0
        __dict__ = {}

    monkeypatch.setattr(runner.SignalMemory, "fuse", lambda self, sig: FakeSig)
    monkeypatch.setattr(runner, "plan_entry", lambda sig: (False, "reject", None, 0, 0))

    result = runner_runner.invoke(
        runner.app,
        [str(f)],
        standalone_mode=False,
    )
    assert "Completed 0 buys" in result.stdout


def test_run_triggers_exits(tmp_path, monkeypatch):
    """Ensure exits branch executes when tick_exits returns values."""
    f = make_signal_file(tmp_path, [{"platform": "mock"}])

    class FakeSig:
        platform = "m"
        source = "s"
        contract = "c"
        ts = 1.0
        score = 2.0
        __dict__ = {}

    monkeypatch.setattr(runner.SignalMemory, "fuse", lambda self, sig: FakeSig)
    monkeypatch.setattr(runner, "plan_entry", lambda sig: (True, "ok", None, 1, 1))
    monkeypatch.setattr(
        runner,
        "decide",
        lambda sig, liq_ok, est_price_impact_bps: type(
            "D", (), {"action": "buy", "max_slippage_bps": 1, "reason": "r"}
        )(),
    )
    monkeypatch.setattr(runner.ExitManager, "tick_exits", lambda self, mode, debug=False: ["exit"])

    result = runner_runner.invoke(
        runner.app,
        [str(f), "--debug"],
        standalone_mode=False,
    )
    assert "Triggered" in result.stdout


def test_main_function_invokes_app(monkeypatch, tmp_path):
    """Call runner.main() with args to cover that path."""
    f = make_signal_file(tmp_path, [{"platform": "mock"}])

    called = {}
    def fake_app(argv): called["yes"] = argv
    monkeypatch.setattr(runner, "app", fake_app)

    runner.main([str(f)])
    assert "yes" in called

def test_module_entrypoint_executes(monkeypatch, tmp_path):
    dummy_file = tmp_path / "dummy.jsonl"
    dummy_file.write_text("")

    monkeypatch.setattr(sys, "argv", ["runner", str(dummy_file)])

    # Run the app directly, suppressing sys.exit
    runner_runner = CliRunner()
    result = runner_runner.invoke(runner.app, [str(dummy_file)], standalone_mode=False)

    assert result.exit_code == 0
    assert "Loaded 0 signals" in result.stdout