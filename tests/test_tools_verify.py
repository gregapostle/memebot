# tests/test_tools_verify.py
import sys
import runpy
import pytest
from typer.testing import CliRunner
import memebot.tools.verify as verify

runner = CliRunner()


def test_telegram_success(monkeypatch):
    async def fake_verify():
        return "mock-user"

    monkeypatch.setattr(verify, "verify_telegram_credentials", fake_verify)

    result = runner.invoke(verify.app, ["telegram"])
    assert result.exit_code == 0
    assert "✅ Telegram login successful: mock-user" in result.stdout


def test_telegram_failure(monkeypatch):
    def fail():
        raise RuntimeError("bad creds")

    monkeypatch.setattr(verify, "verify_telegram_credentials", fail)

    result = runner.invoke(verify.app, ["telegram"])
    assert result.exit_code == 0  # Typer handles exceptions gracefully
    assert "❌ Telegram verification failed" in result.stdout


def test_discord_success(monkeypatch):
    async def fake_verify():
        return "mock-discord"

    monkeypatch.setattr(verify, "verify_discord_credentials", fake_verify)

    result = runner.invoke(verify.app, ["discord"])
    assert result.exit_code == 0
    assert "✅ Discord bot login successful: mock-discord" in result.stdout


def test_discord_failure(monkeypatch):
    def fail():
        raise RuntimeError("bad token")

    monkeypatch.setattr(verify, "verify_discord_credentials", fail)

    result = runner.invoke(verify.app, ["discord"])
    assert result.exit_code == 0
    assert "❌ Discord verification failed" in result.stdout


def test_module_entrypoint(monkeypatch):
    """Ensure verify runs as module without crashing (Typer exits with code 2 if no args)."""
    import sys, runpy

    monkeypatch.setattr(sys, "argv", ["verify"])  # no subcommand

    sys.modules.pop("memebot.tools.verify", None)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("memebot.tools.verify", run_name="__main__")

    # Typer exits with 2 for missing command
    assert exc.value.code == 2