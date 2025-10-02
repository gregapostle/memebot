import os
import sys
import runpy
import subprocess
from pathlib import Path
import pytest
import time
import memebot.tools.pnl_cli as pnl_cli


def test_pnl_cli_runs_as_module(tmp_path: Path):
    """Run pnl_cli as a module with dummy closed trades CSV."""
    csv_file = tmp_path / "positions_closed.csv"
    csv_file.write_text("ts_close,pnl_base,quote\n1234567890,10.5,USDC\n")

    env = {**os.environ, "MEMEBOT_DATA_DIR": str(tmp_path)}

    result = subprocess.run(
        [sys.executable, "-m", "memebot.tools.pnl_cli"],
        capture_output=True,
        env=env,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert "trades=" in result.stdout


def test_pnl_cli_runs_inline(tmp_path: Path, capsys, monkeypatch):
    """Call pnl_cli.main() inline so coverage captures it."""
    csv_file = tmp_path / "positions_closed.csv"
    csv_file.write_text("ts_close,pnl_base,quote\n1234567890,10.5,USDC\n")

    # Patch CLOSED_FILE directly so load_closed_positions() uses tmp_path
    monkeypatch.setattr(pnl_cli, "CLOSED_FILE", csv_file)

    # Run inline
    pnl_cli.main()

    captured = capsys.readouterr()
    assert "trades=1" in captured.out
    assert "gross=10.5000" in captured.out
    assert "USDC" in captured.out

def test_pnl_cli_module_entrypoint(monkeypatch):
    """Ensure pnl_cli runs as module via runpy cleanly."""
    import sys, runpy

    # Patch argv to avoid pytest flags
    monkeypatch.setattr(sys, "argv", ["pnl_cli"])

    # Remove from sys.modules so runpy executes it fresh
    sys.modules.pop("memebot.tools.pnl_cli", None)

    # Catch SystemExit (Typer exits after CLI run)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("memebot.tools.pnl_cli", run_name="__main__")

    # Typer exits with code 0 when argv is just the program name
    assert exc.value.code in (0, 2)  # 0 if help is shown, 2 if no command

def test_load_trades_and_closed_positions_empty(tmp_path, monkeypatch):
    """Ensure load_trades/load_closed_positions return [] if files missing."""
    # Point CLOSED_FILE and TRADES_FILE to tmp_path (files not created)
    monkeypatch.setattr(pnl_cli, "CLOSED_FILE", tmp_path / "positions_closed.csv")
    monkeypatch.setattr(pnl_cli, "TRADES_FILE", tmp_path / "trades.csv")

    assert pnl_cli.load_trades() == []
    assert pnl_cli.load_closed_positions() == []


def test_main_no_trades(capsys, monkeypatch, tmp_path):
    """Ensure main() prints summary even with no trades and skips per-token."""
    monkeypatch.setattr(pnl_cli, "CLOSED_FILE", tmp_path / "positions_closed.csv")
    pnl_cli.CLOSED_FILE.write_text("ts_close,pnl_base,quote\n")  # header only, no data

    pnl_cli.main()

    captured = capsys.readouterr()
    # Should still show a summary line with zeros
    assert "trades=0" in captured.out
    assert "gross=0.0000" in captured.out
    # Should NOT show per-token summary since no trades
    assert "Per-token summary:" not in captured.out


def test_load_trades_reads_file(tmp_path, monkeypatch):
    """Ensure load_trades reads and returns rows from trades.csv."""
    csv_file = tmp_path / "trades.csv"
    csv_file.write_text("ts_close,pnl_base,quote\n1234567890,1.23,USDC\n")

    # Point TRADES_FILE to our temp file
    monkeypatch.setattr(pnl_cli, "TRADES_FILE", csv_file)

    rows = pnl_cli.load_trades()
    assert len(rows) == 1
    assert rows[0]["pnl_base"] == "1.23"
    assert rows[0]["quote"] == "USDC"


def test_daily_loss_exceeded_detects_loss(tmp_path, monkeypatch):
    """Ensure daily_loss_exceeded returns True if today's losses exceed limit."""
    csv_file = tmp_path / "positions_closed.csv"
    today_ts = time.time()
    csv_file.write_text(
        f"ts_close,pnl_base,quote\n{int(today_ts)},-10.0,SOL\n"
    )

    # Patch CLOSED_FILE to point to our temp file
    monkeypatch.setattr(pnl_cli, "CLOSED_FILE", csv_file)

    # Should detect that today's total losses exceed the limit of 5
    assert pnl_cli.daily_loss_exceeded(5.0) is True
    # Should be False if we set a higher limit
    assert pnl_cli.daily_loss_exceeded(20.0) is False

def test_daily_loss_exceeded_skips_invalid_ts(tmp_path, monkeypatch):
    """Ensure rows with ts_close=0 are skipped and do not affect losses."""
    csv_file = tmp_path / "positions_closed.csv"
    # ts_close=0 should trigger the 'continue' path
    csv_file.write_text("ts_close,pnl_base,quote\n0,-50.0,SOL\n")

    monkeypatch.setattr(pnl_cli, "CLOSED_FILE", csv_file)

    # Losses should not count, so this should be False
    assert pnl_cli.daily_loss_exceeded(1.0) is False