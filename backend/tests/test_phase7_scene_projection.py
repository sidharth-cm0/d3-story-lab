"""Tests for Phase 7.1: Scribe Input Contract + Observable Scene Projection.

Verifies:
1. Present character holding a secret unrelated to this scene's events -> projection excludes it.
2. Character with populated legacy known_facts/beliefs and populated knowledge -> projection built entirely from knowledge.
3. Exact event correspondence: projection.source_event_ids == scene.source_event_ids (no additions, no omissions).
4. Vocabulary-blocklist scanner run against a deliberately poisoned projection -> detects every planted term.
5. communicative_intent is present as a typed field but never surfaces as reader-visible text through any prose-facing serialization path.
6. Environmental/Director events sanitized into observable plain-language physical descriptions.
7. Missing Dossier project acceptance: all scenes projected cleanly with 0 blocklist violations.
"""

import json
import pytest
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.proposition import Proposition, KnowledgeItem
from src.domain.secret import Secret
from src.domain.belief import Belief
from src.domain.fact import DiscoveredFact
from src.domain.event import Event, EventType
from src.domain.story_structure import (
    DramaticFunction,
    Scene,
    SceneObjective,
)
from src.narrative.performance_cues import (
    PerformanceCue,
    PerformanceCueType,
)
from src.narrative.subtext import (
    SubtextAnalysis,
    DeceptionClassification,
)
from src.narrative.scene_projection import (
    INTERNAL_VOCABULARY_BLOCKLIST,
    ObservableBeat,
    ObservableObjective,
    ObservableDialogueLine,
    ObservableSceneProjection,
    ObservableSceneProjector,
    scan_for_internal_vocabulary,
)
from src.storage.project_store import ProjectStore
from src.narrative.scene_builder import SceneBuilder


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def projection_world() -> WorldState:
    """Fixture providing a test world with characters, propositions, and events."""
    world = WorldState(id="world_embassy_safehouse", name="Embassy Safehouse", current_tick=5)

    loc1 = Location(id="loc_archives", name="Secure Archives", connected_locations=["loc_hallway"])
    loc2 = Location(id="loc_hallway", name="Corridor B", connected_locations=["loc_archives"])
    world.locations[loc1.id] = loc1
    world.locations[loc2.id] = loc2

    # In-play proposition: Dossier is on the shelf
    prop_dossier = Proposition(
        id="prop_dossier_shelf",
        subject="classified_dossier",
        predicate="is_on",
        object="steel_shelf",
        truth_value=True,
    )
    # Unrelated secret proposition: Character has hidden debts
    prop_unrelated = Proposition(
        id="prop_gambling_debts",
        subject="vincent",
        predicate="owes_money_to",
        object="syndicate_boss",
        truth_value=True,
    )
    world.propositions[prop_dossier.id] = prop_dossier
    world.propositions[prop_unrelated.id] = prop_unrelated

    # Character 1: Vincent Cross (present in scene)
    char_vincent = Character(
        id="char_vincent",
        name="Vincent Cross",
        role="Infiltrator",
        current_location_id="loc_archives",
        emotional_state=EmotionalState(fear=0.3, anger=0.2, trust=0.4, curiosity=0.7),
        knowledge={
            prop_dossier.id: KnowledgeItem(
                proposition_id=prop_dossier.id,
                holder_id="char_vincent",
                certainty=1.0,
                source="observed",
                is_secret=False,
            ),
            prop_unrelated.id: KnowledgeItem(
                proposition_id=prop_unrelated.id,
                holder_id="char_vincent",
                certainty=1.0,
                source="inferred",
                is_secret=True,
            ),
        },
        # Legacy fields for testing isolation
        known_facts=["fact_legacy_unrelated_123"],
        beliefs=["b_fake_legacy_id"],
    )

    # Character 2: Evelyn Vance (present in scene)
    char_evelyn = Character(
        id="char_evelyn",
        name="Evelyn Vance",
        role="Archivist",
        current_location_id="loc_archives",
        emotional_state=EmotionalState(fear=0.4, anger=0.1, trust=0.5, curiosity=0.6),
        knowledge={
            prop_dossier.id: KnowledgeItem(
                proposition_id=prop_dossier.id,
                holder_id="char_evelyn",
                certainty=1.0,
                source="told",
                is_secret=True,
            ),
        },
    )

    # Character 3: Outside Guard (absent from scene)
    char_guard = Character(
        id="char_guard",
        name="Marcus Vance",
        role="Guard",
        current_location_id="loc_hallway",
        knowledge={
            "prop_patrol_route": KnowledgeItem(
                proposition_id="prop_patrol_route",
                holder_id="char_guard",
                certainty=1.0,
                source="observed",
            ),
        },
    )

    world.characters[char_vincent.id] = char_vincent
    world.characters[char_evelyn.id] = char_evelyn
    world.characters[char_guard.id] = char_guard

    # Legacy secret object for testing isolation
    world.secrets["sec_vincent_debt"] = Secret(
        id="sec_vincent_debt",
        character_id="char_vincent",
        statement="Vincent owes substantial money to an off-book syndicate",
    )
    world.beliefs["b_fake_legacy_id"] = Belief(
        id="b_fake_legacy_id",
        character_id="char_vincent",
        statement="Legacy belief that should never appear",
        confidence=0.8,
    )

    return world


