
import requests_mock
import pytest
import requests
from memebot.solana import jupiter
from memebot.solana.jupiter import get_quote, estimate_price_impact_solana

def test_jupiter_quote_unit(monkeypatch, requests_mock):
    """Ensure normal quote flow works with requests_mock."""
    # Force real HTTP path (not mock_jupiter)
    monkeypatch.setattr(jupiter.settings, "mock_jupiter", False)

    url = f"{jupiter.settings.jupiter_base}/quote"
    requests_mock.get(url, json={
        "data": [{"outAmount": "123456", "priceImpactPct": 0.0123}]
    })

    q = get_quote("So11111111111111111111111111111111111111112", "TokenMint", 1_000_000)
    assert q["ok"] is True

    est = estimate_price_impact_solana(
        "So11111111111111111111111111111111111111112", "TokenMint", 1_000_000
    )
    assert est["ok"] is True
    assert est["impact_bps"] == 123
    assert est["out_amount"] == 123456

    
def test_get_quote_mock(monkeypatch):
    """Covers settings.mock_jupiter branch (line 13)."""
    monkeypatch.setattr(jupiter.settings, "mock_jupiter", True)
    q = jupiter.get_quote("in", "out", 10)
    assert q["ok"] is True
    assert "out_amount" in q
    monkeypatch.setattr(jupiter.settings, "mock_jupiter", False)



def test_get_quote_http_error(monkeypatch, requests_mock):
    """Covers HTTP != 200 branch (line 24)."""
    monkeypatch.setattr(jupiter.settings, "mock_jupiter", False)

    url = f"{jupiter.settings.jupiter_base}/quote"
    requests_mock.get(url, status_code=500, text="fail")
    q = jupiter.get_quote("in", "out", 10)
    assert not q["ok"]
    assert "HTTP 500" in q["error"]




def test_get_quote_no_route(monkeypatch, requests_mock):
    """Covers empty data / no route branch (line 27)."""
    monkeypatch.setattr(jupiter.settings, "mock_jupiter", False)

    url = f"{jupiter.settings.jupiter_base}/quote"
    requests_mock.get(url, json={"data": []})
    q = jupiter.get_quote("in", "out", 10)
    assert not q["ok"]
    assert q["error"] == "no_route"


def test_estimate_price_impact_solana_error(monkeypatch):
    """Covers error return in estimate_price_impact_solana (line 42)."""
    monkeypatch.setattr(jupiter, "get_quote", lambda *a, **k: {"ok": False, "error": "boom"})
    q = jupiter.estimate_price_impact_solana("in", "out", 10)
    assert not q["ok"]
    assert q["error"] == "boom"