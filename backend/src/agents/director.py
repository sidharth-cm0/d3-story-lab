"""Director Agent for monitoring scene pacing, tension, and applying bounded environmental pressure."""
from __future__ import annotations
from typing import Optional, List, Dict, Any, Tuple, Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..domain import (
    WorldState,
    Event,
    EventType,
    ActionType,
    ActionProposal,
    Motivation,
)
from ..simulation.recorder import EventRecorder
from enum import Enum
from ..simulation.actions import ActionValidator
from ..story.models import (
    StoryBlueprint,
    BeatPressure,
    DramaticFunction,
)

class DirectorInterventionType(str, Enum):
    """Types of external environmental events the Director can inject."""
    # Environmental tension injections
    KNOCK_ON_DOOR = "knock_on_door"
    PHONE_RING = "phone_ring"
    POWER_FAILURE = "power_failure"
    NEW_INFORMATION = "new_information"
    TIME_PRESSURE = "time_pressure"
    SECURITY_ARRIVAL = "security_arrival"
    ALARM = "alarm"

    # Canonical Phase 4 Director interventions (§B.5)
    INTRODUCE_OBSTACLE = "INTRODUCE_OBSTACLE"
    CHANGE_DOOR_STATE = "CHANGE_DOOR_STATE"
    MOVE_NPC = "MOVE_NPC"
    REVEAL_CLUE = "REVEAL_CLUE"
    ANNOUNCE_DEADLINE = "ANNOUNCE_DEADLINE"
    ENVIRONMENTAL_EVENT = "ENVIRONMENTAL_EVENT"
    INCREASE_TIME_PRESSURE = "INCREASE_TIME_PRESSURE"


