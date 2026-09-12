"""Comprehensive tests for the offline deterministic hand-drawn storyboard engine.

Tests:
- Stroke primitives (SketchStroke, Ellipse, CrossHatch, MotionArrow, SpeedLines)
- Seed determinism (identical seed -> bit-for-bit identical SVG output)
- Stable CharacterSketchIdentity across panels
- Stable LocationSketchIdentity across visits
- Stable ObjectSketchIdentity for canonical props (dossier, flashlight, safe, etc.)
- Shot-aware camera framing (extreme_wide, wide, medium, close_up, insert, over_shoulder)
- Screenplay verb to pose mapping
- Emotion to expression mapping
- HandDrawnStoryboardProvider offline generation, status, capabilities, and version regeneration
"""

import pytest
from src.storyboard.models import (
    StoryboardPanel,
    ShotType,
    CameraAngle,
    ShotPurpose,
    StoryboardImageStatus,
    PageLayoutTemplate,
)
from src.storyboard.visual_bible import (
    VisualBible,
    CharacterVisualReference,
    ObjectVisualReference,
    LocationVisualReference,
)
from src.storyboard.sketch import (
    SketchStroke,
    SketchPolyline,
    SketchPolygon,
    SketchEllipse,
    CrossHatch,
    ScribbleShadow,
    PerspectiveGrid,
    MotionArrow,
    SpeedLines,
    get_rng,
    get_seed_hash,
    PoseType,
    map_action_to_pose,
    ExpressionType,
    map_emotion_to_expression,
    CharacterSketchIdentity,
    CharacterSketchRenderer,
    PropType,
    ObjectSketchIdentity,
    PropSketchRenderer,
    EnvironmentType,
    LocationSketchIdentity,
    EnvironmentSketchRenderer,
    SceneStager,
    HandDrawnStoryboardProvider,
)
from src.storyboard.asset_store import StoryboardAssetStore


def test_seed_determinism_and_primitives():
    """Verify that identical seeds produce bit-for-bit identical SVG markup."""
    svg1 = SketchStroke.render_line(10, 20, 100, 200, seed="test_line_seed_alpha")
    svg2 = SketchStroke.render_line(10, 20, 100, 200, seed="test_line_seed_alpha")
    assert svg1 == svg2, "Identical seeds must produce identical lines"
    assert "<path" in svg1

    # Different seeds produce different jitter
    svg3 = SketchStroke.render_line(10, 20, 100, 200, seed="test_line_seed_beta")
    assert svg1 != svg3

    # Test ellipse determinism
    el1 = SketchEllipse.render(50, 50, 30, 20, seed="ellipse_seed_1")
    el2 = SketchEllipse.render(50, 50, 30, 20, seed="ellipse_seed_1")
    assert el1 == el2
    assert "<path" in el1

    # Test crosshatch determinism
    ch1 = CrossHatch.render(0, 0, 100, 100, seed="hatch_seed")
    ch2 = CrossHatch.render(0, 0, 100, 100, seed="hatch_seed")
    assert ch1 == ch2

    # Test motion arrow and speed lines
    ma = MotionArrow.render_straight(10, 10, 80, 10, seed="arrow_seed")
    assert "<path" in ma
    sl = SpeedLines.render(50, 50, 60, 180, seed="speed_seed")
    assert "<path" in sl


def test_character_identity_stability():
    """Verify CharacterSketchIdentity derives stable proportions and hairstyles."""
    ref_maya = CharacterVisualReference(
        character_id="char_maya",
        name="Maya Lin",
        build="lean athletic build",
        face_features="sharp angular jawline",
        hair="slicked back dark hair",
        clothing="charcoal tailored trench coat",
        signature_props=["glasses"],
    )

    ident1 = CharacterSketchIdentity.from_reference(ref_maya)
    ident2 = CharacterSketchIdentity.from_reference(ref_maya)

    assert ident1.character_id == "char_maya"
    assert ident1.hair_style == "slicked_back"
    assert ident1.clothing_shape == "trench_coat"
    assert ident1.accessory == "glasses"
    assert ident1.head_shape == "angular"
    assert ident1.height_ratio == ident2.height_ratio
    assert ident1.shoulder_width == ident2.shoulder_width

    # Different character has distinct features
    ref_arjun = CharacterVisualReference(
        character_id="char_arjun",
        name="Arjun Mehta",
        build="broad shoulders, imposing build",
        face_features="square jaw",
        hair="curly textured volume",
        clothing="tailored suit",
        signature_props=["silver watch"],
    )
    ident_arjun = CharacterSketchIdentity.from_reference(ref_arjun)
    assert ident_arjun.hair_style == "curly_volume"
    assert ident_arjun.head_shape == "square_jaw"
    assert ident_arjun.shoulder_width > ident1.shoulder_width


