import os
import asyncio
import json
import datetime
import subprocess
from typing import AsyncGenerator, Dict, Any

POLL_INTERVAL = int(os.getenv("TWITTER_POLL_INTERVAL", "60"))  # seconds
TRACK_USERS = os.getenv("TWITTER_TRACK_USERS", "").split(",")
TRACK_KEYWORDS = os.getenv("TWITTER_TRACK_KEYWORDS", "CA:").split(",")

last_seen: Dict[str, str] = {}  # user -> last tweet id


async def fetch_tweets(user: str):
    """
    Call snscrape to fetch tweets for a given user since last seen.
    Returns a list of dicts {id, date, content}.
    """
    cmd = ["snscrape", "--jsonl", f"twitter-user {user}"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    tweets = []

    if proc.stdout is None:
        return []
    for line in iter(proc.stdout.readline, b""):
        if not line:
            break
        try:
            tweet = json.loads(line.decode("utf-8"))
            tweets.append(tweet)
        except Exception:
            continue
    proc.terminate()

    if user in last_seen:
        tweets = [t for t in tweets if str(t["id"]) > last_seen[user]]

    if tweets:
        last_seen[user] = str(max(int(t["id"]) for t in tweets))

    return tweets


async def stream_twitter() -> AsyncGenerator[Dict[str, Any], None]:
    """
    Async generator that yields SocialSignal dicts from tracked users.
    """
    if not TRACK_USERS or TRACK_USERS == [""]:
        return

    while True:
        for user in TRACK_USERS:
            try:
                tweets = await fetch_tweets(user)
                for t in tweets:
                    text = t.get("content", "")
                    if any(kw.lower() in text.lower() for kw in TRACK_KEYWORDS):
                        yield {
                            "type": "social",
                            "platform": "twitter",
                            "source": user,
                            "content": text,
                            "mentions": [
                                kw
                                for kw in TRACK_KEYWORDS
                                if kw.lower() in text.lower()
                            ],
                            "confidence": 0.7,  # placeholder
                            "ts": t.get("date", datetime.datetime.utcnow().isoformat()),
                            "id": str(t.get("id")),
                        }
            except Exception as e:
                print(f"[twitter_ingest] error for {user}: {e}")
                continue
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":  # pragma: no cover

    async def test():
        async for sig in stream_twitter():
            print(sig)

    asyncio.run(test())
