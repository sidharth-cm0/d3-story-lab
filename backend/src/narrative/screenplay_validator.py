"""Screenplay Quality Validator for evaluating narrative coherence, dialogue quality, and grounding."""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Set
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
    provenance_coverage: float = 1.0
    ungrounded_block_count: int = 0
    scene_turn_fulfillment_score: float = 1.0

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

    STOP_WORDS = {
        "about", "after", "again", "against", "all", "and", "any", "are", "aren't", "because",
        "been", "before", "being", "below", "between", "both", "but", "by", "can't", "cannot",
        "could", "couldn't", "did", "didn't", "does", "doesn't", "doing", "don't", "down",
        "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
        "have", "haven't", "having", "her", "here", "here's", "hers", "herself", "him",
        "himself", "his", "how", "how's", "into", "it's", "its", "itself", "let's", "more",
        "most", "mustn't", "myself", "nor", "not", "off", "once", "only", "other", "ought",
        "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd",
        "she'll", "she's", "should", "shouldn't", "some", "such", "than", "that", "that's",
        "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these",
        "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "too",
        "under", "until", "very", "was", "wasn't", "we'd", "we'll", "we're", "we've", "were",
        "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while",
        "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you",
        "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves", "knows"
    }

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
        ungrounded_blocks = 0
        total_groundable_blocks = 0
        grounded_blocks = 0
        scene_turn_satisfied = 0

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
                # Track characters appearing in this scene
                if b.character_id:
                    scene_chars.add(b.character_id)

                # Provenance Grounding Check for Action and Dialogue
                if b.block_type in (ScreenplayBlockType.ACTION, ScreenplayBlockType.DIALOGUE):
                    total_groundable_blocks += 1
                    has_provenance = False

                    if b.source_event_ids:
                        if world and world.events:
                            if any(ev_id in world.events for ev_id in b.source_event_ids):
                                has_provenance = True
                            else:
                                has_provenance = False
                        else:
                            has_provenance = True
                    elif b.derived_from_event_id:
                        if world and world.events:
                            has_provenance = b.derived_from_event_id in world.events
                        else:
                            has_provenance = True
                    elif b.is_performance_cue or b.cue_type:
                        has_provenance = True
                    elif b.metadata.get("spatial_tension") or b.metadata.get("narrative_framing") or b.metadata.get("connective"):
                        has_provenance = True

                    if has_provenance:
                        grounded_blocks += 1
                    else:
                        ungrounded_blocks += 1
                        issues.append(
                            ScreenplayQualityIssue(
                                category="provenance_violation",
                                severity="error",
                                scene_number=scene.scene_number,
                                block_id=b.id,
                                message=f"Block lacks event provenance: Scribe cannot invent events ('{b.text[:40]}...').",
                                recommendation="Ground all action and dialogue directly in validated simulation events.",
                            )
                        )

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
                                s_words = [
                                    w for w in re.findall(r"\b[a-z]{3,}\b", sec.statement.lower())
                                    if w not in self.STOP_WORDS
                                ]
                                if s_words:
                                    matches = [w for w in s_words if w in b.text.lower()]
                                    threshold = max(2, int(len(s_words) * 0.5))
                                    if len(matches) >= threshold or (len(s_words) <= 2 and len(matches) >= 1):
                                        knowledge_leaks += 1
                                        issues.append(
                                            ScreenplayQualityIssue(
                                                category="knowledge_leak",
                                                severity="error",
                                                scene_number=scene.scene_number,
                                                block_id=b.id,
                                                message=f"Character '{char.name}' speaks of secret facts they have not observed or learned: mentions {matches}.",
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

                prev_block_type = b.block_type

            # Check teleporting between scenes
            for cid in scene_chars:
                if cid in last_known_locations:
                    prev_loc = last_known_locations[cid]
                    if prev_loc != loc_id:
                        has_movement = any(
                            b.block_type == ScreenplayBlockType.ACTION and any(kw in b.text.lower() for kw in ["enter", "steps into", "slips through", "walks into", "arrives"])
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

            # Scene turn & CoreEmotionalObjective validation
            scene_has_issue = False
            meta = scene.metadata or {}
            ceo = meta.get("core_emotional_objective")
            scene_purpose = meta.get("scene_purpose")

            if ceo and isinstance(ceo, dict):
                focal_char = ceo.get("focal_character_id")
                if focal_char and (not world or focal_char in world.characters):
                    if focal_char not in scene_chars:
                        scene_has_issue = True
                        issues.append(
                            ScreenplayQualityIssue(
                                category="focal_character_missing",
                                severity="warning",
                                scene_number=scene.scene_number,
                                message=f"Focal character '{focal_char}' driving objective '{ceo.get('immediate_desire')}' is absent from Scene {scene.scene_number}.",
                                recommendation="Ensure focal character active participation in driving scene objective.",
                            )
                        )

            if scene_purpose in ("confrontation", "crisis"):
                if len(scene_chars) < 2 and not any(kw in b.text.lower() for b in scene.blocks for kw in ["alarm", "explosion", "threat", "standoff", "gun", "detonate", "fire"]):
                    issues.append(
                        ScreenplayQualityIssue(
                            category="weak_confrontation",
                            severity="info",
                            scene_number=scene.scene_number,
                            message=f"Scene {scene.scene_number} marked as {scene_purpose} but features only {len(scene_chars)} character(s) without overt crisis action.",
                            recommendation="Increase opposing force presence or environmental obstacles.",
                        )
                    )

            if not scene_has_issue:
                scene_turn_satisfied += 1

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
        provenance_cov = round(grounded_blocks / max(1, total_groundable_blocks), 3) if total_groundable_blocks > 0 else 1.0
        scene_turn_score = round(scene_turn_satisfied / max(1, total_scenes), 2) if total_scenes > 0 else 1.0

        # Calculate score out of 100
        quality = 100.0
        quality -= knowledge_leaks * 20.0
        quality -= ungrounded_blocks * 15.0
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
            provenance_coverage=provenance_cov,
            ungrounded_block_count=ungrounded_blocks,
            scene_turn_fulfillment_score=scene_turn_score,
        )
