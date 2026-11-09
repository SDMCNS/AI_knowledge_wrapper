"""Google Gemini Client using the official google-genai SDK."""

from __future__ import annotations

import logging
import os
from typing import Generator, Optional

try:
    from google import genai
    from google.genai import types
    _GOOGLE_GENAI_AVAILABLE = True
except Exception:
    _GOOGLE_GENAI_AVAILABLE = False

from akw.core.config import AKWConfig
from akw.core.exceptions import LLMError

logger = logging.getLogger("akw.llm.gemini")


class GeminiClient:
    """Wrapper around the official Google GenAI SDK for Gemini models."""

    def __init__(self, api_key: Optional[str] = None, config: Optional[AKWConfig] = None):
        if not _GOOGLE_GENAI_AVAILABLE:
            raise LLMError("google-genai package is not installed. Install via 'pip install google-genai'.")

        self.config = config or AKWConfig()
        self.api_key = api_key or self.config.gemini_api_key or os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise LLMError(
                "Gemini API key is required. Set GEMINI_API_KEY environment variable or pass api_key."
            )

        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            raise LLMError(f"Failed to initialize Gemini Client: {e}") from e

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Synchronously generate a grounded response."""
        model_name = model or self.config.gemini_model
        try:
            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_instruction,
            )
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception as e:
            raise LLMError(f"Gemini generation error: {e}") from e

    def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """Stream response tokens in real-time."""
        model_name = model or self.config.gemini_model
        try:
            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_instruction,
            )
            response_stream = self.client.models.generate_content_stream(
                model=model_name,
                contents=prompt,
                config=config,
            )
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            raise LLMError(f"Gemini streaming error: {e}") from e

