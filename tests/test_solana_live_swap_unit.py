import requests_mock
from memebot.solana.trade import request_swap_tx, trade_live
from memebot.solana.jupiter import get_quote
from memebot.config import settings

def test_request_swap_tx_unit(monkeypatch):
    # mock quote
    quote = {"ok": True, "route": {"foo": "bar"}}
    with requests_mock.Mocker() as m:
        m.post("https://quote-api.jup.ag/v6/swap", json={"swapTransaction":"AQID"})
        res = request_swap_tx(quote)
        assert res["ok"] and res["tx_b64"] == "AQID"

def test_trade_live_blocked(monkeypatch):
    monkeypatch.setenv("ALLOW_LIVE", "0")
    import importlib
    import memebot.solana.trade as tr
    importlib.reload(tr)
    res = tr.trade_live({"ok": True, "route": {"x":1}})
    assert not res["ok"] and res["error"] == "live_disabled"