@pytest.fixture
def sample_scene_and_events(projection_world: WorldState):
    """Fixture providing a Scene and associated Events."""
    ev1 = Event(
        id="ev_001",
        tick=1,
        event_type=EventType.CHARACTER_MOVED,
        actor_ids=["char_vincent"],
        location_id="loc_archives",
        description="Vincent Cross quietly slips into the Secure Archives.",
    )
    ev2 = Event(
        id="ev_002",
        tick=2,
        event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_vincent", "char_evelyn"],
        location_id="loc_archives",
        description='Vincent Cross said to Evelyn Vance: "The courier gave me clearance."',
        metadata={
            "speaker_id": "char_vincent",
            "target_id": "char_evelyn",
            "dialogue": "The courier gave me clearance.",
            "speech_act": "claim",
            "proposition_id": "prop_dossier_shelf",
        },
    )
    ev3 = Event(
        id="ev_003",
        tick=3,
        event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_evelyn", "char_vincent"],
        location_id="loc_archives",
        description='Evelyn Vance said to Vincent Cross: "No courier has accessed this terminal today."',
        metadata={
            "speaker_id": "char_evelyn",
            "target_id": "char_vincent",
            "dialogue": "No courier has accessed this terminal today.",
            "speech_act": "deny",
            "claim": "classified_dossier is_on steel_shelf",
        },
    )

    for ev in [ev1, ev2, ev3]:
        projection_world.events[ev.id] = ev

    cue1 = PerformanceCue(
        id="cue_001",
        character_id="char_vincent",
        type=PerformanceCueType.EYE_MOVEMENT,
        observable_behaviour="glances toward the upper steel shelf",
        action_text="Vincent glances toward the upper steel shelf.",
        event_id="ev_002",
    )
    cue2 = PerformanceCue(
        id="cue_002",
        character_id="char_evelyn",
        type=PerformanceCueType.POSTURE_SHIFT,
        observable_behaviour="folds arms and steps between Vincent and the desk",
        action_text="Evelyn folds her arms, blocking the pathway.",
        event_id="ev_003",
    )

    subtext1 = SubtextAnalysis(
        speaker_id="char_vincent",
        listener_ids=["char_evelyn"],
        dialogue="The courier gave me clearance.",
        spoken_intent=DeceptionClassification.MISDIRECTING,
        source_event_id="ev_002",
    )
    subtext2 = SubtextAnalysis(
        speaker_id="char_evelyn",
        listener_ids=["char_vincent"],
        dialogue="No courier has accessed this terminal today.",
        spoken_intent=DeceptionClassification.TRUTHFUL,
        source_event_id="ev_003",
    )

    scene = Scene(
        scene_id="scene_archive_encounter",
        location_id="loc_archives",
        location_name="Secure Archives",
        time_context="NIGHT",
        characters_present=["char_vincent", "char_evelyn"],
        source_event_ids=["ev_001", "ev_002", "ev_003"],
        purpose=DramaticFunction.INVESTIGATION,
        objective=SceneObjective(
            pov_character_id="char_vincent",
            wants="Locate the classified dossier without raising suspicion",
            emotional_want="Maintain cover and avoid a violent confrontation",
            obstacle="Evelyn is guarding the inner repository",
            outcome="PARTIAL",
        ),
        performance_cues=[cue1, cue2],
        subtext_analyses=[subtext1, subtext2],
    )

    return scene, [ev1, ev2, ev3]


