
import pytest
import memebot.onchain.uniswap_v2 as uni

@pytest.fixture(autouse=True)
def patch_get_amounts_out(monkeypatch):
    def fake_get_amounts_out(amount_in, path):
        return [amount_in, amount_in * 1000]
    monkeypatch.setattr(uni, "get_amounts_out", fake_get_amounts_out)
    yield

def test_estimate_price_impact_unit():
    amount_in = 10**18
    path = [
        "0x000000000000000000000000000000000000dEaD",
        "0x000000000000000000000000000000000000bEEF",
    ]
    res = uni.estimate_price_impact(amount_in, path)
    assert res["ok"] is True
    assert res["impact_bps"] >= 0
    assert res["out_wei"] > 0
