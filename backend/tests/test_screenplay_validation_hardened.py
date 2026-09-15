"""Tests for Screenplay Validation and Provenance Hardening (Phase 7)."""

import pytest
from src.domain.world import WorldState, Location
from src.domain.character import Character, EmotionalState
from src.domain.secret import Secret
from src.domain.event import Event, EventType
from src.narrative.fountain import (
    ScreenplayDocument,
    ScreenplayScene,
    ScreenplayBlock,
    ScreenplayBlockType,
)
from src.narrative.screenplay_validator import ScreenplayQualityValidator


@pytest.fixture
def validation_world():
    world = WorldState(
        id="w_val",
        name="Validation World",
        description="A diplomatic embassy with classified documents",
    )
    loc_lobby = Location(id="loc_lobby", name="Embassy Lobby", connected_locations=["loc_vault"])
    loc_vault = Location(id="loc_vault", name="Subterranean Vault", connected_locations=["loc_lobby"])
    world.locations[loc_lobby.id] = loc_lobby
    world.locations[loc_vault.id] = loc_vault

    alice = Character(
        id="char_alice",
        name="Alice",
        role="Intelligence Operative",
        current_location_id="loc_lobby",
        emotional_state=EmotionalState(fear=0.3, anger=0.1, trust=0.4, curiosity=0.8),
    )
    bob = Character(
        id="char_bob",
        name="Bob",
        role="Embassy Guard",
        current_location_id="loc_lobby",
        emotional_state=EmotionalState(fear=0.1, anger=0.7, trust=0.1, curiosity=0.2),
    )
    world.characters[alice.id] = alice
    world.characters[bob.id] = bob

    secret = Secret(
        id="sec_cipher",
        character_id=alice.id,
        statement="The master cipher key is hidden inside the bronze statue base.",
        known_by=[alice.id],
        importance=0.95,
    )
    world.secrets[secret.id] = secret
    alice.secrets.append(secret.id)

    ev1 = Event(
        id="ev_001",
        tick=1,
        event_type=EventType.CHARACTER_MOVED,
        actor_ids=["char_alice"],
        location_id="loc_lobby",
        description="Alice enters the embassy lobby.",
    )
    ev2 = Event(
        id="ev_002",
        tick=2,
        event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_bob"],
        location_id="loc_lobby",
        description="Bob demands identification.",
        metadata={"dialogue": "Halt. State your clearance level."},
    )
    world.events[ev1.id] = ev1
    world.events[ev2.id] = ev2

    return world


def test_screenplay_100_percent_provenance(validation_world):
    """Screenplay where every block links to valid simulation events passes with 100% provenance."""
    doc = ScreenplayDocument(
        title="Clearance Verification",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_lobby",
                heading="INT. EMBASSY LOBBY - DAY",
                source_event_ids=["ev_001", "ev_002"],
                metadata={
                    "scene_purpose": "confrontation",
                    "core_emotional_objective": {
                        "focal_character_id": "char_alice",
                        "immediate_desire": "Bypass security checkpoint",
                        "immediate_obstacle": "Bob demanding clearance credentials",
                        "emotional_shift": "curiosity to guarded",
                        "stakes": "Compromise of mission",
                    },
                },
                blocks=[
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.ACTION,
                        text="Alice enters the embassy lobby, steps echoing on the polished granite.",
                        source_event_ids=["ev_001"],
                        character_id="char_alice",
                    ),
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.CHARACTER,
                        text="BOB",
                        character_id="char_bob",
                    ),
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.DIALOGUE,
                        text="Halt. State your clearance level.",
                        source_event_ids=["ev_002"],
                        character_id="char_bob",
                    ),
                ],
            )
        ],
    )

    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, validation_world)

    assert report.provenance_coverage == 1.0
    assert report.ungrounded_block_count == 0
    assert report.knowledge_leak_count == 0
    assert report.scene_turn_fulfillment_score == 1.0
    assert report.overall_quality_score >= 90.0


