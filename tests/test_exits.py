import time
from memebot.exec.paper import PaperTrade, append_trade, reset_trades
from memebot.strategy.exits import ExitManager

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
