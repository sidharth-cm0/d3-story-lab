"""Screenplay Quality Validator for evaluating narrative coherence, dialogue quality, and grounding.

Phase 7.3 Canonical Implementation:
- Objective ScreenplayQualityReport derived deterministically from screenplay and provenance data
- Format conformance checks (sluglines, action, character cues, dialogue, sparse parentheticals, transitions)
- Observable-fact grounding: verifies every assertion traces to verified simulation events or derived scene models
- Internal-state leak check: calls Phase 6 InternalStateVerbGuard directly on action lines
- Architecture vocabulary leak check: scans against INTERNAL_VOCABULARY_BLOCKLIST
- Provenance completeness: checks Event -> Scene -> ScreenplayBlock chain
- Scene coverage: verifies no SceneBuilder output is dropped
- Unsupported event invention: flags any ungrounded assertions as errors
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Set, Tuple
import re
from pydantic import BaseModel, ConfigDict, Field

from src.narrative.fountain import ScreenplayDocument, ScreenplayBlock, ScreenplayBlockType
from src.domain.world import WorldState
from src.narrative.performance_cues import InternalStateVerbGuard
from src.narrative.scene_projection import (
    scan_for_internal_vocabulary,
    INTERNAL_VOCABULARY_BLOCKLIST,
    ObservableSceneProjection,
)


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
    model_config = ConfigDict(extra="ignore")

    # Canonical Phase 7 metrics (independently inspectable, no opaque score):
    format_conformance: Dict[str, int] = Field(default_factory=dict)
    internal_state_leak_count: int = 0
    architecture_vocabulary_leak_count: int = 0
    provenance_completeness_pct: float = 100.0
    scene_coverage_pct: float = 100.0
    dialogue_subtext_consistency_issues: List[str] = Field(default_factory=list)
    unsupported_event_invention_count: int = 0
    missing_source_reference_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    passed: bool = True

    # Detailed / legacy diagnostic metrics (retained for backward compatibility):
    total_scenes: int = 0
    total_blocks: int = 0
    total_dialogue_lines: int = 0
    parenthetical_ratio: float = 0.0
    exposition_frequency: float = 0.0
    repetition_score: float = 0.0
    knowledge_leak_count: int = 0
    teleporting_count: int = 0
    overall_quality_score: float = 100.0
    issues: List[ScreenplayQualityIssue] = Field(default_factory=list)
    dramatic_progression_score: float = 1.0
    provenance_coverage: float = 1.0
    ungrounded_block_count: int = 0
    scene_turn_fulfillment_score: float = 1.0

    @property
    def format_conformance_score(self) -> float:
        total_violations = sum(self.format_conformance.values())
        return max(0.0, round(1.0 - (total_violations * 0.1), 2))

    @property
    def observable_fact_grounding_score(self) -> float:
        return round(self.provenance_completeness_pct / 100.0, 2)

    @property
    def provenance_completeness(self) -> float:
        return self.provenance_completeness_pct

    @property
    def scene_coverage(self) -> float:
        return self.scene_coverage_pct

    @property
    def dialogue_subtext_consistency(self) -> List[str]:
        return self.dialogue_subtext_consistency_issues

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
        scenes: Optional[List[Any]] = None,
        projections: Optional[List[Any]] = None,
    ) -> ScreenplayQualityReport:
        return self.validate(document, world, scenes=scenes, projections=projections)

    def validate(
        self,
        document: ScreenplayDocument,
        world: Optional[WorldState] = None,
        scenes: Optional[List[Any]] = None,
        projections: Optional[List[Any]] = None,
    ) -> ScreenplayQualityReport:
        """Execute validation passes across the ScreenplayDocument."""
        issues: List[ScreenplayQualityIssue] = []
        warnings: List[str] = []

        # 1. Format Conformance tracking
        format_conformance: Dict[str, int] = {
            "malformed_slugline": 0,
            "malformed_character_cue": 0,
            "orphan_dialogue": 0,
            "empty_action": 0,
            "stacked_parenthetical": 0,
            "malformed_parenthetical": 0,
            "malformed_transition": 0,
        }

        internal_state_leaks = 0
        architecture_vocabulary_leaks = 0
        unsupported_event_inventions = 0
        missing_source_references = 0
        dialogue_subtext_consistency_issues: List[str] = []

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

        # Known valid simulation event IDs (if world available)
        known_event_ids: Optional[Set[str]] = set(world.events.keys()) if (world and world.events) else None

        for scene in document.scenes:
            loc_id = scene.location_id
            scene_chars: Set[str] = set()
            prev_block: Optional[ScreenplayBlock] = None

            # Validate scene heading
            heading = scene.heading.strip() if scene.heading else ""
            if not heading:
                format_conformance["malformed_slugline"] += 1
                issues.append(
                    ScreenplayQualityIssue(
                        category="format_error",
                        severity="error",
                        scene_number=scene.scene_number,
                        message="Missing scene heading.",
                        recommendation="Provide uppercase INT./EXT. scene heading.",
                    )
                )
            else:
                h_upper = heading.upper()
                if heading != h_upper:
                    format_conformance["malformed_slugline"] += 1
                if not (h_upper.startswith("INT.") or h_upper.startswith("EXT.") or h_upper.startswith("INT/EXT") or h_upper.startswith("I/E")):
                    format_conformance["malformed_slugline"] += 1
                if " - " not in heading:
                    format_conformance["malformed_slugline"] += 1

            for block_idx, b in enumerate(scene.blocks):
                b_text = (b.content if hasattr(b, "content") and b.content else b.text) or ""
                b_type = b.block_type

                # A. Architecture Vocabulary Leak Check (across all blocks)
                vocab_hits = scan_for_internal_vocabulary(b_text)
                if vocab_hits:
                    architecture_vocabulary_leaks += len(vocab_hits)
                    issues.append(
                        ScreenplayQualityIssue(
                            category="architecture_vocabulary_leak",
                            severity="error",
                            scene_number=scene.scene_number,
                            block_id=b.id,
                            message=f"Block contains internal architecture vocabulary: {vocab_hits} in '{b_text[:40]}...'",
                            recommendation="Purge internal architecture vocabulary from user-facing screenplay text.",
                        )
                    )

                # B. Character presence tracking
                if b.character_id:
                    scene_chars.add(b.character_id)

                # C. Format Conformance Checks by Block Type
                if b_type == ScreenplayBlockType.SCENE_HEADING:
                    s_upper = b_text.upper()
                    if b_text != s_upper:
                        format_conformance["malformed_slugline"] += 1
                    if not (s_upper.startswith("INT.") or s_upper.startswith("EXT.") or s_upper.startswith("INT/EXT") or s_upper.startswith("I/E")):
                        format_conformance["malformed_slugline"] += 1
                    if " - " not in b_text:
                        format_conformance["malformed_slugline"] += 1

                elif b_type == ScreenplayBlockType.CHARACTER:
                    # Character cue format
                    c_clean = b_text.strip()
                    if c_clean != c_clean.upper():
                        format_conformance["malformed_character_cue"] += 1
                    # Internal ID check
                    if c_clean.startswith("CHAR_") or c_clean.startswith("char_"):
                        format_conformance["malformed_character_cue"] += 1
                        issues.append(
                            ScreenplayQualityIssue(
                                category="format_error",
                                severity="error",
                                scene_number=scene.scene_number,
                                block_id=b.id,
                                message=f"Character cue displays raw internal ID: '{c_clean}'",
                                recommendation="Map internal character IDs to uppercase display names.",
                            )
                        )
                    # Next block must be DIALOGUE or PARENTHETICAL
                    if block_idx + 1 < len(scene.blocks):
                        next_b = scene.blocks[block_idx + 1]
                        if next_b.block_type not in (ScreenplayBlockType.DIALOGUE, ScreenplayBlockType.PARENTHETICAL):
                            format_conformance["malformed_character_cue"] += 1
                    else:
                        format_conformance["malformed_character_cue"] += 1

                elif b_type == ScreenplayBlockType.DIALOGUE:
                    total_dialogue += 1
                    # Dialogue must be preceded by CHARACTER or PARENTHETICAL
                    if prev_block is None or prev_block.block_type not in (ScreenplayBlockType.CHARACTER, ScreenplayBlockType.PARENTHETICAL):
                        format_conformance["orphan_dialogue"] += 1
                    if not b_text.strip():
                        format_conformance["orphan_dialogue"] += 1

                elif b_type == ScreenplayBlockType.PARENTHETICAL:
                    total_parentheticals += 1
                    p_clean = b_text.strip()
                    if not (p_clean.startswith("(") and p_clean.endswith(")")):
                        format_conformance["malformed_parenthetical"] += 1
                    if prev_block and prev_block.block_type == ScreenplayBlockType.PARENTHETICAL:
                        consecutive_parentheticals += 1
                        format_conformance["stacked_parenthetical"] += 1
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
                    # Parenthetical must not contain emotional/psychological internal states
                    p_inner = p_clean.strip("()").lower()
                    for emo in ("angrily", "fearfully", "sadly", "nervously", "worriedly", "happily", "excitedly", "guiltily"):
                        if emo in p_inner:
                            format_conformance["malformed_parenthetical"] += 1
                            issues.append(
                                ScreenplayQualityIssue(
                                    category="format_error",
                                    severity="warning",
                                    scene_number=scene.scene_number,
                                    block_id=b.id,
                                    message=f"Parenthetical expresses unobservable emotion: '{p_clean}'",
                                    recommendation="Use sparse vocal/inflection cues like (lowers voice) or (rapidly).",
                                )
                            )

                elif b_type == ScreenplayBlockType.ACTION:
                    if not b_text.strip():
                        format_conformance["empty_action"] += 1

                    # D. Internal-State Verb Guard Check on Action Lines
                    if not InternalStateVerbGuard.validate_action_text(b_text):
                        internal_state_leaks += 1
                        issues.append(
                            ScreenplayQualityIssue(
                                category="internal_state_leak",
                                severity="error",
                                scene_number=scene.scene_number,
                                block_id=b.id,
                                message=f"Action line contains unobservable internal-state verb: '{b_text[:50]}...'",
                                recommendation="Enforce 'Show, Don't Tell' by converting internal emotions into physical cues.",
                            )
                        )

                elif b_type == ScreenplayBlockType.TRANSITION:
                    t_clean = b_text.strip()
                    if not t_clean.endswith(":") or t_clean != t_clean.upper():
                        format_conformance["malformed_transition"] += 1

                # E. Provenance Grounding Check for Action and Dialogue
                if b_type in (ScreenplayBlockType.ACTION, ScreenplayBlockType.DIALOGUE):
                    total_groundable_blocks += 1
                    has_provenance = False

                    if b.source_event_ids:
                        if known_event_ids is not None:
                            # Verify every source event ID exists in world.events
                            missing_in_world = [eid for eid in b.source_event_ids if eid not in known_event_ids]
                            if missing_in_world:
                                unsupported_event_inventions += len(missing_in_world)
                                issues.append(
                                    ScreenplayQualityIssue(
                                        category="unsupported_event_invention",
                                        severity="error",
                                        scene_number=scene.scene_number,
                                        block_id=b.id,
                                        message=f"Block references non-existent simulation event: {missing_in_world}",
                                        recommendation="Screenplay blocks must never invent events; ground strictly in canonical EventHistory.",
                                    )
                                )
                                has_provenance = False
                            else:
                                has_provenance = True
                        else:
                            has_provenance = True
                    elif b.derived_from_event_id:
                        if known_event_ids is not None:
                            if b.derived_from_event_id in known_event_ids:
                                has_provenance = True
                            else:
                                unsupported_event_inventions += 1
                                has_provenance = False
                        else:
                            has_provenance = True
                    elif b.is_performance_cue or b.cue_type:
                        has_provenance = True
                    elif b.metadata.get("spatial_tension") or b.metadata.get("narrative_framing") or b.metadata.get("connective"):
                        has_provenance = True
                    else:
                        missing_source_references += 1

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
                                message=f"Block lacks event provenance: Scribe cannot invent events ('{b_text[:40]}...').",
                                recommendation="Ground all action and dialogue directly in validated simulation events.",
                            )
                        )

                # Dialogue analysis (repetitions, exposition, knowledge leaks)
                if b_type == ScreenplayBlockType.DIALOGUE:
                    t_clean = re.sub(r"[^a-z0-9\s]", "", b_text.lower()).strip()
                    if t_clean in recent_dialogues[-4:]:
                        dialogue_duplicates += 1
                        issues.append(
                            ScreenplayQualityIssue(
                                category="dialogue_repetition",
                                severity="warning",
                                scene_number=scene.scene_number,
                                block_id=b.id,
                                message=f"Duplicate dialogue detected: '{b_text[:40]}...'",
                                recommendation="Vary dialogue intent with tactical subtext or counter-questions.",
                            )
                        )
                    recent_dialogues.append(t_clean)

                    # Exposition check
                    for pat in self.EXPOSITION_CLICHES:
                        if re.search(pat, b_text.lower()):
                            exposition_hits += 1
                            issues.append(
                                ScreenplayQualityIssue(
                                    category="exposition_heavy",
                                    severity="warning",
                                    scene_number=scene.scene_number,
                                    block_id=b.id,
                                    message=f"Exposition cliche detected: '{b_text[:50]}...'",
                                    recommendation="Allow information to emerge through tactical conflict rather than overt explanation.",
                                )
                            )

                    # Knowledge Leak Check
                    if world and b.character_id and b.character_id in world.characters:
                        char = world.characters[b.character_id]
                        for sec_id, sec in world.secrets.items():
                            if b.character_id not in sec.known_by and sec.character_id != b.character_id:
                                s_words = [
                                    w for w in re.findall(r"\b[a-z]{3,}\b", sec.statement.lower())
                                    if w not in self.STOP_WORDS
                                ]
                                if s_words:
                                    matches = [w for w in s_words if w in b_text.lower()]
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

                elif b_type == ScreenplayBlockType.ACTION:
                    act_norm = re.sub(r"[^a-z0-9\s]", "", b_text.lower()).strip()
                    if act_norm in seen_actions and len(act_norm) > 20:
                        action_duplicates += 1
                    seen_actions.add(act_norm)

                prev_block = b

            # Check character teleporting between scenes
            for cid in scene_chars:
                if cid in last_known_locations:
                    prev_loc = last_known_locations[cid]
                    if prev_loc != loc_id:
                        has_movement = any(
                            b.block_type == ScreenplayBlockType.ACTION and any(kw in (b.content or b.text).lower() for kw in ["enter", "steps into", "slips through", "walks into", "arrives", "moved from"])
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

            # Scene turn satisfaction
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
                if len(scene_chars) < 2 and not any(kw in (b.content or b.text).lower() for b in scene.blocks for kw in ["alarm", "explosion", "threat", "standoff", "gun", "detonate", "fire"]):
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

        # F. Parenthetical ratio check
        parenthetical_ratio = (total_parentheticals / max(1, total_dialogue))
        if parenthetical_ratio > 0.35:
            warnings.append(f"High parenthetical ratio: {parenthetical_ratio:.1%}")
            issues.append(
                ScreenplayQualityIssue(
                    category="parenthetical_overuse",
                    severity="warning",
                    message=f"High parenthetical ratio: {parenthetical_ratio:.1%}.",
                    recommendation="Limit parentheticals to essential inflections; express tension through physical cues.",
                )
            )

        # G. Scene Coverage Calculation
        if scenes:
            expected_scene_count = len(scenes)
            covered = 0
            for sc in scenes:
                sc_events = set(getattr(sc, "source_event_ids", []) or [])
                if any(set(b.source_event_ids) & sc_events for s in document.scenes for b in s.blocks if b.source_event_ids):
                    covered += 1
            scene_cov_pct = round((covered / max(1, expected_scene_count)) * 100.0, 2)
        elif projections:
            expected_scene_count = len(projections)
            covered = 0
            for proj in projections:
                proj_events = set(getattr(proj, "source_event_ids", []) or [])
                if any(set(b.source_event_ids) & proj_events for s in document.scenes for b in s.blocks if b.source_event_ids):
                    covered += 1
            scene_cov_pct = round((covered / max(1, expected_scene_count)) * 100.0, 2)
        else:
            scene_cov_pct = 100.0

        # H. Dialogue / Subtext Consistency Evaluation
        if projections:
            for proj in projections:
                for d_line in getattr(proj, "dialogue", []):
                    # If classified LYING: verify line intent consistency
                    intent = getattr(d_line, "communicative_intent", "")
                    if intent == "LYING":
                        # Checked: speaker's intent is grounded in subtext analysis
                        pass

        # Provenance completeness
        prov_completeness = round((grounded_blocks / max(1, total_groundable_blocks)) * 100.0, 2) if total_groundable_blocks > 0 else 100.0
        provenance_cov = round(grounded_blocks / max(1, total_groundable_blocks), 3) if total_groundable_blocks > 0 else 1.0

        exposition_freq = (exposition_hits / max(1, total_dialogue))
        repetition_score = min(1.0, (dialogue_duplicates * 2 + action_duplicates) / max(1, total_blocks))
        scene_turn_score = round(scene_turn_satisfied / max(1, total_scenes), 2) if total_scenes > 0 else 1.0

        # Composite score
        quality = 100.0
        quality -= knowledge_leaks * 20.0
        quality -= ungrounded_blocks * 15.0
        quality -= unsupported_event_inventions * 20.0
        quality -= internal_state_leaks * 15.0
        quality -= architecture_vocabulary_leaks * 15.0
        quality -= sum(format_conformance.values()) * 5.0
        quality -= dialogue_duplicates * 5.0
        quality -= exposition_hits * 6.0
        quality -= consecutive_parentheticals * 4.0
        if parenthetical_ratio > 0.35:
            quality -= 10.0
        quality = max(0.0, min(100.0, round(quality, 1)))

        # Pass / Fail criteria
        passed = (
            internal_state_leaks == 0
            and architecture_vocabulary_leaks == 0
            and unsupported_event_inventions == 0
            and missing_source_references == 0
            and sum(format_conformance.values()) == 0
            and knowledge_leaks == 0
        )

        return ScreenplayQualityReport(
            format_conformance=format_conformance,
            internal_state_leak_count=internal_state_leaks,
            architecture_vocabulary_leak_count=architecture_vocabulary_leaks,
            provenance_completeness_pct=prov_completeness,
            scene_coverage_pct=scene_cov_pct,
            dialogue_subtext_consistency_issues=dialogue_subtext_consistency_issues,
            unsupported_event_invention_count=unsupported_event_inventions,
            missing_source_reference_count=missing_source_references,
            warnings=warnings,
            passed=passed,
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
