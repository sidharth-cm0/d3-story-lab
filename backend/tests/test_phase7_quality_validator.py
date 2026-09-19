"""Tests for Phase 7 Prompt 3: Screenplay Quality Validator, Legacy Migration, and Acceptance.

Covers all 15 required specifications:
1. Valid screenplay passes format conformance.
2. Malformed slugline flagged.
3. Malformed character/dialogue structure flagged.
4. Internal-state verb leak counted.
5. Externalized performance cue passes.
6. Every supported screenplay block preserves provenance.
7. Missing provenance is reported, not silently repaired.
8. Unsupported invented event is detected.
9. Legacy 'Director injects...' phrase no longer appears in grounded output.
10. Legacy 'second sovereign actor' phrase no longer appears.
11. Provider-disabled Scribe completes successfully.
12. Provider spy count == 0.
13. Screenplay remains deterministic with same seed/input.
14. EventHistory remains byte-identical before/after Scribe + validation.
15. Missing Dossier acceptance report passes required quality thresholds.
"""

import json
import pytest
from typing import List, Dict

from src.domain.world import WorldState, Location
from src.domain.character import Character
from src.domain.event import Event, EventType
from src.domain.story_structure import DramaticFunction
from src.narrative.fountain import (
    ScreenplayDocument,
    ScreenplayScene,
    ScreenplayBlock,
    ScreenplayBlockType,
)
from src.narrative.screenplay_validator import (
    ScreenplayQualityValidator,
    ScreenplayQualityReport,
)
from src.narrative.performance_cues import (
    PerformanceCue,
    PerformanceCueType,
    InternalStateVerbGuard,
)
from src.narrative.scene_projection import (
    ObservableSceneProjector,
    ObservableSceneProjection,
    ObservableBeat,
    ObservableDialogueLine,
    ObservableObjective,
    scan_for_internal_vocabulary,
)
from src.narrative.scribe import Scribe
from src.narrative.synopsis import SynopsisGenerator, sanitize_narrative_text
from src.narrative.completion import StoryCompletionEngine, StoryInputType
from src.narrative.scene_builder import SceneBuilder
from src.storage.project_store import ProjectStore
from src.providers.base import LLMProvider


# =============================================================================
# FIXTURES
# =============================================================================

class MockProviderSpy(LLMProvider):
    """Spy provider tracking total calls to assert zero-AI execution."""
    def __init__(self):
        self.call_count = 0

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        self.call_count += 1
        raise RuntimeError("AI Provider should never be invoked in deterministic mode!")

    def generate_structured(self, schema, prompt: str, system_prompt: Optional[str] = None):
        self.call_count += 1
        raise RuntimeError("AI Provider should never be invoked in deterministic mode!")


@pytest.fixture
def sample_world() -> WorldState:
    world = WorldState(id="w_test", name="Test World", description="A high-stakes facility")
    loc1 = Location(id="loc_bay", name="Industrial Bay", connected_locations=["loc_vault"])
    loc2 = Location(id="loc_vault", name="Archive Vault", connected_locations=["loc_bay"])
    world.locations[loc1.id] = loc1
    world.locations[loc2.id] = loc2

    c1 = Character(id="char_alpha", name="Vincent Cross", role="Infiltrator", current_location_id="loc_bay")
    c2 = Character(id="char_beta", name="Evelyn Vance", role="Custodian", current_location_id="loc_bay")
    world.characters[c1.id] = c1
    world.characters[c2.id] = c2

    ev1 = Event(id="evt_01", tick=1, event_type=EventType.CHARACTER_MOVED, actor_ids=["char_alpha"], location_id="loc_bay", description="Vincent Cross enters the bay.")
    ev2 = Event(id="evt_02", tick=2, event_type=EventType.CHARACTER_SPOKE, actor_ids=["char_beta"], location_id="loc_bay", description="Evelyn Vance speaks.")
    world.events[ev1.id] = ev1
    world.events[ev2.id] = ev2
    return world


