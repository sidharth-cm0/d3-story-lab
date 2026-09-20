"""Tests for Phase 8.1: Shot Planner, Domain Models, and Psychological Camera.

Verifies:
1. All 11 rules in Section 5's psychological camera table fire against crafted ShotContextSignals.
2. emotion is populated from PerformanceCue.observable_behaviour (assert source path, not raw emotion vector).
3. Every ShotPlan carries non-empty screenplay_block_ids and non-empty source_event_ids.
4. The full shot list is unbudgeted and not truncated to 4/8/12.
5. Crafted case with no strong signal produces the neutral default with honest rationale.
6. Acceptance on The Missing Dossier (world_init_4bef81).
"""

import json
import pytest
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.proposition import Proposition, KnowledgeItem
from src.domain.story_structure import DramaticFunction, Scene, SceneObjective
from src.narrative.performance_cues import PerformanceCue, PerformanceCueType, InternalStateVerbGuard
from src.narrative.fountain import ScreenplayDocument, ScreenplayScene, ScreenplayBlock
from src.narrative.scene_projection import (
    ObservableSceneProjection,
    ObservableBeat,
    ObservableDialogueLine,
    ObservableObjective,
    ObservableSceneProjector,
)
from src.narrative.scene_builder import SceneBuilder
from src.narrative.scribe import Scribe
from src.storage.project_store import ProjectStore
from src.storyboard.shot_planner import (
    ShotType,
    CameraAngle,
    ShotContextSignals,
    CompositionPlan,
    ShotPlan,
    ShotPlanner,
    evaluate_camera_rules,
    resolve_lens_feel,
    PSYCHOLOGICAL_CAMERA_RULES,
)


# =============================================================================
# 1. PSYCHOLOGICAL CAMERA RULES TABLE TESTS (ONE TEST PER ROW)
# =============================================================================

def test_row_1_diminished_exposed():
    """Row 1: power_differential < -0.3 and fear_level > 0.5 -> MEDIUM_CLOSE_UP, HIGH_ANGLE."""
    signals = ShotContextSignals(
        power_differential=-0.6,
        fear_level=0.75,
        certainty_level=0.3,
        information_advantage=-0.2,
        emotional_intensity=0.6,
    )
    shot_type, angle, rationale, contrib = evaluate_camera_rules(signals)
    assert shot_type == ShotType.MEDIUM_CLOSE_UP
    assert angle == CameraAngle.HIGH_ANGLE
    assert "diminished" in rationale.lower()
    assert contrib["rule_diminished_exposed_match"] == 1.0


def test_row_2_revelation_reaction():
    """Row 2: is_revelation_moment and is_reaction_beat -> REACTION, EYE_LEVEL or HIGH_ANGLE per fear."""
    # Low fear -> EYE_LEVEL
    signals_calm = ShotContextSignals(
        is_revelation_moment=True,
        is_reaction_beat=True,
        fear_level=0.3,
    )
    shot_type1, angle1, rationale1, _ = evaluate_camera_rules(signals_calm)
    assert shot_type1 == ShotType.REACTION
    assert angle1 == CameraAngle.EYE_LEVEL
    assert "realization" in rationale1.lower()

    # High fear -> HIGH_ANGLE
    signals_afraid = ShotContextSignals(
        is_revelation_moment=True,
        is_reaction_beat=True,
        fear_level=0.85,
    )
    shot_type2, angle2, rationale2, _ = evaluate_camera_rules(signals_afraid)
    assert shot_type2 == ShotType.REACTION
    assert angle2 == CameraAngle.HIGH_ANGLE
    assert "high angle" in rationale2.lower()


def test_row_3_empowering_low_angle():
    """Row 3: goal_progress_delta > 0.3 -> LOW_ANGLE (empowering angle)."""
    signals = ShotContextSignals(
        goal_progress_delta=0.45,
        power_differential=0.2,
    )
    shot_type, angle, rationale, contrib = evaluate_camera_rules(signals)
    assert angle == CameraAngle.LOW_ANGLE
    assert "empowering" in rationale.lower()
    assert contrib["rule_empowering_low_angle_angle_match"] == 1.0


def test_row_4_diminishing_high_angle():
    """Row 4: goal_progress_delta < -0.3 -> HIGH_ANGLE (diminishing angle)."""
    signals = ShotContextSignals(
        goal_progress_delta=-0.45,
        power_differential=-0.1,
    )
    shot_type, angle, rationale, contrib = evaluate_camera_rules(signals)
    assert angle == CameraAngle.HIGH_ANGLE
    assert "diminishing" in rationale.lower()
    assert contrib["rule_diminishing_high_angle_angle_match"] == 1.0


