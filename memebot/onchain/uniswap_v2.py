from web3 import Web3
from memebot.onchain.eth import w3
from memebot.config import settings

ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
        ],
        "name": "getAmountsOut",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
        ],
        "stateMutability": "view",
        "type": "function",
    }
]


def _router():
    return w3().eth.contract(
        address=Web3.to_checksum_address(settings.uniswap_v2_router), abi=ROUTER_ABI
    )


def get_amounts_out(amount_in_wei: int, path: list[str]) -> list[int]:
    router = _router()
    return router.functions.getAmountsOut(
        amount_in_wei, [Web3.to_checksum_address(p) for p in path]
    ).call()


def estimate_price_impact(
    amount_in_wei: int, path: list[str], probe_in_wei: int = 10**12
) -> dict:
    try:
        probe_out = get_amounts_out(probe_in_wei, path)[-1]
        trade_out = get_amounts_out(amount_in_wei, path)[-1]
        mid_px = probe_out / probe_in_wei
        exe_px = trade_out / amount_in_wei
        impact = 0.0 if mid_px == 0 else (mid_px - exe_px) / mid_px
        impact_bps = max(0, int(impact * 10_000))
        return {
            "ok": True,
            "impact_bps": impact_bps,
            "out_wei": int(trade_out),
            "error": None,
        }
    except Exception as e:
        return {"ok": False, "impact_bps": 0, "out_wei": 0, "error": str(e)}


def estimate_buy_eth_to_token(
    amount_eth: float, token_address: str, wrapped_native: str | None = None
) -> dict:
    wn = wrapped_native or settings.wrapped_native
    amount_in = int(amount_eth * 10**18)
    if not token_address:
        return {"ok": False, "impact_bps": 0, "out_wei": 0, "error": "missing_token"}
    if wn is None:
        raise ValueError("Wrapped native address is required")

    path: list[str] = [wn, token_address]
    return estimate_price_impact(amount_in, path)
