"""Groq fallback LLM client for ReconQ.

Used when Gemini API is unavailable or rate-limited.
Model: llama-3.3-70b-versatile (fast, strong, free tier friendly).
"""
import os
from groq import Groq

GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def get_groq_client() -> Groq | None:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    return Groq(api_key=api_key)


def groq_chat(system_prompt: str, user_message: str, max_tokens: int = 4096) -> str:
    """Send a single-turn message to Groq and return the reply text."""
    client = get_groq_client()
    if not client:
        return "No LLM available. Please add GEMINI_API_KEY or GROQ_API_KEY to your .env file."
    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return completion.choices[0].message.content or "No response generated."
    except Exception as exc:
        return f"Groq error: {exc}"


def groq_available() -> bool:
    return bool(os.environ.get("GROQ_API_KEY", "").strip())
