import time
from memebot.strategy.fusion import Signal, SignalMemory

def test_fusion_scoring_boost():
    mem = SignalMemory(decay_seconds=60)

    s1 = Signal(platform="twitter", type="social", source="user1", content="CA: token", mentions=["CA:token"], ts=time.time())
    fused1 = mem.fuse(s1)
    score1 = fused1.score

    s2 = Signal(platform="telegram", type="social", source="user2", content="CA: token", mentions=["CA:token"], ts=time.time())
    fused2 = mem.fuse(s2)
    score2 = fused2.score

    assert score1 > 0
    assert score2 > score1  # boosted after second signal


def test_fusion_decay():
    mem = SignalMemory(decay_seconds=1)

    s1 = Signal(platform="twitter", type="social", source="user1", content="CA: token", mentions=["CA:token"], ts=time.time()-2)
    fused = mem.fuse(s1)

    assert fused.score < 0.5  # decayed due to age

