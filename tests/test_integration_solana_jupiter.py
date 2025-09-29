
import os
import pytest
from memebot.solana.jupiter import estimate_price_impact_solana
from memebot.config import settings

live = os.getenv("LIVE_JUPITER", "0") == "1"

@pytest.mark.skipif(not live, reason="Set LIVE_JUPITER=1 to hit Jupiter API")
def test_live_jupiter_quote():
    out_mint = os.getenv("TEST_SOLANA_MINT", "")
    assert out_mint, "Provide TEST_SOLANA_MINT in env"
    res = estimate_price_impact_solana(settings.wsol_mint, out_mint, 1_000_000)
    assert res["ok"] is True
    assert res["out_amount"] >= 0
