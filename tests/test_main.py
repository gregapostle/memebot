import runpy
import sys
import pytest
import time
from typer.testing import CliRunner
from memebot import main
from memebot.types import SocialSignal

runner = CliRunner()
app = main.app


@pytest.fixture(autouse=True)
def patch_jupiter(monkeypatch):
    """Patch Jupiter API so tests don’t hit the network."""
    monkeypatch.setattr(
        "memebot.solana.jupiter.get_quote",
        lambda *a, **k: {
            "ok": True,
            "out_amount": 1000,
            "impact_bps": 10,
            "route": {"mock": True},
        },
    )

def test_run_simulate(monkeypatch):
    result = runner.invoke(app, ["--mode", "simulate", "--max-signals", "1", "--debug"])
    assert result.exit_code == 0


def test_run_paper(monkeypatch):
    result = runner.invoke(app, ["--mode", "paper", "--max-signals", "1", "--debug"])
    assert result.exit_code == 0


def make_signal():
    return SocialSignal(
        platform="test",
        source="unit",
        symbol="BONK",
        contract="MintAddr",
        confidence=1.0,
        text="test",
        timestamp=time.time(),
        caller="tester",
    )


def test_handle_signal_live_trade(monkeypatch):
    sig = make_signal()
    monkeypatch.setattr(main.settings, "network", "solana")
    monkeypatch.setattr(main.settings, "wsol_mint", "So11111111111111111111111111111111111111112")
    monkeypatch.setattr(main, "get_quote", lambda *a, **k: {"ok": True, "out_amount": 1000})
    monkeypatch.setattr(main, "trade_live", lambda q: {"ok": True, "tx": "sig"})

    result = main.handle_signal(sig, debug=True, mode="live")
    assert result is not None  # should return a decision


def test_run_with_telegram_and_discord(monkeypatch):
    sig = make_signal()
    # Patch watchlist and settings
    monkeypatch.setitem(main.watchlist, "telegram_groups", ["g1"])
    monkeypatch.setitem(main.watchlist, "telegram_api_id", "id")
    monkeypatch.setitem(main.watchlist, "telegram_api_hash", "hash")
    monkeypatch.setitem(main.watchlist, "discord_channels", ["c1"])
    monkeypatch.setitem(main.watchlist, "discord_token", "token")
    monkeypatch.setattr(main.settings, "enable_telegram", True)
    monkeypatch.setattr(main.settings, "enable_discord", True)
    monkeypatch.setattr(main.settings, "enable_mock", False)

    # ✅ async replacement (since main uses asyncio.run)
    async def fake_run_telegram_ingest(cb, debug=False):
        cb(sig)

    # ✅ sync replacement (since main calls directly in thread)
    def fake_run_discord_ingest(cb, debug=False):
        cb(sig)

    monkeypatch.setattr(main, "run_telegram_ingest", fake_run_telegram_ingest)
    monkeypatch.setattr(main, "run_discord_ingest", fake_run_discord_ingest)

    result = runner.invoke(app, ["--mode", "simulate", "--max-signals", "1"])
    assert result.exit_code == 0


def test_run_with_exit_loop(monkeypatch):
    class DummyExitLoop:
        def __init__(self, manager, mode):
            self.started = False
            self.stopped = False
        def start(self, debug=False): self.started = True
        def stop(self): self.stopped = True

    monkeypatch.setattr(main, "ExitLoop", DummyExitLoop)
    monkeypatch.setattr(main.settings, "enable_mock", False)
    monkeypatch.setitem(main.watchlist, "telegram_groups", None)
    monkeypatch.setitem(main.watchlist, "discord_channels", None)

    result = runner.invoke(app, ["--mode", "simulate", "--max-signals", "0", "--enable-exits"])
    assert result.exit_code == 0


def test_handle_signal_live_trade_no_quote(monkeypatch, caplog):
    """Covers branch where get_quote returns not ok."""
    sig = make_signal()
    monkeypatch.setattr(main.settings, "network", "solana")
    monkeypatch.setattr(main.settings, "wsol_mint", "So111...")

    # Force decision to 'buy' so we hit the quote logic
    class FakeDecision:
        action = "buy"
        reason = "forced"
        max_slippage_bps = 100
    monkeypatch.setattr(main, "decide", lambda *a, **k: FakeDecision())

    monkeypatch.setattr(main, "get_quote", lambda *a, **k: {"ok": False})

    with caplog.at_level("WARNING"):
        result = main.handle_signal(sig, debug=True, mode="live")

    assert result is not None
    assert any("no_quote" in m for m in caplog.messages)