class DirectorIntervention(BaseModel):
    """An external event intervention decided by the Director.

    Cannot be constructed outside the allowed DirectorIntervention enum.
    """
    model_config = ConfigDict(frozen=True)

    intervention_type: DirectorInterventionType
    description: str
    target_location_id: Optional[str] = None
    target_entity_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DirectorAgent:
    """Monitors scene tension, repetition, and pacing, injecting environmental pressures without puppeteering characters.

    The Director is NOT privileged: its interventions pass through the exact same
    ActionValidator as character actions.
    """

    def __init__(
        self,
        inactivity_threshold: int = 3,
        blueprint: Optional[StoryBlueprint] = None,
        target_ticks: int = 20,
        max_interventions_total: int = 5,
        min_ticks_between_interventions: int = 3,
        evaluation_interval_ticks: int = 5,
    ):
        self.inactivity_threshold = inactivity_threshold
        self.blueprint = blueprint
        self.target_ticks = target_ticks
        self.max_interventions_total = max_interventions_total
        self.min_ticks_between_interventions = min_ticks_between_interventions
        self.evaluation_interval_ticks = evaluation_interval_ticks
        self.last_intervention_tick = -999
        self.interventions_history: List[DirectorIntervention] = []
        self._escalated_beats: set[str] = set()

    def can_intervene(self, current_tick: int) -> bool:
        """Check if Director is within total budget and pacing cooldown."""
        if len(self.interventions_history) >= self.max_interventions_total:
            return False
        if (current_tick - self.last_intervention_tick) < self.min_ticks_between_interventions:
            return False
        return True

    def create_action_proposal(
        self,
        intervention: DirectorIntervention,
        world: WorldState,
    ) -> ActionProposal:
        """Convert an intervention into a standard ActionProposal for validator gate check."""
        action_type = ActionType.INTERACT
        target = intervention.target_entity_id

        if intervention.intervention_type == "CHANGE_DOOR_STATE":
            action_type = ActionType.OPEN_OBJECT
        elif intervention.intervention_type == "MOVE_NPC":
            action_type = ActionType.MOVE

        return ActionProposal(
            id=f"prop_dir_{world.current_tick}_{len(self.interventions_history)}",
            actor_id="DIRECTOR",
            action_type=action_type,
            target_id=target,
            location_id=intervention.target_location_id,
            tick_proposed=world.current_tick,
            motivation=Motivation(kind="PURSUE_GOAL", goal_id="director_pacing"),
            parameters={
                "intervention_type": intervention.intervention_type,
                "description": intervention.description,
                "target_entity_id": intervention.target_entity_id,
                **intervention.metadata,
            },
            reason=intervention.description,
        )

    def get_current_blueprint_pressure(self, current_tick: int) -> Optional[str]:
        """Read the soft pressure signal for the current normalized progress point."""
        if not self.blueprint:
            return None
        if hasattr(self.blueprint, "expected_beats") and self.blueprint.expected_beats:
            norm_pos = min(1.0, current_tick / max(1, self.target_ticks))
            closest_beat = min(
                self.blueprint.expected_beats,
                key=lambda b: abs(b.target_position_pct - norm_pos),
            )
            return getattr(closest_beat, "pressure_signal", None)
        return None

    def evaluate_pacing(
        self,
        world: WorldState,
        inactivity_count: int = 0,
        stagnation_count: int = 0,
    ) -> Optional[DirectorIntervention]:
        """Evaluate if external event injection is needed due to scene inactivity or stagnation."""
        if not self.can_intervene(world.current_tick):
            return None

        # If characters have been idle/waiting or scene has stalled
        if inactivity_count >= self.inactivity_threshold or stagnation_count >= 3:
            target_loc_id = None
            for char in world.characters.values():
                if char.current_location_id:
                    target_loc_id = char.current_location_id
                    break
            if not target_loc_id:
                target_loc_id = next(iter(world.locations.keys()), "loc_room307")

            pressure_sig = self.get_current_blueprint_pressure(world.current_tick)
            meta_extra = {"blueprint_pressure_signal": pressure_sig} if pressure_sig else {}

            step = len(self.interventions_history) % 4
            if step == 0:
                return DirectorIntervention(
                    intervention_type=DirectorInterventionType.KNOCK_ON_DOOR,
                    description="A sharp, insistent knock echoes from the hallway outside the door.",
                    target_location_id=target_loc_id,
                    metadata={"urgency": "high", "incident_type": "KNOCK_ON_DOOR", **meta_extra},
                )
            elif step == 1:
                return DirectorIntervention(
                    intervention_type=DirectorInterventionType.PHONE_RING,
                    description="The room phone suddenly blares with an incoming outside call.",
                    target_location_id=target_loc_id,
                    metadata={"urgency": "medium", "incident_type": "PHONE_RING", **meta_extra},
                )
            elif step == 2:
                return DirectorIntervention(
                    intervention_type=DirectorInterventionType.POWER_FAILURE,
                    description="The overhead lights flicker violently and plunge the room into dim emergency backup lighting.",
                    target_location_id=target_loc_id,
                    metadata={"urgency": "high", "incident_type": "POWER_FAILURE", **meta_extra},
                )
            else:
                return DirectorIntervention(
                    intervention_type=DirectorInterventionType.ALARM,
                    description="A muted security alarm begins pulsing from the hallway.",
                    target_location_id=target_loc_id,
                    metadata={"urgency": "high", "incident_type": "ALARM", **meta_extra},
                )

        return None

    def inject_intervention(
        self,
        world: WorldState,
        recorder: EventRecorder,
        intervention: DirectorIntervention,
        validator: Optional[ActionValidator] = None,
    ) -> Optional[Event]:
        """Validate and canonically log the director's external event.

        Goes through the exact same four validator gates as character actions.
        """
        if not self.can_intervene(world.current_tick):
            return None

        # Pass through ActionValidator
        if validator is not None:
            proposal = self.create_action_proposal(intervention, world)
            valid, err, gate = validator.validate_proposal(world, proposal)
            if not valid:
                # Rejected by validator gates identical to character actions
                return None

        int_val = (
            intervention.intervention_type.value
            if hasattr(intervention.intervention_type, "value")
            else str(intervention.intervention_type)
        )
        event = recorder.record_event(
            event_type=EventType.OTHER,
            description=intervention.description,
            actor_ids=[],  # Director interventions have no character actor
            location_id=intervention.target_location_id,
            source="DIRECTOR",
            metadata={
                "source": "DIRECTOR",
                "director_intervention": int_val,
                "incident_type": intervention.metadata.get("incident_type", int_val),
                **intervention.metadata,
            },
        )
        self.interventions_history.append(intervention)
        self.last_intervention_tick = world.current_tick
        return event

    def evaluate_beat_escalation(
        self,
        world: WorldState,
        recorder: EventRecorder,
        validator: ActionValidator,
        total_ticks: int,
    ) -> List[Event]:
        """Evaluate active beats against their normalized target windows and ladder."""
        if not self.blueprint:
            return []

        events: List[Event] = []
        current_tick = world.current_tick

        for beat in self.blueprint.beats:
            if beat.status not in ("PENDING", "PARTIAL"):
                continue

            win_start = int(beat.target_window[0] * total_ticks)
            win_end = int(beat.target_window[1] * total_ticks)

            # Check if within window
            if win_start <= current_tick <= win_end:
                win_len = max(1, win_end - win_start)
                progress = (current_tick - win_start) / win_len

                # If progress >= 0.6 and not yet escalated and budget allows
                if progress >= 0.6 and beat.beat_id not in self._escalated_beats:
                    if self.can_intervene(current_tick) and beat.escalation_ladder:
                        # Climb one rung of the ladder
                        intervention_type = beat.escalation_ladder[0]
                        loc_id = next(iter(world.locations.keys()), "loc_warehouse")
                        interv = DirectorIntervention(
                            intervention_type=intervention_type,
                            description=f"Director intervention: {intervention_type} to pressure beat '{beat.beat_id}'",
                            target_location_id=loc_id,
                            metadata={"target_beat_id": beat.beat_id},
                        )
                        evt = self.inject_intervention(world, recorder, interv, validator=validator)
                        if evt:
                            events.append(evt)
                            self._escalated_beats.add(beat.beat_id)

            # Check if window has fully closed without satisfaction
            elif current_tick > win_end and beat.status == "PENDING":
                beat.status = "UNSATISFIED"
                beat.deviation_note = (
                    f"Beat window [{beat.target_window[0]:.2f}, {beat.target_window[1]:.2f}] "
                    f"closed at tick {current_tick} without satisfaction predicate being met."
                )

        return events
