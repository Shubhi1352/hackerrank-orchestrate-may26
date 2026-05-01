import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from groq import Groq
from google import genai
from google.genai import types

from config import settings

logger = logging.getLogger(__name__)

# Lazy clients
_groq_client: Groq | None = None
_gemini_configured = False


def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client


def configure_gemini() -> None:
    global _gemini_configured
    if not _gemini_configured:
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        _gemini_configured = True


async def groq_json_call(prompt: str, system: str = "") -> dict:
    """
    Call Groq and parse JSON response.
    Returns empty dict on failure — caller handles fallback.
    """
    import asyncio
    client = get_groq_client()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        # Groq SDK is sync — run in executor to not block event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        logger.error(f"Groq call failed: {e}")
        return {}


async def gemini_text_call(prompt: str) -> str:
    import asyncio
    configure_gemini()
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=settings.MAX_RESPONSE_TOKENS,
                )
            )
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        return ""