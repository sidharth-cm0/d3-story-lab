"""Observer agent for D3 Story Lab.

The Observer monitors the immutable Event log, scores dramatic significance,
filters mundane noise, and clusters related events into cohesive narrative beats
while maintaining strict provenance (source_event_ids).
"""

from __future__ import annotations
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field

from src.domain.event import Event, EventType
from src.domain.world import WorldState
from src.providers.base import LLMProvider


class NarrativeBeatType(str, Enum):
    """Dramatic classification for a narrative beat."""
    ESTABLISHING = "establishing"
    INCITING_INCIDENT = "inciting_incident"
    RISING_ACTION = "rising_action"
    CONFRONTATION = "confrontation"
    REVELATION = "revelation"
    CRISIS = "crisis"
    RESOLUTION = "resolution"
    TRANSITION = "transition"


class NarrativeBeat(BaseModel):
    """A cohesive narrative beat composed of one or more source events."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(default_factory=lambda: f"beat_{uuid.uuid4().hex[:8]}")
    beat_type: NarrativeBeatType = NarrativeBeatType.RISING_ACTION
    start_tick: int
    end_tick: int
    location_id: str
    character_ids: list[str] = Field(default_factory=list)
    dramatic_score: float = Field(ge=0.0, le=1.0)
    summary: str
    source_event_ids: list[str] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NarrativeEventSelection(BaseModel):
    """Collection of narrative beats filtered from the event stream."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_events_observed: int
    filtered_beats: list[NarrativeBeat] = Field(default_factory=list)
    dramatic_arc_summary: str = ""
    tension_progression: list[float] = Field(default_factory=list)


