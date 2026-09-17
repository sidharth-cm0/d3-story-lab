"""Tests for Pre-Phase-5 Carry-Over Stabilization.

Covers:
1. Early-beat satisfaction: GOAL_ADOPTED opening beat vs later beat window semantics (Section 1).
2. SubtextAnalyzer migration to typed KnowledgeItem (Rule 4 & 5 compliance) with legacy fallback (Section 2).
"""

import pytest
from src.domain import (
    WorldState,
    Location,
    WorldObject,
    Character,
    EmotionalState,
    Secret,
    Belief,
    DiscoveredFact,
    Goal,
    GoalStatus,
    Proposition,
    KnowledgeItem,
)
from src.demo_world import create_demo_world
from src.simulation.differ import StateSnapshotDiffer
from src.story.models import PredicateClause
from src.narrative.subtext import SubtextAnalyzer, DeceptionClassification
from src.storage.project_store import ProjectStore


# ==============================================================================
# SECTION 1: EARLY-BEAT SATISFACTION (GOAL_ADOPTED DIAGNOSTIC & REGRESSION TESTS)
# ==============================================================================

def test_s1_01_goal_seeded_before_simulation_satisfies_opening_beat_at_tick_0():
    """1. Goal seeded before simulation satisfies opening beat starting at tick 0."""
    world = create_demo_world()
    differ = StateSnapshotDiffer(world)

    differ.capture_snapshot(0, world)
    differ.capture_snapshot(1, world)

    # Arjun has goal_arjun_001 seeded during world initialization
    clause_arjun = PredicateClause(type="GOAL_ADOPTED", character="char_arjun")
    assert differ.evaluate_clause(world, clause_arjun, start_tick=0, end_tick=1) is True

    # Generic clause without character specified evaluates to True if any character holds a seeded goal
    clause_generic = PredicateClause(type="GOAL_ADOPTED")
    assert differ.evaluate_clause(world, clause_generic, start_tick=0, end_tick=1) is True


def test_s1_02_goal_adopted_inside_later_beat_window_satisfies_that_window():
    """2. Goal actually adopted inside a later beat window satisfies that window."""
    world = create_demo_world()
    differ = StateSnapshotDiffer(world)

    differ.capture_snapshot(0, world)
    differ.capture_snapshot(2, world)

    # Adopt new goal at tick 3
    char = world.characters["char_arjun"]
    new_goal = Goal(
        id="goal_arjun_escaped",
        character_id="char_arjun",
        description="Escape the hotel through the service stairwell",
        status=GoalStatus.ACTIVE,
    )
    world.goals[new_goal.id] = new_goal
    char.goals.append(new_goal.id)
    differ.capture_snapshot(5, world)

    # Later window [2, 5] detects the transition
    clause = PredicateClause(type="GOAL_ADOPTED", character="char_arjun")
    assert differ.evaluate_clause(world, clause, start_tick=2, end_tick=5) is True


def test_s1_03_goal_already_present_before_later_window_does_not_count_as_newly_adopted():
    """3. Goal already present before a later window does NOT count as newly adopted."""
    world = create_demo_world()
    differ = StateSnapshotDiffer(world)

    differ.capture_snapshot(0, world)
    differ.capture_snapshot(2, world)
    differ.capture_snapshot(5, world)

    # Maya only had goal_maya_001 seeded at tick 0; no new goal adopted in [2, 5]
    clause_maya = PredicateClause(type="GOAL_ADOPTED", character="char_maya")
    assert differ.evaluate_clause(world, clause_maya, start_tick=2, end_tick=5) is False

    # Arjun also did not adopt a new goal in [2, 5]
    clause_arjun = PredicateClause(type="GOAL_ADOPTED", character="char_arjun")
    assert differ.evaluate_clause(world, clause_arjun, start_tick=2, end_tick=5) is False


# ==============================================================================
# SECTION 2: SUBTEXT ANALYZER KNOWLEDGE MIGRATION (REGRESSION TESTS)
# ==============================================================================

@pytest.fixture
def subtext_test_world():
    world = WorldState(
        id="world_subtext_test",
        name="Subtext Test World",
        description="Private knowledge testing environment",
    )
    loc = Location(
        id="loc_office",
        name="Private Office",
        description="Locked office with confidential files",
    )
    world.locations[loc.id] = loc

    evelyn = Character(
        id="char_evelyn",
        name="Evelyn",
        role="Undercover Agent",
        current_location_id=loc.id,
        emotional_state=EmotionalState(fear=0.3, anger=0.2, trust=0.1, curiosity=0.8),
    )
    vincent = Character(
        id="char_vincent",
        name="Vincent",
        role="Smuggler Boss",
        current_location_id=loc.id,
        emotional_state=EmotionalState(fear=0.2, anger=0.5, trust=0.2, curiosity=0.5),
    )
    world.characters[evelyn.id] = evelyn
    world.characters[vincent.id] = vincent

    return world


