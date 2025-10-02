import builtins
import os
import sys
import importlib
import base64
import pytest
import requests_mock

import memebot.solana.trade as trade


def test_request_swap_tx_unit():
    # mock quote
    quote = {"ok": True, "route": {"foo": "bar"}}
    with requests_mock.Mocker() as m:
        m.post("https://quote-api.jup.ag/v6/swap", json={"swapTransaction": "AQID"})
        res = trade.request_swap_tx(quote)
        assert res["ok"] and res["tx_b64"] == "AQID"


def test_trade_live_blocked(monkeypatch):
    monkeypatch.setenv("ALLOW_LIVE", "0")
    importlib.reload(trade)
    res = trade.trade_live({"ok": True, "route": {"x": 1}})
    assert not res["ok"] and res["error"] == "live_disabled"

def test_expand_expands_home(tmp_path):
    fake = str(tmp_path / "key.json")
    expanded = trade._expand(fake)
    assert expanded == os.path.abspath(fake)


def test_load_private_none(monkeypatch):
    """No env vars set, should return all None."""
    import importlib
    import memebot.solana.trade as trade

    # Clear env vars that back these settings
    monkeypatch.delenv("SOLANA_PRIVATE_KEY_FILE", raising=False)
    monkeypatch.delenv("SOLANA_PRIVATE_B58", raising=False)

    importlib.reload(trade)
    res = trade._load_private_from_env_or_file()
    assert res == (None, None, None)


def test_load_private_file_missing(monkeypatch, tmp_path):
    fakefile = tmp_path / "missing.json"
    monkeypatch.setenv("SOLANA_PRIVATE_KEY_FILE", str(fakefile))
    monkeypatch.setenv("SOLANA_PRIVATE_B58", "")
    importlib.reload(trade)
    res = trade._load_private_from_env_or_file()
    assert res == (None, None, None)


def test_sign_and_send_no_solana(monkeypatch):
    monkeypatch.setattr(trade, "HAVE_SOLANA", False)
    res = trade.sign_and_send("AQID")
    assert not res["ok"] and "solana libs" in res["error"]


def test_sign_and_send_missing_keys(monkeypatch):
    monkeypatch.setattr(trade, "HAVE_SOLANA", True)
    monkeypatch.setattr(trade, "_load_private_from_env_or_file", lambda: (None, None, None))

    class DummyClient:
        def send_raw_transaction(self, raw): 
            return {"result": "sig"}

    # Patch solana.rpc.api with DummyClient
    sys.modules["solana.rpc.api"] = type("M", (), {"Client": DummyClient})
    res = trade.sign_and_send(base64.b64encode(b"hi").decode())
    # Should error because missing keys
    assert not res["ok"]


def test_trade_live_mainnet_block(monkeypatch):
    monkeypatch.setattr(trade, "_allow_live_env", lambda: True)
    monkeypatch.setattr(trade.settings, "solana_cluster", "mainnet-beta")
    monkeypatch.setattr(trade.settings, "force_mainnet_live", False)
    res = trade.trade_live({"ok": True, "route": {}})
    assert not res["ok"] and "mainnet" in res["error"]


def test_trade_live_missing_owner(monkeypatch):
    monkeypatch.setattr(trade, "_allow_live_env", lambda: True)
    monkeypatch.setattr(trade.settings, "solana_cluster", "devnet")
    monkeypatch.setattr(trade.settings, "force_mainnet_live", False)
    monkeypatch.setattr(trade, "_load_private_from_env_or_file", lambda: (None, None, None))
    monkeypatch.setattr(trade.settings, "solana_owner", "")
    res = trade.trade_live({"ok": True, "route": {}})
    assert not res["ok"] and res["error"] == "missing_owner"


def test_trade_live_happy(monkeypatch):
    monkeypatch.setattr(trade, "_allow_live_env", lambda: True)
    monkeypatch.setattr(trade.settings, "solana_cluster", "devnet")
    monkeypatch.setattr(trade.settings, "force_mainnet_live", False)
    monkeypatch.setattr(trade, "_load_private_from_env_or_file", lambda: ("kp", "secret", "owner"))
    monkeypatch.setattr(trade.settings, "solana_owner", "owner123")
    monkeypatch.setattr(trade, "request_swap_tx", lambda q, owner=None: {"ok": True, "tx_b64": "AQID"})
    monkeypatch.setattr(trade, "sign_and_send", lambda tx: {"ok": True, "signature": "sig321"})
    res = trade.trade_live({"ok": True, "route": {}})
    assert res["ok"] and res["signature"] == "sig321"

def test_optional_imports(monkeypatch):
    """Simulate presence of solana libs so HAVE_SOLANA becomes True."""
    # Fake Keypair and Client so the import block succeeds
    class DummyKeypair:
        @staticmethod
        def from_bytes(data): return "dummy_kp"
        @staticmethod
        def from_base58_string(s): return "dummy_kp"
        def pubkey(self): return "dummy_pub"

    class DummyClient:
        def __init__(self, *a, **k): pass
        def send_raw_transaction(self, raw): return {"result": "sig123"}

    monkeypatch.setitem(sys.modules, "solders.keypair", type("M", (), {"Keypair": DummyKeypair}))
    monkeypatch.setitem(sys.modules, "solana.rpc.api", type("M", (), {"Client": DummyClient}))

    import importlib
    trade_module = importlib.reload(trade)

    # Now HAVE_SOLANA should be True
    assert trade_module.HAVE_SOLANA is True

