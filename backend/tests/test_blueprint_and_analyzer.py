"""Tests for StoryBlueprint generation, Director pressure integration, and StructureAnalyzer."""

import pytest
from src.domain.story_structure import (
    StoryStructureType,
    StructureSelectionMode,
    StructureSelectionResult,
    StoryBlueprint,
)
from src.domain.event import Event, EventType
from src.narrative.blueprint_generator import StoryBlueprintGenerator
from src.narrative.structure_analyzer import StructureAnalyzer
from src.narrative.structure_selector import StructureSelector
from src.agents.director import DirectorAgent
from src.domain.world import WorldState, Location, Character


def test_blueprint_generator_creates_soft_constraints():
    """Verify that StoryBlueprint contains soft constraints, theme, and pressure signals without puppetry."""
    prompt = "An undercover detective infiltrates an abandoned warehouse to retrieve a classified dossier."
    selector = StructureSelector()
    sel_res = selector.select_structure(prompt, mode=StructureSelectionMode.AUTO)

    gen = StoryBlueprintGenerator()
    blueprint = gen.generate_blueprint(prompt, sel_res, title="THE WAREHOUSE RECOVERY")

    assert blueprint.story_title == "THE WAREHOUSE RECOVERY"
    assert blueprint.primary_structure == sel_res.primary_structure
    assert blueprint.theme
    assert blueprint.dramatic_question
    assert blueprint.stakes
    assert len(blueprint.expected_beats) >= 4

    # Confirm non-puppetry softness
    gen.assert_blueprint_is_soft(blueprint)

    # Confirm attempting to inject puppetry raises ValueError
    bad_blueprint = blueprint.model_copy(deep=True)
    bad_blueprint.soft_constraints["forced_dialogue"] = "Detective must say: 'Where is the file?'"
    with pytest.raises(ValueError, match="Architectural Rule Violation"):
        gen.assert_blueprint_is_soft(bad_blueprint)


def test_director_modulates_pressure_from_blueprint():
    """Verify DirectorAgent reads blueprint pressure signals without dictating character dialogue or actions."""
    selector = StructureSelector()
    sel_res = selector.select_structure("A detective enters a warehouse", mode=StructureSelectionMode.AUTO)
    gen = StoryBlueprintGenerator()
    blueprint = gen.generate_blueprint("A detective enters a warehouse", sel_res)

    director = DirectorAgent(inactivity_threshold=1, blueprint=blueprint, target_ticks=10)

    # Test reading pressure signal at different tick points
    sig_early = director.get_current_blueprint_pressure(current_tick=1)
    assert sig_early is not None

    sig_mid = director.get_current_blueprint_pressure(current_tick=5)
    assert sig_mid is not None

    # Verify intervention metadata receives blueprint pressure signal
    world = WorldState(
        id="test_w",
        name="Test",
        current_tick=5,
        locations={"loc_1": Location(id="loc_1", name="Main Hall")},
        characters={"char_1": Character(id="char_1", name="Detective", role="Investigator", current_location_id="loc_1")},
    )

    intervention = director.evaluate_pacing(world, inactivity_count=2)
    assert intervention is not None
    assert "blueprint_pressure_signal" in intervention.metadata
    # Confirm director does not dictate exact character speech or action
    assert "forced_dialogue" not in intervention.metadata


def test_structure_analyzer_observes_fulfillment_and_deviation():
    """Verify StructureAnalyzer observes beat fulfillment and organic deviations without mutating history."""
    selector = StructureSelector()
    sel_res = selector.select_structure("An undercover detective infiltrates a warehouse", mode=StructureSelectionMode.AUTO)
    gen = StoryBlueprintGenerator()
    blueprint = gen.generate_blueprint("An undercover detective infiltrates a warehouse", sel_res)

    # Create synthetic events
    events = [
        Event(id="ev_01", tick=1, event_type=EventType.CHARACTER_MOVED, description="Detective enters warehouse setup location", actor_ids=["char_1"]),
        Event(id="ev_02", tick=2, event_type=EventType.CHARACTER_SPOKE, description="Courier denies knowing anything, creating disruption and tension", actor_ids=["char_2"]),
        Event(id="ev_03", tick=5, event_type=EventType.CHARACTER_OBSERVED, description="Detective uncovers hidden dossier in locked safe, major revelation reversal", actor_ids=["char_1"]),
    ]

    analyzer = StructureAnalyzer()
    report = analyzer.analyze_fulfillment(blueprint, events, max_ticks=10)

    assert report.is_purely_observational is True
    assert report.total_expected_beats == len(blueprint.expected_beats)
    assert report.fulfilled_beats_count >= 1
    assert len(report.beat_assessments) == len(blueprint.expected_beats)
    assert 0.0 <= report.overall_alignment_score <= 100.0
    assert report.deviation_summary

    # Verify that history was not rewritten or mutated
    assert len(events) == 3
    assert events[0].id == "ev_01"
