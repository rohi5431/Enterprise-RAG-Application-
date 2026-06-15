"""
Google Gemini LLM Client
"""
from __future__ import annotations

import logging
from typing import Generator, Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for Google Gemini API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": max_tokens,
            },
        }
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return parts[0].get("text", "") if parts else ""
            return ""
        except Exception as exc:
            logger.error("Gemini generation failed: %s", exc)
            raise RuntimeError(f"Gemini generation failed: {exc}") from exc

    def generate_stream(self, prompt: str) -> Generator[str, None, None]:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:streamGenerateContent?key={self.api_key}&alt=sse"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 512},
        }
        try:
            with requests.post(url, json=payload, timeout=self.timeout, stream=True) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.startswith(b"data: "):
                        continue
                    import json
                    chunk = json.loads(line[6:])
                    for candidate in chunk.get("candidates", []):
                        for part in candidate.get("content", {}).get("parts", []):
                            text = part.get("text", "")
                            if text:
                                yield text
        except Exception as exc:
            logger.error("Gemini streaming failed: %s", exc)
            raise RuntimeError(f"Gemini streaming failed: {exc}") from exc
