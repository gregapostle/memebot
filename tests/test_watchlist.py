import os
import importlib


def test_watchlist_parsing(monkeypatch):
    monkeypatch.setenv("TELEGRAM_GROUPS", "group1, group2")
    monkeypatch.setenv("DISCORD_CHANNELS", "chan1,chan2")
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("DISCORD_TOKEN", "token123")

    # reload the module to force re-parse
    mod = importlib.import_module("memebot.config.watchlist")
    importlib.reload(mod)

    wl = mod.watchlist
    assert wl["telegram_groups"] == ["group1", "group2"]
    assert wl["discord_channels"] == ["chan1", "chan2"]
    assert wl["telegram_api_id"] == "123"
    assert wl["discord_token"] == "token123"
