
import requests_mock
from memebot.solana.jupiter import get_quote, estimate_price_impact_solana

def test_jupiter_quote_unit():
    with requests_mock.Mocker() as m:
        m.get("https://quote-api.jup.ag/v6/quote", json={
            "data": [{"outAmount": "123456", "priceImpactPct": 0.0123}]
        })
        q = get_quote("So11111111111111111111111111111111111111112", "TokenMint", 1_000_000)
        assert q["ok"] is True
        est = estimate_price_impact_solana("So11111111111111111111111111111111111111112", "TokenMint", 1_000_000)
        assert est["ok"] is True
        assert est["impact_bps"] == 123
        assert est["out_amount"] == 123456
