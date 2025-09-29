
import os, importlib
from memebot.exec import pnl

def test_empty_report(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pnl)
    r = pnl.report()
    assert r.trades == 0 and r.net_base == 0.0

def test_simple_report(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pnl)
    path = pnl._data_dir() / "positions_closed.csv"
    with open(path, "w") as f:
        f.write("ts_open,ts_close,chain,base,quote,entry_base,entry_out_raw,exit_base,pnl_base,reason\n")
        f.write("1,2,solana,SOL,TokenMintA,1.0,1000,1.3,0.3,take_profit\n")
        f.write("3,4,solana,SOL,TokenMintB,1.0,1000,0.8,-0.2,stop_loss\n")
    r = pnl.report()
    assert r.trades == 2
    assert abs(r.net_base - 0.1) < 1e-9
    assert r.winners == 1 and r.losers == 1
