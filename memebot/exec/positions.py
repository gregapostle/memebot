import csv
import os
import time
import pathlib
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from memebot.config import settings
from memebot.solana.jupiter import estimate_price_impact_solana


def _data_dir() -> pathlib.Path:
    d = pathlib.Path(os.getenv("MEMEBOT_DATA_DIR", "./data"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _open_csv() -> pathlib.Path:
    return _data_dir() / "positions_open.csv"


def _closed_csv() -> pathlib.Path:
    return _data_dir() / "positions_closed.csv"


class _PathProxy:
    def __init__(self, getter):
        self._getter = getter

    def _p(self) -> pathlib.Path:
        return self._getter()

    def exists(self):
        return self._p().exists()

    def __str__(self):
        return str(self._p())

    def __fspath__(self):
        return str(self._p())

    def __truediv__(self, other):
        return self._p() / other

    def __getattr__(self, name):
        return getattr(self._p(), name)


OPEN_CSV = _PathProxy(_open_csv)
CLOSED_CSV = _PathProxy(_closed_csv)


@dataclass
class OpenPosition:
    ts_open: float
    chain: str
    base: str
    quote: str
    entry_base: float
    entry_out_raw: float
    note: str = ""


@dataclass
class ClosedPosition:
    ts_open: float
    ts_close: float
    chain: str
    base: str
    quote: str
    entry_base: float
    entry_out_raw: float
    exit_base: float
    pnl_base: float
    reason: str


class ExitRules:
    """Defaults; can be overridden via ENV_EXIT_RULES()"""

    tp_pct = 20.0
    sl_pct = -30.0
    trail_pct = 10.0
    min_hold_sec = 10.0


def _read_csv(path: pathlib.Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: pathlib.Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        header = [
            "ts_open",
            "chain",
            "base",
            "quote",
            "entry_base",
            "entry_out_raw",
            "note",
            "ts_close",
            "exit_base",
            "pnl_base",
            "reason",
        ]
        with open(path, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=header).writeheader()
        return
    keys = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def list_open_positions():
    return _read_csv(_open_csv())


def open_position(
    chain: str,
    base: str,
    quote: str,
    entry_base: float,
    entry_out_raw: float,
    note: str = "",
) -> OpenPosition:
    pos = OpenPosition(
        ts_open=time.time(),
        chain=chain,
        base=base,
        quote=quote,
        entry_base=float(entry_base),
        entry_out_raw=float(entry_out_raw),
        note=note,
    )
    rows = _read_csv(_open_csv())
    rows.append(asdict(pos))
    _write_csv(_open_csv(), rows)
    return pos


def ENV_EXIT_RULES() -> ExitRules:
    r = ExitRules()
    r.tp_pct = float(os.getenv("TP_PCT", str(r.tp_pct)) or r.tp_pct)
    r.sl_pct = float(os.getenv("SL_PCT", str(r.sl_pct)) or r.sl_pct)
    r.trail_pct = float(os.getenv("TRAIL_PCT", str(r.trail_pct)) or r.trail_pct)
    r.min_hold_sec = float(
        os.getenv("MIN_HOLD_SEC", str(r.min_hold_sec)) or r.min_hold_sec
    )
    return r


def tick_exits(
    target_gain_pct: float = 20.0,
    target_stop_pct: float = -30.0,
    rules: Optional[ExitRules] = None,
) -> Dict[str, int]:
    open_path = _open_csv()
    closed_path = _closed_csv()
    open_rows = _read_csv(open_path)
    if rules is None:
        rules = ENV_EXIT_RULES()
    if not open_rows:
        _write_csv(closed_path, _read_csv(closed_path))
        return {"closed": 0}
    remaining: List[Dict[str, Any]] = []
    closed: List[Dict[str, Any]] = _read_csv(closed_path)
    closed_count = 0
    now = time.time()
    for r in open_rows:
        chain = r.get("chain", "solana")
        base = r.get("base", "SOL")
        quote = r.get("quote")
        entry_base = float(r.get("entry_base", 0.0))
        entry_out_raw = float(r.get("entry_out_raw", 0.0))
        should_close = False
        reason = ""
        ts_open = float(r.get("ts_open", now))
        exit_base = 0.0

        if chain == "solana":
            amt = int(entry_out_raw)
            if quote is None:
                continue
            q = estimate_price_impact_solana(str(quote), settings.wsol_mint, amt)  # type: ignore[arg-type]

            if q.get("ok") and int(q.get("out_amount", 0)) > 0:
                exit_base = int(q["out_amount"]) / 1_000_000_000
                hold_ok = (now - ts_open) >= rules.min_hold_sec
                if hold_ok:
                    pnl_pct = (
                        0.0
                        if entry_base == 0
                        else (exit_base - entry_base) / entry_base * 100.0
                    )
                    if pnl_pct >= rules.tp_pct:
                        should_close, reason = True, "take_profit"
                    elif pnl_pct <= rules.sl_pct:
                        should_close, reason = True, "stop_loss"
                    else:
                        note = r.get("note", "") or ""
                        peak_key = "peak="
                        peak = (
                            float(note.split(peak_key)[1])
                            if peak_key in note
                            else pnl_pct
                        )
                        new_peak = max(peak, pnl_pct)
                        r["note"] = f"peak={new_peak:.6f}"
                        if peak - pnl_pct >= rules.trail_pct:
                            should_close, reason = True, "trailing_exit"

        if should_close:
            cp = ClosedPosition(
                ts_open=float(r.get("ts_open", now)),
                ts_close=now,
                chain=chain,
                base=base,
                quote=str(quote),
                entry_base=entry_base,
                entry_out_raw=entry_out_raw,
                exit_base=exit_base,
                pnl_base=exit_base - entry_base,
                reason=reason or "rule_exit",
            )
            closed.append(asdict(cp))
            closed_count += 1
        else:
            remaining.append(r)

    _write_csv(closed_path, closed)
    _write_csv(open_path, remaining)
    return {"closed": closed_count}
