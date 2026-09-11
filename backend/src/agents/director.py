"""Director Agent for monitoring scene pacing, tension, and environmental pressure."""

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from ..domain import WorldState, Event, EventType
from ..simulation.recorder import EventRecorder


class DirectorInterventionType(str, Enum):
    """Types of external environmental events the Director can inject"""

    KNOCK_ON_DOOR = "knock_on_door"
    PHONE_RING = "phone_ring"
    POWER_FAILURE = "power_failure"
    NEW_INFORMATION = "new_information"
    TIME_PRESSURE = "time_pressure"
    SECURITY_ARRIVAL = "security_arrival"
    ALARM = "alarm"


class DirectorIntervention(BaseModel):
    """An external event intervention decided by the Director"""

    intervention_type: DirectorInterventionType
    description: str
    target_location_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class DirectorAgent:
    """Monitors scene tension, repetition, and pacing, injecting environmental pressures without puppeteering characters"""

    def __init__(self, inactivity_threshold: int = 3):
        self.inactivity_threshold = inactivity_threshold
        self.interventions_history: List[DirectorIntervention] = []

    def evaluate_pacing(
        self,
        world: WorldState,
        inactivity_count: int,
        stagnation_count: int = 0,
    ) -> Optional[DirectorIntervention]:
        """Evaluate if external pressure is needed based on inactivity or semantic stagnation"""
        # If characters have been idle/waiting or scene has stalled
        if inactivity_count >= self.inactivity_threshold or stagnation_count >= 3:
            # Target location where characters are currently located
            target_loc_id = None
            for char in world.characters.values():
                if char.current_location_id:
                    target_loc_id = char.current_location_id
                    break
            if not target_loc_id:
                target_loc_id = next(iter(world.locations.keys()), "loc_room307")

            step = len(self.interventions_history) % 4
            if step == 0:
                return DirectorIntervention(
                    intervention_type=DirectorInterventionType.KNOCK_ON_DOOR,
                    description="A sharp, insistent knock echoes from the hallway outside the door.",
                    target_location_id=target_loc_id,
                    metadata={"urgency": "high", "incident_type": "KNOCK_ON_DOOR"},
                )
            elif step == 1:
                return DirectorIntervention(
                    intervention_type=DirectorInterventionType.PHONE_RING,
                    description="The room phone suddenly blares with an incoming outside call.",
                    target_location_id=target_loc_id,
                    metadata={"urgency": "medium", "incident_type": "PHONE_RING"},
                )
            elif step == 2:
                return DirectorIntervention(
                    intervention_type=DirectorInterventionType.POWER_FAILURE,
                    description="The overhead lights flicker violently and plunge the room into dim emergency backup lighting.",
                    target_location_id=target_loc_id,
                    metadata={"urgency": "high", "incident_type": "POWER_FAILURE"},
                )
            else:
                return DirectorIntervention(
                    intervention_type=DirectorInterventionType.ALARM,
                    description="A muted security alarm begins pulsing from the hallway.",
                    target_location_id=target_loc_id,
                    metadata={"urgency": "high", "incident_type": "ALARM"},
                )

        return None

    def inject_intervention(
        self,
        world: WorldState,
        recorder: EventRecorder,
        intervention: DirectorIntervention,
    ) -> Event:
        """Canonically log the director's external event into WorldState"""
        event = recorder.record_event(
            event_type=EventType.OTHER,
            description=intervention.description,
            actor_ids=[],  # Director interventions have no character actor
            location_id=intervention.target_location_id,
            metadata={
                "director_intervention": intervention.intervention_type.value,
                "incident_type": intervention.metadata.get("incident_type", intervention.intervention_type.value),
                **intervention.metadata,
            },
        )
        self.interventions_history.append(intervention)
        return event
