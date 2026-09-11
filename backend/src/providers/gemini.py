"""Gemini LLM Provider implementation using environment variables"""
import os
import json
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from .base import LLMProvider

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """Production provider using Google Gemini models with structured JSON output and schema validation"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self._client = None

    def _get_client(self):
        """Lazy initialize client to prevent startup failure when API key is unconfigured"""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "GEMINI_API_KEY is not set. Please set it in your environment or .env file, or use MockLLMProvider."
                )
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "The 'google-genai' package is required to use GeminiProvider. Run 'pip install google-genai'."
                )
        return self._client

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using Gemini model"""
        client = self._get_client()
        config = {}
        if system_prompt:
            config["system_instruction"] = system_prompt

        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        return response.text or ""

    def generate_structured(
        self,
        schema: Type[T],
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> T:
        """Generate and validate structured output against Pydantic schema"""
        client = self._get_client()
        schema_json = json.dumps(schema.model_json_schema())
        augmented_prompt = (
            f"{prompt}\n\nRespond ONLY with a valid JSON object strictly conforming to this JSON Schema:\n{schema_json}"
        )

        config = {"response_mime_type": "application/json"}
        if system_prompt:
            config["system_instruction"] = system_prompt

        response = client.models.generate_content(
            model=self.model_name,
            contents=augmented_prompt,
            config=config,
        )
        text = response.text or "{}"
        return schema.model_validate_json(text)
