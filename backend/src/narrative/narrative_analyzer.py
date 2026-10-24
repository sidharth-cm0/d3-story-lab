"""Deterministic Narrative Analyzer for D3 Story Lab.

Grounded evaluation of simulation windows against abstract narrative patterns.

CRITICAL INVARIANTS:
1. STRUCTURE WITHOUT PUPPETRY:
   - Analyzer is purely observational and read-only.
   - It NEVER mutates WorldState, EventLog, or character internals.
2. EVENT GROUNDING:
   - All dramatic findings MUST reference verified canonical EventLog IDs.
3. DETERMINISTIC & PROVIDER-OFF COMPATIBLE:
   - Rule-based analysis without requiring external AI providers.
"""

from __future__ import annotations
import uuid
from typing import List, Dict, Optional, Any, Set
from datetime import datetime, timezone

from ..domain.world import WorldState
from ..domain.event import Event, EventType
from ..domain.story_structure import StoryBlueprint
from ..domain.conflict import ConflictGraph, ConflictDimension
from ..domain.narrative_genome import (
    NarrativeAnalysisResult,
    DramaticFunction,
    ConflictType,
    CausalRelation,
    TensionDirection,
    InformationPattern,
    ScenePurpose,
    SetupPayoffState,
)
from .dramatic_signals import extract_dramatic_signals, DramaticSignalsReport
from .conflict_engine import ConflictEngine