def test_character_rendering_poses_and_acting():
    """Verify CharacterSketchRenderer produces valid SVG with pose and expression acting."""
    renderer = CharacterSketchRenderer()
    ref = CharacterVisualReference(
        character_id="char_detective",
        name="Detective Cross",
        face_features="sharp angular",
        hair="slicked back",
        clothing="trench coat",
    )
    ident = renderer.get_or_create_identity("char_detective", ref=ref)

    # Full body walking
    svg_walk, meta = renderer.render_character(
        identity=ident,
        x=400,
        y=100,
        height=300,
        pose_type=PoseType.WALKING,
        expression_type=ExpressionType.DETERMINED,
        seed="char_test_1",
    )
    assert "<svg" not in svg_walk  # Layer snippet
    assert "<path" in svg_walk
    assert meta.get("hand_point") is not None

    # Bust crop close-up reaction
    svg_close, _ = renderer.render_character(
        identity=ident,
        x=480,
        y=50,
        height=480,
        pose_type=PoseType.SHOCKED,
        expression_type=ExpressionType.SHOCKED,
        crop_to_bust=True,
        seed="char_test_2",
    )
    assert "<path" in svg_close
    assert len(svg_close) > 100


def test_prop_sketch_renderer_continuity():
    """Verify PropSketchRenderer maintains recognizable features for canonical props."""
    renderer = PropSketchRenderer()
    ref_dossier = ObjectVisualReference(
        object_id="obj_dossier",
        name="Encrypted Dossier",
        form_factor="Rectangular folio dossier with wax seal",
        unique_markings="Red wax seal and corner brass clips",
    )
    ident = renderer.get_or_create_identity("obj_dossier", ref=ref_dossier)
    assert ident.prop_type == PropType.DOSSIER

    # Render dossier in panel 3
    svg_p3 = renderer.render_prop(ident, cx=300, cy=200, scale=1.0, seed="pnl_3_prop")
    # Render dossier in panel 12
    svg_p12 = renderer.render_prop(ident, cx=400, cy=250, scale=1.5, seed="pnl_12_prop")

    assert "seal" in svg_p3
    assert "folio" in svg_p3
    assert "clip" in svg_p3
    assert "seal" in svg_p12

    # Verify other prop types
    ref_fl = ObjectVisualReference(object_id="obj_torch", name="Heavy Flashlight", form_factor="Flashlight torch")
    ident_fl = renderer.get_or_create_identity("obj_torch", ref=ref_fl)
    svg_fl = renderer.render_prop(ident_fl, cx=200, cy=200, scale=1.0, seed="torch_seed")
    assert "beam" in svg_fl or "fl_head" in svg_fl


def test_environment_sketch_renderer_continuity():
    """Verify EnvironmentSketchRenderer creates distinct architectural backgrounds."""
    renderer = EnvironmentSketchRenderer()
    loc_wh = LocationVisualReference(
        location_id="loc_warehouse",
        name="Abandoned Docks Warehouse",
        environment_type="Industrial Warehouse",
        architecture="Heavy I-beams and broken multi-pane windows",
    )
    ident_wh = renderer.get_or_create_identity("loc_warehouse", ref=loc_wh)
    assert ident_wh.env_type == EnvironmentType.WAREHOUSE

    svg_wh = renderer.render_environment(ident_wh, width=960, height=540, seed="wh_seed")
    assert "beam" in svg_wh
    assert "win" in svg_wh

    # Corridor
    loc_corr = LocationVisualReference(
        location_id="loc_corridor",
        name="Penthouse Corridor",
        environment_type="Hotel Corridor",
        architecture="Linear perspective doors",
    )
    ident_corr = renderer.get_or_create_identity("loc_corridor", ref=loc_corr)
    assert ident_corr.env_type == EnvironmentType.CORRIDOR
    svg_corr = renderer.render_environment(ident_corr, width=960, height=540, seed="corr_seed")
    assert "door" in svg_corr


def test_action_and_emotion_mappers():
    """Verify screenplay action verbs and emotions map to expressive poses and faces."""
    assert map_action_to_pose("Maya walks down the hall") == PoseType.WALKING
    assert map_action_to_pose("Arjun sprints to the exit") == PoseType.RUNNING
    assert map_action_to_pose("She examines the dossier carefully") == PoseType.EXAMINING_OBJECT
    assert map_action_to_pose("Elena opens the heavy vault door") == PoseType.OPENING_DOOR
    assert map_action_to_pose("He aims his flashlight into the darkness") == PoseType.AIMING_FLASHLIGHT
    assert map_action_to_pose("Victor turns toward the noise") == PoseType.TURNING
    assert map_action_to_pose("She points at the intruder") == PoseType.POINTING
    assert map_action_to_pose("He reaches for the ledger") == PoseType.REACHING
    assert map_action_to_pose("She speaks softly", dialogue_text="Listen to me.") == PoseType.TALKING

    assert map_emotion_to_expression("Suspicious and guarded") == ExpressionType.SUSPICIOUS
    assert map_emotion_to_expression("Terrified and panicked") == ExpressionType.AFRAID
    assert map_emotion_to_expression("Furious rage") == ExpressionType.ANGRY
    assert map_emotion_to_expression("Stunned disbelief and shock") == ExpressionType.SHOCKED
    assert map_emotion_to_expression("Determined focus") == ExpressionType.DETERMINED
    assert map_emotion_to_expression("Confident smirk") == ExpressionType.CONFIDENT


