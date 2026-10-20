"""Local OpenAI-compatible / llama.cpp / Ollama provider scaffold for D3 Story Lab.

Designed for future local creative writing models (e.g. Crownelius/The-Crow-9B-Creative-Writing-Opus4.6-DISTILL-Heretic)
to act as an offline D3 Scribe or Narrative Intelligence model without downloading weights during v0.1.
"""

from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Type, TypeVar, Optional
from pydantic import BaseModel

from .base import LLMProvider

T = TypeVar("T", bound=BaseModel)


class LocalOpenAICompatibleProvider(LLMProvider):
    """Scaffold for local LLM inference engines (llama.cpp server, Ollama, vLLM, Aphrodite).

    Points to local OpenAI-compatible chat completion endpoints.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080/v1",
        model_name: str = "Crownelius/The-Crow-9B-Creative-Writing-Opus4.6-DISTILL-Heretic",
        timeout_seconds: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        """Check if local inference server is running and reachable."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/models",
                headers={"User-Agent": "D3-Story-Lab"},
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate freeform textual response from local model server."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "D3-Story-Lab"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                return res_json["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Local model provider unavailable at {self.base_url}: {e}") from e

    def generate_structured(
        self,
        schema: Type[T],
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> T:
        """Generate structured Pydantic response via JSON schema instruction."""
        schema_json = json.dumps(schema.model_json_schema())
        augmented_system = (
            (system_prompt or "") +
            f"\nYou MUST respond ONLY with valid JSON conforming to this schema:\n{schema_json}"
        )
        raw_text = self.generate_text(prompt, system_prompt=augmented_system.strip())

        # Clean markdown codeblocks if present
        clean = raw_text.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            clean = "\n".join(lines).strip()

        parsed = json.loads(clean)
        return schema.model_validate(parsed)
