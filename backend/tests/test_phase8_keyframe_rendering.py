"""Tests for Phase 8.2: Visual Bible, Keyframe Budgeting, and Grounded SVG Rendering.

Verifies:
1. KeyframeSelector selects exactly N shots for budget N, in correct priority order.
2. Repeated reference to same entity_id reuses cached VisualBible entry (generation invoked once).
3. Deterministic fallback produces complete Visual Bible with generic-but-honest placeholders.
4. Assembled prompts pass vocabulary blocklist and InternalStateVerbGuard (poisoned prompt rejected).
5. Full pipeline with image provider disabled produces exactly N StoryboardPanel records, all DETERMINISTIC_SVG_FALLBACK.
6. Content-hash caching prevents re-rendering identical shots (reusing Phase 1 budget governor).
7. Missing Dossier acceptance at budget=4, 8, 12.
"""

import pytest
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.narrative.performance_cues import PerformanceCue, PerformanceCueType, InternalStateVerbGuard
from src.storyboard.shot_planner import (
    ShotPlan,
    ShotType,
    CameraAngle,
    CompositionPlan,
    ShotPlanner,
)
from src.storyboard.keyframe_rendering import (
    CharacterVisualRef,
    LocationVisualRef,
    PropVisualRef,
    VisualBible,
    ContinuityPack,
    StoryboardPanel,
    KeyframeSelector,
    PRIORITY_ORDER,
    VisualBibleBuilder,
    StoryboardPromptBuilder,
    GroundedStoryboardRenderer,
)
from src.providers.budget import BudgetGovernor, ContentHashCache
from src.storage.project_store import ProjectStore
from src.narrative.scene_builder import SceneBuilder
from src.narrative.scene_projection import ObservableSceneProjector
from src.narrative.scribe import Scribe


# =============================================================================
# 1. KEYFRAME SELECTOR TESTS
# =============================================================================

def test_keyframe_selector_exact_count_and_priority_order():
    """Test that KeyframeSelector selects exactly N shots for budget N in priority order."""
    shots = [
        ShotPlan(
            shot_id=f"shot_{i:02d}",
            scene_id="scene_01",
            screenplay_block_ids=[f"blk_{i}"],
            source_event_ids=[f"evt_{i}"],
            shot_type=ShotType.MEDIUM,
            camera_angle=CameraAngle.EYE_LEVEL,
            lens_feel="normal",
            subject_focus="char_alpha",
            rationale="neutral default",
            emotion="composed posture, observant expression",
            composition_plan=CompositionPlan(framing_rect="0,0,1920,1080", focal_point="char_alpha"),
        )
        for i in range(10)
    ]

    # Craft specific priority signals
    # shot_0: SCENE_OPENING (establishing)
    shots[0].shot_type = ShotType.ESTABLISHING
    shots[0].contributing_signals["scene_opening"] = 1.0

    # shot_1: CHARACTER_INTRODUCTION (char_beta introduced)
    shots[1].actor_positions = {"char_beta": "staging_zone_1"}

    # shot_2: CLUE_DISCOVERY (dossier found)
    shots[2].contributing_signals["is_revelation_moment"] = 1.0
    shots[2].important_props = ["prop_dossier"]

    # shot_3: REACTION
    shots[3].shot_type = ShotType.REACTION
    shots[3].contributing_signals["is_reaction_beat"] = 1.0

    # shot_4: MIDPOINT_REVERSAL
    shots[4].camera_angle = CameraAngle.DUTCH_ANGLE
    shots[4].rationale = "destabilization reversal"

    # Test budget=4
    selected_4 = KeyframeSelector.select_keyframes(shots, budget=4)
    assert len(selected_4) == 4
    selected_ids_4 = [s.shot_id for s in selected_4]
    # Priority order guarantees top priority shots are included
    assert "shot_00" in selected_ids_4  # SCENE_OPENING
    assert "shot_01" in selected_ids_4  # CHARACTER_INTRODUCTION
    assert "shot_02" in selected_ids_4  # CLUE_DISCOVERY

    # Test budget=8
    selected_8 = KeyframeSelector.select_keyframes(shots, budget=8)
    assert len(selected_8) == 8

    # Test budget=12 (when shots length is 10, returns min(12, 10) = 10)
    selected_12 = KeyframeSelector.select_keyframes(shots, budget=12)
    assert len(selected_12) == 10


# =============================================================================
# 2. VISUAL BIBLE CACHING & PROP SCOPING
# =============================================================================