def test_load_private_from_file_success(monkeypatch, tmp_path):
    """Covers reading a private key file successfully."""
    # Create a fake key file
    keyfile = tmp_path / "key.json"
    keyfile.write_text("[1,2,3,4]")  # JSON array so Keypair.from_bytes branch is triggered

    # Point settings.solana_private_key_file to this path
    monkeypatch.setattr(trade.settings, "solana_private_key_file", str(keyfile))
    monkeypatch.setattr(trade, "HAVE_SOLANA", False)  # prevent Keypair usage

    # Reload module to re-evaluate settings
    import importlib
    importlib.reload(trade)

    kp, secret, owner = trade._load_private_from_env_or_file()
    # Since HAVE_SOLANA is False, we get secret text only
    assert kp is None
    assert secret == "[1,2,3,4]"
    assert owner is None

def test_load_private_file_open_error(monkeypatch, tmp_path):
    """Force an exception when opening the key file to hit the except branch."""
    keyfile = tmp_path / "bad.json"
    keyfile.write_text("not used")  # file exists but we'll break open()

    # Patch settings to point to this file
    monkeypatch.setattr(trade.settings, "solana_private_key_file", str(keyfile))

    # Patch builtins.open so that any call raises OSError
    monkeypatch.setattr(builtins, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("fail")))

    res = trade._load_private_from_env_or_file()
    assert res == (None, None, None)

def test_load_private_from_env_b58(monkeypatch):
    """Covers path where private key is read from SOLANA_PRIVATE_B58 env."""
    import importlib

    # Clear key file and inject b58 secret directly into settings
    monkeypatch.setattr(trade.settings, "solana_private_key_file", "")
    monkeypatch.setattr(trade.settings, "solana_private_b58", "dummyb58secret")

    # Force HAVE_SOLANA = False
    monkeypatch.setattr(trade, "HAVE_SOLANA", False)

    # Reload module to re-evaluate with patched settings
    trade_module = importlib.reload(trade)

    kp, secret, owner = trade_module._load_private_from_env_or_file()
    assert kp is None
    assert secret == "dummyb58secret"
    assert owner is None

def test_load_private_json_array_success(monkeypatch, tmp_path):
    """Covers the JSON array path with HAVE_SOLANA=True."""
    # Fake Keypair with pubkey method
    class DummyKeypair:
        def __init__(self, val): self._val = val
        @staticmethod
        def from_bytes(b): return DummyKeypair("bytes_kp")
        def pubkey(self): return "pub_from_bytes"

    monkeypatch.setitem(sys.modules, "solders.keypair", type("M", (), {"Keypair": DummyKeypair}))
    monkeypatch.setitem(sys.modules, "solana.rpc.api", type("M", (), {"Client": lambda *a, **k: None}))

    import importlib
    trade_module = importlib.reload(trade)

    # Patch settings so file contains JSON array
    keyfile = tmp_path / "key.json"
    keyfile.write_text("[1,2,3]")
    monkeypatch.setattr(trade_module.settings, "solana_private_key_file", str(keyfile))

    kp, secret, owner = trade_module._load_private_from_env_or_file()
    assert isinstance(kp, DummyKeypair)
    assert secret is None
    assert owner == "pub_from_bytes"


def test_load_private_base58_success(monkeypatch):
    """Covers the base58 string path with HAVE_SOLANA=True."""
    class DummyKeypair:
        @staticmethod
        def from_base58_string(s): return DummyKeypair()
        def pubkey(self): return "pub_from_b58"

    monkeypatch.setitem(sys.modules, "solders.keypair", type("M", (), {"Keypair": DummyKeypair}))
    monkeypatch.setitem(sys.modules, "solana.rpc.api", type("M", (), {"Client": lambda *a, **k: None}))

    import importlib
    trade_module = importlib.reload(trade)

    monkeypatch.setattr(trade_module.settings, "solana_private_key_file", "")
    monkeypatch.setattr(trade_module.settings, "solana_private_b58", "fakeb58")

    kp, secret, owner = trade_module._load_private_from_env_or_file()
    assert isinstance(kp, DummyKeypair)
    assert secret == "fakeb58"
    assert owner == "pub_from_b58"


def test_load_private_json_array_failure(monkeypatch, tmp_path):
    """Covers exception inside JSON array parsing branch."""
    class DummyKeypair:
        @staticmethod
        def from_bytes(b): raise ValueError("bad key")

    monkeypatch.setitem(sys.modules, "solders.keypair", type("M", (), {"Keypair": DummyKeypair}))
    monkeypatch.setitem(sys.modules, "solana.rpc.api", type("M", (), {"Client": lambda *a, **k: None}))

    import importlib
    trade_module = importlib.reload(trade)

    keyfile = tmp_path / "bad.json"
    keyfile.write_text("[1,2,3]")
    monkeypatch.setattr(trade_module.settings, "solana_private_key_file", str(keyfile))

    kp, secret, owner = trade_module._load_private_from_env_or_file()
    assert (kp, secret, owner) == (None, None, None)

