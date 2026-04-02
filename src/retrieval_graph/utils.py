"""Utility functions for LLM calls and shared helpers."""

import os
import json
import asyncio
import logging
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> AsyncAnthropic:
    """Get or create the async Anthropic client singleton."""
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return _client


async def load_chat_model(
    system_prompt: str,
    user_message: str,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 4096,
    retries: int = 3,
) -> str:
    """
    Send a chat message to the LLM and return the text response.

    Uses exponential backoff on failure, up to `retries` attempts.
    """
    client = _get_client()
    for attempt in range(retries):
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except Exception as e:
            logger.warning("LLM call attempt %d failed: %s", attempt + 1, e)
            if attempt < retries - 1:
                await asyncio.sleep(2 ** (attempt + 1))
            else:
                raise


async def load_chat_model_json(
    system_prompt: str,
    user_message: str,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 4096,
    retries: int = 3,
) -> dict:
    """
    Send a chat message and parse the response as JSON.

    Extracts JSON from the response, handling markdown code fences if present.
    """
    raw = await load_chat_model(system_prompt, user_message, model, max_tokens, retries)
    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (fences)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)