def test_row_5_two_character_information_advantage():
    """Row 5: information_advantage != 0, two-character exchange -> OVER_THE_SHOULDER, EYE_LEVEL."""
    signals = ShotContextSignals(
        information_advantage=0.55,
        certainty_level=0.8,
    )
    context = {"is_two_character_exchange": True}
    shot_type, angle, rationale, contrib = evaluate_camera_rules(signals, context)
    assert shot_type == ShotType.OVER_THE_SHOULDER
    assert angle == CameraAngle.EYE_LEVEL
    assert "informationally-advantaged" in rationale.lower()
    assert contrib["rule_two_character_info_advantage_match"] == 1.0


def test_row_6_intimate_intensity():
    """Row 6: emotional_intensity > 0.7, no clear power/info signal -> EXTREME_CLOSE_UP, EYE_LEVEL."""
    signals = ShotContextSignals(
        emotional_intensity=0.85,
        power_differential=0.1,
        information_advantage=0.0,
    )
    shot_type, angle, rationale, contrib = evaluate_camera_rules(signals)
    assert shot_type == ShotType.EXTREME_CLOSE_UP
    assert angle == CameraAngle.EYE_LEVEL
    assert "maximum intimacy" in rationale.lower()
    assert contrib["rule_intimate_intensity_match"] == 1.0


def test_row_7_scene_first_beat():
    """Row 7: scene's first beat -> ESTABLISHING or WIDE, EYE_LEVEL."""
    signals = ShotContextSignals()
    context = {"is_first_beat": True}
    shot_type, angle, rationale, contrib = evaluate_camera_rules(signals, context)
    assert shot_type in (ShotType.ESTABLISHING, ShotType.WIDE)
    assert angle == CameraAngle.EYE_LEVEL
    assert "orient the audience" in rationale.lower()
    assert contrib["rule_scene_first_beat_match"] == 1.0


def test_row_8_multiple_characters_ensemble():
    """Row 8: multiple characters, no single focal point -> WIDE, EYE_LEVEL."""
    signals = ShotContextSignals()
    context = {"num_characters": 3, "has_single_focal_point": False, "is_ensemble": True}
    shot_type, angle, rationale, contrib = evaluate_camera_rules(signals, context)
    assert shot_type == ShotType.WIDE
    assert angle == CameraAngle.EYE_LEVEL
    assert "ensemble" in rationale.lower()
    assert contrib["rule_ensemble_wide_match"] == 1.0


def test_row_9_physical_action_tracking():
    """Row 9: physical action / chase-type beat -> TRACKING, EYE_LEVEL."""
    signals = ShotContextSignals()
    context = {"is_physical_action": True}
    shot_type, angle, rationale, contrib = evaluate_camera_rules(signals, context)
    assert shot_type == ShotType.TRACKING
    assert angle == CameraAngle.EYE_LEVEL
    assert "tracking" in rationale.lower()
    assert contrib["rule_physical_action_tracking_match"] == 1.0


def test_row_10_destabilization_dutch_angle():
    """Row 10: SceneLink type BUT or dramatic REVERSAL -> DUTCH_ANGLE."""
    # Via BUT link
    signals = ShotContextSignals()
    context_but = {"link_type": "BUT"}
    _, angle_but, rationale_but, contrib_but = evaluate_camera_rules(signals, context_but)
    assert angle_but == CameraAngle.DUTCH_ANGLE
    assert "destabilization" in rationale_but.lower()

    # Via dramatic REVERSAL
    context_rev = {"dramatic_function": "REVERSAL"}
    _, angle_rev, rationale_rev, contrib_rev = evaluate_camera_rules(signals, context_rev)
    assert angle_rev == CameraAngle.DUTCH_ANGLE
    assert "destabilization" in rationale_rev.lower()


def test_row_11_neutral_default_honest_rationale():
    """Row 11: none of the above fire clearly -> MEDIUM, EYE_LEVEL, honest neutral rationale."""
    signals = ShotContextSignals(
        power_differential=0.0,
        fear_level=0.2,
        certainty_level=0.5,
        information_advantage=0.0,
        emotional_intensity=0.3,
        goal_progress_delta=0.0,
        is_revelation_moment=False,
        is_reaction_beat=False,
    )
    context = {
        "is_first_beat": False,
        "is_two_character_exchange": False,
        "has_single_focal_point": True,
        "is_physical_action": False,
        "is_ensemble": False,
    }
    shot_type, angle, rationale, contrib = evaluate_camera_rules(signals, context)
    assert shot_type == ShotType.MEDIUM
    assert angle == CameraAngle.EYE_LEVEL
    # MUST say verbatim: "no strong psychological signal, neutral default"
    assert rationale == "no strong psychological signal, neutral default"
    assert contrib["neutral_default"] == 1.0