@pytest.fixture
def valid_screenplay(sample_world) -> ScreenplayDocument:
    return ScreenplayDocument(
        title="THE EXTRACTION",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_bay",
                heading="INT. INDUSTRIAL BAY - NIGHT",
                source_event_ids=["evt_01", "evt_02"],
                blocks=[
                    ScreenplayBlock(
                        block_id="b_slug",
                        scene_id="s1",
                        element_type="SLUGLINE",
                        content="INT. INDUSTRIAL BAY - NIGHT",
                        source_event_ids=["evt_01"],
                        presentation_position=1,
                    ),
                    ScreenplayBlock(
                        block_id="b_act",
                        scene_id="s1",
                        element_type="ACTION",
                        content="Vincent Cross examines the metal container on the workbench.",
                        source_event_ids=["evt_01"],
                        presentation_position=2,
                    ),
                    ScreenplayBlock(
                        block_id="b_cue",
                        scene_id="s1",
                        element_type="CHARACTER_CUE",
                        content="EVELYN VANCE",
                        source_event_ids=["evt_02"],
                        presentation_position=3,
                    ),
                    ScreenplayBlock(
                        block_id="b_dial",
                        scene_id="s1",
                        element_type="DIALOGUE",
                        content="The clearance logs for that sector were sealed this morning.",
                        source_event_ids=["evt_02"],
                        presentation_position=4,
                    ),
                ],
            )
        ],
    )


# =============================================================================
# UNIT TESTS
# =============================================================================

def test_1_valid_screenplay_passes_format_conformance(valid_screenplay, sample_world):
    """Test 1: Valid screenplay passes format conformance."""
    validator = ScreenplayQualityValidator()
    report = validator.validate(valid_screenplay, sample_world)

    assert sum(report.format_conformance.values()) == 0
    assert report.format_conformance_score == 1.0
    assert report.passed is True


def test_2_malformed_slugline_flagged(sample_world):
    """Test 2: Malformed slugline is flagged in format_conformance."""
    doc = ScreenplayDocument(
        title="BAD SLUGLINE",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_bay",
                heading="int. industrial bay night",  # Lowercase, missing dash separator
                source_event_ids=["evt_01"],
                blocks=[
                    ScreenplayBlock(
                        block_id="b_slug",
                        scene_id="s1",
                        element_type="SLUGLINE",
                        content="int. industrial bay night",
                        source_event_ids=["evt_01"],
                        presentation_position=1,
                    )
                ],
            )
        ],
    )
    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, sample_world)

    assert report.format_conformance["malformed_slugline"] > 0
    assert report.passed is False


def test_3_malformed_character_dialogue_structure_flagged(sample_world):
    """Test 3: Malformed character/dialogue structure flagged (e.g., orphan dialogue or internal ID cue)."""
    doc = ScreenplayDocument(
        title="MALFORMED STRUCTURE",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_bay",
                heading="INT. INDUSTRIAL BAY - NIGHT",
                source_event_ids=["evt_01"],
                blocks=[
                    # Raw internal ID leaked as character cue
                    ScreenplayBlock(
                        block_id="b_cue",
                        scene_id="s1",
                        element_type="CHARACTER_CUE",
                        content="CHAR_ALPHA",
                        source_event_ids=["evt_01"],
                        presentation_position=1,
                    ),
                    # Followed by action instead of dialogue
                    ScreenplayBlock(
                        block_id="b_act",
                        scene_id="s1",
                        element_type="ACTION",
                        content="Vincent Cross turns around.",
                        source_event_ids=["evt_01"],
                        presentation_position=2,
                    ),
                    # Orphan dialogue not preceded by character cue
                    ScreenplayBlock(
                        block_id="b_dial",
                        scene_id="s1",
                        element_type="DIALOGUE",
                        content="Where is the dossier?",
                        source_event_ids=["evt_01"],
                        presentation_position=3,
                    ),
                ],
            )
        ],
    )
    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, sample_world)

    assert report.format_conformance["malformed_character_cue"] > 0
    assert report.format_conformance["orphan_dialogue"] > 0
    assert report.passed is False


def test_4_internal_state_verb_leak_counted(sample_world):
    """Test 4: Internal-state verb leak counted via InternalStateVerbGuard."""
    doc = ScreenplayDocument(
        title="TELL NOT SHOW",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_bay",
                heading="INT. INDUSTRIAL BAY - NIGHT",
                source_event_ids=["evt_01"],
                blocks=[
                    ScreenplayBlock(
                        block_id="b_act_leak",
                        scene_id="s1",
                        element_type="ACTION",
                        content="Vincent realizes the courier is lying and feels intense panic.",
                        source_event_ids=["evt_01"],
                        presentation_position=1,
                    ),
                ],
            )
        ],
    )
    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, sample_world)

    assert report.internal_state_leak_count > 0
    assert report.passed is False
    assert any(i.category == "internal_state_leak" for i in report.issues)


