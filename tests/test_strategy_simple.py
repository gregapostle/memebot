from memebot.strategy import simple
from memebot.types import SocialSignal, TradeDecision


def make_signal(**kwargs):
    return SocialSignal(
        platform="mock",
        source="tester",
        symbol=kwargs.get("symbol", "BONK"),
        contract=kwargs.get("contract", "mint"),
        confidence=kwargs.get("confidence", 0.8),
    )


def test_simple_strategy_returns_decision():
    sig = make_signal()
    decision = simple.decide(sig, liq_ok=True, est_price_impact_bps=50.0)

    assert isinstance(decision, TradeDecision)
    assert decision.action in ("buy", "skip")
    assert decision.contract == "mint"
    assert decision.symbol == "BONK"


def test_no_contract_skips():
    sig = make_signal(contract=None)
    decision = simple.decide(sig, liq_ok=True, est_price_impact_bps=50)
    assert decision.action == "skip"
    assert decision.reason == "no_contract"


def test_low_confidence_skips():
    sig = make_signal(confidence=0.5)
    decision = simple.decide(sig, liq_ok=True, est_price_impact_bps=50)
    assert decision.action == "skip"
    assert decision.reason == "low_confidence"


def test_liquidity_not_ok_skips():
    sig = make_signal()
    decision = simple.decide(sig, liq_ok=False, est_price_impact_bps=50)
    assert decision.action == "skip"
    assert decision.reason == "insufficient_liquidity"


def test_too_much_price_impact_skips():
    sig = make_signal()
    decision = simple.decide(sig, liq_ok=True, est_price_impact_bps=1000)
    assert decision.action == "skip"
    assert decision.reason == "too_much_price_impact"