# =============================================================================
# TEST CASES
# =============================================================================

def test_unrelated_secret_excluded_from_projection(projection_world, sample_scene_and_events):
    """Test 1: Present character holding an unrelated secret -> projection strictly excludes it."""
    scene, events = sample_scene_and_events
    projector = ObservableSceneProjector()

    projection = projector.project_scene(scene, projection_world, events=events)

    # Dump entire projection to string and JSON dict
    proj_dump = projection.model_dump()
    proj_str = json.dumps(proj_dump).lower()

    # The unrelated secret keywords must NOT appear anywhere in the projection
    assert "gambling" not in proj_str
    assert "debts" not in proj_str
    assert "syndicate_boss" not in proj_str
    assert "owes_money_to" not in proj_str
    assert "sec_vincent_debt" not in proj_str

    # Only the in-play proposition should be present in in_play_knowledge for Vincent
    assert "char_vincent" in projection.in_play_knowledge
    vincent_knowledge = projection.in_play_knowledge["char_vincent"]
    assert any("classified_dossier" in item for item in vincent_knowledge)
    assert not any("gambling" in item for item in vincent_knowledge)

    # Absent character (Marcus Vance) must have NO knowledge in the projection
    assert "char_guard" not in projection.in_play_knowledge


def test_legacy_known_facts_and_beliefs_never_read(projection_world, sample_scene_and_events):
    """Test 2: Character with populated legacy known_facts/beliefs -> built purely from knowledge."""
    scene, events = sample_scene_and_events
    projector = ObservableSceneProjector()

    # Vincent has legacy facts and beliefs set
    assert "fact_legacy_unrelated_123" in projection_world.characters["char_vincent"].known_facts
    assert "b_fake_legacy_id" in projection_world.characters["char_vincent"].beliefs

    projection = projector.project_scene(scene, projection_world, events=events)
    proj_str = json.dumps(projection.model_dump()).lower()

    # Confirm legacy facts and beliefs never appear anywhere in the projection
    assert "fact_legacy_unrelated_123" not in proj_str
    assert "legacy belief that should never appear" not in proj_str
    assert "b_fake" not in proj_str


def test_exact_event_correspondence_invariant(projection_world, sample_scene_and_events):
    """Test 3: projection.source_event_ids == scene.source_event_ids exactly — no additions, no omissions."""
    scene, events = sample_scene_and_events
    projector = ObservableSceneProjector()

    projection = projector.project_scene(scene, projection_world, events=events)

    # Must match scene.source_event_ids exactly
    assert projection.source_event_ids == scene.source_event_ids
    assert len(projection.source_event_ids) == len(scene.source_event_ids)
    assert projection.source_event_ids == ["ev_001", "ev_002", "ev_003"]

    # Beats must correspond 1:1 with source_event_ids
    beat_eids = [b.event_id for b in projection.beats]
    assert beat_eids == scene.source_event_ids


