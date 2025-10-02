import importlib
import os
import tempfile
import csv
from memebot.exec import pnl


def test_report_no_file(monkeypatch, tmp_path):
    # Point MEMEBOT_DATA_DIR to a temp dir that has no CSV yet
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pnl)

    res = pnl.report()
    assert isinstance(res, pnl.PnLSummary)
    assert res.trades == 0
    assert res.gross_base == 0.0
    assert res.net_base == 0.0
    assert res.winners == 0
    assert res.losers == 0


def test_report_with_data(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pnl)

    # Create a fake closed positions CSV
    path = pnl._closed_csv()
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["ts_close", "exit_base", "pnl_base"]
        )
        writer.writeheader()
        writer.writerow({"ts_close": "100", "exit_base": "2.0", "pnl_base": "1.0"})
        writer.writerow({"ts_close": "200", "exit_base": "3.0", "pnl_base": "-1.5"})

    res = pnl.report(since_ts=50)
    assert res.trades == 2
    assert res.gross_base == 5.0
    assert res.net_base == -0.5
    assert res.winners == 1
    assert res.losers == 1