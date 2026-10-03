"""Thin Groq wrapper. Works with a .env file, environment variable, or Streamlit secrets."""
import json
import os
import re

from groq import Groq

from . import config

_client = None


def _api_key():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            key = None
    return key


def has_key() -> bool:
    return bool(_api_key())


def client() -> Groq:
    global _client
    if _client is None:
        key = _api_key()
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set (use .env or Streamlit secrets).")
        _client = Groq(api_key=key)
    return _client


def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text or "", re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}


def chat_json(system: str, user: str, temperature: float = 0.1, max_tokens: int = 1500) -> dict:
    """Call Groq in JSON mode (prompts must mention JSON)."""
    resp = client().chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    return _parse_json(resp.choices[0].message.content or "")


def transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """Speech-to-text via Groq Whisper (supports Urdu)."""
    r = client().audio.transcriptions.create(
        file=(filename, audio_bytes), model=config.WHISPER_MODEL, response_format="text"
    )
    return r if isinstance(r, str) else getattr(r, "text", "")
