import logging
import asyncio
import inspect
from typing import Callable, Generator, Optional
from memebot.types import SocialSignal
from memebot.config.watchlist import watchlist
from memebot.ingest.llm_filter import filter_signal_with_llm

logger = logging.getLogger("memebot.twitter")

USE_REAL_TWITTER = bool(
    watchlist.get("twitter_accounts") or watchlist.get("twitter_keywords")
)

if USE_REAL_TWITTER:
    from twikit import Client

    client = Client("en-US")

    async def ensure_login():
        """
        Loads cookies for Twitter session. 
        You must run `client.login()` once manually and save cookies to twitter_cookies.json.
        """
        try:
            client.load_cookies("twitter_cookies_twikit.json")
            logger.info("[twitter] Loaded cookies for authenticated session.")
        except Exception:
            logger.error("[twitter] Missing or invalid cookies. Run manual login once:")
            logger.error(
                "   >>> from twikit import Client\n"
                "   >>> client = Client('en-US')\n"
                "   >>> client.login(auth_info_1='email', auth_info_2='username', password='password')\n"
                "   >>> client.save_cookies('twitter_cookies.json')"
            )
            raise


async def _process_signal(sig: SocialSignal, callback, debug: bool = False):
    """Run a signal through the LLM filter before forwarding."""
    result = await filter_signal_with_llm(sig)
    if result["valuable"]:
        sig.symbol = result.get("token") or sig.symbol
        sig.confidence = result.get("confidence", sig.confidence)
        if debug:
            logger.info(f"[twitter][LLM] accepted {result}")
        if inspect.iscoroutinefunction(callback):
            await callback(sig)
        else:
            callback(sig)
    else:
        if debug:
            logger.info(f"[twitter][LLM] dropped as noise: {result.get('reason')}")


async def run_twitter_ingest(
    callback: Callable[[SocialSignal], None], debug: bool = False
):
    accounts = watchlist.get("twitter_accounts", [])
    keywords = watchlist.get("twitter_keywords", [])
    logger.info(
        f"[twitter] starting... monitoring accounts={accounts} keywords={keywords}"
    )

    if not USE_REAL_TWITTER:
        # --- Mock Mode ---
        msg_text = "Mocked tweet about BONK"
        sig = SocialSignal(
            platform="twitter",
            source="mock_account",
            symbol="BONK",
            contract="So11111111111111111111111111111111111111112",
            confidence=0.8,
            text=msg_text,
            caller="tw-user",
        )
        await _process_signal(sig, callback, debug)
        return

    # --- Real Mode (twikit) ---
    await ensure_login()

    async def fetch_user_tweets(username: str, limit: int = 5):
        try:
            user = await client.get_user_by_screen_name(username)
            tweets = await user.get_tweets("Tweets", count=limit)
            for t in tweets:
                sig = SocialSignal(
                    platform="twitter",
                    source=username,
                    symbol=None,
                    contract=None,
                    confidence=0.5,
                    text=t.text,
                    caller=username,
                )
                await _process_signal(sig, callback, debug)
        except Exception as e:
            logger.error(f"[twitter] error fetching tweets for {username}: {e}")

    while True:
        for acc in accounts:
            await fetch_user_tweets(acc, limit=3)
        await asyncio.sleep(60)


async def verify_twitter_credentials() -> str:
    if not USE_REAL_TWITTER:
        return "mock-twitter-user"
    try:
        await ensure_login()
    except Exception as e:
        raise RuntimeError(f"Twitter credentials not set up: {e}")
    return "twitter-user"


def stream_twitter(limit: int = 1) -> Generator[SocialSignal, None, None]:
    if not USE_REAL_TWITTER:
        q: asyncio.Queue[Optional[SocialSignal]] = asyncio.Queue()

        async def runner():
            await run_twitter_ingest(q.put, debug=False)
            await q.put(None)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(runner())

        for _ in range(limit):
            sig = loop.run_until_complete(q.get())
            if sig is None:
                break
            yield sig

        loop.close()
    else:
        raise RuntimeError("stream_twitter() is not supported in real mode")


if __name__ == "__main__":

    async def consume(sig):
        print("[TWITTER]", sig)

    async def main():
        print("[twitter] starting ingest…")

        async def heartbeat():
            while True:
                print("[twitter] alive, still monitoring...")
                await asyncio.sleep(30)

        asyncio.create_task(heartbeat())
        await run_twitter_ingest(consume, debug=True)

    asyncio.run(main())