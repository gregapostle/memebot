from memebot.types import TradeDecision
import random


def simulate_swap(decision: TradeDecision) -> dict:
    if decision.action != "buy":
        return {"ok": False, "reason": "no_trade"}
    slip_bps = min(
        500, decision.expected_price_impact_bps + int(random.uniform(10, 120))
    )
    return {"ok": True, "filled": True, "slippage_bps": slip_bps}
