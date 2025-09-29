from pathlib import Path
from memebot.backtest.runner import load_signals

def test_load_signals(tmp_path: Path):
    f = tmp_path / "signals.jsonl"
    f.write_text(
        '{"platform":"twitter","type":"social","source":"user","content":"CA:token","mentions":["token"],"confidence":0.8,"contract":"token","ts":12345}\n'
    )
    signals = load_signals(f)
    assert len(signals) == 1
    assert signals[0].platform == "twitter"
    assert signals[0].contract == "token"

