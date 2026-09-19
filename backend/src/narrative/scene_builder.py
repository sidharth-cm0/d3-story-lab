"""Scene Builder for D3 Story Lab (Phase 5A).

Sits between the Observer (which filters events into narrative beats) and the Scribe
(which converts structured scenes into Fountain screenplay format).

Every constructed scene possesses:
1. scene_purpose / purpose: DramaticFunction (SETUP, INVESTIGATION, DISCOVERY, etc.)
2. SceneObjective / core_emotional_objective (pov_character_id, wants, emotional_want, obstacle, tactics, outcome, state_delta)
3. turning_point_event_id: deterministic turning point from source_event_ids
4. is_static: flag when state_delta contains no meaningful change
5. 100% strict provenance linking back to canonical source_event_ids.
6. Execution gating: rejected if NarrativeSufficiencyGate recommendation is CONTINUE or ADJUST_PRESSURE_AND_CONTINUE.
"""

from __future__ import annotations
from typing import List, Dict, Optional, Any, Set, Literal
from src.domain.world import WorldState
from src.domain.event import Event, EventType
from src.domain.story_structure import (
    Scene,
    SceneData,
    DramaticFunction,
    ScenePurposeType,
    SceneObjective,
    CoreEmotionalObjective,
    StoryBlueprint,
)
from src.story.models import SufficiencyReport
from src.narrative.sufficiency_gate import NarrativeSufficiencyGate
from src.narrative.observer import NarrativeEventSelection, NarrativeBeat, Observer, EventSalience
from src.narrative.scene_purpose import ScenePurposeAnalyzer
from src.simulation.differ import StateSnapshotDiffer


class SufficiencyGateExecutionError(ValueError):
    """Raised when SceneBuilder is executed before NarrativeSufficiencyGate reaches a terminal recommendation."""
    pass


