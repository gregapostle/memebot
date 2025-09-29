
import os
import pytest
from memebot.config import Settings

have_rpc = bool(os.getenv("ALCHEMY_HTTP") or os.getenv("ETH_HTTP"))
token = os.getenv("TEST_TOKEN_ADDR", "")

@pytest.mark.skipif(not have_rpc or not token, reason="Requires ETH/BSC RPC and TEST_TOKEN_ADDR")
def test_live_quote_evm():
    s = Settings()
    from memebot.onchain.uniswap_v2 import estimate_buy_eth_to_token
    q = estimate_buy_eth_to_token(0.001, token)
    assert q["ok"] is True
    assert q["out_wei"] >= 0
