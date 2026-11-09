"""LM Studio & OpenAI-Compatible Local LLM Client."""

from __future__ import annotations

import json
import logging
from typing import Generator, List, Optional
import requests

from akw.core.config import AKWConfig
from akw.core.exceptions import LLMError

logger = logging.getLogger("akw.llm.lmstudio")


class LMStudioClient:
    """Client for local LLMs via LM Studio (OpenAI-compatible /v1 endpoints)."""

    def __init__(self, host: Optional[str] = None, config: Optional[AKWConfig] = None):
        self.config = config or AKWConfig()
        base = (host or self.config.lmstudio_host).rstrip("/")
        # Ensure /v1 suffix if not present
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        self.base_url = base

    def list_models(self) -> List[str]:
        """Query LM Studio for available loaded models."""
        url = f"{self.base_url}/models"
        try:
            resp = requests.get(url, timeout=3.0)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                # Filter out pure embedding models from chat completions list
                chat_models = []
                for m in models:
                    mid = m.get("id", "")
                    if mid and not mid.startswith("text-embedding-"):
                        chat_models.append(mid)
                return chat_models
        except Exception as e:
            logger.debug("LM Studio not reachable: %s", e)
        return []

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Synchronously generate response from LM Studio."""
        model_name = model or self.config.lmstudio_model
        url = f"{self.base_url}/chat/completions"

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        try:
            resp = requests.post(url, json=payload, timeout=120.0)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices and "message" in choices[0]:
                return choices[0]["message"].get("content", "")
            return ""
        except Exception as e:
            raise LLMError(f"LM Studio generation failed: {e}") from e

    def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """Stream response tokens from LM Studio using SSE."""
        model_name = model or self.config.lmstudio_model
        url = f"{self.base_url}/chat/completions"

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        try:
            with requests.post(url, json=payload, stream=True, timeout=120.0) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    clean_line = line.strip()
                    if clean_line.startswith("data: "):
                        data_str = clean_line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                token = delta.get("content", "")
                                if token:
                                    yield token
                        except Exception:
                            continue
        except Exception as e:
            raise LLMError(f"LM Studio streaming failed: {e}") from e

