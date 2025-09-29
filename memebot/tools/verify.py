import typer
import asyncio
from memebot.ingest.social.telegram_ingest import verify_telegram_credentials
from memebot.ingest.social.discord_ingest import verify_discord_credentials

app = typer.Typer()


@app.command()
def telegram():
    """Verify Telegram credentials work"""
    try:
        username = asyncio.run(verify_telegram_credentials())
        typer.echo(f"✅ Telegram login successful: {username}")
    except Exception as e:
        typer.echo(f"❌ Telegram verification failed: {e}")


@app.command()
def discord():
    """Verify Discord bot token works"""
    try:
        user = asyncio.run(verify_discord_credentials())
        typer.echo(f"✅ Discord bot login successful: {user}")
    except Exception as e:
        typer.echo(f"❌ Discord verification failed: {e}")


if __name__ == "__main__":
    app()
