# Updated fusion.py
# memebot/strategy/fusion.py

from dataclasses import dataclass, field
import time
from typing import Optional, List


@dataclass
class Signal:
    platform: str = "unknown"
    type: str = "social"
    source: str = ""
    content: str = ""
    mentions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    ts: float = field(default_factory=lambda: time.time())
    id: Optional[str] = None
    contract: Optional[str] = None
    symbol: Optional[str] = None
    caller: Optional[str] = None
    url: Optional[str] = None
    score: float = 0.0


# Backward compatibility
SocialSignal = Signal


class SignalMemory:
    """Rolling memory of signals, with decay support."""

    def __init__(self, decay_seconds: float = 3600):
        self.decay_seconds = decay_seconds
        self._signals: List[Signal] = []

    def add(self, sig: Signal):
        self._signals.append(sig)
        self._prune()

    def recent(self) -> List[Signal]:
        self._prune()
        return list(self._signals)

    def _prune(self):
        cutoff = time.time() - self.decay_seconds
        self._signals = [s for s in self._signals if s.ts >= cutoff]

    def fuse(self, sig: Signal) -> Signal:
        """Fuse a new signal into memory, return enriched signal with .score"""
        self.add(sig)
        now = time.time()

        # Start score with confidence, or a baseline if unset
        score = sig.confidence if sig.confidence and sig.confidence > 0 else 0.5

        # Boost if multiple recent signals mention same contract
        for s in self._signals:
            if s is sig:
                continue
            if s.contract and s.contract == sig.contract:
                if now - s.ts < self.decay_seconds:
                    score += 0.5

        # Apply decay
        age = now - sig.ts
        if self.decay_seconds > 0 and age > 0:
            decay = max(0.0, 1.0 - age / self.decay_seconds)
            score *= decay

        sig.score = score
        return sig
