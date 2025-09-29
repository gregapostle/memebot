import os
from pathlib import Path
import datetime


def _data_dir():
    return Path(os.getenv("MEMEBOT_DATA_DIR", "."))


def daily_loss_exceeded(cap_sol: float) -> bool:
    path = _data_dir() / "positions_closed.csv"
    if not path.exists():
        return False

    today = datetime.date.today()
    total_loss = 0.0
    with open(path) as f:
        next(f, None)  # skip header
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 9:
                continue
            ts_close = float(parts[1])
            pnl_base = float(parts[8])
            date = datetime.date.fromtimestamp(ts_close)
            if date == today and pnl_base < 0:
                total_loss += -pnl_base
    return total_loss >= cap_sol
