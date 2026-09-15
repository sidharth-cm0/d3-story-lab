"""Scene Builder for D3 Story Lab.

Sits between the Observer (which filters events into narrative beats) and the Scribe
(which converts structured scenes into Fountain screenplay format).

Every constructed scene possesses:
1. scene_purpose (SETUP, INVESTIGATION, DISCOVERY, NEGOTIATION, CONFRONTATION, ESCALATION, REVERSAL, CHASE, REVELATION, CLIMAX, RESOLUTION)
2. CoreEmotionalObjective (focal character, immediate desire, immediate obstacle, emotional shift, stakes at risk)
3. 100% strict provenance linking back to canonical source_event_ids.
"""

from typing import List, Dict, Optional, Any, Set
from src.domain.world import WorldState
from src.domain.event import Event, EventType
from src.domain.story_structure import (
    SceneData,
    ScenePurposeType,
    CoreEmotionalObjective,
    StoryBlueprint,
)
from src.narrative.observer import NarrativeEventSelection, NarrativeBeat
from src.narrative.scene_purpose import ScenePurposeAnalyzer


class SceneBuilder:
    """Constructs rich dramatic SceneData units from Observer narrative beats and world state."""

    def __init__(self):
        self.purpose_analyzer = ScenePurposeAnalyzer()

    def _determine_focal_character(
        self,
        events: List[Event],
        world: WorldState,
    ) -> Optional[str]:
        """Identify the primary focal character experiencing the highest dramatic agency or tension in this scene."""
        char_activity: Dict[str, int] = {}
        for ev in events:
            for aid in ev.actor_ids:
                if aid in world.characters:
                    char_activity[aid] = char_activity.get(aid, 0) + 1

        if not char_activity:
            if world.characters:
                return next(iter(world.characters.keys()))
            return None

        # Sort by activity count
        sorted_chars = sorted(char_activity.items(), key=lambda x: x[1], reverse=True)
        return sorted_chars[0][0]

    def _derive_core_emotional_objective(
        self,
        focal_char_id: str,
        events: List[Event],
        world: WorldState,
        scene_purpose: ScenePurposeType,
    ) -> CoreEmotionalObjective:
        """Derive immediate desire, obstacle, emotional shift, and stakes for the focal character."""
        char = world.characters.get(focal_char_id)
        char_name = char.name if char else "Focal Character"

        # Find character goal
        goal_desc = "uncover the truth and secure the objective"
        stakes_desc = "compromised mission and personal peril"
        if char and world.goals:
            for g in world.goals.values():
                if g.character_id == focal_char_id:
                    goal_desc = g.description
                    break

        # Check opposing characters present
        present_chars = set()
        for ev in events:
            for aid in ev.actor_ids:
                if aid != focal_char_id and aid in world.characters:
                    present_chars.add(world.characters[aid].name)

        opposing_str = f"opposing presence of {', '.join(present_chars)}" if present_chars else "hostile environment and secrecy"

        # Determine emotional shift from events
        emo_shifts = []
        for ev in events:
            if ev.event_type == EventType.EMOTION_CHANGED and focal_char_id in ev.actor_ids:
                emo_shifts.append(ev.description)

        if emo_shifts:
            shift_text = f"Evolving state: {emo_shifts[-1]}"
        elif scene_purpose == ScenePurposeType.CONFRONTATION:
            shift_text = "Cautious probing shifts into hardened defiance"
        elif scene_purpose == ScenePurposeType.DISCOVERY:
            shift_text = "Tense suspicion converts to calculated certainty"
        elif scene_purpose == ScenePurposeType.REVELATION:
            shift_text = "Doubt collapses under unequivocal revelation"
        elif scene_purpose == ScenePurposeType.INVESTIGATION:
            shift_text = "Vigilant curiosity confronts deceptive resistance"
        else:
            shift_text = "Guarded equilibrium shifts under mounting pressure"

        desire_by_purpose = {
            ScenePurposeType.SETUP: f"{char_name} urgently needs to assess the perimeter and confirm operational security.",
            ScenePurposeType.INVESTIGATION: f"{char_name} must extract actionable information without tipping their hand.",
            ScenePurposeType.DISCOVERY: f"{char_name} desperately seeks physical possession of the classified objective.",
            ScenePurposeType.NEGOTIATION: f"{char_name} aims to secure compliance or extract a critical concession.",
            ScenePurposeType.CONFRONTATION: f"{char_name} must assert total command over the adversary before force is used.",
            ScenePurposeType.ESCALATION: f"{char_name} seeks to regain control as variables spiral out of hand.",
            ScenePurposeType.REVERSAL: f"{char_name} must adapt instantly to a compromised assumption.",
            ScenePurposeType.CHASE: f"{char_name} must break line of sight and preserve the recovered assets.",
            ScenePurposeType.REVELATION: f"{char_name} demands immediate transparency regarding the hidden truth.",
            ScenePurposeType.CLIMAX: f"{char_name} must survive the decisive clash and neutralize the primary threat.",
            ScenePurposeType.RESOLUTION: f"{char_name} seeks to consolidate survival and comprehend the aftermath.",
        }

        immediate_desire = desire_by_purpose.get(scene_purpose, f"{char_name} pursues: {goal_desc}")
        immediate_obstacle = f"Guarded resistance and {opposing_str}"

        return CoreEmotionalObjective(
            focal_character_id=focal_char_id,
            immediate_desire=immediate_desire,
            immediate_obstacle=immediate_obstacle,
            emotional_shift=shift_text,
            stakes_at_risk=stakes_desc,
        )

    def build_scenes(
        self,
        selection: NarrativeEventSelection,
        world: WorldState,
        blueprint: Optional[StoryBlueprint] = None,
    ) -> List[SceneData]:
        """Construct canonical SceneData instances from filtered beats and world state."""
        scenes: List[SceneData] = []
        if not selection.filtered_beats:
            return scenes

        scene_num = 0
        current_loc_id: Optional[str] = None
        current_beat_ids: List[str] = []
        current_event_ids: List[str] = []
        current_events: List[Event] = []

        def commit_scene():
            nonlocal scene_num, current_loc_id, current_beat_ids, current_event_ids, current_events
            if not current_event_ids:
                return

            scene_num += 1
            loc = world.locations.get(current_loc_id) if current_loc_id else None
            loc_name = loc.name if loc else "Unknown Location"
            heading = f"INT. {loc_name.upper()} - CONTINUOUS"

            # Aggregate present character names
            chars_present = set()
            for ev in current_events:
                for aid in ev.actor_ids:
                    if aid in world.characters:
                        chars_present.add(world.characters[aid].name)

            # Determine scene purpose using keywords and events
            combined_desc = " ".join(e.description.lower() for e in current_events)
            if any(w in combined_desc for w in ["climax", "shootout", "final standoff", "cornered"]):
                purpose = ScenePurposeType.CLIMAX
            elif any(w in combined_desc for w in ["confront", "threat", "gun", "freeze", "accuse"]):
                purpose = ScenePurposeType.CONFRONTATION
            elif any(w in combined_desc for w in ["dossier", "find", "safe", "discover", "ledger", "cache"]):
                purpose = ScenePurposeType.DISCOVERY
            elif any(w in combined_desc for w in ["secret", "confess", "truth", "lying", "unmask"]):
                purpose = ScenePurposeType.REVELATION
            elif any(w in combined_desc for w in ["negotiat", "bargain", "deal", "offer", "compromise"]):
                purpose = ScenePurposeType.NEGOTIATION
            elif any(w in combined_desc for w in ["examine", "inspect", "probe", "search", "investigat"]):
                purpose = ScenePurposeType.INVESTIGATION
            elif any(w in combined_desc for w in ["flee", "chase", "escape", "run", "pursuit"]):
                purpose = ScenePurposeType.CHASE
            elif any(w in combined_desc for w in ["reversal", "betrayal", "twist", "surprise"]):
                purpose = ScenePurposeType.REVERSAL
            elif scene_num == 1:
                purpose = ScenePurposeType.SETUP
            else:
                purpose = ScenePurposeType.INVESTIGATION

            # Determine focal character and emotional objective
            focal_id = self._determine_focal_character(current_events, world) or "char_protagonist"
            ceo = self._derive_core_emotional_objective(
                focal_char_id=focal_id,
                events=current_events,
                world=world,
                scene_purpose=purpose,
            )

            start_t = min((e.tick for e in current_events), default=0)
            end_t = max((e.tick for e in current_events), default=start_t)

            scene_obj = SceneData(
                scene_id=f"scene_{scene_num:02d}",
                scene_number=scene_num,
                location_id=current_loc_id or "loc_main",
                location_name=loc_name,
                heading=heading,
                scene_purpose=purpose,
                core_emotional_objective=ceo,
                source_event_ids=list(dict.fromkeys(current_event_ids)),
                source_beat_id=current_beat_ids[0] if current_beat_ids else None,
                characters_present=sorted(list(chars_present)),
                start_tick=start_t,
                end_tick=end_t,
                dramatic_tension=50.0 + (scene_num * 8.0),
                chronological_position=scene_num,
                presentation_position=scene_num,
                framing_type="chronological",
                metadata={
                    "total_events": len(current_event_ids),
                    "beat_count": len(current_beat_ids),
                },
            )
            scenes.append(scene_obj)

            # Reset accumulation
            current_beat_ids = []
            current_event_ids = []
            current_events = []

        # Group beats into scenes by location continuity
        for beat in selection.filtered_beats:
            beat_events = [world.events[eid] for eid in beat.source_event_ids if eid in world.events]
            if not beat_events:
                continue

            beat_loc = beat.location_id or beat_events[0].location_id

            if current_loc_id is not None and beat_loc != current_loc_id:
                commit_scene()

            current_loc_id = beat_loc
            current_beat_ids.append(beat.id)
            for ev in beat_events:
                current_event_ids.append(ev.id)
                current_events.append(ev)

        commit_scene()
        return scenes