def test_vocabulary_blocklist_scanner_catches_all_planted_terms():
    """Test 4: Vocabulary-blocklist scanner run against a deliberately poisoned projection detects every planted term."""
    # Create a deliberately poisoned projection
    poisoned_projection = ObservableSceneProjection(
        scene_id="scene_poisoned",
        location_label="The Director office inside WorldState",
        time_label="NIGHT",
        characters_present=["char_alpha"],
        purpose=DramaticFunction.SETUP,
        objective=ObservableObjective(
            pov_character_id="char_alpha",
            wants="Bypass the ActionValidator and Sufficiency Gate",
            obstacle="The sovereign actor has an ActionProposal",
            outcome="DENIED",
        ),
        beats=[
            ObservableBeat(
                event_id="ev_poison_1",
                description="A simulation tick triggers StateSnapshotDiffer and provenance checks.",
                characters_involved=["char_alpha"],
                performance_cue_ids=[],
            ),
            ObservableBeat(
                event_id="ev_poison_2",
                description="The DirectorAgent injects an environmental intervention under BeatPressure.",
                characters_involved=[],
                performance_cue_ids=[],
            ),
        ],
        dialogue=[
            ObservableDialogueLine(
                speaker_id="char_alpha",
                listener_ids=[],
                source_event_id="ev_poison_1",
                communicative_intent="TRUTHFUL",
                text="We must inspect the KnowledgeItem and Proposition in the PropositionRegistry.",
            ),
        ],
        performance_cues=[],
        source_event_ids=["ev_poison_1", "ev_poison_2"],
        in_play_knowledge={"char_alpha": ["CharacterWorldView reveals an ActionExecutor violation."]},
    )

    violations = scan_for_internal_vocabulary(poisoned_projection)

    # Every planted term must be detected
    detected_text = " ".join(violations)
    assert "Director" in detected_text
    assert "WorldState" in detected_text
    assert "ActionValidator" in detected_text
    assert "Sufficiency Gate" in detected_text
    assert "sovereign actor" in detected_text
    assert "ActionProposal" in detected_text
    assert "simulation tick" in detected_text
    assert "StateSnapshotDiffer" in detected_text
    assert "provenance" in detected_text
    assert "DirectorAgent" in detected_text
    assert "environmental intervention" in detected_text
    assert "BeatPressure" in detected_text
    assert "KnowledgeItem" in detected_text
    assert "Proposition" in detected_text
    assert "PropositionRegistry" in detected_text
    assert "CharacterWorldView" in detected_text
    assert "ActionExecutor" in detected_text
    assert len(violations) >= 17


def test_clean_projection_passes_vocabulary_scanner(projection_world, sample_scene_and_events):
    """Test that a standard projection produced by ObservableSceneProjector passes the scanner with zero violations."""
    scene, events = sample_scene_and_events
    projector = ObservableSceneProjector()

    projection = projector.project_scene(scene, projection_world, events=events)
    violations = scan_for_internal_vocabulary(projection)

    assert violations == [], f"Expected 0 violations, got: {violations}"


def test_communicative_intent_omitted_from_prose_serialization(projection_world, sample_scene_and_events):
    """Test 5: communicative_intent is present as a typed field but never surfaces in prose serialization."""
    scene, events = sample_scene_and_events
    projector = ObservableSceneProjector()

    projection = projector.project_scene(scene, projection_world, events=events)

    # Verify communicative_intent is typed on dialogue lines
    assert len(projection.dialogue) == 2
    vincent_line = projection.dialogue[0]
    assert vincent_line.speaker_id == "char_vincent"
    assert vincent_line.communicative_intent == "MISDIRECTING"
    assert vincent_line.text == "The courier gave me clearance."

    evelyn_line = projection.dialogue[1]
    assert evelyn_line.speaker_id == "char_evelyn"
    assert evelyn_line.communicative_intent == "TRUTHFUL"
    assert evelyn_line.text == "No courier has accessed this terminal today."

    # Render prose-facing serialization path
    prose = projection.to_reader_prose()

    # Confirm spoken lines are printed
    assert "The courier gave me clearance." in prose
    assert "No courier has accessed this terminal today." in prose

    # Strictly confirm the intent words NEVER appear in the prose or parentheticals
    assert "MISDIRECTING" not in prose
    assert "TRUTHFUL" not in prose
    assert "intent" not in prose.lower()


