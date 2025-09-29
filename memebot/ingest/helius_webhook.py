import os
import hmac
import hashlib
from fastapi import FastAPI, Request, Header, HTTPException
import uvicorn
import json

from memebot.config import settings
from memebot.strategy.fusion import Signal
from memebot.ingest.stream_helius import enqueue_signal

app = FastAPI()


def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature)


@app.post("/helius")
async def helius_handler(
    request: Request,
    x_helius_signature: str = Header(None),
):
    body = await request.body()

    secret = settings.helius_webhook_secret or ""
    if not verify_signature(secret, body, x_helius_signature or ""):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)

    for txn in payload.get("transactions", []):
        account = txn.get("account", "")
        description = txn.get("description", "")
        token = txn.get("tokenTransfers", [{}])[0].get("mint", None)

        if not token:
            continue

        sig = Signal(
            platform="helius",
            type="wallet",
            source=account,
            content=description,
            mentions=[token],
            confidence=1.0,
            contract=token,
        )
        enqueue_signal(sig)

    return {"ok": True}


def start():
    port = int(os.getenv("PORT", "8787"))
    uvicorn.run(
        "memebot.ingest.helius_webhook:app", host="0.0.0.0", port=port, reload=False
    )


if __name__ == "__main__":
    start()