class SceneBuilder:
    """Constructs rich dramatic Scene units from Observer narrative beats, events, and world state."""

    def __init__(self):
        self.purpose_analyzer = ScenePurposeAnalyzer()
        self.observer = Observer()

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

        sorted_chars = sorted(char_activity.items(), key=lambda x: x[1], reverse=True)
        return sorted_chars[0][0]

    def _compute_state_delta(
        self,
        differ: StateSnapshotDiffer,
        world: WorldState,
        start_tick: int,
        end_tick: int,
        scene_events: Optional[List[Event]] = None,
    ) -> Dict[str, Any]:
        """Compute state delta from scene entry to exit using StateSnapshotDiffer and events."""
        entry_tick = max(0, start_tick - 1) if start_tick > 0 else 0
        snap_start = differ.get_or_create_snapshot(entry_tick, world)
        snap_end = differ.get_or_create_snapshot(end_tick, world)

        obj_holders = {}
        for oid, h_start in snap_start.object_holders.items():
            h_end = snap_end.object_holders.get(oid)
            if h_start != h_end:
                obj_holders[oid] = {"from": h_start, "to": h_end}

        obj_locs = {}
        for oid, l_start in snap_start.object_locations.items():
            l_end = snap_end.object_locations.get(oid)
            if l_start != l_end:
                obj_locs[oid] = {"from": l_start, "to": l_end}

        char_locs = {}
        for cid, l_start in snap_start.character_locations.items():
            l_end = snap_end.character_locations.get(cid)
            if l_start != l_end:
                char_locs[cid] = {"from": l_start, "to": l_end}

        knowledge_acquired = []
        for cid, char in world.characters.items():
            for pid, k_item in getattr(char, "knowledge", {}).items():
                if k_item.acquired_at_event and k_item.acquired_at_event in world.events:
                    evt = world.events[k_item.acquired_at_event]
                    if start_tick <= evt.tick <= end_tick:
                        knowledge_acquired.append({"character_id": cid, "proposition_id": pid})

        rel_deltas = {}
        all_rel_keys = set(snap_start.relationships.keys()) | set(snap_end.relationships.keys())
        for pair in all_rel_keys:
            aff_start = snap_start.relationships.get(pair, 0.0)
            aff_end = snap_end.relationships.get(pair, 0.0)
            if abs(aff_end - aff_start) >= 0.05:
                rel_deltas[f"{pair[0]}->{pair[1]}"] = round(aff_end - aff_start, 3)

        goals_changed = []
        for gid, g in getattr(world, "goals", {}).items():
            if getattr(g, "created_at_event", None) in world.events:
                evt = world.events[g.created_at_event]
                if start_tick <= evt.tick <= end_tick:
                    goals_changed.append({"goal_id": gid, "change": "CREATED"})
            if getattr(g, "completed_at_event", None) in world.events:
                evt = world.events[g.completed_at_event]
                if start_tick <= evt.tick <= end_tick:
                    goals_changed.append({"goal_id": gid, "change": "COMPLETED"})

        # Also incorporate explicit state changes directly from the scene's canonical events
        if scene_events:
            for ev in scene_events:
                if ev.event_type in (EventType.OBJECT_PICKED_UP, EventType.OBJECT_DROPPED, EventType.OBJECT_GIVEN):
                    oid = ev.metadata.get("object_id") or "object"
                    actor = ev.actor_ids[0] if ev.actor_ids else "actor"
                    if oid not in obj_holders:
                        obj_holders[oid] = {"from": None, "to": actor}
                elif ev.event_type == EventType.CHARACTER_MOVED:
                    actor = ev.actor_ids[0] if ev.actor_ids else "actor"
                    if actor not in char_locs:
                        char_locs[actor] = {"from": ev.metadata.get("from_location"), "to": ev.location_id}
                elif ev.event_type == EventType.BELIEF_FORMED:
                    knowledge_acquired.append({"character_id": ev.actor_ids[0] if ev.actor_ids else "char", "event_id": ev.id})

        return {
            "object_holders": obj_holders,
            "object_locations": obj_locs,
            "character_locations": char_locs,
            "knowledge_acquired": knowledge_acquired,
            "relationship_deltas": rel_deltas,
            "goals_changed": goals_changed,
        }


    def _is_static_scene(self, state_delta: Dict[str, Any]) -> bool:
        """Flag as STATIC_SCENE if state_delta contains no meaningful world state changes."""
        if not state_delta:
            return True
        for k in ("object_holders", "object_locations", "character_locations", "knowledge_acquired", "relationship_deltas", "goals_changed"):
            if state_delta.get(k):
                return False
        return True

    def _derive_scene_objective(
        self,
        pov_char_id: str,
        events: List[Event],
        world: WorldState,
        state_delta: Dict[str, Any],
        scene_purpose: DramaticFunction,
    ) -> SceneObjective:
        """Derive observational SceneObjective for the POV character."""
        char = world.characters.get(pov_char_id)
        char_name = char.name if char else "Focal Character"

        # 1. wants: from active goal during that scene
        wants = "Assess perimeter and maintain operational situational awareness"
        if char and hasattr(char, "goals") and char.goals:
            first_goal = char.goals[0]
            if isinstance(first_goal, str):
                g_obj = world.goals.get(first_goal) if hasattr(world, "goals") else None
                if g_obj and hasattr(g_obj, "description"):
                    wants = str(g_obj.description)
                else:
                    wants = str(first_goal)
            elif hasattr(first_goal, "description"):
                wants = str(first_goal.description)
            else:
                wants = str(first_goal)
        elif hasattr(world, "goals") and world.goals:
            for g in world.goals.values():
                if getattr(g, "character_id", None) == pov_char_id:
                    wants = str(getattr(g, "description", ""))
                    break

        wants = str(wants)


        # 2. emotional_want: deterministically derive from typed emotion_vector + active goal
        dominant_emotion = "cautious"
        if char and hasattr(char, "emotional_state") and char.emotional_state:
            emo = char.emotional_state
            if hasattr(emo, "dominant_emotion") and emo.dominant_emotion:
                dominant_emotion = emo.dominant_emotion
            elif hasattr(emo, "tension") and emo.tension > 0.6:
                dominant_emotion = "fearful and highly pressured"
            elif hasattr(emo, "arousal") and emo.arousal > 0.6:
                dominant_emotion = "intense and urgent"
            elif hasattr(emo, "valence") and emo.valence < -0.2:
                dominant_emotion = "defiant and conflicted"

        emotional_want = f"Drive to {wants.lower().rstrip('.')} under {dominant_emotion} pressure"

        # 3. obstacle: derive from actual world/event constraints in the scene
        present_others = []
        for ev in events:
            for aid in ev.actor_ids:
                if aid != pov_char_id and aid in world.characters:
                    c_name = world.characters[aid].name
                    if c_name not in present_others:
                        present_others.append(c_name)

        has_barrier = any("lock" in (e.description or "").lower() or "door" in (e.description or "").lower() for e in events)

        if present_others and has_barrier:
            obstacle = f"Guarded resistance of {', '.join(present_others)} and secured physical barriers"
        elif present_others:
            obstacle = f"Opposing presence and scrutiny of {', '.join(present_others)}"
        elif has_barrier:
            obstacle = "Physical barriers, locked access, and security perimeters"
        else:
            obstacle = "Operational friction, secrecy, and time constraints"

        # 4. tactics: actions actually attempted by POV character. Do not invent tactics.
        tactics = []
        for ev in events:
            if pov_char_id in ev.actor_ids:
                tactics.append(ev.description)

        # 5. outcome: ACHIEVED, DENIED, PARTIAL, ACHIEVED_AT_COST
        goal_completed = any(
            gc.get("change") == "COMPLETED"
            for gc in state_delta.get("goals_changed", [])
        )
        has_knowledge = bool(state_delta.get("knowledge_acquired"))
        has_possession = bool(state_delta.get("object_holders"))
        has_opponents = bool(present_others)

        if goal_completed:
            outcome: Literal["ACHIEVED", "DENIED", "PARTIAL", "ACHIEVED_AT_COST"] = "ACHIEVED"
        elif (has_knowledge or has_possession) and has_opponents:
            outcome = "ACHIEVED_AT_COST"
        elif not tactics or (self._is_static_scene(state_delta) and scene_purpose in (DramaticFunction.CONFRONTATION, DramaticFunction.CRISIS)):
            outcome = "DENIED"
        else:
            outcome = "PARTIAL"

        return SceneObjective(
            pov_character_id=pov_char_id,
            wants=wants,
            emotional_want=emotional_want,
            obstacle=obstacle,
            tactics=tactics,
            outcome=outcome,
            state_delta=state_delta,
        )

    def _derive_core_emotional_objective(
        self,
        focal_char_id: str,
        events: List[Event],
        world: WorldState,
        scene_purpose: ScenePurposeType,
    ) -> CoreEmotionalObjective:
        """Backward-compatible wrapper returning CoreEmotionalObjective / SceneObjective."""
        differ = StateSnapshotDiffer(world)
        start_t = min((e.tick for e in events), default=0)
        end_t = max((e.tick for e in events), default=start_t)
        state_delta = self._compute_state_delta(differ, world, start_t, end_t, scene_events=events)
        return self._derive_scene_objective(

            pov_char_id=focal_char_id,
            events=events,
            world=world,
            state_delta=state_delta,
            scene_purpose=scene_purpose,
        )

    def _select_turning_point(
        self,
        scene_events: List[Event],
        salience_map: Dict[str, EventSalience],
        state_delta: Dict[str, Any],
    ) -> Optional[str]:
        """Select turning_point_event_id deterministically from source_event_ids.

        Prefers the event with highest meaningful salience that produces state change,
        knowledge change, relationship change, goal progress, or dramatic beat evidence.
        Returns None if no defensible turning point exists.
        """
        if not scene_events:
            return None

        candidates: List[Event] = []
        for ev in scene_events:
            sal = salience_map.get(ev.id)
            if not sal:
                continue
            sigs = sal.signals
            meaningful = (
                sigs.get("goal_progress_delta", 0.0) > 0.0
                or sigs.get("knowledge_change_magnitude", 0.0) > 0.0
                or sigs.get("relationship_change_magnitude", 0.0) > 0.0
                or sigs.get("state_delta_magnitude", 0.0) > 0.0
                or sigs.get("beat_binding_bonus", 0.0) > 0.0
            )
            if meaningful and sal.score >= 0.25:
                candidates.append(ev)

        if not candidates:
            high_sal = [
                ev for ev in scene_events
                if salience_map.get(ev.id, EventSalience(event_id=ev.id, score=0, signals={})).score >= 0.60
            ]
            if high_sal:
                candidates = high_sal

        if not candidates:
            return None

        best_ev = max(candidates, key=lambda e: salience_map[e.id].score)
        return best_ev.id

    def _determine_scene_purpose(
        self,
        events: List[Event],
        scene_num: int,
    ) -> DramaticFunction:
        """Determine dramatic purpose using event types, keywords, and narrative position."""
        combined_desc = " ".join(e.description.lower() for e in events)
        if any(w in combined_desc for w in ["climax", "shootout", "final standoff", "cornered"]):
            return DramaticFunction.CLIMAX
        elif any(w in combined_desc for w in ["confront", "threat", "gun", "freeze", "accuse"]):
            return DramaticFunction.CONFRONTATION
        elif any(w in combined_desc for w in ["dossier", "find", "safe", "discover", "ledger", "cache"]):
            return DramaticFunction.DISCOVERY
        elif any(w in combined_desc for w in ["secret", "confess", "truth", "lying", "unmask"]):
            return DramaticFunction.REVELATION
        elif any(w in combined_desc for w in ["negotiat", "bargain", "deal", "offer", "compromise"]):
            return DramaticFunction.NEGOTIATION
        elif any(w in combined_desc for w in ["examine", "inspect", "probe", "search", "investigat"]):
            return DramaticFunction.INVESTIGATION
        elif any(w in combined_desc for w in ["flee", "chase", "escape", "run", "pursuit"]):
            return DramaticFunction.CHASE
        elif any(w in combined_desc for w in ["reversal", "betrayal", "twist", "surprise"]):
            return DramaticFunction.REVERSAL
        elif scene_num == 1:
            return DramaticFunction.SETUP
        else:
            return DramaticFunction.INVESTIGATION

    def _group_events_into_scenes(
        self,
        events: List[Event],
    ) -> List[List[Event]]:
        """Group contiguous canonical source events by location changes, time gaps, and actor shifts."""
        if not events:
            return []

        grouped_scenes: List[List[Event]] = []
        current_group: List[Event] = [events[0]]

        for curr_ev in events[1:]:
            prev_ev = current_group[-1]

            # 1. Location change: distinct locations trigger boundary
            location_changed = (
                curr_ev.location_id is not None
                and prev_ev.location_id is not None
                and curr_ev.location_id != prev_ev.location_id
            )

            # 2. Significant time gap: > 2 ticks triggers boundary
            temporal_gap = (curr_ev.tick - prev_ev.tick) > 2

            # 3. Participant shift: completely disjoint actors across scene boundary
            scene_all_actors = {aid for e in current_group for aid in e.actor_ids}
            actors_curr = set(curr_ev.actor_ids)
            disjoint_actors = bool(
                scene_all_actors
                and actors_curr
                and not (scene_all_actors & actors_curr)
                and (curr_ev.tick - prev_ev.tick >= 2)
            )

            if location_changed or temporal_gap or disjoint_actors:
                grouped_scenes.append(current_group)
                current_group = [curr_ev]
            else:
                current_group.append(curr_ev)

        if current_group:
            grouped_scenes.append(current_group)

        return grouped_scenes

    def build_scenes(
        self,
        selection: Optional[NarrativeEventSelection] = None,
        world: Optional[WorldState] = None,
        blueprint: Optional[StoryBlueprint] = None,
        sufficiency_report: Optional[SufficiencyReport] = None,
        events: Optional[List[Event]] = None,
        provenance: Any | None = None,
        gate_report: Optional[SufficiencyReport] = None,
        differ: Any | None = None,
    ) -> List[Scene]:
        """Construct canonical Scene instances from events and world state.

        Execution Gate Rule:
        Scene Builder may run only AFTER Narrative Sufficiency Gate reaches a terminal recommendation:
        PROCEED or HALT_INSUFFICIENT.
        It MUST NOT run while recommendation is CONTINUE or ADJUST_PRESSURE_AND_CONTINUE.
        """
        if sufficiency_report is None and gate_report is not None:
            sufficiency_report = gate_report
        # 1. Enforce Execution Gate
        if sufficiency_report is not None:
            if sufficiency_report.recommendation in ("CONTINUE", "ADJUST_PRESSURE_AND_CONTINUE"):
                raise SufficiencyGateExecutionError(
                    f"SceneBuilder execution rejected: NarrativeSufficiencyGate returned non-terminal recommendation "
                    f"'{sufficiency_report.recommendation}'. SceneBuilder requires PROCEED or HALT_INSUFFICIENT."
                )
        elif blueprint is not None and world is not None:
            gate = NarrativeSufficiencyGate()
            report = gate.evaluate(
                blueprint=blueprint,
                world=world,
                current_tick=world.current_tick,
                current_budget_ticks=getattr(blueprint, "budget_ticks", world.current_tick),
                hard_cap_ticks=getattr(blueprint, "hard_cap_ticks", world.current_tick + 10),
            )
            if report.recommendation in ("CONTINUE", "ADJUST_PRESSURE_AND_CONTINUE"):
                raise SufficiencyGateExecutionError(
                    f"SceneBuilder execution rejected: NarrativeSufficiencyGate evaluated non-terminal recommendation "
                    f"'{report.recommendation}'. SceneBuilder requires PROCEED or HALT_INSUFFICIENT."
                )

        if world is None:
            return []

        # 2. Collect events in canonical chronological order
        source_events: List[Event] = []
        if events is not None:
            source_events = sorted(events, key=lambda e: (e.tick, e.id))
        elif selection is not None and selection.filtered_beats:
            seen_ids = set()
            for beat in selection.filtered_beats:
                for eid in beat.source_event_ids:
                    if eid in world.events and eid not in seen_ids:
                        source_events.append(world.events[eid])
                        seen_ids.add(eid)
            source_events.sort(key=lambda e: (e.tick, e.id))
        else:
            source_events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))

        if not source_events:
            return []

        # 3. Differ and Observer Scoring
        differ = StateSnapshotDiffer(world)
        salience_map = self.observer.score_all_events(
            source_events,
            world=world,
            differ=differ,
            blueprint=blueprint,
        )

        # 4. Group contiguous events into scene clusters
        grouped_event_clusters = self._group_events_into_scenes(source_events)

        scenes: List[Scene] = []
        for idx, cluster in enumerate(grouped_event_clusters, start=1):
            start_t = min(e.tick for e in cluster)
            end_t = max(e.tick for e in cluster)
            loc_id = cluster[0].location_id or "loc_main"
            loc = world.locations.get(loc_id)
            loc_name = loc.name if loc else "Unknown Location"
            heading = f"INT. {loc_name.upper()} - CONTINUOUS"

            chars_present = sorted(list({aid for e in cluster for aid in e.actor_ids if aid in world.characters}))
            focal_id = self._determine_focal_character(cluster, world) or "char_protagonist"

            # Compute State Delta
            state_delta = self._compute_state_delta(differ, world, start_t, end_t, scene_events=cluster)
            is_static = self._is_static_scene(state_delta)


            # Determine Purpose
            purpose = self._determine_scene_purpose(cluster, idx)

            # Derive Objective
            objective = self._derive_scene_objective(focal_id, cluster, world, state_delta, purpose)

            # Determine Turning Point
            turning_point_id = self._select_turning_point(cluster, salience_map, state_delta)

            outcome: Literal["ACHIEVED", "DENIED", "PARTIAL", "ACHIEVED_AT_COST", "STATIC"] = (
                "STATIC" if is_static else objective.outcome
            )

            # In Phase 5A: presentation_position MUST equal chronological_position
            chronological_position = idx
            presentation_position = idx

            scene_metadata: Dict[str, Any] = {
                "total_events": len(cluster),
                "static_scene": is_static,
            }
            if is_static:
                scene_metadata["scene_flag"] = "STATIC_SCENE"

            scene_obj = Scene(
                scene_id=f"scene_{idx:02d}",
                scene_number=idx,
                location_id=loc_id,
                location_name=loc_name,
                heading=heading,
                purpose=purpose,
                scene_purpose=purpose,
                objective=objective,
                core_emotional_objective=objective,
                source_event_ids=[e.id for e in cluster],
                characters_present=chars_present,
                start_tick=start_t,
                end_tick=end_t,
                dramatic_tension=50.0 + (idx * 8.0),
                chronological_position=chronological_position,
                presentation_position=presentation_position,
                is_static=is_static,
                turning_point_event_id=turning_point_id,
                outcome=outcome,
                framing_type="chronological",
                time_context="CONTINUOUS",
                metadata=scene_metadata,
            )
            scenes.append(scene_obj)

        if provenance is not None and hasattr(provenance, "register_scenes"):
            provenance.register_scenes(scenes)

        return scenes

    def enrich_scenes_with_phase6(
        self,
        scenes: List[Scene],
        world: WorldState,
        events: Optional[List[Event]] = None,
    ) -> List[Scene]:
        """Enrich scenes with character arcs, subtext analyses, and performance cues for Phase 7 consumption."""
        from src.narrative.arc_tracker import CharacterArcTracker
        from src.narrative.subtext import SubtextAnalyzer
        from src.narrative.performance_cues import PerformanceCueGenerator

        all_events = events if events is not None else sorted(world.events.values(), key=lambda e: (e.tick, e.id))
        arc_tracker = CharacterArcTracker()
        subtext_analyzer = SubtextAnalyzer()
        cue_generator = PerformanceCueGenerator()

        all_arcs = arc_tracker.trace_all_arcs(world, all_events)

        for scene in scenes:
            scene.character_arcs = {
                cid: arc for cid, arc in all_arcs.items()
                if cid in scene.characters_present
            }

            subtext_list = []
            cues_list = []

            for eid in scene.source_event_ids:
                ev = world.events.get(eid)
                if not ev:
                    continue
                if ev.event_type == EventType.CHARACTER_SPOKE:
                    speaker_id = ev.actor_ids[0] if ev.actor_ids else None
                    speaker = world.characters.get(speaker_id) if speaker_id else None
                    if speaker:
                        dialogue_text = ev.metadata.get("dialogue") or ev.description
                        listener_ids = [aid for aid in scene.characters_present if aid != speaker_id]
                        listener_id = listener_ids[0] if listener_ids else None
                        analysis = subtext_analyzer.analyze(
                            speaker=speaker,
                            dialogue=dialogue_text,
                            world=world,
                            listener_id=listener_id,
                            listener_ids=listener_ids,
                            event_metadata=ev.metadata,
                        )
                        cue = cue_generator.generate_cue(
                            analysis=analysis,
                            character=speaker,
                            world=world,
                            source_event_id=ev.id,
                        )
                        subtext_list.append(analysis)
                        cues_list.append(cue)

            scene.subtext_analyses = subtext_list
            scene.performance_cues = cues_list

        return scenes