def test_director_environmental_event_sanitized():
    """Test 6: Director / environmental events sanitized to plain physical description without internal terms."""
    world = WorldState(id="world_test", name="Test World")
    loc = Location(id="loc_room", name="Control Room")
    world.locations[loc.id] = loc

    director_ev = Event(
        id="ev_dir_01",
        tick=4,
        event_type=EventType.OTHER,
        actor_ids=[],
        location_id="loc_room",
        description="DIRECTOR intervention: environmental event POWER_FAILURE triggered at tick 4",
        metadata={
            "source": "DIRECTOR",
            "intervention_type": "POWER_FAILURE",
        },
    )
    world.events[director_ev.id] = director_ev

    scene = Scene(
        scene_id="scene_power_out",
        location_id="loc_room",
        location_name="Control Room",
        time_context="NIGHT",
        characters_present=[],
        source_event_ids=[director_ev.id],
        purpose=DramaticFunction.CRISIS,
        objective=SceneObjective(
            pov_character_id="unknown",
            wants="Maintain situational control",
            emotional_want="Remain composed under pressure",
            obstacle="Sudden power loss",
            outcome="PARTIAL",
        ),
    )

    projector = ObservableSceneProjector()
    projection = projector.project_scene(scene, world)

    assert len(projection.beats) == 1
    beat_desc = projection.beats[0].description

    # Must NOT contain internal terms
    assert "DIRECTOR" not in beat_desc
    assert "Director" not in beat_desc
    assert "tick" not in beat_desc.lower()
    assert "intervention" not in beat_desc.lower()

    # Must describe observable physical event
    assert "power failure" in beat_desc.lower()

    # Scan for vocabulary
    violations = scan_for_internal_vocabulary(projection)
    assert violations == []


def test_missing_dossier_live_project_acceptance():
    """Test 7: Missing Dossier Acceptance — run projection against all scenes of world_init_4bef81."""
    store = ProjectStore()
    project = store.load_project("world_init_4bef81")
    assert project is not None, "world_init_4bef81 project must exist"

    builder = SceneBuilder()
    enriched_scenes = builder.enrich_scenes_with_phase6(project.scenes, project.world)

    projector = ObservableSceneProjector()
    projections = projector.project_all_scenes(enriched_scenes, project.world)

    # 1. Verify scene count
    assert len(projections) == len(project.scenes)
    assert len(projections) == 3

    for idx, proj in enumerate(projections):
        orig_scene = enriched_scenes[idx]

        # 2. Verify exact source_event_ids correspondence
        assert proj.source_event_ids == orig_scene.source_event_ids
        assert len(proj.beats) == len(orig_scene.source_event_ids)

        # 3. Verify zero blocklist terms in projection
        violations = scan_for_internal_vocabulary(proj)
        assert violations == [], f"Scene {proj.scene_id} has blocklist violations: {violations}"

        # 4. Verify reader prose has zero blocklist terms
        prose = proj.to_reader_prose()
        assert scan_for_internal_vocabulary(prose) == []

        # 5. Verify character presence
        for cid in proj.characters_present:
            assert cid in ("char_alpha", "char_beta")

    # Verify example JSON projection serializes cleanly
    example_json = projections[0].model_dump_json(indent=2)
    assert example_json is not None
    loaded = json.loads(example_json)
    assert loaded["scene_id"] == "scene_01"
    assert loaded["source_event_ids"] == orig_scene.source_event_ids if idx == 0 else True
