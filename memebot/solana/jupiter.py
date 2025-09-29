import requests
from memebot.config import settings


def get_quote(
    input_mint: str,
    output_mint: str,
    amount: int,
    slippage_bps: int = 300,
    only_direct_routes: bool = False,
) -> dict:
    if settings.mock_jupiter:
        return {"ok": True, "out_amount": int(amount * 120), "impact_bps": 30}
    url = f"{settings.jupiter_base}/quote"
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": str(amount),
        "slippageBps": str(slippage_bps),
        "onlyDirectRoutes": "true" if only_direct_routes else "false",
    }
    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        return {"ok": False, "error": f"HTTP {r.status_code} {r.text}"}
    data = r.json()
    if not data or "data" not in data or not data["data"]:
        return {"ok": False, "error": "no_route"}
    route = data["data"][0]
    return {
        "ok": True,
        "route": route,
        "out_amount": int(route.get("outAmount", 0)),
        "impact_bps": int(abs(float(route.get("priceImpactPct", 0.0))) * 10000),
    }


def estimate_price_impact_solana(
    input_mint: str, output_mint: str, amount: int
) -> dict:
    q = get_quote(input_mint, output_mint, amount)
    if not q.get("ok"):
        return {
            "ok": False,
            "impact_bps": 0,
            "out_amount": 0,
            "error": q.get("error", "unknown"),
        }
    return {
        "ok": True,
        "impact_bps": q["impact_bps"],
        "out_amount": q["out_amount"],
        "route": q.get("route"),
    }