class Observer:
    """Monitors events, filters noise, and groups significant events into narrative beats."""

    def __init__(self, provider: LLMProvider | None = None, min_significance_threshold: float = 0.25):
        self.provider = provider
        self.min_significance_threshold = min_significance_threshold

    def score_event(self, event: Event) -> float:
        """Deterministically calculate dramatic significance of an event."""
        scores: dict[EventType, float] = {
            EventType.CHARACTER_SPOKE: 0.65,
            EventType.CHARACTER_MOVED: 0.35,
            EventType.OBJECT_PICKED_UP: 0.55,
            EventType.OBJECT_DROPPED: 0.35,
            EventType.OBJECT_GIVEN: 0.60,
            EventType.DOOR_OPENED: 0.45,
            EventType.DOOR_CLOSED: 0.30,
            EventType.CHARACTER_OBSERVED: 0.40,
            EventType.EMOTION_CHANGED: 0.50,
            EventType.BELIEF_FORMED: 0.45,
            EventType.MEMORY_CREATED: 0.40,
            EventType.RELATIONSHIP_CHANGED: 0.60,
            EventType.OTHER: 0.50,
        }

        base_score = scores.get(event.event_type, 0.4)

        desc = event.description.lower()
        if any(w in desc for w in ["secret", "document", "ledger", "stolen", "lie", "confront", "truth", "arrest", "kill"]):
            base_score = min(1.0, base_score + 0.25)
        elif any(w in desc for w in ["knock", "phone", "urgent", "door", "sudden", "warning"]):
            base_score = min(1.0, base_score + 0.20)

        # De-emphasize idle wait descriptions
        if "wait" in desc or "pauses" in desc:
            base_score = 0.10

        return round(base_score, 3)

    def classify_beat_type(self, events: list[Event], avg_score: float) -> NarrativeBeatType:
        """Infer beat type from clustered events."""
        event_types = {e.event_type for e in events}
        descriptions = " ".join(e.description.lower() for e in events)

        if "confess" in descriptions or "reveal" in descriptions or "secret" in descriptions:
            return NarrativeBeatType.REVELATION
        if "knock" in descriptions or "phone" in descriptions or any("incident_type" in e.metadata for e in events):
            return NarrativeBeatType.INCITING_INCIDENT
        if "confront" in descriptions or "demand" in descriptions or "accuse" in descriptions:
            return NarrativeBeatType.CONFRONTATION
        if avg_score >= 0.85:
            return NarrativeBeatType.CRISIS
        if all(e.event_type == EventType.CHARACTER_MOVED for e in events):
            return NarrativeBeatType.TRANSITION
        if events[0].tick == 0 or "enter" in descriptions:
            return NarrativeBeatType.ESTABLISHING

        return NarrativeBeatType.RISING_ACTION

    def observe_events(
        self,
        events: list[Event],
        world: WorldState | None = None,
    ) -> NarrativeEventSelection:
        """Filter and cluster raw simulation events into dramatic beats."""
        if not events:
            return NarrativeEventSelection(
                total_events_observed=0,
                filtered_beats=[],
                dramatic_arc_summary="No events to observe.",
                tension_progression=[],
            )

        scored_events: list[tuple[Event, float]] = []
        for ev in events:
            score = self.score_event(ev)
            if score >= self.min_significance_threshold:
                scored_events.append((ev, score))

        if not scored_events:
            best_event = max(events, key=self.score_event)
            scored_events.append((best_event, self.score_event(best_event)))

        clusters: list[list[tuple[Event, float]]] = []
        current_cluster: list[tuple[Event, float]] = [scored_events[0]]

        for item in scored_events[1:]:
            prev_ev, _ = current_cluster[-1]
            curr_ev, _ = item

            same_location = (curr_ev.location_id == prev_ev.location_id)
            near_in_time = (curr_ev.tick - prev_ev.tick <= 2)
            both_dialogue = (curr_ev.event_type == EventType.CHARACTER_SPOKE and prev_ev.event_type == EventType.CHARACTER_SPOKE)
            both_object = (curr_ev.event_type in (EventType.OBJECT_PICKED_UP, EventType.OBJECT_DROPPED, EventType.OBJECT_GIVEN)
                           and prev_ev.event_type in (EventType.OBJECT_PICKED_UP, EventType.OBJECT_DROPPED, EventType.OBJECT_GIVEN))
            both_movement = (curr_ev.event_type == EventType.CHARACTER_MOVED and prev_ev.event_type == EventType.CHARACTER_MOVED)

            can_cluster = near_in_time and (
                (same_location and (both_dialogue or both_object))
                or both_movement
            )

            if can_cluster:
                current_cluster.append(item)
            else:
                clusters.append(current_cluster)
                current_cluster = [item]

        if current_cluster:
            clusters.append(current_cluster)

        beats: list[NarrativeBeat] = []
        tension_progression: list[float] = []

        for cluster in clusters:
            evs = [ev for ev, _ in cluster]
            scores = [sc for _, sc in cluster]
            avg_score = round(sum(scores) / len(scores), 3)

            start_tick = min(e.tick for e in evs)
            end_tick = max(e.tick for e in evs)
            location_id = evs[0].location_id or "unknown"
            character_ids = sorted(list({actor for e in evs for actor in e.actor_ids}))
            source_event_ids = [e.id for e in evs]

            beat_type = self.classify_beat_type(evs, avg_score)

            if len(evs) == 1:
                summary = evs[0].description
            else:
                summary = f"{evs[0].description} followed by: {'; '.join(e.description for e in evs[1:])}"

            beat = NarrativeBeat(
                beat_type=beat_type,
                start_tick=start_tick,
                end_tick=end_tick,
                location_id=location_id,
                character_ids=character_ids,
                dramatic_score=avg_score,
                summary=summary,
                source_event_ids=source_event_ids,
                metadata={"event_count": len(evs)},
            )
            beats.append(beat)
            tension_progression.append(avg_score)

        arc_summary = f"Simulated {len(events)} events yielding {len(beats)} dramatic narrative beats across ticks {events[0].tick} to {events[-1].tick}."

        return NarrativeEventSelection(
            total_events_observed=len(events),
            filtered_beats=beats,
            dramatic_arc_summary=arc_summary,
            tension_progression=tension_progression,
        )
