"""Observable Scene Projection & Scribe Input Contract (Phase 7.1).

Enforces the omniscience firewall between canonical simulation state and the Scribe:
the Scribe never receives raw WorldState or unrestricted character knowledge, only
an explicitly projected, pre-sanitized observable view.
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.story_structure import DramaticFunction, Scene, SceneObjective
from src.domain.event import Event, EventType
from src.domain.world import WorldState
from src.domain.character import Character
from src.domain.proposition import KnowledgeItem, Proposition
from src.narrative.performance_cues import PerformanceCue, InternalStateVerbGuard


# =============================================================================
# § 4. INTERNAL VOCABULARY BLOCKLIST
# =============================================================================

INTERNAL_VOCABULARY_BLOCKLIST: List[str] = [
    "Director",
    "BeatPressure",
    "Sufficiency Gate",
    "sufficiency gate",
    "sovereign actor",
    "simulation tick",
    "validator",
    "ActionProposal",
    "WorldState",
    "CharacterWorldView",
    "KnowledgeItem",
    "Proposition",
    "StateSnapshotDiffer",
    "provenance",
    "environmental intervention",
    "NarrativeSufficiencyGate",
    "DirectorAgent",
    "ActionValidator",
    "ActionExecutor",
    "EventRecorder",
    "SimulationOrchestrator",
    "CharacterArcTracker",
    "SubtextAnalyzer",
    "PerformanceCueGenerator",
    "InternalStateVerbGuard",
    "SceneBuilder",
    "CausalContinuityAnalyzer",
    "StoryCompletionEngine",
    "SynopsisGenerator",
    "PropositionRegistry",
]


# =============================================================================
# § 3. DOMAIN MODELS FOR OBSERVABLE SCENE PROJECTION
# =============================================================================

class ObservableBeat(BaseModel):
    """An observable physical or communicative beat in a scene."""
    model_config = ConfigDict(extra="ignore")

    event_id: str
    description: str                # plain-language, observable-only
    characters_involved: List[str] = Field(default_factory=list)
    performance_cue_ids: List[str] = Field(default_factory=list)


class ObservableObjective(BaseModel):
    """Core dramatic driver for the scene POV character, expressed purely as observable pursuit."""
    model_config = ConfigDict(extra="ignore")

    pov_character_id: str
    wants: str
    obstacle: str
    outcome: Literal["ACHIEVED", "DENIED", "PARTIAL", "ACHIEVED_AT_COST"] = "PARTIAL"


class ObservableDialogueLine(BaseModel):
    """A single spoken utterance within a scene."""
    model_config = ConfigDict(extra="ignore")

    speaker_id: str
    listener_ids: List[str] = Field(default_factory=list)
    source_event_id: str
    communicative_intent: str       # carried for Prompt 2's cue-selection use only — see §5
    text: str = ""                  # literal dialogue line
    dialogue: Optional[str] = None  # alias for backward compatibility

    @model_validator(mode="before")
    @classmethod
    def sync_dialogue_text(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "dialogue" in data and "text" not in data:
                data["text"] = data["dialogue"]
            elif "text" in data and "dialogue" not in data:
                data["dialogue"] = data["text"]
        return data


class ObservableSceneProjection(BaseModel):
    """Firewalled observable scene projection provided as the sole canonical input to the Scribe."""
    model_config = ConfigDict(extra="ignore")

    scene_id: str
    location_label: str
    time_label: str
    characters_present: List[str] = Field(default_factory=list)
    purpose: DramaticFunction        # available for tone; never printed literally
    objective: ObservableObjective
    beats: List[ObservableBeat] = Field(default_factory=list)
    dialogue: List[ObservableDialogueLine] = Field(default_factory=list)
    performance_cues: List[PerformanceCue] = Field(default_factory=list)     # from Phase 6, unchanged
    source_event_ids: List[str] = Field(default_factory=list)      # must exactly match Scene.source_event_ids
    in_play_knowledge: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Only propositions explicitly active in this scene for characters present.",
    )

    def to_reader_prose(self) -> str:
        """Format an observable prose overview for reader inspection.

        Invariant §6: communicative_intent is NEVER surfaced as reader-visible text
        or parenthetical prose here.
        """
        lines: List[str] = []
        lines.append(f"SCENE: {self.location_label.upper()} - {self.time_label.upper()}")
        lines.append(f"PRESENT: {', '.join(self.characters_present)}")
        lines.append(f"OBJECTIVE: [{self.objective.pov_character_id}] Wants {self.objective.wants} against {self.objective.obstacle} -> {self.objective.outcome}")
        lines.append("")

        for beat in self.beats:
            lines.append(f"ACTION: {beat.description}")

        for line in self.dialogue:
            # Strictly omit communicative_intent
            listeners_str = f" (to {', '.join(line.listener_ids)})" if line.listener_ids else ""
            lines.append(f"{line.speaker_id}{listeners_str}: \"{line.text}\"")

        for cue in self.performance_cues:
            cue_text = cue.action_text or cue.observable_behaviour
            if cue_text:
                lines.append(f"PERFORMANCE ({cue.character_id}): {cue_text}")

        return "\n".join(lines)


# =============================================================================
# § 4. VOCABULARY SCANNER
# =============================================================================

def scan_for_internal_vocabulary(
    target: Union[ObservableSceneProjection, Dict[str, Any], str, List[Any]],
    blocklist: Optional[List[str]] = None,
    allow_fields: Optional[List[str]] = None,
) -> List[str]:
    """Scan projection, dictionary, or string recursively for forbidden internal vocabulary.

    Args:
        target: The object, dict, or string to scan.
        blocklist: Vocabulary terms to scan for (defaults to INTERNAL_VOCABULARY_BLOCKLIST).
        allow_fields: Field names whose values are exempted (e.g. 'communicative_intent').

    Returns:
        List of violation messages detailing the forbidden term and where it was found.
    """
    active_blocklist = blocklist if blocklist is not None else INTERNAL_VOCABULARY_BLOCKLIST
    allowed = set(allow_fields or ["communicative_intent"])
    violations: List[str] = []

    def _scan_str(text: str, context: str) -> None:
        for term in active_blocklist:
            # Word-boundary check (case-insensitive for multi-word or exact)
            pattern = rf"(?i)\b{re.escape(term)}\b"
            if re.search(pattern, text):
                violations.append(f"Forbidden term '{term}' found in {context}: '{text}'")

    def _walk(item: Any, path: str) -> None:
        if isinstance(item, str):
            _scan_str(item, path)
        elif isinstance(item, dict):
            for k, v in item.items():
                if k in allowed:
                    continue
                _walk(v, f"{path}.{k}" if path else k)
        elif isinstance(item, list):
            for idx, el in enumerate(item):
                _walk(el, f"{path}[{idx}]")
        elif isinstance(item, BaseModel):
            data = item.model_dump()
            _walk(data, path)

    if isinstance(target, str):
        _scan_str(target, "text")
    elif isinstance(target, BaseModel):
        _walk(target.model_dump(), target.__class__.__name__)
    else:
        _walk(target, "root")

    return violations


# =============================================================================
# § 5. OBSERVABLE SCENE PROJECTOR
# =============================================================================

class ObservableSceneProjector:
    """Projects canonical scenes and world state into sanitized ObservableSceneProjection objects."""

    def __init__(self, blocklist: Optional[List[str]] = None) -> None:
        self.blocklist = blocklist if blocklist is not None else INTERNAL_VOCABULARY_BLOCKLIST

    def project_scene(
        self,
        scene: Scene,
        world: WorldState,
        events: Optional[List[Event]] = None,
    ) -> ObservableSceneProjection:
        """Construct an observable projection of a single scene adhering to all firewall rules.

        Invariants enforced:
        - Invariant #2/#3: Scribe receives only ObservableSceneProjection.
        - Invariant #4: EventHistory is immutable (read-only traversal).
        - Invariant #9: Canonical events are preserved: source_event_ids match exactly.
        - Exclusion Rules:
            - Raw WorldState and PropositionRegistry are excluded.
            - Character.known_facts / Character.beliefs are never read; only Character.knowledge.
            - Knowledge for absent characters is omitted.
            - Unrelated secrets held by present characters are omitted.
            - Internal vocabulary is sanitized out of observable descriptions.
            - SubtextAnalysis.spoken_intent is typed on ObservableDialogueLine.communicative_intent,
              never rendered as raw prose.
        """
        # 1. Resolve Location and Time Labels
        location_label = scene.location_name
        if not location_label and scene.location_id in world.locations:
            location_label = world.locations[scene.location_id].name
        if not location_label:
            location_label = f"Location {scene.location_id}"
        location_label = self._sanitize_text(location_label)

        time_label = scene.time_context or "CONTINUOUS"

        # 2. Characters Present
        characters_present = list(scene.characters_present)

        # 3. Purpose (DramaticFunction enum)
        purpose = scene.purpose or DramaticFunction.SETUP

        # 4. Objective
        if scene.objective:
            objective = ObservableObjective(
                pov_character_id=scene.objective.pov_character_id,
                wants=self._sanitize_text(scene.objective.wants),
                obstacle=self._sanitize_text(scene.objective.obstacle),
                outcome=scene.objective.outcome,
            )
        else:
            default_pov = characters_present[0] if characters_present else "unknown"
            objective = ObservableObjective(
                pov_character_id=default_pov,
                wants="Navigate the active environment",
                obstacle="Uncertain conditions",
                outcome="PARTIAL",
            )

        # 5. Invariant #9: Source event IDs must match exactly
        source_event_ids = list(scene.source_event_ids)

        # Map available events
        events_map: Dict[str, Event] = {}
        if events:
            for ev in events:
                events_map[ev.id] = ev
        else:
            events_map = world.events

        # Map subtext analyses & performance cues by event_id and (speaker, dialogue)
        subtext_by_event: Dict[str, Any] = {}
        subtext_by_speaker_dialogue: Dict[tuple, Any] = {}
        for sub in getattr(scene, "subtext_analyses", []):
            eid = getattr(sub, "source_event_id", None) or getattr(sub, "event_id", None)
            if eid:
                subtext_by_event[eid] = sub
            spk = getattr(sub, "speaker_id", "")
            dlg = (getattr(sub, "dialogue", "") or "").strip().lower()
            if spk and dlg:
                subtext_by_speaker_dialogue[(spk, dlg)] = sub

        cues_by_event: Dict[str, List[str]] = {}
        filtered_cues: List[PerformanceCue] = []
        for cue in getattr(scene, "performance_cues", []):
            if isinstance(cue, PerformanceCue):
                eid = cue.event_id or cue.derived_from_event_id
                if eid:
                    cues_by_event.setdefault(eid, []).append(cue.id)
                filtered_cues.append(cue)

        # 6. Observable Beats & Dialogue
        beats: List[ObservableBeat] = []
        dialogue_lines: List[ObservableDialogueLine] = []

        # Identify propositions and secrets referenced by scene events
        in_play_proposition_ids: set[str] = set()
        for eid in source_event_ids:
            ev = events_map.get(eid)
            if not ev:
                continue

            # Check metadata for proposition references
            prop_id = ev.metadata.get("proposition_id") or ev.metadata.get("prop_id")
            if prop_id:
                in_play_proposition_ids.add(str(prop_id))

            claim = ev.metadata.get("claim")
            if claim:
                in_play_proposition_ids.add(str(claim).lower())

            # Cues for this beat
            beat_cue_ids = cues_by_event.get(eid, [])

            # Observable-only plain language description
            desc = self._build_observable_description(ev, world)
            beats.append(
                ObservableBeat(
                    event_id=ev.id,
                    description=desc,
                    characters_involved=list(ev.actor_ids),
                    performance_cue_ids=beat_cue_ids,
                )
            )

            # Dialogue Line Extraction
            if ev.event_type == EventType.CHARACTER_SPOKE:
                speaker_id = ev.metadata.get("speaker_id") or (ev.actor_ids[0] if ev.actor_ids else "")
                listeners = [cid for cid in characters_present if cid != speaker_id]
                diag_text = ev.metadata.get("dialogue") or ev.description
                if diag_text.startswith(f"{speaker_id} said:"):
                    diag_text = diag_text.split(":", 1)[1].strip().strip('"')

                # Determine communicative intent
                sub = subtext_by_event.get(eid)
                if not sub:
                    clean_diag = diag_text.strip().lower()
                    sub = subtext_by_speaker_dialogue.get((speaker_id, clean_diag))
                    if not sub:
                        for (s_spk, s_dlg), s_candidate in subtext_by_speaker_dialogue.items():
                            if s_spk == speaker_id and (s_dlg in clean_diag or clean_diag in s_dlg):
                                sub = s_candidate
                                break

                if sub and hasattr(sub, "spoken_intent"):
                    intent_val = sub.spoken_intent.value if hasattr(sub.spoken_intent, "value") else str(sub.spoken_intent)
                else:
                    intent_val = ev.metadata.get("speech_act") or "speak"

                dialogue_lines.append(
                    ObservableDialogueLine(
                        speaker_id=speaker_id,
                        listener_ids=listeners,
                        source_event_id=ev.id,
                        communicative_intent=str(intent_val),
                        text=diag_text,
                    )
                )

        # 7. In-Play Knowledge Filtering (Rules §4 & §5)
        # Only present characters; only propositions in play; strictly Character.knowledge
        in_play_knowledge: Dict[str, List[str]] = {}
        for cid in characters_present:
            char = world.characters.get(cid)
            if not char:
                continue

            # RULE: Never read char.known_facts or char.beliefs here.
            # ONLY read char.knowledge (dict[str, KnowledgeItem]).
            char_knowledge: Dict[str, KnowledgeItem] = getattr(char, "knowledge", {}) or {}
            char_in_play: List[str] = []

            for pid, k_item in char_knowledge.items():
                # Must be in-play for this scene's events
                prop = world.propositions.get(pid)
                is_active = (
                    pid in in_play_proposition_ids
                    or (k_item.acquired_at_event in source_event_ids)
                )

                if prop and not is_active:
                    # Check if subject/object matches an active in-play term
                    p_text = f"{prop.subject} {prop.predicate} {prop.object}".lower()
                    for active_term in in_play_proposition_ids:
                        if active_term in p_text or p_text in active_term:
                            is_active = True
                            break

                if is_active and prop:
                    summary = f"{prop.subject} {prop.predicate} {prop.object}"
                    char_in_play.append(self._sanitize_text(summary))

            if char_in_play:
                in_play_knowledge[cid] = char_in_play

        return ObservableSceneProjection(
            scene_id=scene.scene_id,
            location_label=location_label,
            time_label=time_label,
            characters_present=characters_present,
            purpose=purpose,
            objective=objective,
            beats=beats,
            dialogue=dialogue_lines,
            performance_cues=filtered_cues,
            source_event_ids=source_event_ids,
            in_play_knowledge=in_play_knowledge,
        )

    def project_all_scenes(
        self,
        scenes: List[Scene],
        world: WorldState,
        events: Optional[List[Event]] = None,
    ) -> List[ObservableSceneProjection]:
        """Project a sequence of scenes into observable scene projections."""
        return [self.project_scene(scene, world, events=events) for scene in scenes]

    def _build_observable_description(self, event: Event, world: WorldState) -> str:
        """Format an event into an observable physical description, scrubbing internal vocabulary."""
        desc = event.description

        # Scrub director or environmental engine vocabulary
        if "DIRECTOR" in desc or "Director" in desc or event.metadata.get("source") == "DIRECTOR":
            intervention_type = event.metadata.get("intervention_type") or event.metadata.get("action_type")
            if intervention_type:
                clean_type = str(intervention_type).replace("_", " ").lower()
                desc = f"An environmental occurrence shifts conditions: {clean_type}."
            else:
                desc = "The room atmosphere shifts noticeably."

        desc = self._sanitize_text(desc)
        return desc

    def _sanitize_text(self, text: str) -> str:
        """Sanitize text against internal engine vocabulary."""
        sanitized = text
        for term in self.blocklist:
            # Word-boundary replacement
            pattern = rf"(?i)\b{re.escape(term)}\b"
            if re.search(pattern, sanitized):
                # Replace with generic narrative phrasing
                if term.lower() in ("director", "directoragent"):
                    sanitized = re.sub(pattern, "ambient environment", sanitized)
                elif term.lower() in ("beatpressure", "sufficiency gate", "narrativesufficiencygate"):
                    sanitized = re.sub(pattern, "dramatic tension", sanitized)
                elif term.lower() in ("sovereign actor", "actionproposal"):
                    sanitized = re.sub(pattern, "figure", sanitized)
                elif term.lower() in ("simulation tick", "statesnapshotdiffer"):
                    sanitized = re.sub(pattern, "moment", sanitized)
                elif term.lower() in ("worldstate", "characterworldview", "knowledgeitem", "proposition", "propositionregistry"):
                    sanitized = re.sub(pattern, "revelation", sanitized)
                elif term.lower() in ("validator", "actionvalidator", "actionexecutor"):
                    sanitized = re.sub(pattern, "constraint", sanitized)
                elif term.lower() in ("environmental intervention",):
                    sanitized = re.sub(pattern, "sudden shift", sanitized)
                else:
                    sanitized = re.sub(pattern, "", sanitized).strip()

        # Clean up any leftover double spaces
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        return sanitized
