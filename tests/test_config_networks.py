
import os
from memebot.config import Settings

def test_eth_defaults():
    os.environ["NETWORK"] = "ethereum"
    s = Settings()
    assert s.network == "ethereum"
    assert s.chain_id in (1, int(os.getenv("CHAIN_ID") or "1"))
    assert s.wrapped_native.lower().startswith("0x")
    assert s.uniswap_v2_router.lower().startswith("0x")

def test_bsc_defaults():
    os.environ["NETWORK"] = "bsc"
    s = Settings()
    assert s.network == "bsc"
    assert s.chain_id in (56, int(os.getenv("CHAIN_ID") or "56"))
    assert s.wrapped_native.lower().startswith("0x")
    assert s.uniswap_v2_router.lower().startswith("0x")

def test_solana_defaults():
    os.environ["NETWORK"] = "solana"
    s = Settings()
    assert s.network == "solana"
    assert s.wsol_mint == "So11111111111111111111111111111111111111112"
    assert s.jupiter_base.startswith("https://")
