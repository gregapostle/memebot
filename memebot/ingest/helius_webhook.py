import os
import hmac
import hashlib
import argparse
import json
import logging
from fastapi import FastAPI, Request, Header, HTTPException
import uvicorn

from memebot.config import settings
from memebot.strategy.fusion import Signal
from memebot.ingest.stream_helius import enqueue_signal
from memebot.ingest.llm_filter import filter_signal_with_llm  # ✅ Correct import

logger = logging.getLogger("memebot.helius")
app = FastAPI()


def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    if secret:
        mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(mac, signature)
    try:
        import base58  # type: ignore
        from nacl.signing import VerifyKey  # type: ignore
        HELIUS_PUBLIC_KEY = "7hcm7kCwXL2XqZLzY4dp5RvZuj76Rxct6e1Fz9wW6nJw"
        verify_key = VerifyKey(base58.b58decode(HELIUS_PUBLIC_KEY))
        verify_key.verify(body, base58.b58decode(signature))
        return True
    except Exception:
        return False


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
    accepted, dropped = 0, 0

    for txn in payload.get("transactions", []):
        account = txn.get("account", "")
        description = txn.get("description", "")
        token = txn.get("tokenTransfers", [{}])[0].get("mint")

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

        # ✅ LLM filter
        filtered = await filter_signal_with_llm(sig)
        if not filtered or not filtered.get("valuable"):
            dropped += 1
            continue

        sig.symbol = filtered.get("token")
        sig.contract = filtered.get("contract", sig.contract)
        sig.confidence = filtered.get("confidence", sig.confidence)

        enqueue_signal(sig)
        accepted += 1

    logger.info(f"[helius] accepted={accepted} dropped={dropped}")
    return {"ok": True, "accepted": accepted, "dropped": dropped}


def start(port: int | None = None):
    if port is None:
        port = int(os.getenv("PORT", "8787"))
    uvicorn.run(
        "memebot.ingest.helius_webhook:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Run Helius Webhook server")
    parser.add_argument("--port", type=int, help="Port to bind (default from $PORT or 8787)")
    args = parser.parse_args()
    logger.info("[helius] starting server...")
    start(args.port)