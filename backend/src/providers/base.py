"""Abstract LLM Provider interface"""
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Abstract interface decoupling simulation and generator logic from specific LLM vendors"""

    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate freeform textual response"""
        pass

    @abstractmethod
    def generate_structured(
        self,
        schema: Type[T],
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> T:
        """Generate a response deterministically validated against a Pydantic schema"""
        pass