class NarrativeAnalyzer:
    """Analyzes simulation windows to extract abstract dramatic patterns and tension movements."""

    def __init__(self, window_size: int = 15):
        self.window_size = window_size

    def analyze(
        self,
        world: WorldState,
        events: Optional[List[Event]] = None,
        blueprint: Optional[StoryBlueprint] = None,
        conflict_graph: Optional[ConflictGraph] = None,
    ) -> NarrativeAnalysisResult:
        """Deterministically analyze recent simulation events and current world state."""
        all_events = sorted(
            events if events is not None else list(world.events.values()),
            key=lambda e: (e.tick, e.id)
        )
        recent_events = all_events[-self.window_size:] if all_events else []
        event_ids = [e.id for e in recent_events]

        # 1. Reuse existing dramatic signals extraction
        signals: DramaticSignalsReport = extract_dramatic_signals(
            world=world,
            events=recent_events,
            existing_graph=conflict_graph,
        )

        # 2. Derive tension before, after, and delta
        curr_tension = signals.unresolved_tension_level
        prev_tension = self._calculate_prior_tension(all_events, recent_events)
        tension_delta = round(curr_tension - prev_tension, 2)

        if tension_delta >= 0.15:
            tension_dir = TensionDirection.SPIKE if tension_delta >= 0.30 else TensionDirection.RISING
        elif tension_delta <= -0.15:
            tension_dir = TensionDirection.RELEASE if tension_delta <= -0.30 else TensionDirection.FALLING
        else:
            tension_dir = TensionDirection.SUSTAINED

        # 3. Active conflicts grounded in ConflictEngine and dramatic signals
        active_conflicts = []
        for edge in signals.unresolved_conflicts:
            active_conflicts.append({
                "source_character_id": edge.source_character_id,
                "target_character_id": edge.target_character_id,
                "intensity": edge.aggregate_intensity,
                "dimensions": [d.value if hasattr(d, "value") else str(d) for d in edge.dimensions.keys()],
                "evidence_ids": [ev.source_id for ev in edge.evidence],
            })

        # 4. Infer dramatic functions present in this window
        dramatic_functions = self._infer_dramatic_functions(recent_events, signals, tension_dir)

        # 5. Extract causal chain connections
        causal_chain = self._extract_causal_chains(recent_events)

        # 6. Information patterns and asymmetry
        information_state = self._evaluate_information_state(world, recent_events, signals)

        # 7. Setup / Payoff status tracking
        setup_payoffs = self._evaluate_setup_payoffs(world, all_events, recent_events)

        # 8. Infer scene purposes
        scene_purposes = self._infer_scene_purposes(recent_events, signals, dramatic_functions)

        # 9. Pacing assessment
        pacing = self._assess_pacing(recent_events, signals, tension_dir)

        # 10. Unresolved threads
        unresolved_threads = self._identify_unresolved_threads(world, signals, recent_events)

        # 11. Narrative opportunities & warnings
        opportunities = self._generate_opportunities(signals, information_state, pacing)
        warnings = self._generate_warnings(signals, pacing, recent_events)

        analysis_id = f"na_{world.current_tick}_{len(recent_events)}"

        return NarrativeAnalysisResult(
            id=analysis_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_ids=event_ids,
            dramatic_functions=dramatic_functions,
            active_conflicts=active_conflicts,
            causal_chain=causal_chain,
            tension={
                "before": prev_tension,
                "after": curr_tension,
                "delta": tension_delta,
            },
            tension_direction=tension_dir,
            information_state=information_state,
            setup_payoff_status=setup_payoffs,
            scene_purpose=scene_purposes,
            pacing_assessment=pacing,
            unresolved_threads=unresolved_threads,
            opportunities=opportunities,
            warnings=warnings,
            confidence=1.0,
        )

    def _calculate_prior_tension(
        self,
        all_events: List[Event],
        recent_events: List[Event],
    ) -> float:
        """Estimate baseline tension level prior to the recent event window."""
        if not recent_events or len(all_events) <= len(recent_events):
            return 0.30

        older_events = all_events[:-len(recent_events)]
        if not older_events:
            return 0.30

        # Heuristic baseline based on older events confrontation/tension keywords
        t_score = 0.30
        for ev in older_events[-5:]:
            desc = (ev.description or "").lower()
            if any(w in desc for w in ["confront", "threat", "draws", "secret", "alarm"]):
                t_score += 0.10
            elif any(w in desc for w in ["calm", "rests", "truce", "leaves"]):
                t_score -= 0.05
        return round(max(0.0, min(1.0, t_score)), 2)

    def _infer_dramatic_functions(
        self,
        events: List[Event],
        signals: DramaticSignalsReport,
        tension_dir: TensionDirection,
    ) -> List[DramaticFunction]:
        """Infer active dramatic functions from verified events and signals."""
        funcs: Set[DramaticFunction] = set()

        if not events:
            return [DramaticFunction.SETUP]

        for ev in events:
            desc = (ev.description or "").lower()
            meta = ev.metadata or {}

            if any(w in desc for w in ["arrive", "enter", "inspects perimeter", "begins"]):
                funcs.add(DramaticFunction.SETUP)
            if any(w in desc for w in ["discovers", "uncovers", "finds", "locates"]):
                funcs.add(DramaticFunction.DISCOVERY)
            if any(w in desc for w in ["reveal", "confess", "unmask"]) or meta.get("speech_act") == "reveal":
                funcs.add(DramaticFunction.REVELATION)
            if any(w in desc for w in ["confront", "accuse", "threat", "standoff", "draws weapon"]):
                funcs.add(DramaticFunction.CONFRONTATION)
            if any(w in desc for w in ["negotiate", "bargain", "plead", "demand"]):
                funcs.add(DramaticFunction.NEGOTIATION)
            if any(w in desc for w in ["fails", "blocked", "locked door", "jammed", "barrier"]):
                funcs.add(DramaticFunction.COMPLICATION)
            if any(w in desc for w in ["chase", "pursuit", "sprints", "escapes"]):
                funcs.add(DramaticFunction.CHASE)
            if any(w in desc for w in ["inverts", "reversal", "tables turned", "disarmed"]):
                funcs.add(DramaticFunction.REVERSAL)
            if any(w in desc for w in ["climax", "reckoning", "final stand"]):
                funcs.add(DramaticFunction.CLIMAX)
            if any(w in desc for w in ["resolved", "truce", "retreats", "concluded"]):
                funcs.add(DramaticFunction.RESOLUTION)

        if signals.has_major_conflict_escalation or tension_dir in (TensionDirection.RISING, TensionDirection.SPIKE):
            funcs.add(DramaticFunction.ESCALATION)

        if signals.secret_revelations:
            funcs.add(DramaticFunction.REVELATION)

        if not funcs:
            funcs.add(DramaticFunction.ESCALATION if signals.unresolved_tension_level >= 0.5 else DramaticFunction.SETUP)

        return sorted(list(funcs), key=lambda f: f.value)

    def _extract_causal_chains(self, events: List[Event]) -> List[Dict[str, Any]]:
        """Identify causal links between events via caused_by relationships."""
        chains: List[Dict[str, Any]] = []
        event_dict = {e.id: e for e in events}

        for ev in events:
            if ev.caused_by:
                for parent_id in ev.caused_by:
                    relation = CausalRelation.CAUSES
                    if ev.event_type in (EventType.OBJECT_PICKED_UP, EventType.OBJECT_DROPPED):
                        relation = CausalRelation.ENABLES
                    elif "blocked" in (ev.description or "").lower():
                        relation = CausalRelation.PREVENTS

                    chains.append({
                        "from_event_id": parent_id,
                        "to_event_id": ev.id,
                        "relation": relation.value,
                        "tick": ev.tick,
                    })
        return chains

    def _evaluate_information_state(
        self,
        world: WorldState,
        events: List[Event],
        signals: DramaticSignalsReport,
    ) -> List[Dict[str, Any]]:
        """Map asymmetric knowledge, secrets, dramatic irony, and revelations."""
        info_items: List[Dict[str, Any]] = []

        # 1. World Secrets asymmetry
        for sec_id, sec in world.secrets.items():
            holder = sec.character_id
            knowers = set(sec.known_by) | {holder}
            non_knowers = set(world.characters.keys()) - knowers

            # Check if holder is co-located with any non-knower (Dramatic Irony)
            holder_char = world.characters.get(holder)
            holder_loc = holder_char.current_location_id if holder_char else None

            irony_targets = []
            if holder_loc:
                for nk_id in non_knowers:
                    nk_char = world.characters.get(nk_id)
                    if nk_char and nk_char.current_location_id == holder_loc:
                        irony_targets.append(nk_id)

            if irony_targets:
                info_items.append({
                    "pattern": InformationPattern.DRAMATIC_IRONY.value,
                    "secret_id": sec_id,
                    "holder_id": holder,
                    "unaware_character_ids": irony_targets,
                    "description": f"Character '{holder}' conceals '{sec.statement}' from co-located characters {irony_targets}.",
                })
            else:
                info_items.append({
                    "pattern": InformationPattern.CONCEALMENT.value,
                    "secret_id": sec_id,
                    "holder_id": holder,
                    "description": f"Concealed secret '{sec.statement}' remains hidden from {len(non_knowers)} character(s).",
                })

        # 2. Event-based discoveries, revelations, and belief flips (deduplicated by event ID)
        seen_event_ids: Set[str] = set()
        for ev in events:
            if ev.id in seen_event_ids:
                continue
            seen_event_ids.add(ev.id)

            desc = (ev.description or "").lower()
            meta = ev.metadata or {}

            if any(w in desc for w in ["discover", "found", "uncover"]) or meta.get("discovery"):
                info_items.append({
                    "pattern": InformationPattern.DISCOVERY.value,
                    "event_id": ev.id,
                    "actor_ids": ev.actor_ids,
                    "description": ev.description,
                })
            elif (
                any(w in desc for w in ["reveal", "confess", "secret revealed"])
                or meta.get("secret_revealed")
                or meta.get("speech_act") == "reveal"
            ):
                info_items.append({
                    "pattern": InformationPattern.REVELATION.value,
                    "event_id": ev.id,
                    "actor_ids": ev.actor_ids,
                    "description": ev.description,
                })
            elif (
                ev.event_type == EventType.BELIEF_FORMED
                or "belief" in desc
                or meta.get("belief_flipped")
            ):
                is_contradiction = (
                    meta.get("belief_flipped")
                    or any(w in desc for w in ["contradict", "inverted", "false", "doubt", "shattered"])
                )
                pattern = InformationPattern.CONTRADICTION.value if is_contradiction else InformationPattern.CONFIRMATION.value
                info_items.append({
                    "pattern": pattern,
                    "event_id": ev.id,
                    "actor_ids": ev.actor_ids,
                    "description": ev.description,
                })

        return info_items

    def _evaluate_setup_payoffs(
        self,
        world: WorldState,
        all_events: List[Event],
        recent_events: List[Event],
    ) -> List[Dict[str, Any]]:
        """Track potential setups and payoffs across objects and clues."""
        items: List[Dict[str, Any]] = []

        # Track portable objects in world
        for obj_id, obj in world.objects.items():
            if obj.portable:
                # Find pickup events
                pickup_events = [e for e in all_events if e.event_type == EventType.OBJECT_PICKED_UP and e.metadata.get("object_id") == obj_id]
                drop_or_use = [e for e in all_events if e.event_type in (EventType.OBJECT_DROPPED, EventType.OBJECT_GIVEN) and e.metadata.get("object_id") == obj_id]

                if pickup_events and not drop_or_use:
                    items.append({
                        "entity_id": obj_id,
                        "name": obj.name,
                        "state": SetupPayoffState.SETUP.value,
                        "setup_event_id": pickup_events[-1].id,
                        "holder_id": obj.holder_id,
                        "description": f"Object '{obj.name}' was acquired and remains held for future payoff.",
                    })
                elif pickup_events and drop_or_use:
                    items.append({
                        "entity_id": obj_id,
                        "name": obj.name,
                        "state": SetupPayoffState.PAID.value,
                        "setup_event_id": pickup_events[-1].id,
                        "payoff_event_id": drop_or_use[-1].id,
                        "description": f"Object '{obj.name}' was acquired and subsequently passed/used.",
                    })

        return items

    def _infer_scene_purposes(
        self,
        events: List[Event],
        signals: DramaticSignalsReport,
        dramatic_funcs: List[DramaticFunction],
    ) -> List[ScenePurpose]:
        """Map sequence observations to abstract scene purposes."""
        purposes: Set[ScenePurpose] = set()

        if DramaticFunction.SETUP in dramatic_funcs:
            purposes.add(ScenePurpose.ESTABLISH)
            purposes.add(ScenePurpose.SETUP)
        if DramaticFunction.ESCALATION in dramatic_funcs:
            purposes.add(ScenePurpose.ESCALATE)
        if DramaticFunction.REVELATION in dramatic_funcs:
            purposes.add(ScenePurpose.REVEAL)
        if DramaticFunction.CONFRONTATION in dramatic_funcs:
            purposes.add(ScenePurpose.TEST_RELATIONSHIP)
            purposes.add(ScenePurpose.CREATE_CHOICE)
        if DramaticFunction.COMPLICATION in dramatic_funcs:
            purposes.add(ScenePurpose.INTRODUCE_OBSTACLE)
        if DramaticFunction.PAYOFF in dramatic_funcs:
            purposes.add(ScenePurpose.RESOLVE_OBSTACLE)
            purposes.add(ScenePurpose.PAYOFF)
        if DramaticFunction.RESOLUTION in dramatic_funcs or DramaticFunction.TRANSITION in dramatic_funcs:
            purposes.add(ScenePurpose.TRANSITION)

        if signals.stalled_relationships:
            purposes.add(ScenePurpose.TEST_RELATIONSHIP)

        if not purposes:
            purposes.add(ScenePurpose.ESCALATE if signals.unresolved_tension_level >= 0.5 else ScenePurpose.ESTABLISH)

        return sorted(list(purposes), key=lambda p: p.value)

    def _assess_pacing(
        self,
        events: List[Event],
        signals: DramaticSignalsReport,
        tension_dir: TensionDirection,
    ) -> Dict[str, Any]:
        stagnation = len(signals.stalled_relationships)
        consecutive_idle = sum(
            1 for e in events
            if e.metadata.get("action_type") == "wait" or "wait" in (e.description or "").lower()
        ) if events else 0

        pacing_state = "healthy"
        if consecutive_idle >= 3:
            pacing_state = "idle"
        elif stagnation >= 2:
            pacing_state = "stalled"
        elif signals.unresolved_tension_level >= 0.8:
            pacing_state = "overheated"

        return {
            "pacing_state": pacing_state,
            "tension_level": signals.unresolved_tension_level,
            "tension_direction": tension_dir.value,
            "stalled_relationships_count": stagnation,
            "idle_events_count": consecutive_idle,
            "event_density": len(events),
        }

    def _identify_unresolved_threads(
        self,
        world: WorldState,
        signals: DramaticSignalsReport,
        recent_events: List[Event],
    ) -> List[Dict[str, Any]]:
        """Identify open narrative threads and unconsummated conflict potentials."""
        threads: List[Dict[str, Any]] = []

        # 1. Unresolved high-intensity conflicts
        for edge in signals.unresolved_conflicts:
            if edge.aggregate_intensity >= 0.6:
                threads.append({
                    "thread_type": "interpersonal_conflict",
                    "character_a_id": edge.source_character_id,
                    "character_b_id": edge.target_character_id,
                    "intensity": edge.aggregate_intensity,
                    "description": f"Acute unresolved tension ({edge.aggregate_intensity:.2f}) between {edge.source_character_id} and {edge.target_character_id}.",
                })

        # 2. Unrevealed secrets in shared spaces
        for sec_id, sec in world.secrets.items():
            if not sec.known_by:
                threads.append({
                    "thread_type": "concealed_secret",
                    "secret_id": sec_id,
                    "holder_id": sec.character_id,
                    "description": f"Unrevealed secret '{sec.statement}' held by {sec.character_id}.",
                })

        # 3. Stalled interpersonal relationships
        for stalled in signals.stalled_relationships:
            c_a = getattr(stalled, "source_character_id", getattr(stalled, "character_a_id", ""))
            c_b = getattr(stalled, "target_character_id", getattr(stalled, "character_b_id", ""))
            threads.append({
                "thread_type": "stalled_relationship",
                "character_a_id": c_a,
                "character_b_id": c_b,
                "description": f"Stalled relationship interaction deadlock between {c_a} and {c_b}.",
            })

        return threads

    def _generate_opportunities(
        self,
        signals: DramaticSignalsReport,
        information_state: List[Dict[str, Any]],
        pacing: Dict[str, Any],
    ) -> List[str]:
        """Synthesize narrative opportunities grounded in current dramatic configuration."""
        opps: List[str] = []

        if signals.stalled_relationships:
            opps.append("Opportunity for environmental disruption to break interpersonal stagnation.")

        has_irony = any(item.get("pattern") == InformationPattern.DRAMATIC_IRONY.value for item in information_state)
        if has_irony:
            opps.append("Opportunity for discovery catalyst to expose concealed truth.")

        if signals.unresolved_conflicts:
            opps.append("Opportunity to test conflicting commitments under external constraint.")

        if pacing.get("pacing_state") == "overheated":
            opps.append("Opportunity for transitional decompression before next escalation.")

        if not opps:
            opps.append("Opportunity to introduce subtle environmental complication to test character goals.")

        return opps

    def _generate_warnings(
        self,
        signals: DramaticSignalsReport,
        pacing: Dict[str, Any],
        recent_events: List[Event],
    ) -> List[str]:
        """Detect potential dramatic pitfalls such as sustained inactivity or endless loops."""
        warnings: List[str] = []

        if pacing.get("pacing_state") == "stalled":
            warnings.append("Interpersonal tension is high but characters have ceased taking proactive action.")

        if pacing.get("pacing_state") == "idle":
            warnings.append("Excessive WAIT or idle actions observed in recent simulation window.")

        if signals.unresolved_tension_level >= 0.85:
            warnings.append("Tension sustained at near-maximum ceiling without release or climactic reckoning.")

        return warnings
