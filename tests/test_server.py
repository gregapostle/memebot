import pytest
import httpx
import time
from memebot import server


def test_auth_ok_with_and_without_secret(monkeypatch):
    # No secret set → always True
    monkeypatch.setattr(server.settings, "helius_webhook_secret", "")
    assert server._auth_ok(None) is True
    assert server._auth_ok("anything") is True

    # With secret set → must match
    monkeypatch.setattr(server.settings, "helius_webhook_secret", "secret123")
    assert server._auth_ok("secret123") is True
    assert server._auth_ok("wrong") is False


def test_extract_signals_valid_and_invalid(monkeypatch):
    now = time.time()
    payload = {
        "events": {
            "token": [
                {"mint": "mintA", "rawTokenAmount": {"tokenAmount": "2000000"}},
                {"mint": "mintB", "rawTokenAmount": {"tokenAmount": "oops"}},  # invalid float
                {"mint": None, "rawTokenAmount": {"tokenAmount": "100"}},      # missing mint
            ]
        },
        "accountData": {"owner": "owner123"},
    }
    signals = server._extract_signals(payload)
    assert len(signals) == 1  # Only the first one qualifies
    sig = signals[0]
    assert sig.platform == "helius"
    assert sig.contract == "mintA"
    assert "Wallet acquired" in sig.text


@pytest.mark.asyncio
async def test_helius_webhook_unauthorized(monkeypatch):
    monkeypatch.setattr(server.settings, "helius_webhook_secret", "secret123")

    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/helius", headers={"x-helius-signature": "wrong"}, json={})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "bad signature"


@pytest.mark.asyncio
async def test_helius_webhook_authorized_and_accepts(monkeypatch):
    monkeypatch.setattr(server.settings, "helius_webhook_secret", "secret123")

    # Patch handle_signal so we can count calls
    called = {}
    def fake_handle_signal(sig, debug=False):
        called["sig"] = sig
    monkeypatch.setattr(server, "handle_signal", fake_handle_signal)

    payload = {
        "data": {
            "events": {"token": [{"mint": "mintA", "rawTokenAmount": {"tokenAmount": "2000000"}}]}
        }
    }

    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/webhooks/helius",
            headers={"x-helius-signature": "secret123"},
            json=payload,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["accepted"] == 1
    assert "sig" in called


@pytest.mark.asyncio
async def test_helius_webhook_with_list_payload(monkeypatch):
    """Ensure list payloads are accepted too."""
    monkeypatch.setattr(server.settings, "helius_webhook_secret", "")

    called = {"count": 0}
    def fake_handle_signal(sig, debug=False):
        called["count"] += 1
    monkeypatch.setattr(server, "handle_signal", fake_handle_signal)

    payload = [
        {
            "data": {
                "events": {"token": [{"mint": "mintA", "rawTokenAmount": {"tokenAmount": "2000000"}}]}
            }
        }
    ]

    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/helius", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] == 1
    assert called["count"] == 1

@pytest.mark.asyncio
async def test_helius_webhook_with_non_dict_note(monkeypatch):
    """Cover the branch where note itself is used because data is not a dict."""
    monkeypatch.setattr(server.settings, "helius_webhook_secret", "")

    called = {"count": 0}
    def fake_handle_signal(sig, debug=False):
        called["count"] += 1
    monkeypatch.setattr(server, "handle_signal", fake_handle_signal)

    # Pass a bare dict without "data" so data = note triggers
    payload = {
        "events": {
            "token": [
                {"mint": "mintX", "rawTokenAmount": {"tokenAmount": "1000000"}}
            ]
        }
    }

    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/helius", json=payload)

    assert resp.status_code == 200
    assert resp.json()["accepted"] == 1
    assert called["count"] == 1