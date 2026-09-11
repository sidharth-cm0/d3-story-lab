"""Tests for Observer narrative intelligence layer."""

import pytest
from src.domain.event import Event, EventType
from src.narrative.observer import Observer, NarrativeBeatType


class TestObserver:
    @pytest.fixture
    def sample_events(self) -> list[Event]:
        return [
            Event(
                id="evt_0",
                tick=0,
                event_type=EventType.CHARACTER_MOVED,
                actor_ids=["char_maya"],
                location_id="loc_penthouse",
                description="Maya enters the Penthouse.",
                metadata={},
            ),
            Event(
                id="evt_1",
                tick=1,
                event_type=EventType.OTHER,
                actor_ids=["char_maya"],
                location_id="loc_penthouse",
                description="Maya pauses and looks around.",
                metadata={},
            ),
            Event(
                id="evt_2",
                tick=2,
                event_type=EventType.CHARACTER_SPOKE,
                actor_ids=["char_maya", "char_arjun"],
                location_id="loc_penthouse",
                description="Maya says: 'Where is the ledger, Arjun?'",
                metadata={"dialogue": "Where is the ledger, Arjun?"},
            ),
            Event(
                id="evt_3",
                tick=3,
                event_type=EventType.CHARACTER_SPOKE,
                actor_ids=["char_arjun", "char_maya"],
                location_id="loc_penthouse",
                description="Arjun says: 'I don't know what you're talking about.'",
                metadata={"dialogue": "I don't know what you're talking about."},
            ),
            Event(
                id="evt_4",
                tick=5,
                event_type=EventType.OTHER,
                actor_ids=[],
                location_id="loc_penthouse",
                description="A sudden loud knock bangs against the suite door.",
                metadata={"incident_type": "KNOCK_ON_DOOR"},
            ),
            Event(
                id="evt_5",
                tick=7,
                event_type=EventType.CHARACTER_MOVED,
                actor_ids=["char_arjun"],
                location_id="loc_lobby",
                description="Arjun moves to the Hotel Lobby.",
                metadata={},
            ),
        ]

    def test_score_event_distinguishes_significance(self):
        observer = Observer()
        idle_event = Event(id="e1", tick=1, event_type=EventType.OTHER, description="Arjun pauses and waits.")
        confront_event = Event(id="e2", tick=2, event_type=EventType.CHARACTER_SPOKE, description="Maya confronts Arjun about the secret ledger.")
        director_event = Event(id="e3", tick=3, event_type=EventType.OTHER, description="A sudden loud knock on the door.", metadata={"incident_type": "KNOCK_ON_DOOR"})

        score_idle = observer.score_event(idle_event)
        score_confront = observer.score_event(confront_event)
        score_director = observer.score_event(director_event)

        assert score_idle < 0.25
        assert score_confront >= 0.8
        assert score_director >= 0.6

    def test_observe_events_filters_and_clusters(self, sample_events):
        observer = Observer(min_significance_threshold=0.25)
        selection = observer.observe_events(sample_events)

        assert selection.total_events_observed == 6
        assert len(selection.filtered_beats) >= 2

        # Verify the dialogue events (tick 2 and 3) clustered together
        dialogue_beat = next(
            (b for b in selection.filtered_beats if "char_maya" in b.character_ids and "char_arjun" in b.character_ids and len(b.source_event_ids) >= 2),
            None
        )
        assert dialogue_beat is not None
        assert len(dialogue_beat.source_event_ids) == 2
        assert dialogue_beat.start_tick == 2
        assert dialogue_beat.end_tick == 3
        assert dialogue_beat.location_id == "loc_penthouse"

    def test_observer_provenance_integrity(self, sample_events):
        observer = Observer()
        selection = observer.observe_events(sample_events)

        all_source_ids = {eid for beat in selection.filtered_beats for eid in beat.source_event_ids}
        raw_event_ids = {e.id for e in sample_events}

        # Every source event referenced must exist in original events
        assert all_source_ids.issubset(raw_event_ids)

    def test_empty_events(self):
        observer = Observer()
        selection = observer.observe_events([])
        assert selection.total_events_observed == 0
        assert selection.filtered_beats == []
