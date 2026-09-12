"""Screenplay Quality Validator for evaluating narrative coherence, dialogue quality, and grounding."""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import re
from pydantic import BaseModel, ConfigDict, Field

from src.narrative.fountain import ScreenplayDocument, ScreenplayBlockType
from src.domain.world import WorldState


class ScreenplayQualityIssue(BaseModel):
    """An identified issue in screenplay structure or character performance."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    category: str
    severity: str  # "warning" | "error" | "info"
    scene_number: Optional[int] = None
    block_id: Optional[str] = None
    message: str
    recommendation: str


class ScreenplayQualityReport(BaseModel):
    """Quality metrics and validation diagnostics for a generated screenplay."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_scenes: int
    total_blocks: int
    total_dialogue_lines: int
    parenthetical_ratio: float
    exposition_frequency: float
    repetition_score: float  # 0.0 (no repetition) to 1.0 (heavy repetition)
    knowledge_leak_count: int
    teleporting_count: int
    overall_quality_score: float  # 0.0 to 100.0
    issues: List[ScreenplayQualityIssue] = Field(default_factory=list)
    dramatic_progression_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class ScreenplayQualityValidator:
    """Validates screenplay formatting, dialogue quality, knowledge leaks, and dramatic progression."""

    EXPOSITION_CLICHES = [
        r"\bas you know\b",
        r"\blet me explain\b",
        r"\bhere is what happened\b",
        r"\bremember when we\b",
        r"\bwe need to talk about\b",
        r"\bto be completely honest with you\b",
    ]

    def validate_screenplay(
        self,
        document: ScreenplayDocument,
        world: Optional[WorldState] = None,
    ) -> ScreenplayQualityReport:
        return self.validate(document, world)

    def validate(
        self,
        document: ScreenplayDocument,
        world: Optional[WorldState] = None,
    ) -> ScreenplayQualityReport:
        """Execute validation passes across the ScreenplayDocument."""
        issues: List[ScreenplayQualityIssue] = []

        total_scenes = len(document.scenes)
        total_blocks = sum(len(s.blocks) for s in document.scenes)
        total_dialogue = 0
        total_parentheticals = 0
        exposition_hits = 0
        consecutive_parentheticals = 0
        knowledge_leaks = 0
        teleporting_count = 0

        recent_dialogues: List[str] = []
        dialogue_duplicates = 0
        action_duplicates = 0
        seen_actions: Set[str] = set()

        last_known_locations: Dict[str, str] = {}

        for scene in document.scenes:
            loc_id = scene.location_id
            scene_chars: Set[str] = set()
            prev_block_type = None

            for b in scene.blocks:
                if b.block_type == ScreenplayBlockType.DIALOGUE:
                    total_dialogue += 1
                    t_clean = re.sub(r"[^a-z0-9\s]", "", b.text.lower()).strip()
                    if t_clean in recent_dialogues[-4:]:
                        dialogue_duplicates += 1
                        issues.append(
                            ScreenplayQualityIssue(
                                category="dialogue_repetition",
                                severity="warning",
                                scene_number=scene.scene_number,
                                block_id=b.id,
                                message=f"Duplicate dialogue detected: '{b.text[:40]}...'",
                                recommendation="Vary dialogue intent with tactical subtext or counter-questions.",
                            )
                        )
                    recent_dialogues.append(t_clean)

                    # Exposition check
                    for pat in self.EXPOSITION_CLICHES:
                        if re.search(pat, b.text.lower()):
                            exposition_hits += 1
                            issues.append(
                                ScreenplayQualityIssue(
                                    category="exposition_heavy",
                                    severity="warning",
                                    scene_number=scene.scene_number,
                                    block_id=b.id,
                                    message=f"Exposition cliche detected: '{b.text[:50]}...'",
                                    recommendation="Allow information to emerge through tactical conflict rather than overt explanation.",
                                )
                            )

                    # Knowledge Leak Check
                    if world and b.character_id and b.character_id in world.characters:
                        char = world.characters[b.character_id]
                        for sec_id, sec in world.secrets.items():
                            if b.character_id not in sec.known_by and sec.character_id != b.character_id:
                                # Character does NOT know this secret
                                s_words = [w for w in sec.statement.lower().split() if len(w) > 4]
                                matches = [w for w in s_words if w in b.text.lower()]
                                if len(matches) >= 3:
                                    knowledge_leaks += 1
                                    issues.append(
                                        ScreenplayQualityIssue(
                                            category="knowledge_leak",
                                            severity="error",
                                            scene_number=scene.scene_number,
                                            block_id=b.id,
                                            message=f"Character '{char.name}' speaks of secret facts they have not observed or learned.",
                                            recommendation="Restrict dialogue to character's canonical known facts and beliefs.",
                                        )
                                    )

                elif b.block_type == ScreenplayBlockType.PARENTHETICAL:
                    total_parentheticals += 1
                    if prev_block_type == ScreenplayBlockType.PARENTHETICAL:
                        consecutive_parentheticals += 1
                        issues.append(
                            ScreenplayQualityIssue(
                                category="parenthetical_overuse",
                                severity="warning",
                                scene_number=scene.scene_number,
                                block_id=b.id,
                                message="Consecutive stacked parentheticals detected.",
                                recommendation="Translate emotional beats into physical action lines rather than stacked parentheticals.",
                            )
                        )

                elif b.block_type == ScreenplayBlockType.ACTION:
                    act_norm = re.sub(r"[^a-z0-9\s]", "", b.text.lower()).strip()
                    if act_norm in seen_actions and len(act_norm) > 20:
                        action_duplicates += 1
                    seen_actions.add(act_norm)

                if b.character_id:
                    scene_chars.add(b.character_id)

                prev_block_type = b.block_type

            # Check teleporting between scenes
            for cid in scene_chars:
                if cid in last_known_locations:
                    prev_loc = last_known_locations[cid]
                    if prev_loc != loc_id:
                        # Check if scene contains movement block for this character
                        has_movement = any(
                            b.block_type == ScreenplayBlockType.ACTION and "enter" in b.text.lower()
                            for b in scene.blocks
                        )
                        if not has_movement and prev_loc != "unknown":
                            teleporting_count += 1
                            issues.append(
                                ScreenplayQualityIssue(
                                    category="teleporting",
                                    severity="info",
                                    scene_number=scene.scene_number,
                                    message=f"Character {cid} transitions from {prev_loc} to {loc_id} without explicit movement line.",
                                    recommendation="Ensure entrance action line bridges location change.",
                                )
                            )
                last_known_locations[cid] = loc_id

        parenthetical_ratio = (total_parentheticals / max(1, total_dialogue))
        if parenthetical_ratio > 0.35:
            issues.append(
                ScreenplayQualityIssue(
                    category="parenthetical_overuse",
                    severity="warning",
                    message=f"High parenthetical ratio: {parenthetical_ratio:.1%}.",
                    recommendation="Limit parentheticals to essential inflections; express tension through physical cues.",
                )
            )

        exposition_freq = (exposition_hits / max(1, total_dialogue))
        repetition_score = min(1.0, (dialogue_duplicates * 2 + action_duplicates) / max(1, total_blocks))

        # Calculate score out of 100
        quality = 100.0
        quality -= knowledge_leaks * 20.0
        quality -= dialogue_duplicates * 5.0
        quality -= exposition_hits * 6.0
        quality -= consecutive_parentheticals * 4.0
        if parenthetical_ratio > 0.35:
            quality -= 10.0
        quality = max(0.0, min(100.0, round(quality, 1)))

        return ScreenplayQualityReport(
            total_scenes=total_scenes,
            total_blocks=total_blocks,
            total_dialogue_lines=total_dialogue,
            parenthetical_ratio=round(parenthetical_ratio, 3),
            exposition_frequency=round(exposition_freq, 3),
            repetition_score=round(repetition_score, 3),
            knowledge_leak_count=knowledge_leaks,
            teleporting_count=teleporting_count,
            overall_quality_score=quality,
            issues=issues,
            dramatic_progression_score=round(max(0.6, 1.0 - repetition_score), 2),
        )
