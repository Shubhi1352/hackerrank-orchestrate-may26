import json
import logging
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from groq import Groq
from config import settings

logger = logging.getLogger(__name__)

_groq_client: Groq | None = None


def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client


async def _openrouter_call(prompt: str, json_mode: bool = False) -> str:
    """OpenRouter free tier."""
    import httpx
    if not settings.OPENROUTER_API_KEY:
        return ""

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/hackerrank-orchestrate",
    }
    body = {
        "model": "openai/gpt-oss-20b:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 800,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=body,
            )
            data = r.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"].strip()
            logger.error(f"OpenRouter error: {data}")
            return ""
    except Exception as e:
        logger.error(f"OpenRouter failed: {e}")
        return ""


async def _groq_call_with_retry(
    messages: list,
    max_tokens: int,
    response_format: dict | None = None,
    retries: int = 5,
) -> str:
    """Groq call with exponential backoff on 429s."""
    client = get_groq_client()
    loop = asyncio.get_event_loop()

    for attempt in range(retries):
        try:
            kwargs = dict(
                model=settings.GROQ_MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=max_tokens,
            )
            if response_format:
                kwargs['response_format'] = response_format

            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(**kwargs)
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            err_str = str(e)
            if '429' in err_str:
                wait = 3.0 * (attempt + 1)
                try:
                    match = re.search(r'try again in (\d+\.?\d*)s', err_str)
                    if match:
                        wait = float(match.group(1)) + 0.5
                except Exception:
                    pass
                logger.warning(f"Groq 429 — waiting {wait:.1f}s (attempt {attempt+1}/{retries})")
                await asyncio.sleep(wait)
            else:
                logger.error(f"Groq call failed: {e}")
                return ""

    logger.error(f"Groq call failed after {retries} retries")
    return ""


async def groq_json_call(prompt: str, system: str = "") -> dict:
    """Classification — OpenRouter first, Groq fallback."""
    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    # Try OpenRouter first
    content = await _openrouter_call(full_prompt, json_mode=True)

    # Fallback to Groq
    if not content:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        content = await _groq_call_with_retry(
            messages=messages,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

    if not content:
        return {}
    try:
        clean = content.strip().strip("```json").strip("```").strip()
        return json.loads(clean)
    except Exception as e:
        logger.error(f"JSON parse failed: {e} | {content[:100]}")
        return {}


async def gemini_text_call(prompt: str) -> str:
    """Generation — OpenRouter first, Groq fallback."""
    content = await _openrouter_call(prompt, json_mode=False)
    if content:
        return content

    messages = [{"role": "user", "content": prompt}]
    return await _groq_call_with_retry(
        messages=messages,
        max_tokens=settings.MAX_RESPONSE_TOKENS,
    )