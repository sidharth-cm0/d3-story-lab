"""Deterministic Mock LLM Provider for offline simulation and testing"""
from typing import Type, TypeVar, Optional, Dict, Any, Callable
from pydantic import BaseModel
from .base import LLMProvider

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """Deterministic, keyless provider generating valid structured and text outputs for tests"""

    def __init__(self):
        self._structured_handlers: Dict[Type[BaseModel], Callable[[str], BaseModel]] = {}
        self._text_handlers: Dict[str, str] = {}
        self.call_history = []

    def register_structured_handler(
        self,
        schema: Type[T],
        handler: Callable[[str], T],
    ):
        """Register a custom handler for a specific Pydantic schema"""
        self._structured_handlers[schema] = handler

    def register_text_response(self, prompt_substring: str, response: str):
        """Register fixed response for prompts containing substring"""
        self._text_handlers[prompt_substring] = response

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate deterministic text response"""
        self.call_history.append({"type": "text", "prompt": prompt, "system_prompt": system_prompt})
        for substring, response in self._text_handlers.items():
            if substring.lower() in prompt.lower():
                return response
        return "Deterministic mock text response."

    def generate_structured(
        self,
        schema: Type[T],
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> T:
        """Generate deterministic structured response matching the target schema"""
        self.call_history.append(
            {"type": "structured", "schema": schema.__name__, "prompt": prompt, "system_prompt": system_prompt}
        )

        # Check registered handler
        if schema in self._structured_handlers:
            return self._structured_handlers[schema](prompt)  # type: ignore

        from pydantic_core import PydanticUndefined

        # Construct default instance from schema fields
        field_defaults = {}
        for field_name, field_info in schema.model_fields.items():
            if (
                field_info.default is not None
                and field_info.default is not ...
                and field_info.default is not PydanticUndefined
            ):
                field_defaults[field_name] = field_info.default
            elif field_info.default_factory is not None:
                field_defaults[field_name] = field_info.default_factory()
            elif field_info.annotation is str:
                field_defaults[field_name] = f"mock_{field_name}"
            elif field_info.annotation is int:
                field_defaults[field_name] = 1
            elif field_info.annotation is float:
                field_defaults[field_name] = 0.5
            elif field_info.annotation is bool:
                field_defaults[field_name] = True
            elif getattr(field_info.annotation, "__origin__", None) is list:
                field_defaults[field_name] = []
            elif getattr(field_info.annotation, "__origin__", None) is dict:
                field_defaults[field_name] = {}
            else:
                field_defaults[field_name] = None

        return schema.model_validate(field_defaults)
