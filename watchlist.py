from memebot.config import settings

def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]

class Watchlist:
    @property
    def solana_wallets(self) -> list[str]:
        return _parse_csv(getattr(settings, "watch_wallets_sol", None))

    @property
    def eth_wallets(self) -> list[str]:
        return _parse_csv(getattr(settings, "watch_wallets_eth", None))

    @property
    def twitter_accounts(self) -> list[str]:
        return _parse_csv(getattr(settings, "twitter_accounts", None))

    @property
    def twitter_keywords(self) -> list[str]:
        return _parse_csv(getattr(settings, "twitter_keywords", None))

    @property
    def telegram_groups(self) -> list[str]:
        return _parse_csv(getattr(settings, "telegram_groups", None))

    @property
    def discord_channels(self) -> list[str]:
        return _parse_csv(getattr(settings, "discord_channels", None))

watchlist = Watchlist()

