
import importlib
from memebot.exec.positions import open_position, tick_exits, _write_csv, CLOSED_CSV
import memebot.exec.positions as pos

def test_tick_exits_with_mock_quotes(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pos)
    _write_csv(pos.OPEN_CSV, [])
    _write_csv(pos.CLOSED_CSV, [])
    p = open_position(chain="solana", base="SOL", quote="TokenMintA", entry_base=1.0, entry_out_raw=1000.0)

    def fake_estimate_price_impact_solana(input_mint, output_mint, amount):
        return {"ok": True, "out_amount": int(1.3 * 1_000_000_000), "impact_bps": 50}
    monkeypatch.setattr(pos, "estimate_price_impact_solana", fake_estimate_price_impact_solana)

    rules = pos.ExitRules()
    rules.min_hold_sec = 0
    res = tick_exits(rules=rules)
    assert res["closed"] == 1
    assert CLOSED_CSV.exists()
