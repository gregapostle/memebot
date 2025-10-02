import importlib
import os
import csv
import time
import pathlib
import pytest
from memebot.exec import positions as pos


def test_pathproxy_methods(tmp_path):
    p = pos._PathProxy(lambda: tmp_path / "file.txt")
    # __fspath__ and __str__
    assert str(p) == str(tmp_path / "file.txt")
    assert os.fspath(p) == str(tmp_path / "file.txt")
    # __truediv__
    assert (p / "x").name == "x"
    # __getattr__ forwards
    assert (p.parent).exists()


def test_write_csv_header_only(tmp_path):
    f = tmp_path / "out.csv"
    pos._write_csv(f, [])
    text = f.read_text()
    assert "ts_open" in text and "reason" in text


def test_env_exit_rules(monkeypatch):
    monkeypatch.setenv("TP_PCT", "5")
    monkeypatch.setenv("SL_PCT", "-10")
    monkeypatch.setenv("TRAIL_PCT", "2")
    monkeypatch.setenv("MIN_HOLD_SEC", "1")
    r = pos.ENV_EXIT_RULES()
    assert r.tp_pct == 5.0
    assert r.sl_pct == -10.0
    assert r.trail_pct == 2.0
    assert r.min_hold_sec == 1.0


def test_tick_exits_take_profit(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pos)
    pos._write_csv(pos.OPEN_CSV, [])
    pos._write_csv(pos.CLOSED_CSV, [])
    pos.open_position("solana", "SOL", "Mint", 1.0, 1000.0)

    def fake_estimate(*a, **k):
        return {"ok": True, "out_amount": int(2.0 * 1_000_000_000)}
    monkeypatch.setattr(pos, "estimate_price_impact_solana", fake_estimate)

    rules = pos.ExitRules()
    rules.min_hold_sec = 0
    res = pos.tick_exits(rules=rules)
    assert res["closed"] == 1


def test_tick_exits_stop_loss(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pos)
    pos._write_csv(pos.OPEN_CSV, [])
    pos._write_csv(pos.CLOSED_CSV, [])
    pos.open_position("solana", "SOL", "Mint", 10.0, 1000.0)

    def fake_estimate(*a, **k):
        return {"ok": True, "out_amount": int(1.0 * 1_000_000_000)}  # exit_base=1.0
    monkeypatch.setattr(pos, "estimate_price_impact_solana", fake_estimate)

    rules = pos.ExitRules()
    rules.min_hold_sec = 0
    rules.sl_pct = 0  # triggers stop_loss
    res = pos.tick_exits(rules=rules)
    assert res["closed"] == 1


def test_tick_exits_trailing_exit(monkeypatch, tmp_path):
    """Covers line 220: trigger trailing stop exit."""
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pos)

    # Write an open position with a peak much higher than current pnl
    row = {
        "ts_open": time.time() - 100,  # held long enough
        "chain": "solana",
        "base": "SOL",
        "quote": "TokenMintA",
        "entry_base": 1.0,
        "entry_out_raw": 1000.0,
        "note": "peak=50.0",  # high peak
    }
    pos._write_csv(pos._open_csv(), [row])
    pos._write_csv(pos._closed_csv(), [])

    # Fake Jupiter quote with exit_base much lower than peak
    def fake_estimate_price_impact_solana(input_mint, output_mint, amount):
        # exit_base = 0.8, so pnl_pct = -20%
        return {"ok": True, "out_amount": int(0.8 * 1_000_000_000)}

    monkeypatch.setattr(pos, "estimate_price_impact_solana", fake_estimate_price_impact_solana)

    rules = pos.ExitRules()
    rules.min_hold_sec = 0
    rules.trail_pct = 10.0  # trailing threshold

    res = pos.tick_exits(rules=rules)
    assert res["closed"] == 1  # should close due to trailing stop

def test_tick_exits_no_open_positions(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pos)
    pos._write_csv(pos.OPEN_CSV, [])
    pos._write_csv(pos.CLOSED_CSV, [])
    res = pos.tick_exits()
    assert res == {"closed": 0}

def test_pathproxy_exists(tmp_path):
    f = tmp_path / "foo.csv"
    f.write_text("hello")
    proxy = pos._PathProxy(lambda: f)
    assert proxy.exists()  # triggers ._p().exists()


def test_read_csv_and_list_open_positions(tmp_path, monkeypatch):
    f = tmp_path / "open.csv"
    f.write_text("ts_open,chain,base,quote,entry_base,entry_out_raw,note\n1,solana,SOL,XYZ,1.0,100.0,\n")
    rows = pos._read_csv(f)
    assert rows and rows[0]["chain"] == "solana"

    # patch _open_csv to point here and hit list_open_positions
    monkeypatch.setattr(pos, "_open_csv", lambda: f)
    listed = pos.list_open_positions()
    assert listed == rows

def test_tick_exits_remaining_open(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pos)
    pos._write_csv(pos.OPEN_CSV, [])
    pos._write_csv(pos.CLOSED_CSV, [])

    pos.open_position("solana", "SOL", "Mint", entry_base=1.0, entry_out_raw=1000.0)

    # mock price impact but not enough to trigger close
    def fake_estimate(*a, **k):
        return {"ok": True, "out_amount": int(1.01 * 1_000_000_000)}
    monkeypatch.setattr(pos, "estimate_price_impact_solana", fake_estimate)

    rules = pos.ExitRules()
    rules.min_hold_sec = 0
    rules.tp_pct = 999  # unreachable
    rules.sl_pct = -999 # unreachable

    res = pos.tick_exits(rules=rules)
    # no closes, so remaining still exists
    assert res["closed"] == 0
    assert pos.list_open_positions()  # still in OPEN_CSV

    #--#--

def test_read_csv_returns_empty_if_missing(tmp_path, monkeypatch):
    """Covers line 88: _read_csv returns [] when file doesn't exist."""
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pos)

    fake_file = tmp_path / "nonexistent.csv"
    result = pos._read_csv(fake_file)
    assert result == []  # ✅ should hit the early return


def test_tick_exits_quote_none(monkeypatch, tmp_path):
    """Covers line 193: skip/continue when quote is None."""
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pos)

    # Create CSV with an empty quote field
    rows = [{
        "ts_open": 1234567890.0,
        "chain": "solana",
        "base": "SOL",
        "quote": "",   # empty -> treated as missing
        "entry_base": 1.0,
        "entry_out_raw": 1000.0,
    }]
    pos._write_csv(pos._open_csv(), rows)
    pos._write_csv(pos._closed_csv(), [])

    # Fail if estimate_price_impact_solana gets called
    def bad_call(*a, **k):
        raise AssertionError("estimate_price_impact_solana should not be called")

    monkeypatch.setattr(pos, "estimate_price_impact_solana", bad_call)

    res = pos.tick_exits()
    assert res["closed"] == 0

def test_tick_exits_no_closures(monkeypatch, tmp_path):
    """Covers line 220: returning at the end with no closures."""
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pos)

    # Patch estimate_price_impact_solana to return no out_amount
    def fake_quote(input_mint, output_mint, amount):
        return {"ok": True, "out_amount": 0}

    monkeypatch.setattr(pos, "estimate_price_impact_solana", fake_quote)

    # Open one valid position
    pos.open_position(
        chain="solana",
        base="SOL",
        quote="TokenMintA",
        entry_base=1.0,
        entry_out_raw=1000.0,
    )

    res = pos.tick_exits()
    assert res == {"closed": 0}  # ✅ hits the final return