def test_5_externalized_performance_cue_passes(sample_world):
    """Test 5: Externalized performance cue passes InternalStateVerbGuard."""
    observable_cue = "Vincent Cross lowers his voice and glances toward the desk drawer."
    assert InternalStateVerbGuard.validate_action_text(observable_cue) is True

    doc = ScreenplayDocument(
        title="EXTERNALIZED PERFORMANCE",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_bay",
                heading="INT. INDUSTRIAL BAY - NIGHT",
                source_event_ids=["evt_01"],
                blocks=[
                    ScreenplayBlock(
                        block_id="b_cue_act",
                        scene_id="s1",
                        element_type="ACTION",
                        content=observable_cue,
                        source_event_ids=["evt_01"],
                        presentation_position=1,
                    ),
                ],
            )
        ],
    )
    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, sample_world)
    assert report.internal_state_leak_count == 0


def test_6_every_supported_screenplay_block_preserves_provenance(valid_screenplay, sample_world):
    """Test 6: Every supported screenplay block preserves provenance."""
    validator = ScreenplayQualityValidator()
    report = validator.validate(valid_screenplay, sample_world)

    assert report.provenance_completeness_pct == 100.0
    assert report.unsupported_event_invention_count == 0
    assert report.missing_source_reference_count == 0


def test_7_missing_provenance_reported_not_silently_repaired(sample_world):
    """Test 7: Missing provenance is reported, not silently repaired."""
    doc = ScreenplayDocument(
        title="MISSING PROVENANCE",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_bay",
                heading="INT. INDUSTRIAL BAY - NIGHT",
                blocks=[
                    # Action with empty source events
                    ScreenplayBlock(
                        block_id="b_act_noprov",
                        scene_id="s1",
                        element_type="ACTION",
                        content="A shadow moves past the corrugated window.",
                        source_event_ids=[],
                        presentation_position=1,
                    ),
                ],
            )
        ],
    )
    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, sample_world)

    assert report.missing_source_reference_count > 0
    assert report.ungrounded_block_count > 0
    assert report.passed is False


def test_8_unsupported_invented_event_detected(sample_world):
    """Test 8: Unsupported invented event is detected."""
    doc = ScreenplayDocument(
        title="INVENTED EVENT",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_bay",
                heading="INT. INDUSTRIAL BAY - NIGHT",
                source_event_ids=["evt_nonexistent_fake_999"],
                blocks=[
                    ScreenplayBlock(
                        block_id="b_act_fake",
                        scene_id="s1",
                        element_type="ACTION",
                        content="Helicopters surround the building rooftop.",
                        source_event_ids=["evt_nonexistent_fake_999"],
                        presentation_position=1,
                    ),
                ],
            )
        ],
    )
    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, sample_world)

    assert report.unsupported_event_invention_count > 0
    assert report.passed is False
    assert any(i.category == "unsupported_event_invention" for i in report.issues)


def test_9_legacy_director_injects_phrase_no_longer_appears(sample_world):
    """Test 9: Legacy 'Director injects...' phrase no longer appears in grounded output."""
    generator = SynopsisGenerator()
    syn = generator.generate_synopsis(outline=None, world=sample_world)

    full_text = f"{syn.logline} {syn.paragraph_summary} {syn.full_synopsis}"
    assert "Director injects" not in full_text
    assert "Director interventions" not in full_text
    assert "critical environmental interventions" not in full_text


def test_10_legacy_second_sovereign_actor_phrase_no_longer_appears():
    """Test 10: Legacy 'second sovereign actor' phrase no longer appears."""
    comp = StoryCompletionEngine(provider=None)
    outline = comp._complete_from_beginning("An operative enters an abandoned warehouse", "The Warehouse", 20)

    for act_key, act_text in outline.act_structure.items():
        assert "sovereign actor" not in act_text
        assert "second sovereign actor" not in act_text

    for beat in outline.key_scenes:
        assert "sovereign actor" not in beat.description
        assert "Director triggers" not in beat.description
        assert "The Director triggers" not in beat.description


def test_11_provider_disabled_scribe_completes_successfully(sample_world):
    """Test 11: Provider-disabled Scribe completes successfully."""
    scribe = Scribe(provider=None)

    proj = ObservableSceneProjection(
        scene_id="sc_01",
        scene_number=1,
        source_event_ids=["evt_01", "evt_02"],
        location_label="Industrial Bay",
        time_label="NIGHT",
        characters_present=["char_alpha", "char_beta"],
        purpose=DramaticFunction.INVESTIGATION,
        objective=ObservableObjective(
            pov_character_id="char_alpha",
            wants="Recover the transit dossier",
            obstacle="Evelyn conceals its location",
            outcome="PARTIAL",
        ),
        beats=[
            ObservableBeat(event_id="evt_01", description="Vincent Cross steps inside.", characters_involved=["char_alpha"]),
            ObservableBeat(event_id="evt_02", description="Evelyn Vance answers.", characters_involved=["char_beta"]),
        ],
        dialogue=[
            ObservableDialogueLine(speaker_id="char_beta", communicative_intent="TRUTHFUL", source_event_id="evt_02", text="The room is secure."),
        ],
    )
    doc = scribe.compose_from_projections([proj], title="OFFLINE TEST")

    assert isinstance(doc, ScreenplayDocument)
    assert len(doc.scenes) == 1
    assert len(doc.scenes[0].blocks) >= 3


