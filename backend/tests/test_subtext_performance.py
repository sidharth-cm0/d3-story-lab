"""Tests for SubtextAnalyzer and PerformanceCueGenerator (Phase 1)."""

import pytest
from src.domain.world import WorldState, Location
from src.domain.character import Character, EmotionalState
from src.domain.secret import Secret
from src.domain.belief import Belief
from src.narrative.subtext import SubtextAnalyzer, DeceptionClassification
from src.narrative.performance_cues import PerformanceCueGenerator, PerformanceCueType


@pytest.fixture
def test_world():
    world = WorldState(
        id="world_warehouse",
        name="Abandoned Warehouse Intrigue",
        description="Midnight waterfront warehouse with hidden cache",
    )
    loc = Location(
        id="loc_warehouse",
        name="Main Storage Floor",
        description="Cavernous storage depot lined with metal cabinets and shipping crates",
        connected_locations=["loc_corridor"],
    )
    world.locations[loc.id] = loc

    evelyn = Character(
        id="char_evelyn",
        name="Evelyn",
        role="Undercover Agent",
        current_location_id=loc.id,
        emotional_state=EmotionalState(fear=0.6, anger=0.2, trust=0.1, curiosity=0.8),
    )
    vincent = Character(
        id="char_vincent",
        name="Vincent",
        role="Smuggler Boss",
        current_location_id=loc.id,
        emotional_state=EmotionalState(fear=0.2, anger=0.7, trust=0.2, curiosity=0.5),
    )
    world.characters[evelyn.id] = evelyn
    world.characters[vincent.id] = vincent

    secret = Secret(
        id="sec_dossier",
        character_id=evelyn.id,
        statement="Evelyn knows the stolen classified dossier is concealed inside the metal cabinet.",
        known_by=[evelyn.id],
        importance=0.9,
    )
    world.secrets[secret.id] = secret
    evelyn.secrets.append(secret.id)

    return world


def test_lying_dialogue_classification(test_world):
    analyzer = SubtextAnalyzer()
    evelyn = test_world.characters["char_evelyn"]

    analysis = analyzer.analyze(
        speaker=evelyn,
        dialogue="I haven't seen any dossier in this room.",
        world=test_world,
        listener_id="char_vincent",
    )

    assert DeceptionClassification.LYING in analysis.classifications
    assert DeceptionClassification.CONCEALING in analysis.classifications
    assert analysis.conflict_focus_object == "dossier"
    assert analysis.cognitive_dissonance_score > 0.7


def test_evasive_dialogue_classification(test_world):
    analyzer = SubtextAnalyzer()
    evelyn = test_world.characters["char_evelyn"]

    analysis = analyzer.analyze(
        speaker=evelyn,
        dialogue="Why do you ask? That's none of your business.",
        world=test_world,
        listener_id="char_vincent",
    )

    assert (DeceptionClassification.EVASIVE in analysis.classifications or
            DeceptionClassification.DEFLECTING in analysis.classifications)


def test_truthful_dialogue_classification(test_world):
    analyzer = SubtextAnalyzer()
    vincent = test_world.characters["char_vincent"]

    analysis = analyzer.analyze(
        speaker=vincent,
        dialogue="The patrol car just passed outside.",
        world=test_world,
        listener_id="char_evelyn",
    )

    assert DeceptionClassification.TRUTHFUL in analysis.classifications


def test_private_secret_not_leaked_in_action_lines(test_world):
    analyzer = SubtextAnalyzer()
    cue_gen = PerformanceCueGenerator()
    evelyn = test_world.characters["char_evelyn"]

    analysis = analyzer.analyze(
        speaker=evelyn,
        dialogue="I haven't seen it. The room was empty when I arrived.",
        world=test_world,
        listener_id="char_vincent",
    )
    cue = cue_gen.generate_cue(
        analysis=analysis,
        character=evelyn,
        world=test_world,
        source_event_id="ev_test_1",
    )

    # Invariant: Screenplay action must show observable behavior, NOT leak secret statement
    assert "knows the stolen classified dossier" not in cue.action_text
    assert "Evelyn lies because" not in cue.action_text
    # Should observe physical behavior
    assert any(term in cue.action_text.lower() for term in ["gaze", "flicks", "jaw", "looks away", "cabinet", "dossier"])


def test_performance_cue_provenance(test_world):
    analyzer = SubtextAnalyzer()
    cue_gen = PerformanceCueGenerator()
    evelyn = test_world.characters["char_evelyn"]

    analysis = analyzer.analyze(
        speaker=evelyn,
        dialogue="I haven't seen it.",
        world=test_world,
        listener_id="char_vincent",
    )
    cue = cue_gen.generate_cue(
        analysis=analysis,
        character=evelyn,
        world=test_world,
        source_event_id="ev_042",
    )

    assert cue.is_performance_cue is True
    assert cue.derived_from_event_id == "ev_042"
    assert len(cue.derived_from_actor_state_ids) >= 2
    assert any("char_char_evelyn" in s for s in cue.derived_from_actor_state_ids)
