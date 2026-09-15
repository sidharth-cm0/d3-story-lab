"""Budget Governor and content-hash caching for AI call sites."""
from __future__ import annotations
import hashlib
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class BudgetExceededError(Exception):
    """Raised when an operation exceeds allocated token, panel, or cost limits."""
    pass


class BudgetGovernor:
    """Enforces hard limits on tokens, image panels, and estimated USD cost."""

    def __init__(
        self,
        max_tokens: int = 100_000,
        max_panels: int = 50,
        max_cost_usd: float = 5.0,
        cost_per_1k_tokens: float = 0.002,
        cost_per_panel: float = 0.02,
    ):
        self.max_tokens = max_tokens
        self.max_panels = max_panels
        self.max_cost_usd = max_cost_usd
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.cost_per_panel = cost_per_panel

        self.total_tokens: int = 0
        self.total_panels: int = 0
        self.estimated_cost_usd: float = 0.0

    def check_limits(self, additional_tokens: int = 0, additional_panels: int = 0):
        """Check whether adding tokens or panels would exceed budget. Raises BudgetExceededError if exceeded."""
        next_tokens = self.total_tokens + additional_tokens
        next_panels = self.total_panels + additional_panels
        token_cost = (additional_tokens / 1000.0) * self.cost_per_1k_tokens
        panel_cost = additional_panels * self.cost_per_panel
        next_cost = self.estimated_cost_usd + token_cost + panel_cost

        if next_tokens > self.max_tokens:
            raise BudgetExceededError(
                f"Token budget exceeded: {next_tokens} > {self.max_tokens}"
            )
        if next_panels > self.max_panels:
            raise BudgetExceededError(
                f"Panel budget exceeded: {next_panels} > {self.max_panels}"
            )
        if next_cost > self.max_cost_usd:
            raise BudgetExceededError(
                f"Cost budget exceeded: ${next_cost:.4f} > ${self.max_cost_usd:.4f}"
            )

    def charge_tokens(self, tokens: int):
        """Record token consumption after checking limits."""
        self.check_limits(additional_tokens=tokens, additional_panels=0)
        self.total_tokens += tokens
        self.estimated_cost_usd += (tokens / 1000.0) * self.cost_per_1k_tokens

    def charge_panel(self):
        """Record a generated panel after checking limits."""
        self.check_limits(additional_tokens=0, additional_panels=1)
        self.total_panels += 1
        self.estimated_cost_usd += self.cost_per_panel

    def get_summary(self) -> Dict[str, Any]:
        """Return budget consumption summary."""
        return {
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "total_panels": self.total_panels,
            "max_panels": self.max_panels,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "max_cost_usd": self.max_cost_usd,
        }


class ContentHashCache:
    """Content-hash cache for image generation avoiding duplicate provider calls.
    Key = SHA-256 hash of (shot prompt + visual style prompt + character visual anchor descriptions + aspect ratio).
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    @staticmethod
    def compute_hash(
        shot_prompt: str,
        visual_style_prompt: str = "",
        character_visual_anchors: str = "",
        aspect_ratio: str = "16:9",
    ) -> str:
        """Compute SHA-256 key from shot prompt, visual style, anchors, and aspect ratio."""
        payload = (
            f"{shot_prompt.strip()}|"
            f"{visual_style_prompt.strip()}|"
            f"{character_visual_anchors.strip()}|"
            f"{aspect_ratio.strip()}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> Optional[Any]:
        return self._cache.get(cache_key)

    def set(self, cache_key: str, value: Any):
        self._cache[cache_key] = value

    def contains(self, cache_key: str) -> bool:
        return cache_key in self._cache

    def clear(self):
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)
