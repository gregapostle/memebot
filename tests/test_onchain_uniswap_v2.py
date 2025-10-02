import pytest
import memebot.onchain.uniswap_v2 as uni


def test_uniswap_v2_smoke(monkeypatch):
    # Patch Web3 + contract
    class DummyContract:
        def functions(self): return self
        def getReserves(self): return (1000, 2000, 123)

    monkeypatch.setattr(uni, "Web3", lambda *a, **kw: None)
    monkeypatch.setattr(uni, "get_contract", lambda *a, **kw: DummyContract())

    # Ensure methods exist
    assert hasattr(uni, "get_reserves")


@pytest.fixture
def patch_get_amounts_out(monkeypatch):
    """Patch get_amounts_out to a deterministic fake implementation."""
    def fake_get_amounts_out(amount_in, path):
        return [amount_in, amount_in * 1000]
    monkeypatch.setattr(uni, "get_amounts_out", fake_get_amounts_out)
    yield


def test_estimate_price_impact_unit(patch_get_amounts_out):
    amount_in = 10**18
    path = [
        "0x000000000000000000000000000000000000dEaD",
        "0x000000000000000000000000000000000000bEEF",
    ]
    res = uni.estimate_price_impact(amount_in, path)
    assert res["ok"] is True
    assert res["impact_bps"] >= 0
    assert res["out_wei"] > 0


def test_get_amounts_out_success(monkeypatch):
    """Covers normal get_amounts_out path with checksum address conversion."""

    class DummyRouter:
        class functions:
            @staticmethod
            def getAmountsOut(amount_in, path):
                class Call:
                    def call(self_inner):
                        return [amount_in, amount_in * 2]
                return Call()

    monkeypatch.setattr(uni, "_router", lambda: DummyRouter())

    # ✅ use valid 20-byte hex addresses
    addr1 = "0x" + "de" * 20
    addr2 = "0x" + "be" * 20

    res = uni.get_amounts_out(123, [addr1, addr2])
    assert res == [123, 246]


def test_estimate_price_impact_exception(monkeypatch):
    """Covers exception branch inside estimate_price_impact."""
    monkeypatch.setattr(
        uni, "get_amounts_out",
        lambda *a, **k: (_ for _ in ()).throw(Exception("fail"))
    )
    res = uni.estimate_price_impact(1000, ["0xA", "0xB"])
    assert res["ok"] is False
    assert "fail" in res["error"]


def test_estimate_buy_missing_token():
    """Covers missing token address branch."""
    res = uni.estimate_buy_eth_to_token(1.0, "")
    assert res["ok"] is False
    assert res["error"] == "missing_token"


def test_estimate_buy_no_wrapped_native(monkeypatch):
    """Covers wrapped_native=None ValueError branch."""
    with pytest.raises(ValueError):
        uni.estimate_buy_eth_to_token(1.0, "0xdead", wrapped_native=None)


def test_get_contract_and_reserves():
    """Covers get_contract creation and get_reserves success+failure."""

    class DummyEth:
        def contract(self, address, abi): return "dummy"

    class DummyWeb3:
        eth = DummyEth()

    res = uni.get_contract(DummyWeb3(), "0xaddr", [])
    assert res == "dummy"

    # success path
    class GoodContract:
        class functions:
            @staticmethod
            def getReserves():
                class Call:
                    def call(self_inner): return (1, 2, 3)
                return Call()
    assert uni.get_reserves(GoodContract()) == (1, 2, 3)

    # failure path
    class BadContract:
        class functions:
            @staticmethod
            def getReserves():
                class Call:
                    def call(self_inner): raise Exception("boom")
                return Call()
    res = uni.get_reserves(BadContract())
    assert res[0] == 0 and "error" in str(res[2])

def test_router_direct(monkeypatch):
    """Covers the real _router() creation call."""
    dummy_contract = object()

    class DummyEth:
        def contract(self, address, abi):  # matches call in _router
            return dummy_contract

    class DummyW3:
        eth = DummyEth()

    # Patch w3() to return our DummyW3
    monkeypatch.setattr(uni, "w3", lambda: DummyW3())

    # Patch settings.uniswap_v2_router to a valid address
    monkeypatch.setattr(uni.settings, "uniswap_v2_router", "0x" + "aa" * 20)

    res = uni._router()
    assert res is dummy_contract

def test_estimate_buy_eth_to_token_success(monkeypatch):
    """Covers the happy path of estimate_buy_eth_to_token with valid inputs."""

    # Patch settings.wrapped_native to a dummy address
    monkeypatch.setattr(uni.settings, "wrapped_native", "0x" + "aa" * 20)

    # Patch estimate_price_impact to a fake predictable response
    monkeypatch.setattr(
        uni, "estimate_price_impact",
        lambda amount_in, path: {"ok": True, "impact_bps": 123, "out_wei": 456}
    )

    res = uni.estimate_buy_eth_to_token(1.0, "0x" + "bb" * 20)

    assert res["ok"] is True
    assert res["impact_bps"] == 123
    assert res["out_wei"] == 456