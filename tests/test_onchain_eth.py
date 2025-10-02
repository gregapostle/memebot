import pytest
import memebot.onchain.eth as eth


def test_w3_no_eth_http(monkeypatch):
    """Raises if ETH_HTTP is not configured."""
    monkeypatch.setattr(eth.settings, "eth_http", "")
    # Reset cached _w3
    eth._w3 = None
    with pytest.raises(RuntimeError, match="ETH_HTTP"):
        eth.w3()

def test_w3_connection_failure(monkeypatch):
    """Raises if Web3 fails to connect."""
    monkeypatch.setattr(eth.settings, "eth_http", "http://dummy")
    eth._w3 = None

    class DummyWeb3:
        def __init__(self, provider=None, *a, **kw): pass
        def is_connected(self): return False

        # Add this so Web3.HTTPProvider works
        class HTTPProvider:
            def __init__(self, url, *a, **kw): pass

    monkeypatch.setattr(eth, "Web3", DummyWeb3)
    with pytest.raises(RuntimeError, match="failed to connect"):
        eth.w3()


def test_w3_success(monkeypatch):
    monkeypatch.setattr(eth.settings, "eth_http", "http://dummy")
    eth._w3 = None

    class DummyWeb3:
        def __init__(self, provider=None, *a, **kw):
            self.provider = provider
        def is_connected(self):
            return True

    class DummyProvider:
        def __init__(self, url, *a, **kw):
            self.url = url

    # Attach HTTPProvider so it behaves like real Web3
    DummyWeb3.HTTPProvider = DummyProvider  

    # Monkeypatch Web3 to our DummyWeb3 class (not lambda)
    monkeypatch.setattr(eth, "Web3", DummyWeb3)

    client = eth.w3()
    assert isinstance(client, DummyWeb3)
    assert isinstance(client.provider, DummyProvider)
    # Cached result works too
    assert eth.w3() is client


def test_get_eth_client(monkeypatch):
    called = {}

    class DummyWeb3:
        def __init__(self, provider, *a, **kw): called["provider"] = provider

        class HTTPProvider:
            def __init__(self, url, *a, **kw): called["url"] = url

    monkeypatch.setattr(eth, "Web3", DummyWeb3)

    client = eth.get_eth_client("http://dummy")
    assert "url" in called
    assert isinstance(client, DummyWeb3)

def test_eth_module_smoke(monkeypatch):
    # Patch web3 so we don't need a real node
    class DummyWeb3:
        def eth(self): return None
    monkeypatch.setattr(eth, "Web3", lambda *a, **kw: DummyWeb3())

    # Just ensure it imports and initializes without error
    assert hasattr(eth, "get_eth_client")

