from memebot.types import SocialSignal, TradeDecision

MIN_CONFIDENCE = 0.7
MAX_SLIPPAGE_BPS = 300


def decide(
    signal: SocialSignal, liq_ok: bool, est_price_impact_bps: int
) -> TradeDecision:
    if not signal.contract:
        return TradeDecision(action="skip", reason="no_contract")
    if signal.confidence < MIN_CONFIDENCE:
        return TradeDecision(
            action="skip",
            reason="low_confidence",
            contract=signal.contract,
            symbol=signal.symbol,
        )
    if not liq_ok:
        return TradeDecision(
            action="skip",
            reason="insufficient_liquidity",
            contract=signal.contract,
            symbol=signal.symbol,
        )
    if est_price_impact_bps > MAX_SLIPPAGE_BPS:
        return TradeDecision(
            action="skip",
            reason="too_much_price_impact",
            contract=signal.contract,
            symbol=signal.symbol,
        )
    return TradeDecision(
        action="buy",
        reason="rule_pass",
        size_eth=0.05,
        max_slippage_bps=MAX_SLIPPAGE_BPS,
        expected_price_impact_bps=est_price_impact_bps,
        contract=signal.contract,
        symbol=signal.symbol,
    )