def test_12_provider_spy_count_zero(sample_world):
    """Test 12: Provider spy count == 0 in deterministic execution."""
    spy = MockProviderSpy()
    scribe = Scribe(provider=spy)

    proj = ObservableSceneProjection(
        scene_id="sc_01",
        scene_number=1,
        source_event_ids=["evt_01"],
        location_label="Industrial Bay",
        time_label="NIGHT",
        characters_present=["char_alpha"],
        purpose=DramaticFunction.SETUP,
        objective=ObservableObjective(
            pov_character_id="char_alpha",
            wants="Observe",
            obstacle="None",
            outcome="ACHIEVED",
        ),
        beats=[
            ObservableBeat(event_id="evt_01", description="Vincent Cross stands motionless.", characters_involved=["char_alpha"]),
        ],
    )
    doc = scribe.compose_from_projections([proj], title="SPY TEST")

    assert len(doc.scenes) == 1
    assert spy.call_count == 0


def test_13_screenplay_remains_deterministic_same_seed_input():
    """Test 13: Screenplay remains deterministic with same seed/input."""
    store = ProjectStore()
    project = store.load_project("world_init_4bef81")
    assert project is not None

    builder = SceneBuilder()
    enriched = builder.enrich_scenes_with_phase6(project.scenes, project.world)
    projector = ObservableSceneProjector()
    projections = projector.project_all_scenes(enriched, project.world)

    scribe1 = Scribe(provider=None)
    doc1 = scribe1.compose_from_projections(projections, title="RUN 1")

    scribe2 = Scribe(provider=None)
    doc2 = scribe2.compose_from_projections(projections, title="RUN 2")

    # Content and block structure must be identical
    assert len(doc1.scenes) == len(doc2.scenes)
    for s1, s2 in zip(doc1.scenes, doc2.scenes):
        assert len(s1.blocks) == len(s2.blocks)
        for b1, b2 in zip(s1.blocks, s2.blocks):
            assert b1.element_type == b2.element_type
            assert b1.content == b2.content
            assert b1.source_event_ids == b2.source_event_ids


def test_14_event_history_remains_byte_identical_before_after_scribe_and_validation():
    """Test 14: EventHistory remains byte-identical before/after Scribe + validation."""
    store = ProjectStore()
    project = store.load_project("world_init_4bef81")
    assert project is not None

    # Capture serialized EventHistory before Scribe & validation
    events_before = {eid: ev.model_dump_json() for eid, ev in sorted(project.world.events.items())}

    builder = SceneBuilder()
    enriched = builder.enrich_scenes_with_phase6(project.scenes, project.world)
    projector = ObservableSceneProjector()
    projections = projector.project_all_scenes(enriched, project.world)
    scribe = Scribe(provider=None)
    doc = scribe.compose_from_projections(projections, title="THE MISSING DOSSIER")

    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, project.world, scenes=project.scenes, projections=projections)

    # Capture serialized EventHistory after
    events_after = {eid: ev.model_dump_json() for eid, ev in sorted(project.world.events.items())}

    assert events_before == events_after, "Canonical EventHistory was mutated during Scribe or validation!"


def test_15_missing_dossier_acceptance_report_passes_required_thresholds():
    """Test 15: Missing Dossier acceptance report passes required quality thresholds."""
    store = ProjectStore()
    project = store.load_project("world_init_4bef81")
    assert project is not None

    builder = SceneBuilder()
    enriched = builder.enrich_scenes_with_phase6(project.scenes, project.world)
    projector = ObservableSceneProjector()
    projections = projector.project_all_scenes(enriched, project.world)
    scribe = Scribe(provider=None)
    doc = scribe.compose_from_projections(projections, title="THE MISSING DOSSIER")

    validator = ScreenplayQualityValidator()
    report = validator.validate(doc, project.world, scenes=project.scenes, projections=projections)

    # Invariants verification
    assert report.internal_state_leak_count == 0
    assert report.architecture_vocabulary_leak_count == 0
    assert report.unsupported_event_invention_count == 0
    assert report.missing_source_reference_count == 0
    assert sum(report.format_conformance.values()) == 0
    assert report.provenance_completeness_pct >= 90.0
    assert report.scene_coverage_pct == 100.0
    assert report.passed is True
