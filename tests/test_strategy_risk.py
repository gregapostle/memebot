import importlib
import pytest
from memebot.strategy import risk


def test_no_wsol_configured(monkeypatch):
    monkeypatch.setattr(risk.settings, "wsol_mint", "")
    ok, reason, out_amt, impact = risk.can_enter_solana("mintX", 1.0)
    assert ok is False
    assert reason == "no_wsol_configured"
    assert out_amt == 0 and impact == 0


def test_no_buy_route(monkeypatch):
    monkeypatch.setattr(risk.settings, "wsol_mint", "SOLMINT")
    def fake_estimate(input_mint, output_mint, amount):
        return {"ok": False}
    monkeypatch.setattr(risk, "estimate_price_impact_solana", fake_estimate)

    ok, reason, out_amt, impact = risk.can_enter_solana("mintX", 1.0)
    assert ok is False
    assert reason == "no_buy_route"


def test_no_sell_route(monkeypatch):
    monkeypatch.setattr(risk.settings, "wsol_mint", "SOLMINT")
    calls = {"n": 0}
    def fake_estimate(input_mint, output_mint, amount):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"ok": True, "out_amount": 111, "impact_bps": 22}
        return {"ok": False}
    monkeypatch.setattr(risk, "estimate_price_impact_solana", fake_estimate)

    ok, reason, out_amt, impact = risk.can_enter_solana("mintX", 1.0)
    assert ok is False
    assert reason == "no_sell_route"
    assert out_amt == 111
    assert impact == 22


def test_success(monkeypatch):
    monkeypatch.setattr(risk.settings, "wsol_mint", "SOLMINT")
    def fake_estimate(input_mint, output_mint, amount):
        return {"ok": True, "out_amount": 222, "impact_bps": 33}
    monkeypatch.setattr(risk, "estimate_price_impact_solana", fake_estimate)

    ok, reason, out_amt, impact = risk.can_enter_solana("mintX", 1.0)
    assert ok is True
    assert reason == "ok"
    assert out_amt == 222
    assert impact == 33