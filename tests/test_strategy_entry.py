import os, importlib, time
from memebot.strategy.entry import plan_entry
from memebot.types import SocialSignal
from memebot.exec import pnl
import pytest


def test_sizing_by_conf_and_caller(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETWORK", "solana")
    monkeypatch.setenv("BASE_SIZE_SOL", "0.1")
    monkeypatch.setenv("SIZE_BY_CONF", "0.7:1.0,0.8:1.5,0.9:2.0")
    monkeypatch.setenv("CALLER_ALLOWLIST", "alpha:2.0,beta:1.0")
    import memebot.strategy.entry as entry
    importlib.reload(entry)
    monkeypatch.setattr(entry, "can_enter_solana", lambda mint, sz: (True, "ok", 1000, 300))

    sig = SocialSignal(
        platform="test",
        source="test",
        symbol="X",
        contract="TokenMintX",
        confidence=0.9,
        caller="alpha",
    )
    ok, reason, size_sol, *_ = entry.plan_entry(sig)
    assert ok and abs(size_sol - 0.1 * 2.0 * 2.0) < 1e-9


def test_daily_cap_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETWORK", "solana")
    monkeypatch.setenv("BASE_SIZE_SOL", "0.05")
    monkeypatch.setenv("DAILY_LOSS_CAP_SOL", "0.5")
    import memebot.strategy.entry as entry
    importlib.reload(entry)

    importlib.reload(pnl)
    path = pnl._data_dir() / "positions_closed.csv"
    with open(path, "w") as f:
        f.write("ts_open,ts_close,chain,base,quote,entry_base,entry_out_raw,exit_base,pnl_base,reason\n")
        now = time.time()
        f.write(f"1,{now},solana,SOL,Token,1.0,1000,0.4,-0.6,stop_loss\n")

    monkeypatch.setattr(entry, "can_enter_solana", lambda mint, sz: (True, "ok", 1000, 300))

    sig = SocialSignal(
        platform="test",
        source="test",
        symbol="Y",
        contract="TokenMintY",
        confidence=0.8,
        caller="any",
    )
    ok, reason, *_ = entry.plan_entry(sig)
    assert not ok and reason == "daily_cap_reached"


def test_load_size_conf_table_and_empty(monkeypatch):
    import memebot.strategy.entry as entry
    monkeypatch.setenv("SIZE_BY_CONF", "0.5:1.0,0.8:2.0")
    importlib.reload(entry)
    tbl = entry._load_size_conf_table()
    assert tbl == {0.5: 1.0, 0.8: 2.0}

    # Empty should return {}
    monkeypatch.setenv("SIZE_BY_CONF", "")
    importlib.reload(entry)
    assert entry._load_size_conf_table() == {}

def test_load_caller_allowlist_and_empty(monkeypatch):
    import memebot.strategy.entry as entry
    monkeypatch.setenv("CALLER_ALLOWLIST", "alice:1.5,BOB:2.0")
    importlib.reload(entry)
    tbl = entry._load_caller_allowlist()
    assert tbl == {"alice": 1.5, "bob": 2.0}

    # Empty returns {}
    monkeypatch.setenv("CALLER_ALLOWLIST", "")
    importlib.reload(entry)
    assert entry._load_caller_allowlist() == {}

def test_caller_not_allowed(monkeypatch):
    import memebot.strategy.entry as entry
    # Allowlist only has bob
    monkeypatch.setenv("CALLER_ALLOWLIST", "bob:1.0")
    monkeypatch.setenv("BASE_SIZE_SOL", "0.1")
    importlib.reload(entry)

    # Patch can_enter_solana to never be called
    monkeypatch.setattr(entry, "can_enter_solana", lambda *a, **k: (True, "ok", 0, 0))

    sig = SocialSignal(
        platform="test",
        source="src",
        symbol="X",
        contract="MintX",
        confidence=0.9,
        caller="alice",  # not in allowlist
    )
    ok, reason, *_ = entry.plan_entry(sig)
    assert not ok and reason == "caller_not_allowed"

def test_no_contract(monkeypatch):
    import memebot.strategy.entry as entry
    monkeypatch.setenv("CALLER_ALLOWLIST", "")
    monkeypatch.setenv("BASE_SIZE_SOL", "0.1")
    importlib.reload(entry)

    # Patch can_enter_solana so it would fail if called
    monkeypatch.setattr(entry, "can_enter_solana", lambda *a, **k: (_ for _ in ()).throw(Exception("should not be called")))

    sig = SocialSignal(
        platform="test",
        source="src",
        symbol="X",
        contract=None,  # No contract
        confidence=0.9,
        caller="any",
    )
    ok, reason, *_ = entry.plan_entry(sig)
    assert not ok and reason == "no_contract"