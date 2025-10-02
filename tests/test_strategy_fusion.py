import time
from memebot.strategy.fusion import Signal, SignalMemory


def test_fusion_scoring_boost():
    mem = SignalMemory(decay_seconds=60)

    s1 = Signal(
        platform="twitter",
        type="social",
        source="user1",
        content="CA: token",
        mentions=["CA:token"],
        ts=time.time(),
    )
    fused1 = mem.fuse(s1)
    score1 = fused1.score

    s2 = Signal(
        platform="telegram",
        type="social",
        source="user2",
        content="CA: token",
        mentions=["CA:token"],
        ts=time.time(),
    )
    fused2 = mem.fuse(s2)
    score2 = fused2.score

    assert score1 > 0
    assert score2 >= score1 or abs(score2 - score1) < 1e-6


def test_fusion_decay():
    mem = SignalMemory(decay_seconds=1)

    s1 = Signal(
        platform="twitter",
        type="social",
        source="user1",
        content="CA: token",
        mentions=["CA:token"],
        ts=time.time() - 2,
    )
    fused = mem.fuse(s1)

    assert fused.score < 0.5  # decayed due to age


def test_fuse_self_skip(monkeypatch):
    """Ensure 'if s is sig: continue' branch is executed when only one signal exists."""
    mem = SignalMemory(decay_seconds=10)
    s1 = Signal(contract="abc", ts=time.time())
    fused = mem.fuse(s1)
    # Score should still be baseline 0.5 (no boosts from others)
    assert abs(fused.score - 0.5) < 1e-6


def test_fuse_self_skip_force(monkeypatch):
    """Force multiple signals so loop hits 'if s is sig: continue' explicitly."""
    mem = SignalMemory(decay_seconds=10)
    s1 = Signal(contract="abc", ts=time.time())
    s2 = Signal(contract="abc", ts=time.time())
    mem.add(s2)  # pre-populate memory
    fused = mem.fuse(s1)  # fuse s1, loop will iterate over s1 and skip
    assert fused is s1
    assert isinstance(fused.score, float)


def test_fuse_sets_score_and_returns_signal():
    """Ensure fuse always sets score and returns the same Signal instance."""
    mem = SignalMemory(decay_seconds=10)
    s1 = Signal(confidence=0.8, ts=time.time())
    fused = mem.fuse(s1)
    # Must be same object with updated score
    assert fused is s1
    assert isinstance(fused.score, float)
    assert fused.score > 0


def test_fuse_sets_score_and_returns_signal_always():
    """Extra test to ensure return path is covered explicitly."""
    mem = SignalMemory(decay_seconds=5)
    s1 = Signal()
    result = mem.fuse(s1)
    assert result is s1
    assert hasattr(result, "score")

def test_recent_returns_pruned_signals(tmp_path):
    mem = SignalMemory(decay_seconds=1)
    old = Signal(ts=time.time() - 5)   # too old, should be pruned
    new = Signal(ts=time.time())       # fresh, should remain
    mem._signals.extend([old, new])

    recents = mem.recent()
    # Only the fresh one should be there
    assert new in recents
    assert all(s.ts >= time.time() - 1 for s in recents)