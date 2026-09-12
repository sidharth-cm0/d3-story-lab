"""Gemini LLM Provider implementation using environment variables"""
import os
import json
import logging
from typing import Type, TypeVar, Optional, Dict, Any
from pydantic import BaseModel
from .base import LLMProvider

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """Production provider using Google Gemini models with structured JSON output and schema validation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-flash-latest",
    ):
        self.api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY")
        self.model_name = model_name

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using Gemini model."""
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set it in your environment or .env file, or use MockLLMProvider."
            )
        try:
            import httpx

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            payload: Dict[str, Any] = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            if system_prompt:
                payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
                logger.warning(f"Gemini generateContent returned status {resp.status_code}: {resp.text[:150]}")
                return ""
        except Exception as e:
            logger.warning(f"GeminiProvider generate_text failed: {e}")
            return ""

    def generate_structured(
        self,
        schema: Type[T],
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> T:
        """Generate and validate structured output against Pydantic schema."""
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set it in your environment or .env file, or use MockLLMProvider."
            )
        import httpx

        schema_json = json.dumps(schema.model_json_schema())
        augmented_prompt = (
            f"{prompt}\n\nRespond ONLY with a valid JSON object strictly conforming to this JSON Schema:\n{schema_json}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": augmented_prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            text = parts[0]["text"]
                            return schema.model_validate_json(text)
                logger.warning(
                    f"Gemini API returned status {resp.status_code} ({resp.text[:120]}), using fallback provider."
                )
        except Exception as e:
            logger.warning(f"GeminiProvider generate_structured failed ({e}), using fallback provider.")

        from .mock import MockLLMProvider
        return MockLLMProvider().generate_structured(schema, prompt, system_prompt=system_prompt)
