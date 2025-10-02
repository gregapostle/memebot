import typer
import time
from memebot.strategy.exits import ExitManager

app = typer.Typer(add_completion=False)


@app.command()
def main(
    every: int = typer.Option(5, help="Seconds between exit checks"),
    mode: str = typer.Option("simulate", help="simulate | paper | live"),
    debug: bool = typer.Option(False, help="Verbose logs"),
):
    """
    Run exit checks on a cadence, applying TP/SL/Trail rules.
    """
    manager = ExitManager()
    typer.echo(f"Starting exit loop every {every}s in mode={mode}")

    try:
        while True:
            exits = manager.tick_exits(mode=mode, debug=debug)
            if exits and debug:
                typer.echo(f"[loop] Triggered {len(exits)} exits")
            time.sleep(every)
    except KeyboardInterrupt:
        typer.echo("Stopped.")


if __name__ == "__main__":  # pragma: no cover
    app()