def test_visual_bible_cached_reuse():
    """Test that repeated reference to same entity_id reuses cached VisualBible entry."""
    world = WorldState(id="w1", name="Test World")
    char = Character(id="char_alpha", name="Vincent Cross", role="Infiltrator")
    world.characters[char.id] = char

    builder = VisualBibleBuilder(world=world)

    # First access
    ref1 = builder.get_or_create_character("char_alpha")
    assert builder.generation_counts["char_alpha"] == 1

    # Second access
    ref2 = builder.get_or_create_character("char_alpha")
    assert builder.generation_counts["char_alpha"] == 1  # Still 1! Not N!
    assert ref1 is ref2

    # Third access
    ref3 = builder.get_or_create_character("char_alpha")
    assert builder.generation_counts["char_alpha"] == 1


def test_prop_scoping_only_important_props():
    """Test that only props appearing in ShotPlan.important_props are built in VisualBible."""
    world = WorldState(id="w1", name="Test World")
    obj1 = WorldObject(id="prop_dossier", name="Classified Dossier")
    obj2 = WorldObject(id="prop_random_lamp", name="Desk Lamp")
    obj3 = WorldObject(id="prop_chair", name="Wooden Chair")
    world.objects[obj1.id] = obj1
    world.objects[obj2.id] = obj2
    world.objects[obj3.id] = obj3

    # Shot only references prop_dossier
    shot = ShotPlan(
        shot_id="s1",
        scene_id="sc1",
        screenplay_block_ids=["b1"],
        source_event_ids=["e1"],
        shot_type=ShotType.MEDIUM,
        camera_angle=CameraAngle.EYE_LEVEL,
        lens_feel="normal",
        subject_focus="char_alpha",
        important_props=["prop_dossier"],  # Only dossier!
        emotion="watchful expression",
        rationale="neutral default",
        composition_plan=CompositionPlan(framing_rect="0,0,1920,1080", focal_point="char_alpha"),
    )

    builder = VisualBibleBuilder(world=world)
    bible = builder.populate_for_shots([shot])

    # Only prop_dossier in bible.props
    assert "prop_dossier" in bible.props
    assert "prop_random_lamp" not in bible.props
    assert "prop_chair" not in bible.props


def test_deterministic_fallback_honest_placeholders():
    """Test that unpopulated entities get honest generic placeholders, never fabricated specifics."""
    # Empty world with no character/location metadata
    world = WorldState(id="w_empty", name="Empty World")
    builder = VisualBibleBuilder(world=world)

    char_ref = builder.get_or_create_character("char_unknown")
    assert char_ref.face == "unspecified features"
    assert char_ref.hair == "unspecified hair"
    assert char_ref.wardrobe == "neutral attire"

    loc_ref = builder.get_or_create_location("loc_unknown")
    assert loc_ref.architecture == "unspecified architecture"
    assert loc_ref.layout == "unspecified layout"


# =============================================================================
# 3. STORYBOARD PROMPT BUILDER & LEAK CHECKS
# =============================================================================

def test_prompt_builder_style_and_leak_checks():
    """Test that StoryboardPromptBuilder includes style profile and rejects poisoned prompts."""
    builder = StoryboardPromptBuilder()

    shot = ShotPlan(
        shot_id="s1",
        scene_id="sc1",
        screenplay_block_ids=["b1"],
        source_event_ids=["e1"],
        shot_type=ShotType.MEDIUM,
        camera_angle=CameraAngle.EYE_LEVEL,
        lens_feel="normal",
        subject_focus="char_alpha",
        emotion="fingers drum a rapid rhythm against the table",
        rationale="neutral default",
        composition_plan=CompositionPlan(framing_rect="0,0,1920,1080", depth_layers=["foreground", "background"], focal_point="char_alpha"),
    )

    continuity = ContinuityPack(
        shot_id="s1",
        location_ref=LocationVisualRef(
            location_id="loc1",
            architecture="concrete bunker",
            layout="corridor",
            doors="steel",
            windows="none",
            materials="steel",
            lighting="dim red emergency lights",
            landmarks="Bunker A",
        ),
    )

    # Valid prompt assembly
    prompt, p_hash = builder.build_prompt(shot, continuity)
    assert "professional film storyboard" in prompt
    assert "photorealistic movie still" in prompt
    assert len(p_hash) == 64  # SHA-256

    # Poisoned prompt test: internal state verb leak
    poisoned_shot = shot.model_copy()
    poisoned_shot.emotion = "Vincent feels afraid and knows he was caught"
    with pytest.raises(ValueError):
        builder.build_prompt(poisoned_shot, continuity)

    # Poisoned prompt test: vocabulary blocklist leak
    poisoned_vocab = shot.model_copy()
    poisoned_vocab.emotion = "The DirectorAgent intervenes with high salience"
    with pytest.raises(ValueError):
        builder.build_prompt(poisoned_vocab, continuity)


# =============================================================================
# 4. FULL RENDERER PIPELINE & BUDGET COMPLIANCE
# =============================================================================

