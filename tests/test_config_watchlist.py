import importlib
import json
import os
import pytest


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

def test_parse_list_empty(monkeypatch):
    mod = importlib.import_module("memebot.config.watchlist")
    importlib.reload(mod)
    # directly test helper
    assert mod._parse_list(None) == []
    assert mod._parse_list("") == []


def test_parse_list_json_array(monkeypatch):
    mod = importlib.import_module("memebot.config.watchlist")
    importlib.reload(mod)
    # JSON input
    result = mod._parse_list(json.dumps(["foo", "bar"]))
    assert result == ["foo", "bar"]

def test_parse_list_invalid_json(monkeypatch):
    mod = importlib.import_module("memebot.config.watchlist")
    importlib.reload(mod)

    # Input looks like JSON but is invalid
    result = mod._parse_list("[not-json")
    # Should fall back to comma-split behavior, returning the raw string
    assert result == ["[not-json"]