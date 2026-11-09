"""Local LLM Client for Ollama and local OpenAI-compatible endpoints."""

from __future__ import annotations

import json
import logging
from typing import Generator, List, Optional
import requests

from akw.core.config import AKWConfig
from akw.core.exceptions import LLMError

logger = logging.getLogger("akw.llm.local")


class LocalLLMClient:
    """Client for local LLMs via Ollama HTTP API."""

    def __init__(self, host: Optional[str] = None, config: Optional[AKWConfig] = None):
        self.config = config or AKWConfig()
        self.host = (host or self.config.ollama_host).rstrip("/")

    def list_models(self) -> List[str]:
        """Query local Ollama for available installed models."""
        url = f"{self.host}/api/tags"
        try:
            resp = requests.get(url, timeout=3.0)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [m.get("name", "") for m in models if m.get("name")]
        except Exception:
            pass
        return []

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Synchronously generate response from local model."""
        model_name = model or self.config.ollama_model
        url = f"{self.host}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "system": system_instruction or "",
            "stream": False,
            "options": {"temperature": temperature},
        }

        try:
            resp = requests.post(url, json=payload, timeout=120.0)
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            raise LLMError(f"Local LLM generation failed: {e}") from e

    def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """Stream response tokens from local model."""
        model_name = model or self.config.ollama_model
        url = f"{self.host}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "system": system_instruction or "",
            "stream": True,
            "options": {"temperature": temperature},
        }

        try:
            with requests.post(url, json=payload, stream=True, timeout=120.0) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if line:
                        try:
                            data = json.loads(line)
                            token = data.get("response", "")
                            if token:
                                yield token
                            if data.get("done", False):
                                break
                        except Exception:
                            continue
        except Exception as e:
            raise LLMError(f"Local LLM streaming failed: {e}") from e

