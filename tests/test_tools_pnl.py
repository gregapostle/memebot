# tests/test_tools_pnl.py

import os
import datetime
from pathlib import Path
import importlib
import memebot.tools.pnl as pnl


def test_no_file_returns_false(tmp_path, monkeypatch):
    """If positions_closed.csv does not exist, should return False."""
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pnl)
    assert pnl.daily_loss_exceeded(1.0) is False


def test_file_exists_no_losses_today(tmp_path, monkeypatch):
    """If file exists but no losses today, should return False."""
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pnl)

    file = tmp_path / "positions_closed.csv"
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    ts = datetime.datetime.combine(yesterday, datetime.time.min).timestamp()

    file.write_text(
        "header\n"
        f"row,{ts},,,,,,,10.0\n"  # now parts[8] = 10.0
    )
    assert pnl.daily_loss_exceeded(1.0) is False


def test_loss_today_below_cap(tmp_path, monkeypatch):
    """Loss today but below cap should return False."""
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pnl)

    file = tmp_path / "positions_closed.csv"
    today = datetime.date.today()
    ts = datetime.datetime(today.year, today.month, today.day).timestamp()

    file.write_text(
        "header\n"
        f"row,{ts},,,,,,,-0.5\n"  # one small loss
    )
    assert pnl.daily_loss_exceeded(1.0) is False


def test_loss_today_reaches_cap(tmp_path, monkeypatch):
    """Loss today reaching cap should return True."""
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pnl)

    file = tmp_path / "positions_closed.csv"
    today = datetime.date.today()
    ts = datetime.datetime(today.year, today.month, today.day).timestamp()

    file.write_text(
        "header\n"
        f"row,{ts},,,,,,,-5.0\n"
        f"row,{ts},,,,,,,-5.0\n"
    )
    # Total = 10.0, cap=10.0 → should trigger
    assert pnl.daily_loss_exceeded(10.0) is True


def test_skips_short_lines(tmp_path, monkeypatch):
    """Ensure short lines (<9 parts) are skipped without crashing."""
    monkeypatch.setenv("MEMEBOT_DATA_DIR", str(tmp_path))
    importlib.reload(pnl)

    file = tmp_path / "positions_closed.csv"
    today = datetime.date.today()
    ts = datetime.datetime(today.year, today.month, today.day).timestamp()

    # First line too short, second valid loss
    file.write_text(
        "header\n"
        f"short,{ts}\n"
        f"row,{ts},,,,,,,-3.0\n"
    )
    assert pnl.daily_loss_exceeded(1.0) is True