# =============================================================================
# 2. SHOW-DON'T-TELL EMOTION INTEGRATION & VERB GUARD
# =============================================================================

def test_emotion_sourced_from_performance_cue_directly():
    """Test that emotion is populated directly from PerformanceCue.observable_behaviour and passes verb guard."""
    cue = PerformanceCue(
        id="cue_test_101",
        character_id="char_alpha",
        cue_type=PerformanceCueType.GESTURE_TICK,
        observable_behaviour="fingers drum a rapid rhythm against the wooden table edge",
        internal_intent="EVASIVE",
        intensity=0.8,
    )

    beat = ObservableBeat(
        event_id="evt_beat_1",
        description="Vincent denies the allegation, avoiding eye contact.",
        characters_involved=["char_alpha"],
        performance_cue_ids=["cue_test_101"],
    )

    proj = ObservableSceneProjection(
        scene_id="sc_01",
        location_label="INTERROGATION ROOM",
        time_label="NIGHT",
        characters_present=["char_alpha", "char_beta"],
        purpose=DramaticFunction.CONFRONTATION,
        objective=ObservableObjective(
            pov_character_id="char_alpha",
            wants="Conceal truth",
            obstacle="Direct questioning",
            outcome="PARTIAL",
        ),
        beats=[beat],
        performance_cues=[cue],
        source_event_ids=["evt_beat_1"],
    )

    block = ScreenplayBlock(
        block_id="blk_01",
        scene_id="sc_01",
        source_event_ids=["evt_beat_1"],
        element_type="ACTION",
        content="Vincent drums his fingers on the table.",
    )

    scene = ScreenplayScene(
        scene_number=1,
        location_id="loc_room",
        heading="INT. INTERROGATION ROOM - NIGHT",
        blocks=[block],
        source_event_ids=["evt_beat_1"],
        metadata={"scene_id": "sc_01"},
    )

    screenplay = ScreenplayDocument(scenes=[scene])
    planner = ShotPlanner()
    shots = planner.plan_shots_for_screenplay(screenplay, [proj])

    # 1 establishing shot + 1 beat shot
    assert len(shots) == 2
    beat_shot = shots[1]

    # Assert source path: exactly matching the PerformanceCue
    assert beat_shot.performance_cue_id == "cue_test_101"
    assert beat_shot.emotion == "fingers drum a rapid rhythm against the wooden table edge"

    # Verify no raw emotion vector value or unobservable verb
    assert "fear" not in beat_shot.emotion.lower()
    assert "feels" not in beat_shot.emotion.lower()
    assert "knows" not in beat_shot.emotion.lower()

    # Pass through InternalStateVerbGuard directly
    InternalStateVerbGuard.check_and_raise(beat_shot.emotion)


# =============================================================================
# 3. PROVENANCE & UNBUDGETED SHOT LIST TESTS
# =============================================================================

def test_every_shot_has_non_empty_provenance():
    """Test that every ShotPlan carries non-empty screenplay_block_ids and source_event_ids."""
    beat1 = ObservableBeat(event_id="evt_01", description="Character enters.", characters_involved=["char_a"])
    beat2 = ObservableBeat(event_id="evt_02", description="Character inspects safe.", characters_involved=["char_a"])

    proj = ObservableSceneProjection(
        scene_id="sc_01",
        location_label="VAULT",
        time_label="NIGHT",
        characters_present=["char_a"],
        purpose=DramaticFunction.SETUP,
        objective=ObservableObjective(pov_character_id="char_a", wants="Open safe", obstacle="Lock", outcome="ACHIEVED"),
        beats=[beat1, beat2],
        source_event_ids=["evt_01", "evt_02"],
    )

    slug = ScreenplayBlock(block_id="blk_slug", scene_id="sc_01", source_event_ids=["evt_01"], element_type="SLUGLINE", content="INT. VAULT - NIGHT")
    act1 = ScreenplayBlock(block_id="blk_act1", scene_id="sc_01", source_event_ids=["evt_01"], element_type="ACTION", content="A man enters.")
    act2 = ScreenplayBlock(block_id="blk_act2", scene_id="sc_01", source_event_ids=["evt_02"], element_type="ACTION", content="He approaches the safe.")

    scene = ScreenplayScene(
        scene_number=1,
        location_id="loc_vault",
        heading="INT. VAULT - NIGHT",
        blocks=[slug, act1, act2],
        source_event_ids=["evt_01", "evt_02"],
        metadata={"scene_id": "sc_01"},
    )

    screenplay = ScreenplayDocument(scenes=[scene])
    planner = ShotPlanner()
    shots = planner.plan_shots_for_screenplay(screenplay, [proj])

    # 1 establishing + 2 beats = 3 shots
    assert len(shots) == 3
    for shot in shots:
        assert isinstance(shot.screenplay_block_ids, list)
        assert len(shot.screenplay_block_ids) > 0, f"Shot {shot.shot_id} has empty screenplay_block_ids"
        assert isinstance(shot.source_event_ids, list)
        assert len(shot.source_event_ids) > 0, f"Shot {shot.shot_id} has empty source_event_ids"
        assert shot.rationale != ""
        assert len(shot.contributing_signals) > 0