def test_ungrounded_event_detection_and_penalty(validation_world):
    """Blocks lacking event provenance are flagged and penalize quality score."""
    doc = ScreenplayDocument(
        title="Invented Events",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_lobby",
                heading="INT. EMBASSY LOBBY - DAY",
                blocks=[
                    # Fabricated action without source event
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.ACTION,
                        text="A rogue helicopter smashes through the lobby ceiling!",
                        source_event_ids=[],
                    ),
                    # Fabricated dialogue with nonexistent event ID
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.DIALOGUE,
                        text="Get down! We are under attack!",
                        source_event_ids=["ev_nonexistent_999"],
                        character_id="char_bob",
                    ),
                ],
            )
        ],
    )

    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, validation_world)

    assert report.ungrounded_block_count == 2
    assert report.provenance_coverage == 0.0
    assert any(i.category == "provenance_violation" for i in report.issues)
    assert report.overall_quality_score < 80.0


def test_knowledge_leak_detection_defense(validation_world):
    """Unauthorized character speaking of private secrets is caught as knowledge leak."""
    # Bob does NOT know sec_cipher ("The master cipher key is hidden inside the bronze statue base.")
    doc = ScreenplayDocument(
        title="Security Breach",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_lobby",
                heading="INT. EMBASSY LOBBY - DAY",
                source_event_ids=["ev_001"],
                blocks=[
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.ACTION,
                        text="Alice enters the embassy lobby.",
                        source_event_ids=["ev_001"],
                        character_id="char_alice",
                    ),
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.DIALOGUE,
                        text="I know the cipher key is inside the bronze statue base.",
                        source_event_ids=["ev_001"],
                        character_id="char_bob",  # Bob should not know this!
                    ),
                ],
            )
        ],
    )

    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, validation_world)

    assert report.knowledge_leak_count >= 1
    leak_issues = [i for i in report.issues if i.category == "knowledge_leak"]
    assert len(leak_issues) >= 1
    assert "Bob" in leak_issues[0].message or "char_bob" in leak_issues[0].message


def test_authorized_character_secret_mention_is_safe(validation_world):
    """Authorized character who holds the secret speaking about it is not flagged as a leak."""
    doc = ScreenplayDocument(
        title="Authorized Mention",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_lobby",
                heading="INT. EMBASSY LOBBY - DAY",
                source_event_ids=["ev_001"],
                blocks=[
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.ACTION,
                        text="Alice enters the lobby.",
                        source_event_ids=["ev_001"],
                        character_id="char_alice",
                    ),
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.DIALOGUE,
                        text="The cipher key in the bronze statue base is safe with me.",
                        source_event_ids=["ev_001"],
                        character_id="char_alice",  # Alice owns the secret!
                    ),
                ],
            )
        ],
    )

    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, validation_world)

    assert report.knowledge_leak_count == 0


def test_focal_character_missing_objective_turn(validation_world):
    """Scene specifying a CoreEmotionalObjective warns if focal character is absent."""
    doc = ScreenplayDocument(
        title="Absent Focal Actor",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_lobby",
                heading="INT. EMBASSY LOBBY - DAY",
                source_event_ids=["ev_002"],
                metadata={
                    "scene_purpose": "investigation",
                    "core_emotional_objective": {
                        "focal_character_id": "char_alice",
                        "immediate_desire": "Infiltrate vault",
                        "immediate_obstacle": "Checkpoint",
                    },
                },
                blocks=[
                    # Only Bob is here, Alice is missing!
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.ACTION,
                        text="Bob patrols the empty perimeter.",
                        source_event_ids=["ev_002"],
                        character_id="char_bob",
                    ),
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.DIALOGUE,
                        text="All clear on post one.",
                        source_event_ids=["ev_002"],
                        character_id="char_bob",
                    ),
                ],
            )
        ],
    )

    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, validation_world)

    assert report.scene_turn_fulfillment_score < 1.0
    focal_issues = [i for i in report.issues if i.category == "focal_character_missing"]
    assert len(focal_issues) == 1
    assert "char_alice" in focal_issues[0].message
