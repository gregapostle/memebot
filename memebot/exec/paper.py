from dataclasses import dataclass
from typing import List
import csv
import json
from pathlib import Path
import os


@dataclass
class PaperTrade:
    ts: float
    chain: str
    side: str  # "buy" or "sell"
    base: str
    quote: str
    size_base: float
    out_amount: float
    price_impact_bps: int
    slippage_bps: int
    reason: str
    entry_value: float = 0.0

    @property
    def action(self) -> str:
        return self.side


_trades: List[PaperTrade] = []


def _trades_csv() -> Path:
    data_dir = Path(os.getenv("MEMEBOT_DATA_DIR", "."))
    return data_dir / "trades.csv"


def _trades_jsonl() -> Path:
    data_dir = Path(os.getenv("MEMEBOT_DATA_DIR", "."))
    return data_dir / "trades.jsonl"


def append_trade(trade: PaperTrade):
    if trade.size_base > 0 and trade.out_amount > 0 and trade.entry_value == 0:
        trade.entry_value = trade.out_amount
    _trades.append(trade)

    file_path = _trades_csv()
    write_header = not file_path.exists() or file_path.stat().st_size == 0

    with file_path.open("a", newline="") as f:
        fieldnames = [
            "ts",
            "chain",
            "side",
            "base",
            "quote",
            "size_base",
            "out_amount",
            "price_impact_bps",
            "slippage_bps",
            "reason",
            "entry_value",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(trade.__dict__)

    with _trades_jsonl().open("a") as f:
        f.write(json.dumps(trade.__dict__) + "\n")


def get_all_trades() -> List[PaperTrade]:
    return list(_trades)


def reset_trades():
    global _trades
    _trades = []
