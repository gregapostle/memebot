# memebot/config/settings.py

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator


class Settings(BaseSettings):
    # --- Core ---
    network: str = Field(default="solana")
    solana_cluster: str = Field(default="mainnet")

    # --- Features ---
    enable_mock: bool = Field(default=True)
    mock_jupiter: bool = Field(default=False)
    allow_live: bool = Field(default=False)
    force_mainnet_live: bool = Field(default=False)

    enable_twitter: bool = Field(default=False)
    enable_telegram: bool = Field(default=False)
    enable_discord: bool = Field(default=False)

    # --- Trading ---
    base_size_sol: float = Field(default=0.05)
    size_by_conf: Optional[str] = None
    caller_allowlist: Optional[str] = None
    daily_loss_cap_sol: Optional[float] = None

    # --- Chain IDs + Routers ---
    chain_id: Optional[int] = None
    wrapped_native: Optional[str] = None
    uniswap_v2_router: Optional[str] = None
    wsol_mint: Optional[str] = None
    jupiter_base: Optional[str] = None
    solana_owner: Optional[str] = None

    # --- Added configs ---
    eth_http: Optional[str] = None
    solana_http: Optional[str] = None
    helius_webhook_secret: Optional[str] = None

    # --- Wallet + Media tracking ---
    watch_wallets_sol: Optional[str] = Field(default=None, alias="WATCH_WALLETS_SOL")
    watch_wallets_eth: Optional[str] = Field(default=None, alias="WATCH_WALLETS_ETH")
    twitter_accounts: Optional[str] = Field(default=None, alias="TWITTER_ACCOUNTS")
    twitter_keywords: Optional[str] = Field(default=None, alias="TWITTER_KEYWORDS")
    telegram_groups: Optional[str] = Field(default=None, alias="TELEGRAM_GROUPS")
    discord_channels: Optional[str] = Field(default=None, alias="DISCORD_CHANNELS")

    # --- Helpers ---
    def mint(self, symbol: str) -> str:
        """Return known token mint addresses for Solana symbols."""
        mapping = {
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # mainnet USDC
            "WSOL": self.wsol_mint,
        }
        return mapping.get(symbol.upper(), f"unknown-{symbol}") or f"unknown-{symbol}"

    # --- Validators ---
    @model_validator(mode="after")
    def configure_network_defaults(self):
        """Fill defaults depending on the selected network."""
        if self.network == "ethereum":
            self.chain_id = 1
            self.wrapped_native = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            self.uniswap_v2_router = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"

        elif self.network == "bsc":
            self.chain_id = 56
            self.wrapped_native = "0xBB4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
            self.uniswap_v2_router = "0x10ED43C718714eb63d5aA57B78B54704E256024E"

        elif self.network == "solana":
            self.chain_id = 1
            self.wsol_mint = "So11111111111111111111111111111111111111112"
            self.jupiter_base = "https://quote-api.jup.ag/v6"
            self.solana_owner = os.getenv("SOLANA_OWNER", "default_owner")

        return self


# Global settings instance
settings = Settings()
