from web3 import Web3
from memebot.config import settings

_w3 = None


def w3() -> Web3:
    global _w3
    if _w3 is None:
        if not settings.eth_http:
            raise RuntimeError("ETH_HTTP / ALCHEMY_HTTP is not configured")
        _w3 = Web3(Web3.HTTPProvider(settings.eth_http, request_kwargs={"timeout": 20}))
        if not _w3.is_connected():
            raise RuntimeError("Web3 failed to connect")
    return _w3