def test_load_private_base58_failure(monkeypatch):
    """Covers exception inside base58 parsing branch."""
    class DummyKeypair:
        @staticmethod
        def from_base58_string(s): 
            raise ValueError("bad b58")

    # Patch solana modules so HAVE_SOLANA=True
    monkeypatch.setitem(sys.modules, "solders.keypair", type("M", (), {"Keypair": DummyKeypair}))
    monkeypatch.setitem(sys.modules, "solana.rpc.api", type("M", (), {"Client": lambda *a, **k: None}))

    import importlib
    trade_module = importlib.reload(trade)

    # Force Base58 secret
    monkeypatch.setattr(trade_module.settings, "solana_private_key_file", "")
    monkeypatch.setattr(trade_module.settings, "solana_private_b58", "fakeb58")

    kp, secret, owner = trade_module._load_private_from_env_or_file()
    assert (kp, secret, owner) == (None, None, None)

def test_owner_for_request_defaults(monkeypatch):
    """Covers fallback owner_pk branch returning dummy pubkey."""
    # Force settings.solana_owner to empty
    monkeypatch.setattr(trade.settings, "solana_owner", "")

    # Call with no explicit owner
    res = trade._owner_for_request(None)

    # Should return the dummy pubkey
    assert res == "11111111111111111111111111111111"

def test_request_swap_tx_http_error(monkeypatch):
    """Covers branch where Jupiter returns non-200 status."""
    import requests

    class DummyResp:
        status_code = 500
        text = "Internal Server Error"
        def json(self): return {}

    # Force requests.post to return our dummy error response
    monkeypatch.setattr(requests, "post", lambda *a, **k: DummyResp())

    res = trade.request_swap_tx({"route": {"foo": "bar"}}, owner="owner123")
    assert not res["ok"]
    assert "HTTP 500" in res["error"]

def test_request_swap_tx_malformed_response(monkeypatch):
    """Covers case where Jupiter responds 200 but missing swapTransaction."""
    import requests

    class DummyResp:
        status_code = 200
        text = "OK"
        def json(self): 
            return {"unexpected": "field"}

    monkeypatch.setattr(requests, "post", lambda *a, **k: DummyResp())

    res = trade.request_swap_tx({"route": {"foo": "bar"}}, owner="owner123")
    assert not res["ok"]
    assert res["error"] == "malformed_swap_response"

def test_sign_and_send_success(monkeypatch):
    """Covers the full happy path of sign_and_send with dict and string response."""

    class DummyKeypair:
        def pubkey(self): return "pubkey123"

    monkeypatch.setattr(trade, "_load_private_from_env_or_file",
                        lambda: (DummyKeypair(), None, "pubkey123"))

    # Patch trade.Client directly
    class DummyClient:
        def __init__(self, url): pass
        def send_raw_transaction(self, raw): 
            return {"result": "sig123"}

    monkeypatch.setattr(trade, "Client", DummyClient)
    monkeypatch.setattr(trade, "HAVE_SOLANA", True)

    tx_b64 = base64.b64encode(b"hi").decode()
    res = trade.sign_and_send(tx_b64)
    assert res["ok"]
    assert res["signature"] == "sig123"

    # Test with raw string response
    class DummyClient2:
        def __init__(self, url): pass
        def send_raw_transaction(self, raw):
            return "rawsig456"

    monkeypatch.setattr(trade, "Client", DummyClient2)
    res2 = trade.sign_and_send(tx_b64)
    assert res2["ok"]
    assert res2["signature"] == "rawsig456"

def test_trade_live_returns_failed_swap(monkeypatch):
    """Covers trade_live path where request_swap_tx returns a failure dict (line 126)."""
    monkeypatch.setattr(trade, "_allow_live_env", lambda: True)
    monkeypatch.setattr(trade.settings, "solana_cluster", "devnet")
    monkeypatch.setattr(trade.settings, "force_mainnet_live", False)

    # Fake private key loader so owner is present
    monkeypatch.setattr(trade, "_load_private_from_env_or_file", lambda: ("kp", "secret", "owner123"))
    monkeypatch.setattr(trade.settings, "solana_owner", "owner123")

    # Force request_swap_tx to return a failure dict
    monkeypatch.setattr(trade, "request_swap_tx", lambda quote, owner=None: {"ok": False, "error": "swap_failed"})

    res = trade.trade_live({"ok": True, "route": {}})
    assert res == {"ok": False, "error": "swap_failed"}

def test_request_swap_tx_missing_owner(monkeypatch):
    """Covers branch where owner is missing in request_swap_tx (line 78)."""
    # Force _owner_for_request to return empty
    monkeypatch.setattr(trade, "_owner_for_request", lambda owner=None: "")

    res = trade.request_swap_tx({"route": {"foo": "bar"}}, owner=None)
    assert not res["ok"]
    assert res["error"] == "missing_owner"