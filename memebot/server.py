from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import time
from memebot.config import settings
from memebot.types import SocialSignal
from memebot.main import handle_signal

app = FastAPI(title="MemeBot Webhooks")


def _auth_ok(provided: Optional[str]) -> bool:
    secret = settings.helius_webhook_secret
    if not secret:
        return True
    return provided == secret


def _extract_signals(helius_payload: Dict[str, Any]) -> List[SocialSignal]:
    signals: List[SocialSignal] = []
    events = helius_payload.get("events") or {}
    token_balances = events.get("token") or []
    for ev in token_balances:
        mint = ev.get("mint")
        rta = ev.get("rawTokenAmount") or {}
        try:
            amt = float(rta.get("tokenAmount") or 0)
        except Exception:
            amt = 0.0
        if mint and amt > 0:
            sig = SocialSignal(
                source="helius",
                symbol=None,
                contract=mint,
                confidence=min(0.9, 0.5 + min(0.4, amt / 1e6)),
                text=f"Wallet acquired {amt} of {mint}",
                timestamp=time.time(),
                caller=(helius_payload.get("accountData", {}) or {}).get("owner")
                or (helius_payload.get("signatureInfo", {}) or {}).get("signer"),
            )
            signals.append(sig)
    return signals


@app.post("/webhooks/helius")
async def helius_webhook(
    request: Request, x_helius_signature: Optional[str] = Header(default=None)
):
    if not _auth_ok(x_helius_signature):
        raise HTTPException(status_code=401, detail="bad signature")
    payload = await request.json()
    notifications = payload if isinstance(payload, list) else [payload]
    accepted = 0
    for note in notifications:
        data = note.get("data") if isinstance(note, dict) else None
        if not isinstance(data, dict):
            data = note
        for sig in _extract_signals(data if isinstance(data, dict) else {}):
            handle_signal(sig, debug=True)
            accepted += 1
    return JSONResponse({"ok": True, "accepted": accepted})
