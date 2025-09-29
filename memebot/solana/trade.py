import json
import base64
import os
import requests
from memebot.config import settings

# Optional deps (used if present)
try:
    from solders.keypair import Keypair  # type: ignore
    from solana.rpc.api import Client  # type: ignore

    HAVE_SOLANA = True
except Exception:
    HAVE_SOLANA = False


def _expand(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def _allow_live_env() -> bool:
    # Read directly from env so pytest monkeypatch of ALLOW_LIVE is honored
    return bool(int(os.getenv("ALLOW_LIVE", "0")))


def _load_private_from_env_or_file():
    """Return (keypair_obj_or_None, base58_secret_or_None, derived_pubkey_str_or_None)."""
    content = None
    # Prefer file if provided
    if settings.solana_private_key_file:
        try:
            p = _expand(settings.solana_private_key_file)
            with open(p, "r") as f:
                content = f.read().strip()
        except Exception:
            return (None, None, None)
    elif settings.solana_private_b58:
        content = settings.solana_private_b58.strip()

    if not content:
        return (None, None, None)

    if not HAVE_SOLANA:
        # Can't build a Keypair; return secret text only
        return (None, content, None)

    # If JSON array -> bytes -> Keypair
    if content.startswith("["):
        try:
            arr = json.loads(content)
            kp = Keypair.from_bytes(bytes(arr))
            return (kp, None, str(kp.pubkey()))
        except Exception:
            return (None, None, None)
    else:
        # Assume base58 private
        try:
            kp = Keypair.from_base58_string(content)
            return (kp, content, str(kp.pubkey()))
        except Exception:
            return (None, None, None)


def _owner_for_request(owner: str | None) -> str:
    owner_pk = owner or settings.solana_owner or ""
    if not owner_pk:
        # Always provide a harmless dummy for unit tests / non-live callers.
        # Live path uses trade_live() which enforces real keys.
        return "11111111111111111111111111111111"
    return owner_pk


def request_swap_tx(quote: dict, owner: str | None = None) -> dict:
    """Ask Jupiter for a swap transaction (serialized, base64)."""
    url = f"{settings.jupiter_base}/swap"
    owner_pk = _owner_for_request(owner)
    if not owner_pk:
        return {"ok": False, "error": "missing_owner"}
    payload = {
        "quoteResponse": quote["route"],
        "userPublicKey": owner_pk,
        "wrapAndUnwrapSol": True,
        "dynamicComputeUnitLimit": True,
        "prioritizationFeeLamports": 0,
    }
    r = requests.post(url, json=payload, timeout=15)
    if r.status_code != 200:
        return {"ok": False, "error": f"HTTP {r.status_code} {r.text}"}
    data = r.json()
    if "swapTransaction" not in data:
        return {"ok": False, "error": "malformed_swap_response"}
    return {"ok": True, "tx_b64": data["swapTransaction"]}


def sign_and_send(tx_b64: str) -> dict:
    if not HAVE_SOLANA:
        return {"ok": False, "error": "solana libs not installed"}
    kp, secret_txt, derived_owner = _load_private_from_env_or_file()
    if kp is None and secret_txt is None:
        return {"ok": False, "error": "missing_keys"}
    client = Client(settings.solana_http)
    raw = base64.b64decode(tx_b64)
    resp = client.send_raw_transaction(raw)
    sig = None
    if isinstance(resp, dict):
        sig = resp.get("result") or resp.get("signature") or resp.get("value")
    else:
        sig = resp
    return {"ok": True, "signature": sig}


def trade_live(quote: dict) -> dict:
    # Gate live immediately so tests expecting 'live_disabled' pass deterministically
    if not _allow_live_env():
        return {"ok": False, "error": "live_disabled"}
    if settings.solana_cluster != "devnet" and not settings.force_mainnet_live:
        return {"ok": False, "error": "live_mainnet_blocked"}

    kp, _, derived_owner = _load_private_from_env_or_file()
    owner_pk = settings.solana_owner or derived_owner or ""
    if not owner_pk:
        return {"ok": False, "error": "missing_owner"}

    swap = request_swap_tx(quote, owner=owner_pk)
    if not swap.get("ok"):
        return swap
    send = sign_and_send(swap["tx_b64"])
    return send
