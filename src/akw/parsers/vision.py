"""Vision LLM Engine for extracting semantic descriptions of figures and slides."""

from __future__ import annotations

import base64
import logging
from typing import Optional
import requests

from akw.core.config import AKWConfig

logger = logging.getLogger("akw.parsers.vision")


class VisionEngine:
    """Invokes local Vision LLMs (e.g. Qwen-VL in LM Studio) or Gemini to analyze figures and diagrams."""

    DEFAULT_PROMPT = (
        "Analyze this technical figure, chart, or slide diagram in detail. "
        "Transcribe any visible text, key data metrics, titles, and architectural components. "
        "Provide a clear, factual, and search-optimized summary of what is depicted."
    )

    def __init__(self, config: Optional[AKWConfig] = None):
        self.config = config or AKWConfig()

    def describe_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        prompt: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a textual description of an image using the configured Vision LLM.
        
        Returns None if vision is disabled or if the inference fails.
        """
        if not self.config.vision_enabled:
            return None

        user_prompt = prompt or self.DEFAULT_PROMPT
        provider = self.config.vision_llm_provider.lower()

        if provider == "lmstudio":
            return self._describe_lmstudio(image_bytes, mime_type, user_prompt)
        elif provider == "gemini":
            return self._describe_gemini(image_bytes, mime_type, user_prompt)
        elif provider == "ollama":
            return self._describe_ollama(image_bytes, mime_type, user_prompt)

        return None

    def _describe_lmstudio(
        self, image_bytes: bytes, mime_type: str, prompt: str
    ) -> Optional[str]:
        """Query LM Studio (OpenAI-compatible /v1/chat/completions) with image_url."""
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{b64_img}"

        url = f"{self.config.lmstudio_host.rstrip('/')}/chat/completions"
        if not url.endswith("/v1/chat/completions") and "/v1" not in url:
            url = f"{self.config.lmstudio_host.rstrip('/')}/v1/chat/completions"

        payload = {
            "model": self.config.vision_llm_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
            "max_tokens": 400,
            "temperature": 0.2,
            "stream": False,
        }

        try:
            resp = requests.post(
                url, json=payload, timeout=self.config.vision_timeout_seconds
            )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    content = choices[0]["message"].get("content", "").strip()
                    if content:
                        return content
            else:
                logger.debug("LM Studio vision returned HTTP %d: %s", resp.status_code, resp.text)
        except Exception as e:
            logger.debug("Vision analysis via LM Studio skipped (timeout or error): %s", e)

        return None

    def _describe_gemini(
        self, image_bytes: bytes, mime_type: str, prompt: str
    ) -> Optional[str]:
        """Query Gemini multimodal API for vision description."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.config.gemini_api_key)
            part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            resp = client.models.generate_content(
                model=self.config.vision_llm_model or "gemini-3.8-flash",
                contents=[part, prompt],
            )
            return resp.text.strip() if resp.text else None
        except Exception as e:
            logger.debug("Vision analysis via Gemini failed: %s", e)
            return None

    def _describe_ollama(
        self, image_bytes: bytes, mime_type: str, prompt: str
    ) -> Optional[str]:
        """Query Ollama /api/generate with images array."""
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        url = f"{self.config.ollama_host.rstrip('/')}/api/generate"
        payload = {
            "model": self.config.vision_llm_model,
            "prompt": prompt,
            "images": [b64_img],
            "stream": False,
            "options": {"temperature": 0.2},
        }
        try:
            resp = requests.post(
                url, json=payload, timeout=self.config.vision_timeout_seconds
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
        except Exception as e:
            logger.debug("Vision analysis via Ollama failed: %s", e)
        return None

