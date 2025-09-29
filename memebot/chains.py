from dataclasses import dataclass


@dataclass(frozen=True)
class EvmChain:
    name: str
    chain_id: int
    wrapped_native: str
    router_v2: str


ETHEREUM = EvmChain(
    "ethereum",
    1,
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "0x7a250d5630b4cf539739df2c5dAcb4c659F2488D",
)

BSC = EvmChain(
    "bsc",
    56,
    "0xBB4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    "0x10ED43C718714eb63d5aA57B78B54704E256024E",
)

CHAINS = {"ethereum": ETHEREUM, "bsc": BSC}
