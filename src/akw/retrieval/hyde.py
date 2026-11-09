"""Hypothetical Document Embeddings (HyDE) Generator."""

from __future__ import annotations

import logging
from typing import Optional
import numpy as np
import requests

from akw.core.config import AKWConfig

logger = logging.getLogger("akw.hyde")


class HyDEGenerator:
    """Generates hypothetical answer documents using a local or configured LLM."""

    HYDE_SYSTEM_PROMPT = (
        "You are an expert technical documentation assistant. Write a concise, authoritative, "
        "factual document excerpt that directly answers the question below. Do not include greetings, "
        "conversational filler, or disclaimers. Write only the simulated factual passage."
    )

    def __init__(self, config: Optional[AKWConfig] = None):
        self.config = config or AKWConfig()

    def generate_hypothetical_document(self, query: str) -> Optional[str]:
        """Generate a hypothetical document passage for the query.
        
        Returns None if HyDE is disabled or if the local service is unreachable.
        """
        if not self.config.hyde_enabled:
            return None

        prompt = f"Question: {query}\n\nFactual Document Excerpt:"

        if self.config.hyde_provider == "lmstudio":
            return self._generate_lmstudio(prompt)
        elif self.config.hyde_provider == "ollama":
            return self._generate_ollama(prompt)
        elif self.config.hyde_provider == "gemini" and self.config.gemini_api_key:
            return self._generate_gemini(prompt)

        return None

    def _generate_lmstudio(self, prompt: str) -> Optional[str]:
        """Query local LM Studio instance for HyDE expansion."""
        try:
            from akw.llm.lmstudio_client import LMStudioClient
            client = LMStudioClient(config=self.config)
            result = client.generate(
                prompt=prompt,
                model=self.config.hyde_model,
                system_instruction=self.HYDE_SYSTEM_PROMPT,
                temperature=0.3,
            )
            return result.strip() if result else None
        except Exception as e:
            logger.debug("HyDE LM Studio generation skipped: %s", e)
            return None

    def _generate_ollama(self, prompt: str) -> Optional[str]:
        """Query local Ollama instance for HyDE expansion."""
        url = f"{self.config.hyde_host.rstrip('/')}/api/generate"
        payload = {
            "model": self.config.hyde_model,
            "system": self.HYDE_SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 150},
        }

        try:
            response = requests.post(url, json=payload, timeout=8.0)
            if response.status_code == 200:
                result = response.json().get("response", "").strip()
                if result:
                    return result
        except Exception as e:
            logger.debug("HyDE Ollama generation skipped (service unavailable or timed out): %s", e)

        return None

    def _generate_gemini(self, prompt: str) -> Optional[str]:
        """Query Gemini for HyDE if configured."""
        try:
            from google import genai
            client = genai.Client(api_key=self.config.gemini_api_key)
            resp = client.models.generate_content(
                model=self.config.gemini_model,
                contents=f"{self.HYDE_SYSTEM_PROMPT}\n\n{prompt}",
            )
            return resp.text.strip() if resp.text else None
        except Exception as e:
            logger.debug("HyDE Gemini generation failed: %s", e)
            return None

    @staticmethod
    def blend_embeddings(query_vec: np.ndarray, hyde_vec: Optional[np.ndarray], alpha: float = 0.7) -> np.ndarray:
        """Blend hypothetical vector and query vector: alpha * hyde + (1 - alpha) * query."""
        if hyde_vec is None:
            return query_vec

        blended = alpha * hyde_vec + (1.0 - alpha) * query_vec
        norm = np.linalg.norm(blended)
        if norm > 0:
            blended = blended / norm
        return blended

