from pydantic import BaseModel, Field
from typing import Optional


class SocialSignal(BaseModel):
    platform: str  # NEW: telegram | discord | twitter
    source: str
    symbol: str | None = None
    contract: str | None = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    text: Optional[str] = None
    url: Optional[str] = None
    timestamp: float | None = None
    caller: str | None = None


class TradeDecision(BaseModel):
    action: str
    reason: str
    size_eth: float = 0.0
    max_slippage_bps: int = 300
    expected_price_impact_bps: int = 0
    contract: str | None = None
    symbol: str | None = None
