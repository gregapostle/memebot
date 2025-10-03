# memebot/ingest/llm_filter.py
import os
import json
from typing import Dict, Any
from memebot.types import SocialSignal
import openai  # or another LLM client

# Use environment variable for API key
openai.api_key = os.getenv("OPENAI_API_KEY", "")


async def filter_signal_with_llm(signal: SocialSignal) -> Dict[str, Any]:
    """
    Pass a SocialSignal through an LLM to determine if it's valuable.
    Returns a dict with 'valuable', 'reason', 'token', 'confidence'.
    """
    if not openai.api_key:
        # Fail-safe: if no key, mark everything as noise
        return {
            "valuable": False,
            "reason": "No LLM API key set",
            "token": None,
            "confidence": 0.0,
        }

    prompt = f"""
    You are an expert crypto researcher analyzing social media.
    Classify the following message:

    Message: {signal.text}
    Source: {signal.platform} / {signal.source}

    Instructions:
    - If the message contains a genuine crypto signal (e.g. buy/sell/mention of a token/contract), mark valuable=true.
    - If it's spam, giveaway, unrelated noise, mark valuable=false.
    - If valuable=true, extract the token symbol/contract if mentioned.
    - Assign a confidence score (0.0–1.0) for how likely this is actionable.

    Respond ONLY in JSON with keys: valuable (true/false), reason (string), token (string|null), confidence (float).
    """

    try:
        resp = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",  # lightweight fast model
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = resp.choices[0].message["content"]
        return json.loads(raw)
    except Exception as e:
        return {
            "valuable": False,
            "reason": f"LLM error: {e}",
            "token": None,
            "confidence": 0.0,
        }