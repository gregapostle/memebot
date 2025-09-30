import os
import json
from typing import Any, Dict, List


def _parse_list(val: str | None) -> List[str]:
    """Parse env var into list. Accepts comma-separated or JSON array."""
    if not val:
        return []
    val = val.strip()
    try:
        if val.startswith("["):
            return json.loads(val)
    except Exception:
        pass
    return [x.strip() for x in val.split(",") if x.strip()]


def _load_watchlist() -> Dict[str, Any]:
    """Load Telegram, Discord, Twitter, and wallets watchlist from environment."""
    return {
        # Telegram
        "telegram_api_id": os.getenv("TELEGRAM_API_ID"),
        "telegram_api_hash": os.getenv("TELEGRAM_API_HASH"),
        "telegram_groups": _parse_list(os.getenv("TELEGRAM_GROUPS")),
        # Discord
        "discord_token": os.getenv("DISCORD_TOKEN"),
        "discord_channels": _parse_list(os.getenv("DISCORD_CHANNELS")),
        # Twitter
        "twitter_accounts": _parse_list(os.getenv("TWITTER_ACCOUNTS")),
        "twitter_keywords": _parse_list(os.getenv("TWITTER_KEYWORDS")),
        # Wallets
        "watch_wallets_sol": _parse_list(os.getenv("WATCH_WALLETS_SOL")),
        "watch_wallets_eth": _parse_list(os.getenv("WATCH_WALLETS_ETH")),
    }


# Global instance — always a dict
watchlist: Dict[str, Any] = _load_watchlist()
