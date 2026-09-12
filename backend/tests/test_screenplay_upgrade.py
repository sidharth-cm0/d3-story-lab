"""Tests for Screenplay Upgrades: Scribe, NarrativeFramer, ScenePurpose, and Validator (Phase 3)."""

import pytest
from src.domain.world import WorldState, Location
from src.domain.character import Character, EmotionalState
from src.domain.secret import Secret
from src.domain.event import Event, EventType
from src.narrative.observer import NarrativeEventSelection, NarrativeBeat, NarrativeBeatType
from src.narrative.scribe import Scribe
from src.narrative.framer import NarrativeFramer, FramingMode
from src.narrative.fountain import ScreenplayBlockType
from src.narrative.scene_purpose import ScenePurposeAnalyzer, ScenePurposeType
from src.narrative.screenplay_validator import ScreenplayQualityValidator


@pytest.fixture
def narrative_simulation_world():
    world = WorldState(
        id="w_narrative",
        name="Warehouse Standoff",
        description="Midnight warehouse with classified dossier and armed standoff",
    )
    loc_dock = Location(id="loc_dock", name="Waterfront Dock", description="Rain slicked dock", connected_locations=["loc_wh"])
    loc_wh = Location(id="loc_wh", name="Main Warehouse Floor", description="Cavernous depot with shipping crates and steel cabinets", connected_locations=["loc_dock", "loc_office"])
    loc_office = Location(id="loc_office", name="Manager Office", description="Elevated office looking down on depot", connected_locations=["loc_wh"])
    world.locations[loc_dock.id] = loc_dock
    world.locations[loc_wh.id] = loc_wh
    world.locations[loc_office.id] = loc_office

    evelyn = Character(
        id="char_evelyn",
        name="Evelyn",
        role="Undercover Detective",
        current_location_id="loc_dock",
        emotional_state=EmotionalState(fear=0.5, anger=0.2, trust=0.1, curiosity=0.8),
    )
    vincent = Character(
        id="char_vincent",
        name="Vincent",
        role="Smuggler Boss",
        current_location_id="loc_wh",
        emotional_state=EmotionalState(fear=0.2, anger=0.8, trust=0.2, curiosity=0.5),
    )
    world.characters[evelyn.id] = evelyn
    world.characters[vincent.id] = vincent

    secret = Secret(
        id="sec_dossier",
        character_id=evelyn.id,
        statement="Evelyn knows the stolen dossier is hidden in the metal cabinet.",
        known_by=[evelyn.id],
        importance=0.9,
    )
    world.secrets[secret.id] = secret
    evelyn.secrets.append(secret.id)

    # Add simulation events
    events = [
        Event(id="ev_1", tick=1, event_type=EventType.CHARACTER_MOVED, actor_ids=["char_evelyn"], location_id="loc_dock", description="Evelyn steps cautiously onto the waterfront dock.", metadata={"from_location_name": None, "to_location_name": "Waterfront Dock"}),
        Event(id="ev_2", tick=2, event_type=EventType.CHARACTER_MOVED, actor_ids=["char_evelyn"], location_id="loc_wh", description="Evelyn slips through the heavy doors into Main Warehouse Floor.", metadata={"from_location_name": "Waterfront Dock", "to_location_name": "Main Warehouse Floor"}),
        Event(id="ev_3", tick=3, event_type=EventType.CHARACTER_SPOKE, actor_ids=["char_vincent"], location_id="loc_wh", description="Vincent steps out from behind the crates: 'Who told you to come here?'", metadata={"dialogue": "Who told you to come here?", "speech_act": "question", "emotion": "suspicious"}),
        Event(id="ev_4", tick=4, event_type=EventType.CHARACTER_SPOKE, actor_ids=["char_evelyn"], location_id="loc_wh", description="Evelyn denies knowing anything: 'I haven't seen any dossier in this room.'", metadata={"dialogue": "I haven't seen any dossier in this room.", "speech_act": "deny", "emotion": "guarded"}),
        Event(id="ev_5", tick=5, event_type=EventType.CHARACTER_SPOKE, actor_ids=["char_vincent"], location_id="loc_wh", description="Vincent warns her: 'Don't test me. Drop the lockpick.'", metadata={"dialogue": "Don't test me. Drop the lockpick.", "speech_act": "threat", "emotion": "angry"}),
        Event(id="ev_6", tick=6, event_type=EventType.OTHER, actor_ids=["char_vincent"], location_id="loc_office", description="Alarm claxons wail as an explosive charge detonates on the catwalk!", metadata={"incident_type": "explosion"}),
    ]
    for ev in events:
        world.events[ev.id] = ev

    beats = [
        NarrativeBeat(
            id="beat_1",
            beat_type=NarrativeBeatType.ESTABLISHING,
            start_tick=1,
            end_tick=2,
            location_id="loc_wh",
            character_ids=["char_evelyn"],
            dramatic_score=0.4,
            summary="Evelyn infiltrates the warehouse.",
            source_event_ids=["ev_1", "ev_2"],
        ),
        NarrativeBeat(
            id="beat_2",
            beat_type=NarrativeBeatType.CONFRONTATION,
            start_tick=3,
            end_tick=5,
            location_id="loc_wh",
            character_ids=["char_evelyn", "char_vincent"],
            dramatic_score=0.85,
            summary="Vincent corners Evelyn in the depot.",
            source_event_ids=["ev_3", "ev_4", "ev_5"],
        ),
        NarrativeBeat(
            id="beat_3",
            beat_type=NarrativeBeatType.CRISIS,
            start_tick=6,
            end_tick=6,
            location_id="loc_office",
            character_ids=["char_vincent"],
            dramatic_score=0.95,
            summary="Explosion shakes the elevated office.",
            source_event_ids=["ev_6"],
        ),
    ]
    selection = NarrativeEventSelection(
        total_events_observed=len(events),
        filtered_beats=beats,
        dramatic_arc_summary="Infiltration leads to confrontation and sudden explosion.",
        tension_progression=[0.4, 0.85, 0.95],
    )
    return world, selection


