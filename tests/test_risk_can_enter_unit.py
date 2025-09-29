
import importlib
from memebot.strategy.risk import can_enter_solana

def test_can_enter_ok(monkeypatch):
    import memebot.strategy.risk as risk
    def fake_buy(a,b,c): return {"ok": True, "out_amount": 1000, "impact_bps": 500}
    def fake_sell(a,b,c): return {"ok": True, "out_amount": 100, "impact_bps": 200}
    monkeypatch.setattr(risk, "estimate_price_impact_solana", lambda a,b,c: fake_buy(a,b,c) if a.startswith("So") else fake_sell(a,b,c))
    ok, reason, out, imp = can_enter_solana("TokenMintA", 0.1)
    assert ok is True and reason == "ok" and out == 1000 and imp == 500

def test_can_enter_no_sell(monkeypatch):
    import memebot.strategy.risk as risk
    def fake_est(a,b,c):
        if a.startswith("So"): return {"ok": True, "out_amount": 1000, "impact_bps": 200}
        return {"ok": False}
    monkeypatch.setattr(risk, "estimate_price_impact_solana", fake_est)
    ok, reason, *_ = can_enter_solana("TokenMintA", 0.1)
    assert ok is False and reason == "no_sell_route"