def test_handle_signal_live_missing_wsol_or_contract(monkeypatch):
    """Covers branch where wsol_mint is missing or contract is None."""
    sig = make_signal()
    monkeypatch.setattr(main.settings, "network", "solana")

    # Force decision to "buy"
    class FakeDecision:
        action = "buy"
        reason = "forced"
        max_slippage_bps = 100
    monkeypatch.setattr(main, "decide", lambda *a, **k: FakeDecision())
    monkeypatch.setattr(main, "plan_entry", lambda sig: (True, "ok", 1.0, 100, 5))

    # Case 1: missing wsol_mint
    monkeypatch.setattr(main.settings, "wsol_mint", None)
    result1 = main.handle_signal(sig, debug=True, mode="live")
    assert result1.action == "buy"

    # Case 2: contract is None
    sig.contract = None
    monkeypatch.setattr(main.settings, "wsol_mint", "So111...")
    result2 = main.handle_signal(sig, debug=True, mode="live")
    assert result2.action == "buy"

def test_handle_signal_live_trade_with_result(monkeypatch, caplog):
    """Covers branch where trade_live executes and logs result."""
    sig = make_signal()
    monkeypatch.setattr(main.settings, "network", "solana")
    monkeypatch.setattr(main.settings, "wsol_mint", "So11111111111111111111111111111111111111112")

    # Force a "buy" decision
    class FakeDecision:
        action = "buy"
        reason = "forced"
        max_slippage_bps = 100
    monkeypatch.setattr(main, "decide", lambda *a, **k: FakeDecision())
    monkeypatch.setattr(main, "plan_entry", lambda sig: (True, "ok", 1.0, 100, 5))

    # Patch get_quote and trade_live
    monkeypatch.setattr(main, "get_quote", lambda *a, **k: {"ok": True, "out_amount": 1000})
    monkeypatch.setattr(main, "trade_live", lambda q: {"ok": True, "tx": "signature123"})

    with caplog.at_level("INFO"):
        result = main.handle_signal(sig, debug=True, mode="live")

    # Assert decision returned and trade_live log hit
    assert result.action == "buy"
    assert any("signature123" in m for m in caplog.messages)

def test_run_with_mock_stream_hits_sleep(monkeypatch):
    """Covers branch with mock stream so time.sleep is executed."""
    sig = make_signal()

    monkeypatch.setattr(main.settings, "enable_mock", True)

    # Fake stream that yields exactly one signal
    def fake_stream():
        yield sig
    monkeypatch.setattr(main, "stream_mock_signals", lambda: fake_stream())

    # Patch time.sleep to avoid real delay
    called = {}
    monkeypatch.setattr(time, "sleep", lambda x: called.setdefault("slept", True))

    # Use max-signals=0 so it doesn't return before sleep
    result = runner.invoke(app, ["--mode", "simulate", "--max-signals", "0"])
    assert result.exit_code == 0
    assert "slept" in called

def test_main_entrypoint_runs_app(monkeypatch):
    """Covers the `if __name__ == '__main__': app()` line in main.py."""
    import sys, runpy

    called = {}

    # Fake Typer that supports both .command and being called
    class DummyApp:
        def command(self, *a, **k):
            def deco(func):
                return func
            return deco
        def __call__(self, *a, **k):
            called["ok"] = True

    # Patch typer.Typer so main.app = DummyApp()
    monkeypatch.setattr("memebot.main.typer.Typer", lambda *a, **k: DummyApp())

    # Avoid pytest args leaking into Typer
    monkeypatch.setattr(sys, "argv", ["main"])

    # Remove preloaded module to avoid RuntimeWarning
    sys.modules.pop("memebot.main", None)

    # Run module as __main__
    try:
        runpy.run_module("memebot.main", run_name="__main__")
    except SystemExit as e:
        assert e.code == 0

    # Ensure our DummyApp was called
    assert "ok" in called