def test_scene_stager_camera_framing():
    """Verify SceneStager scales actors according to cinematic camera shot types."""
    panel_wide = StoryboardPanel(
        id="pnl_w",
        panel_id="pnl_w",
        shot_type=ShotType.WIDE,
        camera_angle=CameraAngle.EYE_LEVEL,
        character_names=["Maya", "Arjun"],
        characters_present=["char_maya", "char_arjun"],
        action="They confront each other.",
    )
    staged_w = SceneStager.stage_panel(panel_wide)
    assert len(staged_w.actors) == 2
    # In wide shot, actors should be ~240px height
    assert staged_w.actors[0].height == 240.0
    assert not staged_w.actors[0].crop_to_waist

    # Close-up shot
    panel_cu = StoryboardPanel(
        id="pnl_cu",
        panel_id="pnl_cu",
        shot_type=ShotType.CLOSE_UP,
        camera_angle=CameraAngle.EYE_LEVEL,
        character_names=["Maya"],
        characters_present=["char_maya"],
        action="Maya freezes.",
    )
    staged_cu = SceneStager.stage_panel(panel_cu)
    assert staged_cu.actors[0].height > 400.0
    assert staged_cu.actors[0].crop_to_bust

    # Insert shot with prop
    panel_ins = StoryboardPanel(
        id="pnl_ins",
        panel_id="pnl_ins",
        shot_type=ShotType.INSERT,
        objects_in_frame=["obj_dossier"],
        action="The sealed dossier rests under the lamp.",
    )
    staged_ins = SceneStager.stage_panel(panel_ins)
    assert len(staged_ins.props) == 1
    assert staged_ins.props[0].scale >= 2.0


def test_hand_drawn_storyboard_provider_offline(tmp_path):
    """Verify HandDrawnStoryboardProvider operates offline with zero cloud API keys."""
    store = StoryboardAssetStore(base_dir=str(tmp_path))
    provider = HandDrawnStoryboardProvider(asset_store=store)

    # Verify status and capabilities
    status = provider.get_status()
    assert status["storyboard_image_provider"] == "hand_drawn_storyboard"
    assert status["mode"] == "local"
    assert status["status"] == "AVAILABLE"
    assert status["available"] is True

    caps = provider.get_capabilities()
    assert caps["provider"] == "hand_drawn_storyboard"
    assert caps["quota_status"] == "NOT_REQUIRED"
    assert caps["continuity_mode"] == "Deterministic Visual Bible"
    assert caps["fallback_enabled"] is False

    # Render a panel
    panel = StoryboardPanel(
        id="pnl_test_hd_01",
        panel_id="pnl_test_hd_01",
        project_id="proj_demo",
        scene_number=1,
        shot_number=1,
        shot_type=ShotType.MEDIUM,
        camera_angle=CameraAngle.LOW_ANGLE,
        location_id="loc_wh",
        location_name="Abandoned Warehouse",
        character_names=["Elena"],
        characters_present=["char_elena"],
        objects_in_frame=["obj_dossier"],
        action="Elena examines the confidential dossier.",
        lighting="Dramatic key spotlight with high contrast",
        mood="Suspenseful and guarded",
    )

    res_v1 = provider.generate_panel(panel, version=1)
    assert res_v1.status == StoryboardImageStatus.READY
    assert res_v1.provider == "hand_drawn_storyboard"
    assert res_v1.mode == "hand_drawn"
    assert res_v1.fallback_reason is None
    assert "<svg" in res_v1.svg_content
    assert "</svg>" in res_v1.svg_content
    assert res_v1.render_metadata["label"] == "HAND-DRAWN STORYBOARD"
    assert res_v1.render_metadata["style"] == "Pencil Noir"
    assert res_v1.render_metadata["no_cloud_api"] is True

    # Check SVG size is lightweight (< 75KB)
    assert len(res_v1.svg_content.encode("utf-8")) < 75000

    # Test Version 2 Regeneration Variation
    res_v2 = provider.generate_panel(panel, version=2)
    assert res_v2.version == 2
    # Artwork has subtle variation
    assert res_v1.svg_content != res_v2.svg_content
    # But identities and style are preserved
    assert res_v2.render_metadata["style"] == res_v1.render_metadata["style"]
    assert res_v2.render_metadata["environment"] == res_v1.render_metadata["environment"]
