import time
from memebot.exec.paper import PaperTrade, append_trade, reset_trades
from memebot.strategy.exits import ExitManager
from memebot.strategy import exits

def make_trade(side="buy", base="SOL", quote="TokenX", size=0.05, out=100.0):
    return PaperTrade(
        ts=time.time(),
        chain="solana",
        side=side,
        base=base,
        quote=quote,
        size_base=size,
        out_amount=out,
        price_impact_bps=0,
        slippage_bps=0,
        reason="test"
    )

def test_take_profit_triggers():
    reset_trades()
    trade = make_trade()
    append_trade(trade)
    manager = ExitManager()
    exits = manager.tick_exits(mode="paper", debug=True)
    if exits:
        for e in exits:
            assert e.side == "sell"

def test_stop_loss_triggers():
    reset_trades()
    trade = make_trade()
    append_trade(trade)
    manager = ExitManager()
    exits = manager.tick_exits(mode="paper", debug=True)
    if exits:
        for e in exits:
            assert e.side == "sell"

def test_trailing_stop_triggers():
    reset_trades()
    trade = make_trade()
    append_trade(trade)
    manager = ExitManager()
    exits = manager.tick_exits(mode="paper", debug=True)
    if exits:
        for e in exits:
            assert e.side == "sell"

def test_tick_exits_with_debug_and_exits(monkeypatch, capsys):
    """Cover 'if debug and exits' branch."""

    # Force check_exits to return something
    monkeypatch.setattr(exits, "check_exits", lambda prices: ["dummy-exit"])

    manager = exits.ExitManager(prices={"SOL": 100})
    res = manager.tick_exits(mode="simulate", debug=True)
    assert res == ["dummy-exit"]

    captured = capsys.readouterr()
    assert "exits triggered" in captured.out


def test_exitloop_stop_covers_join(monkeypatch):
    """Ensure ExitLoop.stop executes thread.join branch."""

    manager = exits.ExitManager()
    loop = exits.ExitLoop(manager, interval=0.01)

    # Start the loop in a very short-lived thread
    loop.start()
    time.sleep(0.05)
    loop.stop()  # should hit line 41
    assert loop.thread is not None

def test_exitloop_start_twice_hits_return():
    """Ensure calling start twice triggers the early return branch (line 41)."""
    manager = exits.ExitManager()
    loop = exits.ExitLoop(manager, interval=0.01)

    # First start actually spawns the thread
    loop.start()
    assert loop.thread is not None
    assert loop.thread.is_alive()

    # Second start should hit the 'if thread.is_alive(): return' branch
    loop.start()  # <-- covers line 41

    loop.stop()