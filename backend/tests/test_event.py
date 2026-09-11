"""Tests for Event domain model"""
import pytest
import json
from pydantic import ValidationError
from src.domain import Event, EventType


class TestEventCreation:
    """Tests for Event creation"""

    def test_basic_event_creation(self):
        """Test creating a basic event"""
        event = Event(
            id="evt_001",
            tick=1,
            event_type=EventType.CHARACTER_MOVED,
            description="Character moved to new location",
        )
        assert event.id == "evt_001"
        assert event.tick == 1
        assert event.event_type == EventType.CHARACTER_MOVED
        assert len(event.actor_ids) == 0

    def test_event_with_actors_and_location(self):
        """Test event with actor and location"""
        event = Event(
            id="evt_002",
            tick=2,
            event_type=EventType.CHARACTER_SPOKE,
            actor_ids=["char_001", "char_002"],
            location_id="loc_001",
            description="Two characters had a conversation",
        )
        assert len(event.actor_ids) == 2
        assert "char_001" in event.actor_ids
        assert event.location_id == "loc_001"

    def test_event_with_metadata(self):
        """Test event with metadata"""
        metadata = {
            "from_location": "loc_001",
            "to_location": "loc_002",
            "distance": 10,
        }
        event = Event(
            id="evt_003",
            tick=3,
            event_type=EventType.CHARACTER_MOVED,
            description="Character traveled",
            metadata=metadata,
        )
        assert event.metadata["from_location"] == "loc_001"
        assert event.metadata["distance"] == 10

    def test_all_event_types(self):
        """Test that all event types can be created"""
        event_types = [
            EventType.CHARACTER_MOVED,
            EventType.OBJECT_PICKED_UP,
            EventType.OBJECT_DROPPED,
            EventType.CHARACTER_SPOKE,
            EventType.OBJECT_GIVEN,
            EventType.DOOR_OPENED,
            EventType.DOOR_CLOSED,
            EventType.CHARACTER_OBSERVED,
            EventType.EMOTION_CHANGED,
            EventType.BELIEF_FORMED,
            EventType.MEMORY_CREATED,
            EventType.RELATIONSHIP_CHANGED,
            EventType.OTHER,
        ]

        for event_type in event_types:
            event = Event(
                id=f"evt_{event_type.value}",
                tick=0,
                event_type=event_type,
                description=f"Event of type {event_type.value}",
            )
            assert event.event_type == event_type

    def test_event_tick_validation(self):
        """Test that tick must be non-negative"""
        # Valid
        event = Event(
            id="evt_001",
            tick=0,
            event_type=EventType.OTHER,
            description="Test",
        )
        assert event.tick == 0

        # Valid large number
        event_large = Event(
            id="evt_002",
            tick=1000000,
            event_type=EventType.OTHER,
            description="Test",
        )
        assert event_large.tick == 1000000

    def test_event_json_serialization(self):
        """Test event JSON serialization"""
        event = Event(
            id="evt_001",
            tick=5,
            event_type=EventType.CHARACTER_MOVED,
            actor_ids=["char_001"],
            location_id="loc_001",
            description="Character moved",
            metadata={"speed": "fast"},
        )

        # Serialize
        json_str = event.model_dump_json()
        assert isinstance(json_str, str)

        # Parse as dict
        parsed = json.loads(json_str)
        assert parsed["id"] == "evt_001"
        assert parsed["tick"] == 5
        assert parsed["event_type"] == "character_moved"

        # Deserialize back
        restored = Event.model_validate_json(json_str)
        assert restored.id == "evt_001"
        assert restored.tick == 5
        assert restored.event_type == EventType.CHARACTER_MOVED
        assert restored.metadata["speed"] == "fast"


class TestEventImmutability:
    """Tests for event immutability concepts"""

    def test_event_can_be_created_with_complete_data(self):
        """Test that events represent complete objective truth"""
        event = Event(
            id="evt_objective",
            tick=10,
            event_type=EventType.CHARACTER_SPOKE,
            actor_ids=["char_alice", "char_bob"],
            location_id="loc_conference",
            description="Alice told Bob about the plan",
            metadata={
                "statement": "We need to move forward",
                "duration_seconds": 30,
                "witnesses": ["char_charlie"],
            },
        )

        # Verify all data is preserved
        assert event.tick == 10
        assert len(event.actor_ids) == 2
        assert event.metadata["duration_seconds"] == 30

    def test_event_cannot_be_modified_after_creation(self):
        """Test that events are strictly immutable (Rule 7)"""
        event = Event(
            id="evt_immutable",
            tick=1,
            event_type=EventType.CHARACTER_MOVED,
            description="Alice moved to room",
        )
        with pytest.raises(ValidationError):
            event.description = "Attempted modification"

        with pytest.raises(ValidationError):
            event.tick = 2


class TestEventChronology:
    """Tests for ordering events chronologically"""

    def test_events_can_be_ordered_by_tick(self):
        """Test that events can be sorted by tick"""
        events = [
            Event(
                id="evt_003",
                tick=3,
                event_type=EventType.OTHER,
                description="Third event",
            ),
            Event(
                id="evt_001",
                tick=1,
                event_type=EventType.OTHER,
                description="First event",
            ),
            Event(
                id="evt_002",
                tick=2,
                event_type=EventType.OTHER,
                description="Second event",
            ),
        ]

        # Sort by tick
        sorted_events = sorted(events, key=lambda e: e.tick)
        assert sorted_events[0].tick == 1
        assert sorted_events[1].tick == 2
        assert sorted_events[2].tick == 3