def test_shot_list_not_truncated_to_budget():
    """Test that ShotPlanner plans ALL beats and does NOT truncate to 4, 8, or 12."""
    beats = [
        ObservableBeat(event_id=f"evt_{i:02d}", description=f"Beat {i} action occurs.", characters_involved=["char_a"])
        for i in range(15)
    ]

    proj = ObservableSceneProjection(
        scene_id="sc_long",
        location_label="HALLWAY",
        time_label="DAY",
        characters_present=["char_a"],
        purpose=DramaticFunction.ESCALATION,
        objective=ObservableObjective(pov_character_id="char_a", wants="Survive", obstacle="Guards", outcome="PARTIAL"),
        beats=beats,
        source_event_ids=[b.event_id for b in beats],
    )

    blocks = [
        ScreenplayBlock(block_id=f"blk_{i:02d}", scene_id="sc_long", source_event_ids=[f"evt_{i:02d}"], element_type="ACTION", content=f"Action line {i}")
        for i in range(15)
    ]

    scene = ScreenplayScene(
        scene_number=1,
        location_id="loc_hall",
        heading="INT. HALLWAY - DAY",
        blocks=blocks,
        source_event_ids=[b.event_id for b in beats],
        metadata={"scene_id": "sc_long"},
    )

    screenplay = ScreenplayDocument(scenes=[scene])
    planner = ShotPlanner()
    shots = planner.plan_shots_for_screenplay(screenplay, [proj])

    # 1 establishing + 15 beats = 16 shots total (NOT clamped to 4, 8, or 12)
    assert len(shots) == 16
    assert len(shots) > 12


# =============================================================================
# 4. ACCEPTANCE ON THE MISSING DOSSIER (LIVE PROJECT ACCEPTANCE)
# =============================================================================

def test_missing_dossier_acceptance():
    """Verify complete shot planning pipeline on The Missing Dossier (world_init_4bef81)."""
    store = ProjectStore()
    project = store.load_project("world_init_4bef81")
    assert project is not None, "world_init_4bef81 project must exist"

    # Enrich scenes and generate projections
    builder = SceneBuilder()
    enriched_scenes = builder.enrich_scenes_with_phase6(project.scenes, project.world)
    projector = ObservableSceneProjector()
    projections = projector.project_all_scenes(enriched_scenes, project.world)
    assert len(projections) == 3

    # Generate grounded screenplay
    scribe = Scribe(provider=None)
    doc = scribe.compose_from_projections(projections, title="THE MISSING DOSSIER")
    assert len(doc.scenes) == 3

    # Plan complete shot list
    planner = ShotPlanner()
    shot_list = planner.plan_shots_for_screenplay(
        screenplay=doc,
        projections=projections,
        world=project.world,
        scene_links=None,
    )

    # 1. Total Shot Count
    # Scene 1 has 4 beats (+1 establishing = 5)
    # Scene 2 has 4 beats (+1 establishing = 5)
    # Scene 3 has 12 beats (+1 establishing = 13)
    # Total = 23 shots
    assert len(shot_list) == 23

    # 2. Invariants Check Across Every Shot
    shot_types: dict[str, int] = {}
    angles: dict[str, int] = {}

    for shot in shot_list:
        assert isinstance(shot, ShotPlan)
        assert len(shot.screenplay_block_ids) > 0
        assert len(shot.source_event_ids) > 0
        assert shot.rationale != ""
        assert len(shot.contributing_signals) > 0
        assert shot.lens_feel in ("wide-angle distortion", "long lens compression", "normal")
        assert isinstance(shot.composition_plan, CompositionPlan)

        # Show-Don't-Tell check
        InternalStateVerbGuard.check_and_raise(shot.emotion)

        shot_types[shot.shot_type.value] = shot_types.get(shot.shot_type.value, 0) + 1
        angles[shot.camera_angle.value] = angles.get(shot.camera_angle.value, 0) + 1

    # Verify distributions contain expected cinematic variety
    assert "ESTABLISHING" in shot_types
    assert shot_types["ESTABLISHING"] == 3
    assert len(shot_types) >= 3
    assert len(angles) >= 2
