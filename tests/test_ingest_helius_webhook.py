import pytest
import json
import hmac
import hashlib
import httpx
import sys
import runpy
from memebot.ingest import helius_webhook


def make_sig(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_helius_webhook_valid(monkeypatch):
    body = json.dumps({
        "transactions": [
            {"account": "acc", "description": "desc", "tokenTransfers": [{"mint": "mint"}]}
        ]
    }).encode()

    monkeypatch.setattr(helius_webhook.settings, "helius_webhook_secret", "testsecret")
    sig = make_sig("testsecret", body)

    transport = httpx.ASGITransport(app=helius_webhook.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/helius", content=body, headers={"x-helius-signature": sig})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.asyncio
async def test_helius_webhook_invalid_signature(monkeypatch):
    body = json.dumps({"transactions": []}).encode()
    monkeypatch.setattr(helius_webhook.settings, "helius_webhook_secret", "right")
    wrong_sig = make_sig("wrong", body)

    transport = httpx.ASGITransport(app=helius_webhook.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/helius", content=body, headers={"x-helius-signature": wrong_sig})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_helius_webhook_no_token_transfers(monkeypatch):
    body = json.dumps({
        "transactions": [{"account": "acc", "description": "desc", "tokenTransfers": [{}]}]
    }).encode()
    monkeypatch.setattr(helius_webhook.settings, "helius_webhook_secret", "testsecret")
    sig = make_sig("testsecret", body)

    transport = httpx.ASGITransport(app=helius_webhook.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/helius", content=body, headers={"x-helius-signature": sig})
    # Should succeed but enqueue nothing
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_verify_signature_ed25519(monkeypatch):
    """Simulate Ed25519 fallback when no secret is set."""
    monkeypatch.setattr(helius_webhook, "settings", type("S", (), {"helius_webhook_secret": ""}))
    # Patch base58 + VerifyKey to simulate success
    monkeypatch.setitem(sys.modules, "base58", type("M", (), {"b58decode": lambda x: b"abc"}))
    class DummyKey:
        def verify(self, body, sig): return True
    monkeypatch.setitem(sys.modules, "nacl.signing", type("M", (), {"VerifyKey": lambda x: DummyKey()}))

    assert helius_webhook.verify_signature("", b"body", "sig") is True


def test_verify_signature_ed25519_failure(monkeypatch):
    monkeypatch.setattr(helius_webhook, "settings", type("S", (), {"helius_webhook_secret": ""}))
    # Force import error
    monkeypatch.setitem(sys.modules, "base58", None)
    assert helius_webhook.verify_signature("", b"body", "sig") is False


def test_start_runs(monkeypatch):
    called = {}
    def fake_run(*a, **k): called["ok"] = True
    monkeypatch.setattr(helius_webhook.uvicorn, "run", fake_run)

    helius_webhook.start(9999)
    assert called["ok"]

    # also test default port path
    monkeypatch.setenv("PORT", "1234")
    helius_webhook.start(None)
    assert called["ok"]


def test_main_entrypoint(monkeypatch):
    import sys
    import runpy
    from memebot.ingest import helius_webhook

    called = {}

    def fake_run(*args, **kwargs):
        called["ok"] = True

    monkeypatch.setattr(helius_webhook.uvicorn, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["helius_webhook"])

    # Remove module so runpy executes it fresh (prevents warning)
    sys.modules.pop("memebot.ingest.helius_webhook", None)

    runpy.run_module("memebot.ingest.helius_webhook", run_name="__main__")

    assert "ok" in called