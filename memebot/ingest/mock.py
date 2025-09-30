import logging
import time
from typing import Generator
from memebot.types import SocialSignal
from memebot.config.settings import settings

logger = logging.getLogger("memebot.mock")


def stream_mock_signals() -> Generator[SocialSignal, None, None]:
    """Generate fake signals for testing pipeline behavior."""
    logger.info("[mock] starting mock signal stream")

    sample = [
        SocialSignal(
            platform="mock",
            source="mock_source",
            symbol="USDC",
            contract=settings.mint("USDC"),
            confidence=0.82,
            text="caller alpha",
            caller="alpha",
        ),
        SocialSignal(
            platform="mock",
            source="mock_source",
            symbol="BONK",
            contract="So11111111111111111111111111111111111111112",
            confidence=0.78,
            text="caller beta",
            caller="beta",
        ),
    ]

    for sig in sample:
        logger.debug(f"[mock] captured signal: {sig.model_dump()}")
        yield sig
        time.sleep(1)  # simulate streaming pace
