import csv
import pathlib
import os
from dataclasses import dataclass


def _data_dir() -> pathlib.Path:
    d = pathlib.Path(os.getenv("MEMEBOT_DATA_DIR", "./data"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _closed_csv() -> pathlib.Path:
    return _data_dir() / "positions_closed.csv"


@dataclass
class PnLSummary:
    trades: int
    gross_base: float
    net_base: float
    winners: int
    losers: int


def report(since_ts: float | None = None) -> PnLSummary:
    path = _closed_csv()
    if not path.exists():
        return PnLSummary(0, 0.0, 0.0, 0, 0)
    rows = list(csv.DictReader(open(path)))
    if since_ts is not None:
        rows = [r for r in rows if float(r.get("ts_close", 0.0)) >= float(since_ts)]
    trades = len(rows)
    gross = sum(float(r.get("exit_base", 0.0)) for r in rows)
    net = sum(float(r.get("pnl_base", 0.0)) for r in rows)
    wins = sum(1 for r in rows if float(r.get("pnl_base", 0.0)) > 0)
    losses = trades - wins
    return PnLSummary(trades, gross, net, wins, losses)
