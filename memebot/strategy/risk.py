from memebot.config import settings
from memebot.solana.jupiter import estimate_price_impact_solana


def can_enter_solana(token_mint: str, size_base: float):
    if not settings.wsol_mint:
        return False, "no_wsol_configured", 0, 0

    # Check buy (SOL -> token)
    buy_q = estimate_price_impact_solana(
        settings.wsol_mint, token_mint, int(size_base * 1e9)
    )
    if not buy_q.get("ok"):
        return False, "no_buy_route", 0, 0

    # Check sell (token -> SOL)
    sell_q = estimate_price_impact_solana(
        token_mint, settings.wsol_mint, int(size_base * 1e9)
    )
    if not sell_q.get("ok"):
        return (
            False,
            "no_sell_route",
            buy_q.get("out_amount", 0),
            buy_q.get("impact_bps", 0),
        )

    return True, "ok", buy_q.get("out_amount", 0), buy_q.get("impact_bps", 0)