def test_s2_01_typed_knowledge_item_drives_subtext_analysis(subtext_test_world):
    """1. Typed KnowledgeItem drives subtext analysis."""
    world = subtext_test_world
    evelyn = world.characters["char_evelyn"]

    # Register canonical proposition
    prop = Proposition(
        id="prop_dossier_safe",
        subject="obj_dossier",
        predicate="concealed_in",
        object="loc_office_safe",
        truth_value=True,
        is_secret=True,
    )
    world.propositions[prop.id] = prop

    # Evelyn holds typed KnowledgeItem believing it to be true
    evelyn.knowledge[prop.id] = KnowledgeItem(
        proposition_id=prop.id,
        holder_id=evelyn.id,
        believed_truth_value=True,
    )

    analyzer = SubtextAnalyzer()
    analysis = analyzer.analyze(
        speaker=evelyn,
        dialogue="I haven't seen any dossier in this room.",
        world=world,
        listener_id="char_vincent",
    )

    assert DeceptionClassification.LYING in analysis.classifications
    assert DeceptionClassification.CONCEALING in analysis.classifications
    assert analysis.conflict_focus_object == "dossier"
    assert analysis.cognitive_dissonance_score > 0.7
    assert "obj_dossier concealed_in loc_office_safe" in (analysis.private_truth_summary or "")


def test_s2_02_false_belief_remains_false_from_character_perspective(subtext_test_world):
    """2. False belief remains false from that character's perspective."""
    world = subtext_test_world
    evelyn = world.characters["char_evelyn"]

    # Canonical truth: dossier IS in the safe
    prop = Proposition(
        id="prop_dossier_safe",
        subject="obj_dossier",
        predicate="concealed_in",
        object="loc_office_safe",
        truth_value=True,
        is_secret=True,
    )
    world.propositions[prop.id] = prop

    # Evelyn holds a false belief: she subjectively believes the dossier is NOT in the safe
    evelyn.knowledge[prop.id] = KnowledgeItem(
        proposition_id=prop.id,
        holder_id=evelyn.id,
        believed_truth_value=False,
    )

    analyzer = SubtextAnalyzer()
    analysis = analyzer.analyze(
        speaker=evelyn,
        dialogue="I haven't seen any dossier in this room.",
        world=world,
        listener_id="char_vincent",
    )

    # From Evelyn's subjective perspective, she is being TRUTHFUL because she believes it is not there
    assert DeceptionClassification.LYING not in analysis.classifications
    assert analysis.primary_classification == DeceptionClassification.TRUTHFUL
    assert analysis.cognitive_dissonance_score == 0.0


def test_s2_03_unheld_secret_does_not_become_known(subtext_test_world):
    """3. Unheld secret does not become known."""
    world = subtext_test_world
    evelyn = world.characters["char_evelyn"]

    # Proposition is secret in the world, but Evelyn has NO knowledge item for it
    prop = Proposition(
        id="prop_ledger_stolen",
        subject="obj_ledger",
        predicate="stolen_by",
        object="char_vincent",
        truth_value=True,
        is_secret=True,
    )
    world.propositions[prop.id] = prop
    assert prop.id not in evelyn.knowledge

    analyzer = SubtextAnalyzer()
    analysis = analyzer.analyze(
        speaker=evelyn,
        dialogue="I haven't seen any ledger around here.",
        world=world,
        listener_id="char_vincent",
    )

    # Evelyn does not hold the secret, so she cannot be classified as lying about it
    assert DeceptionClassification.LYING not in analysis.classifications
    assert analysis.primary_classification == DeceptionClassification.TRUTHFUL


def test_s2_04_another_character_private_knowledge_not_leaked(subtext_test_world):
    """4. Another character's private KnowledgeItem is not leaked."""
    world = subtext_test_world
    evelyn = world.characters["char_evelyn"]
    vincent = world.characters["char_vincent"]

    prop = Proposition(
        id="prop_vincent_stash",
        subject="obj_money",
        predicate="hidden_in",
        object="loc_vault",
        truth_value=True,
        is_secret=True,
    )
    world.propositions[prop.id] = prop

    # ONLY Vincent holds this knowledge
    vincent.knowledge[prop.id] = KnowledgeItem(
        proposition_id=prop.id,
        holder_id=vincent.id,
        believed_truth_value=True,
    )
    assert prop.id not in evelyn.knowledge

    analyzer = SubtextAnalyzer()
    analysis = analyzer.analyze(
        speaker=evelyn,
        dialogue="I have no idea about any hidden money.",
        world=world,
        listener_id="char_vincent",
    )

    # Evelyn does NOT leak or trigger Vincent's private knowledge
    assert DeceptionClassification.LYING not in analysis.classifications
    assert analysis.primary_classification == DeceptionClassification.TRUTHFUL


