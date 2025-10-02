from memebot.exec.sim import simulate_swap
from memebot.types import TradeDecision


def test_simulate_swap_returns_trade_buy():
    decision = TradeDecision(action="buy", reason="test", contract="Token")
    result = simulate_swap(decision)
    assert isinstance(result, dict)
    assert result["ok"] is True
    assert "slippage_bps" in result
    assert result["filled"] is True


def test_simulate_swap_non_buy_branch():
    decision = TradeDecision(action="sell", reason="test", contract="Token")
    result = simulate_swap(decision)
    assert result == {"ok": False, "reason": "no_trade"}