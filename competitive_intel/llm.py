"""
competitive_intel/llm.py
------------------------
Groq LLM wrapper using openai/gpt-oss-120b.
Provides:
  - call_llm()           non-streaming, returns full string (used inside graph nodes)
  - call_llm_streaming() streaming generator (used in main.py for visible output)
"""

import os
from typing import Generator

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_groq_client: Groq | None = None

MODEL = "openai/gpt-oss-120b"
TEMPERATURE = 1
MAX_TOKENS = 1024   # keep under Groq free-tier 8000 TPM limit
REASONING_EFFORT = "medium"


def _get_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY is not set in .env")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def call_llm(messages: list[dict], reasoning_effort: str = REASONING_EFFORT) -> str:
    """
    Non-streaming LLM call — collects the full response before returning.
    Used inside LangGraph node functions so they return deterministic strings.
    """
    client = _get_client()
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_completion_tokens=MAX_TOKENS,
        top_p=1,
        reasoning_effort=reasoning_effort,
        stream=True,   # stream underneath but collect into one string
        stop=None,
    )
    chunks = []
    for chunk in completion:
        delta = chunk.choices[0].delta.content
        if delta:
            chunks.append(delta)
    return "".join(chunks)


def call_llm_streaming(messages: list[dict], reasoning_effort: str = REASONING_EFFORT) -> Generator[str, None, None]:
    """
    Streaming generator — yields token-by-token for live console display.
    Used only in main.py for the final synthesis output.
    """
    client = _get_client()
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_completion_tokens=MAX_TOKENS,
        top_p=1,
        reasoning_effort=reasoning_effort,
        stream=True,
        stop=None,
    )
    for chunk in completion:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