def test_scribe_performance_cue_and_provenance(narrative_simulation_world):
    world, selection = narrative_simulation_world
    scribe = Scribe()
    doc = scribe.compose_screenplay(selection, world, title="TEST SCREENPLAY")

    assert len(doc.scenes) >= 2
    # Find Evelyn's dialogue block
    evelyn_dialogue_found = False
    perf_cue_found = False

    for scene in doc.scenes:
        for b in scene.blocks:
            if b.block_type == ScreenplayBlockType.DIALOGUE and "dossier" in b.text.lower():
                evelyn_dialogue_found = True
            if b.is_performance_cue:
                perf_cue_found = True
                assert b.derived_from_event_id is not None
                assert b.cue_type is not None
                assert len(b.derived_from_actor_state_ids) > 0
                # Must NOT expose private secret text directly
                assert "Evelyn knows the stolen dossier" not in b.text

    assert evelyn_dialogue_found is True
    assert perf_cue_found is True


def test_parenthetical_overuse_prevention(narrative_simulation_world):
    world, selection = narrative_simulation_world
    scribe = Scribe()
    doc = scribe.compose_screenplay(selection, world)

    # Check parenthetical ratio and consecutive parentheticals
    dialogue_blocks = [b for s in doc.scenes for b in s.blocks if b.block_type == ScreenplayBlockType.DIALOGUE]
    paren_blocks = [b for s in doc.scenes for b in s.blocks if b.block_type == ScreenplayBlockType.PARENTHETICAL]

    if dialogue_blocks:
        ratio = len(paren_blocks) / len(dialogue_blocks)
        assert ratio <= 0.5  # Restrained use of parentheticals

    # Ensure no two parentheticals are consecutively stacked
    for s in doc.scenes:
        for idx in range(len(s.blocks) - 1):
            assert not (
                s.blocks[idx].block_type == ScreenplayBlockType.PARENTHETICAL and
                s.blocks[idx + 1].block_type == ScreenplayBlockType.PARENTHETICAL
            )


def test_narrative_framer_in_media_res(narrative_simulation_world):
    world, selection = narrative_simulation_world
    scribe = Scribe()
    # Generate in-media-res screenplay
    doc = scribe.compose_screenplay(selection, world, framing_mode=FramingMode.IN_MEDIA_RES)

    assert len(doc.scenes) >= 3
    # Scene 1 must be the flashforward hook
    assert doc.scenes[0].framing_type == FramingMode.IN_MEDIA_RES.value
    # Scene 2 must contain the title card for earlier time jump
    has_title_card = any("TITLE CARD" in b.text for b in doc.scenes[1].blocks)
    assert has_title_card is True

    # Check chronological simulation history is completely intact in WorldState
    assert len(world.events) == 6
    assert [e.id for e in sorted(world.events.values(), key=lambda e: e.tick)] == [f"ev_{i}" for i in range(1, 7)]


def test_scene_purpose_analyzer(narrative_simulation_world):
    world, selection = narrative_simulation_world
    scribe = Scribe()
    doc = scribe.compose_screenplay(selection, world)

    analyzer = ScenePurposeAnalyzer()
    purposes = []
    for scn in doc.scenes:
        analysis = analyzer.analyze_scene(scn, world)
        assert analysis.purpose in ScenePurposeType
        assert len(analysis.dramatic_question) > 5
        assert len(analysis.scene_goal) > 5
        purposes.append(analysis.purpose)

    assert len(purposes) == len(doc.scenes)


def test_screenplay_quality_validator(narrative_simulation_world):
    world, selection = narrative_simulation_world
    scribe = Scribe()
    doc = scribe.compose_screenplay(selection, world)

    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, world)

    assert report.total_scenes == len(doc.scenes)
    assert report.knowledge_leak_count == 0  # No secret leakage
    assert report.overall_quality_score >= 80.0
    assert "overall_quality_score" in report.to_dict()


def test_screenplay_and_storyboard_quality_api_integration(narrative_simulation_world, tmp_path):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    from src.storage.project_store import ProjectStore, ProjectData, ProjectMetadata

    world, selection = narrative_simulation_world
    store = ProjectStore(base_dir=tmp_path)
    meta = ProjectMetadata(
        id=world.id,
        title="Warehouse Standoff Test",
        seed_prompt="Warehouse standoff",
    )
    proj = ProjectData(metadata=meta, world=world)
    store.save_project(proj)

    app = create_app(store_dir=str(tmp_path))
    client = TestClient(app)

    # Post generate-screenplay with in_media_res framing mode
    resp = client.post(
        f"/api/projects/{world.id}/generate-screenplay",
        json={"framing_mode": "in_media_res"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "screenplay_quality" in data
    assert "storyboard_quality" in data
    assert data["screenplay_quality"]["overall_quality_score"] > 70.0

    # Test dedicated screenplay quality endpoint
    resp_sq = client.get(f"/api/projects/{world.id}/screenplay/quality")
    assert resp_sq.status_code == 200
    sq_data = resp_sq.json()
    assert sq_data["total_scenes"] >= 3
    assert sq_data["knowledge_leak_count"] == 0

    # Test dedicated storyboard quality endpoint
    resp_sbq = client.get(f"/api/projects/{world.id}/storyboard/quality")
    assert resp_sbq.status_code == 200
    sbq_data = resp_sbq.json()
    assert sbq_data["total_panels"] > 0
    assert sbq_data["overall_storyboard_score"] > 60.0

