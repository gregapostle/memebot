import os, csv, importlib
from memebot.exec import paper as pt


def test_append_paper_trade(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pt)
    t = pt.PaperTrade(
        ts=1234567890.0,
        chain="solana",
        side="buy",
        base="SOL",
        quote="TokenMint",
        size_base=0.5,
        out_amount=12345.0,
        price_impact_bps=100,
        slippage_bps=300,
        reason="test",
    )
    pt.append_trade(t)
    path = pt._trades_csv()
    assert path.exists()
    rows = list(csv.DictReader(open(path)))
    assert len(rows) == 1
    assert rows[0]["chain"] == "solana"
    assert rows[0]["base"] == "SOL"

def test_papertrade_action_property(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pt)

    t = pt.PaperTrade(
        ts=1234567890.0,
        chain="solana",
        side="buy",
        base="SOL",
        quote="TokenMint",
        size_base=1.0,
        out_amount=1000.0,
        price_impact_bps=50,
        slippage_bps=100,
        reason="test",
    )

    # Directly check the property to execute line 25
    assert t.action == "buy"