import time
from memebot.types import SocialSignal
from memebot.config import settings

# Known mainnet mints
MAINNET_BONK = "DezXAZ8bq4hGq4SjuY6rHn1uP1N1xgJg7zQxgZPL46J"


def stream_mock_signals():
    # Avoid SOL as a target; trade WSOL->USDC or WSOL->BONK on mainnet
    if settings.solana_cluster == "mainnet":
        sample = [
            SocialSignal(
                source="mock",
                symbol="USDC",
                contract=settings.mint("USDC"),
                confidence=0.82,
                text="caller alpha",
                caller="alpha",
            ),
            SocialSignal(
                source="mock",
                symbol="BONK",
                contract=MAINNET_BONK,
                confidence=0.78,
                text="caller beta",
                caller="beta",
            ),
        ]
    else:
        # Devnet often lacks liquidity; pair with USDC mint
        sample = [
            SocialSignal(
                source="mock",
                symbol="USDC",
                contract=settings.mint("USDC"),
                confidence=0.82,
                text="caller alpha",
                caller="alpha",
            ),
            # Second signal still points at USDC to avoid WSOL target
            SocialSignal(
                source="mock",
                symbol="USDC",
                contract=settings.mint("USDC"),
                confidence=0.75,
                text="caller beta",
                caller="beta",
            ),
        ]

    for s in sample:
        yield s
        time.sleep(0.25)