def test_s2_05_changing_only_legacy_known_facts_does_not_change_typed_output(subtext_test_world):
    """5. Changing only legacy known_facts does not change typed-mode output."""
    world = subtext_test_world
    evelyn = world.characters["char_evelyn"]

    prop = Proposition(
        id="prop_dossier_safe",
        subject="obj_dossier",
        predicate="concealed_in",
        object="loc_office_safe",
        truth_value=True,
        is_secret=True,
    )
    world.propositions[prop.id] = prop
    evelyn.knowledge[prop.id] = KnowledgeItem(
        proposition_id=prop.id,
        holder_id=evelyn.id,
        believed_truth_value=True,
    )

    analyzer = SubtextAnalyzer()
    evelyn.known_facts = []
    res1 = analyzer.analyze(
        speaker=evelyn,
        dialogue="I haven't seen any dossier in this room.",
        world=world,
        listener_id="char_vincent",
    )

    evelyn.known_facts = ["fact_bogus_1", "fact_bogus_2"]
    res2 = analyzer.analyze(
        speaker=evelyn,
        dialogue="I haven't seen any dossier in this room.",
        world=world,
        listener_id="char_vincent",
    )

    assert res1.classifications == res2.classifications
    assert res1.primary_classification == res2.primary_classification
    assert res1.cognitive_dissonance_score == res2.cognitive_dissonance_score
    assert res1.conflict_focus_object == res2.conflict_focus_object


def test_s2_06_changing_only_legacy_beliefs_does_not_change_typed_output(subtext_test_world):
    """6. Changing only legacy beliefs does not change typed-mode output."""
    world = subtext_test_world
    evelyn = world.characters["char_evelyn"]

    prop = Proposition(
        id="prop_dossier_safe",
        subject="obj_dossier",
        predicate="concealed_in",
        object="loc_office_safe",
        truth_value=True,
        is_secret=True,
    )
    world.propositions[prop.id] = prop
    evelyn.knowledge[prop.id] = KnowledgeItem(
        proposition_id=prop.id,
        holder_id=evelyn.id,
        believed_truth_value=True,
    )

    analyzer = SubtextAnalyzer()
    evelyn.beliefs = []
    res1 = analyzer.analyze(
        speaker=evelyn,
        dialogue="I haven't seen any dossier in this room.",
        world=world,
        listener_id="char_vincent",
    )

    evelyn.beliefs = ["bel_bogus_1", "bel_bogus_2"]
    res2 = analyzer.analyze(
        speaker=evelyn,
        dialogue="I haven't seen any dossier in this room.",
        world=world,
        listener_id="char_vincent",
    )

    assert res1.classifications == res2.classifications
    assert res1.primary_classification == res2.primary_classification
    assert res1.cognitive_dissonance_score == res2.cognitive_dissonance_score
    assert res1.conflict_focus_object == res2.conflict_focus_object


def test_s2_07_legacy_project_migration_still_succeeds(subtext_test_world):
    """7. Legacy project migration still succeeds (fallback mode when knowledge is empty)."""
    world = subtext_test_world
    evelyn = world.characters["char_evelyn"]

    # evelyn.knowledge is empty (legacy project representation)
    evelyn.knowledge = {}

    secret = Secret(
        id="sec_dossier",
        character_id=evelyn.id,
        statement="Evelyn knows the stolen classified dossier is concealed inside the metal cabinet.",
        known_by=[evelyn.id],
        importance=0.9,
    )
    world.secrets[secret.id] = secret
    evelyn.secrets.append(secret.id)

    analyzer = SubtextAnalyzer()
    analysis = analyzer.analyze(
        speaker=evelyn,
        dialogue="I haven't seen any dossier in this room.",
        world=world,
        listener_id="char_vincent",
    )

    # Legacy fallback produces valid subtext analysis
    assert DeceptionClassification.LYING in analysis.classifications
    assert DeceptionClassification.CONCEALING in analysis.classifications
    assert analysis.conflict_focus_object == "dossier"
    assert analysis.cognitive_dissonance_score > 0.7
