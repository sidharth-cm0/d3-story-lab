"""Simulation Orchestrator coordinating multi-agent steps, cognition, evolution, and pacing."""

from typing import List, Dict, Optional, TYPE_CHECKING
from ..domain import (
    WorldState,
    ActionType,
    ActionResult,
    ActionResultStatus,
    ActionProposal,
    GoalStatus,
    EventLog,
    DiscoveredFact,
)
from ..domain.simulation import SimulationClock
from .recorder import EventRecorder
from .actions import ActionValidator, ActionExecutor
from .differ import StateSnapshotDiffer
from ..narrative.sufficiency_gate import NarrativeSufficiencyGate
from ..memory.service import MemoryService
if TYPE_CHECKING:
    from ..agents.actor import ActorAgent
from ..agents.director import DirectorAgent
from ..agents.repetition import RepetitionTracker
from ..evolution.belief import BeliefUpdater
from ..evolution.relationship import RelationshipUpdater
from ..evolution.emotion import EmotionUpdater
from ..providers.base import LLMProvider
from ..providers.mock import MockLLMProvider
from ..story.models import StoryBlueprint, SufficiencyReport


class SimulationOrchestrator:
    """Orchestrates multi-agent cyclic simulation execution with cognition, evolution, and pacing"""

    def __init__(
        self,
        world: WorldState,
        provider: Optional[LLMProvider] = None,
        recorder: Optional[EventRecorder] = None,
        clock: Optional[SimulationClock] = None,
        memory_service: Optional[MemoryService] = None,
        director: Optional[DirectorAgent] = None,
        repetition_tracker: Optional[RepetitionTracker] = None,
        blueprint: Optional[StoryBlueprint] = None,
        story_blueprint: Optional[StoryBlueprint] = None,
        seed: Optional[int] = None,
    ):
        self.seed = seed
        self.world = world
        self.blueprint = blueprint or story_blueprint
        self.provider = provider or MockLLMProvider()
        self.total_ticks = 20
        self.differ = StateSnapshotDiffer(world)
        self.sufficiency_gate = NarrativeSufficiencyGate()
        self.last_sufficiency_report: Optional[SufficiencyReport] = None
        if recorder is not None:
            self.recorder = recorder
            if seed is not None and getattr(self.recorder, "seed", None) is None:
                self.recorder.seed = seed
        else:
            self.recorder = EventRecorder(world, seed=seed)

        self.clock = clock or SimulationClock(
            current_tick=world.current_tick, total_ticks=world.current_tick
        )
        self.memory_service = memory_service or MemoryService(world, seed=seed)
        if director is not None:
            self.director = director
            if self.blueprint and not self.director.blueprint:
                self.director.blueprint = self.blueprint
        else:
            self.director = DirectorAgent(blueprint=self.blueprint)
        self.validator = ActionValidator()
        self.executor = ActionExecutor(validator=self.validator)
        self.repetition_tracker = repetition_tracker or RepetitionTracker()

        # Agents registry per character
        from ..agents.actor import ActorAgent

        self.agents: Dict[str, ActorAgent] = {
            char_id: ActorAgent(
                char_id,
                provider=self.provider,
                memory_service=self.memory_service,
                repetition_tracker=self.repetition_tracker,
                seed=seed,
            )
            for char_id in world.characters.keys()
        }

        # Track activity, repetition, stagnation, and scene resolution
        self._inactivity_count = 0
        self._stagnation_count = 0
        self._previous_facts_count = len(world.facts)
        self._recent_action_signatures: List[str] = []
        self._is_paused = False
        self.scene_resolution_status: Optional[str] = None

    @property
    def rejection_log(self) -> List[Any]:
        """Access the rejection log containing all actions rejected by validator gates."""
        return self.validator.rejections

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def step(self) -> List[ActionResult]:
        """Run one complete cyclic simulation cycle"""
        if self._is_paused:
            return []

        results: List[ActionResult] = []
        tick_action_taken = False

        # 1. Deterministic actor ordering
        active_characters = sorted(self.world.characters.keys())

        # 2. Collect and process proposals
        for char_id in active_characters:
            agent = self.agents[char_id]
            proposal = agent.propose_action(self.world)

            # Record signature for repetition analysis
            sig = f"{char_id}:{proposal.action_type.value}:{proposal.target_id or ''}"
            self._recent_action_signatures.append(sig)

            # Execute proposal
            result = self.executor.execute(self.world, proposal, self.recorder)
            results.append(result)

            if result.status == ActionResultStatus.SUCCESS:
                if proposal.action_type != ActionType.WAIT:
                    tick_action_taken = True
                topic = proposal.parameters.get("topic")
                speech_act = proposal.parameters.get("speech_act") or proposal.parameters.get("social_intent")
                self.repetition_tracker.record_action(
                    actor_id=char_id,
                    action_type=proposal.action_type,
                    target_id=proposal.target_id,
                    location_id=proposal.location_id,
                    intent=proposal.reason,
                    topic=topic,
                    speech_act=speech_act,
                    tick=self.world.current_tick,
                )
                self._apply_cognitive_effects(char_id, proposal, result)

        # 3. Update inactivity and stagnation tracking
        new_facts = len(self.world.facts) - self._previous_facts_count
        self._previous_facts_count = len(self.world.facts)

        if not tick_action_taken:
            self._inactivity_count += 1
        else:
            self._inactivity_count = 0

        if new_facts == 0:
            self._stagnation_count += 1
        else:
            self._stagnation_count = 0

        # 4. Capture snapshot for state diffing and evaluate blueprint beat predicates
        self.differ.capture_snapshot(self.world.current_tick, self.world)

        if self.blueprint and hasattr(self.blueprint, "beats"):
            for beat in self.blueprint.beats:
                if beat.status not in ("PENDING", "PARTIAL") or getattr(beat, "unevaluable", False):
                    continue
                start_tick = int(round(beat.target_window[0] * self.total_ticks))
                end_tick = max(start_tick, int(round(beat.target_window[1] * self.total_ticks)))

                if self.world.current_tick >= start_tick:
                    is_sat = False
                    if beat.satisfaction_predicate.any_of:
                        is_sat = any(
                            self.differ.evaluate_clause(self.world, c, start_tick, self.world.current_tick)
                            for c in beat.satisfaction_predicate.any_of
                        )
                    elif beat.satisfaction_predicate.all_of:
                        is_sat = all(
                            self.differ.evaluate_clause(self.world, c, start_tick, self.world.current_tick)
                            for c in beat.satisfaction_predicate.all_of
                        )
                    if is_sat:
                        beat.status = "SATISFIED"
                        beat.satisfaction_tick = self.world.current_tick
                    elif self.world.current_tick > end_tick:
                        beat.status = "UNSATISFIED"
                        beat.deviation_note = (
                            f"Beat window [{beat.target_window[0]:.2f}, {beat.target_window[1]:.2f}] "
                            f"closed without satisfaction predicate being met."
                        )

            # Director beat escalation check
            if self.director and hasattr(self.director, "evaluate_beat_escalation"):
                self.director.evaluate_beat_escalation(
                    self.world, self.recorder, self.validator, self.total_ticks
                )

        # 5. Director evaluates pacing and potentially intervenes
        if hasattr(self.director, "evaluate_pacing"):
            intervention = self.director.evaluate_pacing(
                self.world, self._inactivity_count, stagnation_count=self._stagnation_count
            )
            if intervention:
                int_event = self.director.inject_intervention(self.world, self.recorder, intervention, validator=self.validator)
                if int_event:
                    self._inactivity_count = 0  # Pressure breaks inactivity
                    self._stagnation_count = 0

                    # Form memory and emotional jolt for actors present at location
                    if intervention.target_location_id:
                        for c in self.world.characters.values():
                            if c.current_location_id == intervention.target_location_id:
                                self.memory_service.form_memory(
                                    character_id=c.id,
                                    summary=intervention.description,
                                    importance=0.9,
                                    emotional_weight=-0.3,
                                    event_id=int_event.id,
                                    tags=["director_intervention", getattr(intervention, "intervention_type", "other")],
                                )
                                EmotionUpdater.adjust_emotion(c, delta_fear=0.3, delta_curiosity=0.3)

                    # Record discovered fact from director environmental intervention
                    int_type = getattr(intervention, "intervention_type", "other")
                    int_type_val = int_type.value if hasattr(int_type, "value") else str(int_type)
                    int_fact_id = f"fact_dir_{self.world.current_tick}_{int_type_val}"
                    if int_fact_id not in self.world.facts:
                        self.world.facts[int_fact_id] = DiscoveredFact(
                            id=int_fact_id,
                            statement=intervention.description,
                            source="observation",
                            confidence=1.0,
                            discovered_by="environment",
                            tick=self.world.current_tick,
                            related_entities=[intervention.target_location_id] if intervention.target_location_id else [],
                            metadata={"incident_type": int_type_val},
                        )

        # 6. Check scene resolution criteria
        for g in self.world.goals.values():
            if g.status in (GoalStatus.ACHIEVED, GoalStatus.COMPLETED):
                if not self.scene_resolution_status:
                    actor_name = self.world.characters[g.character_id].name if g.character_id in self.world.characters else g.character_id
                    self.scene_resolution_status = f"GOAL_ACHIEVED: {actor_name} accomplished '{g.description}'"

        # 7. Advance clock
        self.clock.advance()
        self.world.current_tick = self.clock.current_tick

        return results

    def run(
        self,
        max_ticks: int = 5,
        stop_on_resolution: bool = False,
        hard_cap: Optional[int] = None,
        use_sufficiency_gate: bool = False,
    ) -> List[ActionResult]:
        """Execute multiple steps until max_ticks, hard_cap, or sufficiency gate termination."""
        all_results: List[ActionResult] = []
        current_budget = max_ticks
        self.total_ticks = current_budget
        effective_hard_cap = hard_cap if hard_cap is not None else max(max_ticks, 100)

        while self.world.current_tick < current_budget and self.world.current_tick < effective_hard_cap:
            if self._is_paused:
                break
            tick_results = self.step()
            all_results.extend(tick_results)

            if stop_on_resolution and self.scene_resolution_status:
                break

            # Repetition loop mitigation: if 6 identical consecutive actions occur across actors
            if len(self._recent_action_signatures) >= 6:
                last_six = self._recent_action_signatures[-6:]
                if len(set(last_six)) <= 1:
                    self._stagnation_count += 3
                    break

            # Narrative Sufficiency Gate evaluation
            if use_sufficiency_gate and self.blueprint:
                report = self.sufficiency_gate.evaluate(
                    self.blueprint,
                    self.world,
                    self.world.current_tick,
                    current_budget,
                    effective_hard_cap,
                )
                self.last_sufficiency_report = report

                if report.recommendation == "PROCEED":
                    break
                elif report.recommendation == "HALT_INSUFFICIENT":
                    break
                elif report.recommendation == "ADJUST_PRESSURE_AND_CONTINUE":
                    old_budget = current_budget
                    increment = self.sufficiency_gate.extension_increment_ticks
                    current_budget = min(effective_hard_cap, current_budget + increment)
                    self.total_ticks = current_budget
                    # Window recomputation for still PENDING beats (§B.4)
                    ext_ratio = current_budget / max(1, old_budget)
                    for beat in self.blueprint.beats:
                        if beat.status == "PENDING":
                            beat.target_window = (
                                beat.target_window[0],
                                min(1.0, beat.target_window[1] * ext_ratio),
                            )

        if use_sufficiency_gate and self.blueprint and not self.last_sufficiency_report:
            self.last_sufficiency_report = self.sufficiency_gate.evaluate(
                self.blueprint,
                self.world,
                self.world.current_tick,
                current_budget,
                effective_hard_cap,
            )

        return all_results

    def get_event_log(self) -> EventLog:
        """Retrieve the immutable EventLog from the recorder"""
        return self.recorder.get_event_log()

    def _apply_cognitive_effects(self, actor_id: str, proposal: ActionProposal, result: ActionResult):
        """Deterministically evolve beliefs, memories, relationships, and emotions from actions"""
        actor = self.world.characters[actor_id]

        if proposal.action_type == ActionType.SPEAK:
            dialogue = proposal.parameters.get("dialogue", "")
            target_id = proposal.target_id
            social_intent = proposal.parameters.get("social_intent", "speak")
            topic = proposal.parameters.get("topic", "the situation")

            if target_id and target_id in self.world.characters:
                recipient = self.world.characters[target_id]

                # 1. Memory formation for recipient
                self.memory_service.form_memory(
                    character_id=recipient.id,
                    summary=f"{actor.name} said to me: '{dialogue}'",
                    importance=0.75,
                    emotional_weight=0.1,
                    participants=[actor.id],
                    tags=["dialogue", actor.id, social_intent, topic],
                )

                # 2. Contradiction & Lie Detection
                # Check recipient's memories for contradictory observations
                recipient_mems = [
                    m.summary.lower() for m in self.world.get_character_memories(recipient.id)
                ]
                contradiction_found = False
                if social_intent in ("deny", "lie") or "never" in dialogue.lower() or "nothing" in dialogue.lower():
                    # If dialogue denies something, check if recipient observed otherwise
                    for m_text in recipient_mems:
                        if actor.name.lower() in m_text and (topic in m_text or "pick up" in m_text or "examined" in m_text):
                            contradiction_found = True
                            break

                ev_id = result.events_created[0] if result.events_created else None

                if contradiction_found:
                    # Recipient realizes actor is lying
                    BeliefUpdater.form_or_reinforce_belief(
                        self.world,
                        character_id=recipient.id,
                        statement=f"{actor.name} is lying about {topic}",
                        confidence_delta=0.4,
                    )
                    RelationshipUpdater.apply_interaction(
                        self.world,
                        recipient.id,
                        actor.id,
                        delta_trust=-0.25,
                        delta_affinity=-0.20,
                        delta_suspicion=0.30,
                        delta_resentment=0.20,
                        note=f"Caught lying about {topic}",
                        event_id=ev_id,
                    )
                    EmotionUpdater.adjust_emotion(recipient, delta_anger=0.25, delta_fear=0.1)
                else:
                    # Normal belief update
                    confidence_delta = 0.15
                    rel = self.world.get_relationship(recipient.id, actor.id)
                    if rel and rel.trust < 0:
                        confidence_delta = 0.05

                    BeliefUpdater.form_or_reinforce_belief(
                        self.world,
                        character_id=recipient.id,
                        statement=f"{actor.name} claims: {dialogue[:40]}",
                        confidence_delta=confidence_delta,
                    )

                    # Relationship and emotion evolution based on intent
                    if social_intent == "accuse":
                        has_secret = any(topic in s.statement.lower() for s in self.world.get_character_secrets(recipient.id))
                        if has_secret:
                            EmotionUpdater.adjust_emotion(recipient, delta_fear=0.3, delta_happiness=-0.2)
                            RelationshipUpdater.apply_interaction(
                                self.world,
                                recipient.id,
                                actor.id,
                                delta_trust=-0.15,
                                delta_fear=0.20,
                                delta_suspicion=0.25,
                                delta_resentment=0.20,
                                note="Accused with secret",
                                event_id=ev_id,
                            )
                        else:
                            EmotionUpdater.adjust_emotion(recipient, delta_anger=0.25)
                            RelationshipUpdater.apply_interaction(
                                self.world,
                                recipient.id,
                                actor.id,
                                delta_trust=-0.1,
                                delta_resentment=0.25,
                                delta_suspicion=0.15,
                                note="Falsely accused",
                                event_id=ev_id,
                            )
                    elif social_intent == "cooperate":
                        RelationshipUpdater.apply_interaction(
                            self.world,
                            recipient.id,
                            actor.id,
                            delta_trust=0.1,
                            delta_affinity=0.1,
                            delta_affection=0.1,
                            delta_respect=0.1,
                            note="Cooperation offered",
                            event_id=ev_id,
                        )
                        EmotionUpdater.adjust_emotion(recipient, delta_happiness=0.1)
                    elif social_intent == "warn":
                        EmotionUpdater.adjust_emotion(recipient, delta_fear=0.2, delta_curiosity=0.2)
                    else:
                        RelationshipUpdater.apply_interaction(
                            self.world,
                            recipient.id,
                            actor.id,
                            delta_trust=0.05,
                            delta_respect=0.05,
                            note="Conversation",
                            event_id=ev_id,
                        )

        elif proposal.action_type in (ActionType.TAKE_OBJECT, ActionType.PICKUP):
            obj_id = proposal.target_id
            obj = self.world.objects.get(obj_id)
            obj_name = obj.name if obj else "an item"

            # Actor memory
            self.memory_service.form_memory(
                character_id=actor.id,
                summary=f"I picked up the {obj_name}.",
                importance=0.8,
                emotional_weight=0.2,
                tags=["take_object", obj_id],
            )

            # Observers in same room
            for other_char in self.world.characters.values():
                if other_char.id != actor.id and other_char.current_location_id == actor.current_location_id:
                    self.memory_service.form_memory(
                        character_id=other_char.id,
                        summary=f"I saw {actor.name} pick up the {obj_name}.",
                        importance=0.85,
                        emotional_weight=0.3,
                        participants=[actor.id],
                        tags=["action_observation", obj_id, actor.id],
                    )
                    BeliefUpdater.form_or_reinforce_belief(
                        self.world,
                        character_id=other_char.id,
                        statement=f"{actor.name} possesses the {obj_name}",
                        confidence_delta=0.4,
                    )
                    EmotionUpdater.adjust_emotion(other_char, delta_curiosity=0.25)

        elif proposal.action_type in (ActionType.INSPECT_OBJECT, ActionType.OBSERVE):
            target_id = proposal.target_id
            target_obj = self.world.objects.get(target_id)
            target_char = self.world.characters.get(target_id)
            target_name = target_obj.name if target_obj else (target_char.name if target_char else target_id)

            self.memory_service.form_memory(
                character_id=actor.id,
                summary=f"I closely inspected the {target_name}.",
                importance=0.6,
                emotional_weight=0.1,
                tags=["inspect", str(target_id)],
            )
            if target_obj:
                BeliefUpdater.form_or_reinforce_belief(
                    self.world,
                    character_id=actor.id,
                    statement=f"{target_obj.name} is {target_obj.description[:40]}",
                    confidence_delta=0.3,
                )
            EmotionUpdater.adjust_emotion(actor, delta_curiosity=-0.1)

        elif proposal.action_type in (ActionType.OPEN_OBJECT, ActionType.CLOSE_OBJECT):
            target_id = proposal.target_id
            obj = self.world.objects.get(target_id)
            verb = "opened" if proposal.action_type == ActionType.OPEN_OBJECT else "closed"
            obj_name = obj.name if obj else "container"

            self.memory_service.form_memory(
                character_id=actor.id,
                summary=f"I {verb} the {obj_name}.",
                importance=0.65,
                emotional_weight=0.1,
                tags=[verb, str(target_id)],
            )
            for other_char in self.world.characters.values():
                if other_char.id != actor.id and other_char.current_location_id == actor.current_location_id:
                    self.memory_service.form_memory(
                        character_id=other_char.id,
                        summary=f"I saw {actor.name} {verb} the {obj_name}.",
                        importance=0.7,
                        emotional_weight=0.1,
                        participants=[actor.id],
                        tags=["action_observation", str(target_id)],
                    )

        elif proposal.action_type == ActionType.MOVE:
            dest_id = proposal.location_id or proposal.parameters.get("destination_id")
            dest_loc = self.world.locations.get(dest_id)
            dest_name = dest_loc.name if dest_loc else dest_id
            self.memory_service.form_memory(
                character_id=actor.id,
                summary=f"I moved to {dest_name}.",
                importance=0.5,
                emotional_weight=0.0,
                tags=["move", str(dest_id)],
            )

        # 6. Advance character goals based on consequences
        actor_goals = self.world.get_character_goals(actor.id)
        for goal in actor_goals:
            if goal.status == GoalStatus.ACTIVE:
                if proposal.action_type in (ActionType.INSPECT_OBJECT, ActionType.OBSERVE):
                    target_obj = self.world.objects.get(proposal.target_id)
                    if target_obj and any(w in goal.description.lower() for w in target_obj.name.lower().split()):
                        goal.progress = min(1.0, round(goal.progress + 0.35, 2))
                        goal.last_progress_tick = self.world.current_tick
                        if goal.progress >= 1.0:
                            goal.status = GoalStatus.ACHIEVED
                            self.scene_resolution_status = f"GOAL_ACHIEVED: {actor.name} accomplished '{goal.description}'"

                elif proposal.action_type == ActionType.SPEAK:
                    social_intent = proposal.parameters.get("social_intent") or proposal.parameters.get("speech_act")
                    if social_intent == "reveal":
                        goal.progress = 1.0
                        goal.status = GoalStatus.ACHIEVED
                        self.scene_resolution_status = "CRITICAL_SECRET_REVEALED: Truth uncovered"
                    elif social_intent in ("answer", "cooperate", "accuse"):
                        goal.progress = min(1.0, round(goal.progress + 0.20, 2))
                        goal.last_progress_tick = self.world.current_tick
                        if goal.progress >= 1.0:
                            goal.status = GoalStatus.ACHIEVED
