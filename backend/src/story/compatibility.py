"""Compatibility matrix evaluation between Macro, Beat, and Framing structures."""
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import yaml
from pydantic import BaseModel, ConfigDict

from src.domain.story_structure import (
    CompatibilityVerdict,
    FramingStrategy,
    FRAMING_STRATEGIES,
    normalize_beat_framework,
)
from .loader import DEFAULT_COMPATIBILITY_FILE

VALID_FRAMINGS = set(FRAMING_STRATEGIES) | {
    "chronological",
    "in_medias_res",
    "flashback",
    "intercut",
    "parallel_action",
    "reveal_delay",
}


class CompatibilityRule(BaseModel):
    """Rule defining compatibility verdict and reason for a structure pairing."""
    model_config = ConfigDict(extra="ignore")

    macro: str
    beat_layer: str
    verdict: CompatibilityVerdict
    reason: str


class CompatibilityEvaluator:
    """Evaluates compatibility between Macro dramatic structures, Beat layers, and Framing strategies."""

    def __init__(self, config_path: Optional[Path | str] = None):
        self.config_path = Path(config_path) if config_path else DEFAULT_COMPATIBILITY_FILE
        self.rules: Dict[Tuple[str, str], CompatibilityRule] = {}
        self._load_rules()

    def _load_rules(self) -> None:
        if not self.config_path.is_file():
            return
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Support both 'rules' and legacy 'pairs' keys
        raw_items = data.get("rules") or data.get("pairs") or []
        for item in raw_items:
            macro = str(item.get("macro", "")).strip().lower()
            beat = str(item.get("beat_layer") or item.get("beat", "")).strip().lower()
            beat = normalize_beat_framework(beat)
            reason = str(item.get("reason", ""))

            raw_verdict = item.get("verdict")
            if raw_verdict:
                verdict = CompatibilityVerdict(str(raw_verdict).upper())
            else:
                compatible = item.get("compatible", True)
                warning = item.get("warning", False)
                if not compatible:
                    verdict = CompatibilityVerdict.REJECT
                elif warning:
                    verdict = CompatibilityVerdict.WARN
                else:
                    verdict = CompatibilityVerdict.ALLOW

            if macro and beat:
                self.rules[(macro, beat)] = CompatibilityRule(
                    macro=macro,
                    beat_layer=beat,
                    verdict=verdict,
                    reason=reason,
                )

    def check_macro_beat_verdict(
        self, macro: str, beat_layer: str
    ) -> Tuple[CompatibilityVerdict, str]:
        """Check compatibility verdict between a MACRO structure and a BEAT framework.

        Returns:
            (verdict, reason) where verdict is ALLOW | WARN | REJECT.
        """
        macro_key = macro.strip().lower()
        beat_key = normalize_beat_framework(beat_layer)

        # Check explicit rule in compatibility.yaml
        if (macro_key, beat_key) in self.rules:
            rule = self.rules[(macro_key, beat_key)]
            return rule.verdict, rule.reason

        # Global rule: Kishōtenketsu rejects ANY conflict-based beat layer
        if macro_key == "kishotenketsu":
            return CompatibilityVerdict.REJECT, "The ten is juxtaposition, not escalation"

        # Default fallback
        return CompatibilityVerdict.ALLOW, "Default compatible combination"

    def check_macro_beat_compatibility(
        self, macro: str, beat: str
    ) -> Tuple[bool, bool, str]:
        """Check compatibility between a MACRO structure and a BEAT framework (backward compatible).

        Returns:
            (is_compatible, is_warning, reason)
        """
        verdict, reason = self.check_macro_beat_verdict(macro, beat)
        return (verdict != CompatibilityVerdict.REJECT, verdict == CompatibilityVerdict.WARN, reason)

    def check_macro_framing_verdict(
        self, macro: str, framing: str
    ) -> Tuple[CompatibilityVerdict, str]:
        """Check compatibility between a MACRO structure and a FRAMING strategy.

        Framing is strictly orthogonal to narrative shape: any MACRO + any FRAMING = ALLOW.
        """
        framing_key = framing.strip().lower()
        if framing_key not in VALID_FRAMINGS:
            return CompatibilityVerdict.REJECT, f"Unknown framing strategy: {framing}"
        return CompatibilityVerdict.ALLOW, "Framing is orthogonal to shape"

    def check_macro_framing_compatibility(
        self, macro: str, framing: str
    ) -> Tuple[bool, bool, str]:
        """Check compatibility between a MACRO structure and a FRAMING strategy (backward compatible)."""
        verdict, reason = self.check_macro_framing_verdict(macro, framing)
        return (verdict != CompatibilityVerdict.REJECT, verdict == CompatibilityVerdict.WARN, reason)

    def evaluate_combination(
        self,
        macro: str,
        beat_layer: Optional[str] = None,
        framing: str = "chronological",
    ) -> Tuple[CompatibilityVerdict, str]:
        """Evaluate a full 3-axis combination: MACRO + BEAT + FRAMING returning a verdict."""
        # 1. Framing check
        f_verdict, f_reason = self.check_macro_framing_verdict(macro, framing)
        if f_verdict == CompatibilityVerdict.REJECT:
            return f_verdict, f_reason

        # 2. Beat check if beat layer is provided
        if beat_layer:
            b_verdict, b_reason = self.check_macro_beat_verdict(macro, beat_layer)
            return b_verdict, b_reason

        return CompatibilityVerdict.ALLOW, "Valid structure configuration"

    def validate_combination(
        self,
        macro: str,
        beat_layer: Optional[str] = None,
        framing: str = "chronological",
    ) -> Tuple[bool, bool, str]:
        """Validate a full 3-axis combination: MACRO + BEAT + FRAMING (backward compatible)."""
        verdict, reason = self.evaluate_combination(macro, beat_layer, framing)
        return (verdict != CompatibilityVerdict.REJECT, verdict == CompatibilityVerdict.WARN, reason)


# Singleton instance
DEFAULT_COMPATIBILITY_EVALUATOR = CompatibilityEvaluator()