def test_full_pipeline_with_provider_disabled_produces_exact_panels():
    """Test that full pipeline produces exactly N StoryboardPanels with DETERMINISTIC_SVG_FALLBACK."""
    shots = [
        ShotPlan(
            shot_id=f"shot_{i:02d}",
            scene_id="scene_01",
            screenplay_block_ids=[f"blk_{i}"],
            source_event_ids=[f"evt_{i}"],
            shot_type=ShotType.ESTABLISHING if i == 0 else ShotType.MEDIUM,
            camera_angle=CameraAngle.EYE_LEVEL,
            lens_feel="normal",
            subject_focus="char_alpha",
            emotion="composed posture, watchful expression",
            rationale="scene opening" if i == 0 else "neutral default",
            composition_plan=CompositionPlan(framing_rect="0,0,1920,1080", subject_positions={"char_alpha": (0.5, 0.5, 1.0)}, focal_point="char_alpha"),
        )
        for i in range(10)
    ]

    renderer = GroundedStoryboardRenderer()
    panels, bible = renderer.render_budgeted_storyboard(shots=shots, budget=4, project_id="test_proj")

    assert len(panels) == 4
    for panel in panels:
        assert isinstance(panel, StoryboardPanel)
        assert panel.provider_used == "DETERMINISTIC_SVG_FALLBACK"
        assert panel.generation_status == "GENERATED"
        assert panel.image_path is not None
        assert panel.prompt_content_hash != ""
        assert panel.shot_id.startswith("shot_")


def test_content_hash_caching_prevents_redundant_renders():
    """Test that identical shot prompt reuses cached SVG panel and records cache hit."""
    shot = ShotPlan(
        shot_id="shot_dup",
        scene_id="scene_01",
        screenplay_block_ids=["b1"],
        source_event_ids=["e1"],
        shot_type=ShotType.MEDIUM,
        camera_angle=CameraAngle.EYE_LEVEL,
        lens_feel="normal",
        subject_focus="char_alpha",
        emotion="composed posture, watchful expression",
        rationale="neutral default",
        composition_plan=CompositionPlan(framing_rect="0,0,1920,1080", subject_positions={"char_alpha": (0.5, 0.5, 1.0)}, focal_point="char_alpha"),
    )

    cache = ContentHashCache()
    renderer = GroundedStoryboardRenderer(cache=cache)

    # First render: cache miss
    panels_1, _ = renderer.render_budgeted_storyboard(shots=[shot], budget=1, project_id="test_cache")
    assert len(panels_1) == 1
    assert renderer.cache_hits == 0

    # Second render with identical shot: cache hit!
    panels_2, _ = renderer.render_budgeted_storyboard(shots=[shot], budget=1, project_id="test_cache")
    assert len(panels_2) == 1
    assert renderer.cache_hits == 1
    assert panels_1[0].prompt_content_hash == panels_2[0].prompt_content_hash


# =============================================================================
# 5. MISSING DOSSIER ACCEPTANCE (BUDGET 4, 8, 12)
# =============================================================================

def test_missing_dossier_acceptance_at_budgets():
    """Verify KeyframeSelector on live Missing Dossier at budget=4, 8, and 12, and render budget=8."""
    store = ProjectStore()
    project = store.load_project("world_init_4bef81")
    assert project is not None

    builder = SceneBuilder()
    enriched = builder.enrich_scenes_with_phase6(project.scenes, project.world)
    projector = ObservableSceneProjector()
    projections = projector.project_all_scenes(enriched, project.world)
    scribe = Scribe(provider=None)
    doc = scribe.compose_from_projections(projections, title="THE MISSING DOSSIER")
    planner = ShotPlanner()
    full_shot_list = planner.plan_shots_for_screenplay(doc, projections, project.world)
    assert len(full_shot_list) == 23

    # 1. Budget = 4
    sel_4 = KeyframeSelector.select_keyframes(full_shot_list, budget=4)
    assert len(sel_4) == 4

    # 2. Budget = 8
    sel_8 = KeyframeSelector.select_keyframes(full_shot_list, budget=8)
    assert len(sel_8) == 8

    # 3. Budget = 12
    sel_12 = KeyframeSelector.select_keyframes(full_shot_list, budget=12)
    assert len(sel_12) == 12

    # 4. Fully render budget = 8 case
    renderer = GroundedStoryboardRenderer()
    panels_8, bible = renderer.render_budgeted_storyboard(
        shots=full_shot_list,
        world=project.world,
        budget=8,
        project_id="world_init_4bef81",
    )

    assert len(panels_8) == 8
    for p in panels_8:
        assert p.provider_used == "DETERMINISTIC_SVG_FALLBACK"
        assert p.generation_status == "GENERATED"
        assert p.prompt_used != ""
        assert p.prompt_content_hash != ""

    # Visual Bible checks
    assert len(bible.characters) >= 2  # char_alpha, char_beta
    assert len(bible.locations) >= 2   # Industrial Bay, Vault
    # Props scoped: only important props
    assert len(bible.props) <= len(project.world.objects)
