import os
from memebot.config import settings
from memebot.strategy.risk import can_enter_solana
from memebot.strategy.fusion import Signal as SocialSignal
import memebot.tools.pnl as pnl


def _load_size_conf_table():
    raw = os.getenv("SIZE_BY_CONF", "")
    tbl = {}
    for part in raw.split(","):
        if not part.strip():
            continue
        k, v = part.split(":")
        tbl[float(k)] = float(v)
    return tbl


def _load_caller_allowlist():
    raw = os.getenv("CALLER_ALLOWLIST", "")
    tbl = {}
    for part in raw.split(","):
        if not part.strip():
            continue
        k, v = part.split(":")
        tbl[k.lower()] = float(v)
    return tbl


def _conf_multiplier(conf: float, table: dict[float, float]) -> float:
    best = 1.0
    for threshold, mult in sorted(table.items()):
        if conf >= threshold:
            best = mult
    return best


def plan_entry(signal: SocialSignal):
    base_size = float(os.getenv("BASE_SIZE_SOL", str(settings.base_size_sol)))

    # 1. Daily loss cap check
    cap = float(os.getenv("DAILY_LOSS_CAP_SOL", "0"))
    if cap > 0 and pnl.daily_loss_exceeded(cap):
        return False, "daily_cap_reached", 0.0, 0, 0

    # 2. Caller allowlist
    allow = _load_caller_allowlist()
    caller = (getattr(signal, "caller", "") or "").lower()
    caller_mult = 1.0
    if allow:
        if caller not in allow:
            return False, "caller_not_allowed", 0.0, 0, 0
        caller_mult = allow[caller]

    # 3. Confidence sizing
    size_conf_tbl = _load_size_conf_table()
    conf_mult = _conf_multiplier(signal.confidence, size_conf_tbl)

    print(
        f"[DEBUG] conf={signal.confidence}, conf_mult={conf_mult}, caller_mult={caller_mult}, base={base_size}"
    )

    size_native = base_size * caller_mult * conf_mult
    if not signal.contract:
        return False, "no_contract", 0.0, 0, 0
    ok, reason, out_amt, impact_bps = can_enter_solana(signal.contract, size_native)

    return ok, reason, size_native, out_amt, impact_bps
