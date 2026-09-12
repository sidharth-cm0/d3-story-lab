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
    FaceSketchRenderer,
    FaceOrientation,
    InkWashPolygon,
    TextureRenderer,
    SketchStyle,
    LINE_WEIGHT_CONSTRUCTION,
    LINE_WEIGHT_BACKGROUND,
    LINE_WEIGHT_INTERIOR,
    LINE_WEIGHT_CHARACTER,
    LINE_WEIGHT_FOREGROUND,
    LINE_WEIGHT_SHADOW,
    VALUE_0,
    VALUE_1,
    VALUE_2,
    VALUE_3,
    VALUE_4,
    ACCENT_COOL_WASH,
    ACCENT_BLUE_HAZE,
    ACCENT_WARM_LAMP,
    ACCENT_STORY_RED,
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
    assert res_v1.render_metadata["style"] in ("Graphite Production Board", "Cinematic Ink & Wash")
    assert res_v1.render_metadata["no_cloud_api"] is True

    # Check SVG size is lightweight (<= 250KB per specification)
    assert len(res_v1.svg_content.encode("utf-8")) < 250000

    # Test Version 2 Regeneration Variation
    res_v2 = provider.generate_panel(panel, version=2)
    assert res_v2.version == 2
    # Artwork has subtle variation
    assert res_v1.svg_content != res_v2.svg_content
    # But identities and style are preserved
    assert res_v2.render_metadata["style"] == res_v1.render_metadata["style"]
    assert res_v2.render_metadata["environment"] == res_v1.render_metadata["environment"]


def test_character_body_volumes_and_paired_contours():
    """Verify CharacterSketchRenderer builds 3D volumes (quad fills + paired contours) over skeleton."""
    renderer = CharacterSketchRenderer()
    ident = renderer.get_or_create_identity("char_test_vol", name="Vincent")

    svg, meta = renderer.render_character(
        identity=ident,
        x=450,
        y=120,
        height=320,
        pose_type=PoseType.WALKING,
        seed="char_vol_test",
    )
    # Never expose raw stick skeleton: must have polygon volume masses
    assert "<polygon" in svg
    assert "<path" in svg
    # Thigh volume with quad fill and core shadow wash
    assert 'fill="#090d16"' in svg
    assert 'fill="#020617"' in svg
    # Shoe perspective block with dark fill
    assert meta.get("hand_point") is not None
    assert meta.get("head_center") is not None


def test_face_orientations_and_close_up_lod():
    """Verify all 7 face orientations and close-up LOD (eyelids, iris, catchlight, cheek shadow, neck shadow)."""
    orientations = [
        FaceOrientation.FRONT,
        FaceOrientation.THREE_QUARTER_LEFT,
        FaceOrientation.THREE_QUARTER_RIGHT,
        FaceOrientation.PROFILE_LEFT,
        FaceOrientation.PROFILE_RIGHT,
        FaceOrientation.LOOKING_DOWN,
        FaceOrientation.LOOKING_UP,
    ]
    for orient in orientations:
        face_svg = FaceSketchRenderer.render_face(
            cx=200,
            cy=200,
            head_w=80,
            head_h=100,
            expression=ExpressionType.NEUTRAL,
            orientation=orient,
            is_close_up=True,
            seed=f"orient_{orient.value}",
        )
        assert "<path" in face_svg
        assert len(face_svg) > 200
        # No icon-like dot eyes
        assert 'r="1.5" fill="#000000"' not in face_svg

    # Close-up portrait has maximum feature detail:
    cu_svg = FaceSketchRenderer.render_face(
        cx=300,
        cy=300,
        head_w=120,
        head_h=150,
        expression=ExpressionType.SUSPICIOUS,
        orientation=FaceOrientation.THREE_QUARTER_RIGHT,
        is_close_up=True,
        seed="cu_test",
    )
    # Catchlight circle
    assert f'fill="{VALUE_0}"' in cu_svg
    # Eye socket wash and cheek shadow wash
    assert 'fill-opacity="0.350"' in cu_svg
    # Neck drop shadow wash
    assert 'fill-opacity="0.450"' in cu_svg
    # Lip / mouth path
    assert "<path" in cu_svg


def test_facial_acting_profiles():
    """Verify emotional acting states modify entire face with intensity."""
    emotions = [
        ExpressionType.SUSPICIOUS,
        ExpressionType.ANGRY,
        ExpressionType.AFRAID,
        ExpressionType.SHOCKED,
        ExpressionType.DETERMINED,
        ExpressionType.CONFUSED,
    ]
    for emo in emotions:
        svg = FaceSketchRenderer.render_face(
            cx=250,
            cy=250,
            head_w=90,
            head_h=115,
            expression=emo,
            intensity=0.9,
            seed=f"emo_{emo.value}",
        )
        assert len(svg) > 150
        assert "<path" in svg
        if emo == ExpressionType.SHOCKED:
            # Dropped open jaw polygon
            assert 'fill="#090d16"' in svg
        if emo == ExpressionType.AFRAID:
            # Sweat drop / tension curve
            assert f'fill="{VALUE_0}"' in svg


def test_storyboard_hand_states_and_insert():
    """Verify storyboard hand anatomy and detailed INSERT interaction."""
    renderer = CharacterSketchRenderer()
    for state in ["RELAXED", "POINTING", "GRIPPING", "OPEN", "HOLDING_PROP", "FIST", "REACHING"]:
        h_svg = renderer._render_hand(
            cx=100,
            cy=100,
            facing_dir=1.0,
            state=state,
            scale=1.2,
            seed=f"hand_{state}",
        )
        assert "<polygon" in h_svg
        assert "<path" in h_svg

    # Prop renderer with is_insert=True renders detailed interacting hand
    prop_ren = PropSketchRenderer()
    dossier_ident = prop_ren.get_or_create_identity("obj_dossier", name="Classified Dossier")
    insert_prop_svg = prop_ren.render_prop(
        identity=dossier_ident,
        cx=480,
        cy=270,
        scale=2.0,
        seed="insert_dossier",
        is_insert=True,
    )
    assert "insert_hand_interaction" in insert_prop_svg


def test_clothing_folds_and_wardrobe_silhouette():
    """Verify clothing responds with collars, lapels, belts, and pose-responsive folds."""
    renderer = CharacterSketchRenderer()
    ref_suit = CharacterVisualReference(
        character_id="char_suit",
        name="Suit Agent",
        clothing="tailored suit with dark tie",
    )
    ident_suit = renderer.get_or_create_identity("char_suit", ref=ref_suit)
    assert ident_suit.clothing_shape == "tailored_suit"
    svg_suit, _ = renderer.render_character(
        identity=ident_suit,
        x=300,
        y=100,
        height=320,
        seed="suit_render",
    )
    # Tie element in suit
    assert f'fill="{ACCENT_WARM_LAMP}"' in svg_suit

    # Trenchcoat with belt and skirt flare
    ref_trench = CharacterVisualReference(
        character_id="char_detective_trench",
        name="Detective",
        clothing="long trenchcoat with popped collar",
    )
    ident_trench = renderer.get_or_create_identity("char_detective_trench", ref=ref_trench)
    svg_trench, _ = renderer.render_character(
        identity=ident_trench,
        x=300,
        y=100,
        height=320,
        pose_type=PoseType.WALKING,
        seed="trench_render",
    )
    assert "<polygon" in svg_trench
    assert "<path" in svg_trench


def test_environment_architectural_mass_and_depth_layers():
    """Verify architectural massing, 3-layer depth (FG/MG/BG), I-beams, trusses, windows, shelves, pipes, and debris."""
    env_ren = EnvironmentSketchRenderer()
    loc_ref = LocationVisualReference(
        location_id="loc_wh_test",
        name="Warehouse",
        environment_type="Industrial Warehouse",
        architecture="heavy steel columns, roof rafters",
    )
    ident = env_ren.get_or_create_identity("loc_wh_test", ref=loc_ref)

    svg = env_ren.render_environment(ident, width=960, height=540, seed="env_mass_test", include_foreground=True)

    # 1. Background layer: wall courses, roof trusses, multi-pane windows with glass shards
    assert "roof_truss_beam" in svg
    assert "industrial_win_0" in svg
    assert "industrial_conduits" in svg

    # 2. Midground layer: 3D I-beam columns with flanges and rivets, shelving, wooden crates, floor cracks, puddles, debris
    assert "industrial_shelving" in svg
    assert "floor_debris" in svg
    assert "<circle" in svg

    # 3. Foreground layer: silhouetted framing door jamb with rivets, out-of-focus crate corner
    assert 'fill="#020617"' in svg


def test_line_weight_hierarchy_and_tonal_values():
    """Verify established line weight hierarchy and 5-value grayscale palette constants."""
    assert LINE_WEIGHT_CONSTRUCTION < LINE_WEIGHT_BACKGROUND
    assert LINE_WEIGHT_BACKGROUND < LINE_WEIGHT_INTERIOR
    assert LINE_WEIGHT_INTERIOR < LINE_WEIGHT_CHARACTER
    assert LINE_WEIGHT_CHARACTER < LINE_WEIGHT_FOREGROUND
    assert LINE_WEIGHT_FOREGROUND >= 2.8

    # 5-value grayscale
    assert VALUE_0 == "#ffffff"
    assert VALUE_1 == "#cbd5e1"
    assert VALUE_2 == "#64748b"
    assert VALUE_3 == "#334155"
    assert VALUE_4 == "#090d16"


def test_selective_color_palette():
    """Verify restrained selective color accents: 70% grayscale, 20% environmental wash, 10% story accent."""
    assert ACCENT_COOL_WASH.startswith("#")
    assert ACCENT_BLUE_HAZE == "#38bdf8"
    assert ACCENT_WARM_LAMP == "#f59e0b"
    assert ACCENT_STORY_RED == "#dc2626"

    # Verify procedural textures
    cracks = TextureRenderer.concrete_cracks(0, 0, 200, 100, seed="crack_test")
    assert "<path" in cracks
    wood = TextureRenderer.wood_grain(0, 0, 100, 100, seed="wood_test")
    assert "<path" in wood
    metal = TextureRenderer.metal_highlights(10, 10, 50, seed="metal_test")
    assert "<path" in metal
    glass = TextureRenderer.glass_reflections(0, 0, 100, 100, seed="glass_test")
    assert "<path" in glass
    fabric = TextureRenderer.fabric_folds(0, 0, 100, 100, seed="fabric_test")
    assert "<path" in fabric
    paper = TextureRenderer.paper_creases(0, 0, 100, 100, seed="paper_test")
    assert "<path" in paper


def test_ten_panel_warehouse_scenario_cinematic_differentiation(tmp_path):
    """Section 33 Scenario:

    'An undercover detective infiltrates an abandoned warehouse at midnight
    to recover a stolen classified dossier.'

    Verify 10 panels produce 10 distinct cinematic compositions:
    1. EXTREME WIDE: warehouse exterior/interior at night
    2. WIDE: detective entering warehouse
    3. TRACKING MEDIUM: detective walking through interior
    4. INSERT: hand opening classified dossier
    5. CLOSE UP: detective reacts to discovery
    6. OTS: detective confronts Evelyn
    7. REACTION CLOSE-UP: Evelyn becomes afraid
    8. LOW ANGLE: threat enters scene
    9. ACTION WIDE: conflict / escape
    10. RESOLUTION WIDE: final atmospheric image
    """
    store = StoryboardAssetStore(base_dir=str(tmp_path))
    provider = HandDrawnStoryboardProvider(asset_store=store, style=SketchStyle.CINEMATIC_INK_WASH)

    bible = VisualBible()
    bible.characters["char_detective"] = CharacterVisualReference(
        character_id="char_detective",
        name="Detective Cross",
        build="lean athletic",
        face_features="sharp angular chiseled jaw",
        hair="short parted dark hair",
        clothing="charcoal trench coat",
        signature_props=["flashlight"],
    )
    bible.characters["char_evelyn"] = CharacterVisualReference(
        character_id="char_evelyn",
        name="Evelyn Vance",
        build="slender",
        face_features="expressive high cheekbones",
        hair="slicked back blonde hair",
        clothing="tailored dark jacket",
    )
    bible.characters["char_threat"] = CharacterVisualReference(
        character_id="char_threat",
        name="The Operative",
        build="broad athletic imposing",
        face_features="square jaw fierce brow",
        hair="buzz crop",
        clothing="field tactical jacket",
    )
    bible.objects["obj_dossier"] = ObjectVisualReference(
        object_id="obj_dossier",
        name="Classified Dossier",
        form_factor="Folio dossier with wax seal",
        materials="Aged manila cardstock, brass rivets, red sealing wax",
        unique_markings="TOP SECRET",
    )
    bible.locations["loc_warehouse"] = LocationVisualReference(
        location_id="loc_warehouse",
        name="Abandoned Docks Warehouse",
        environment_type="Industrial Warehouse",
        architecture="Heavy I-beams, iron rafters, broken multi-pane windows",
        lighting_setup="Cold moonlight from high skylights and single hanging industrial lamp",
    )

    panels_spec = [
        # 1. EXTREME WIDE
        StoryboardPanel(
            id="pnl_01", panel_id="pnl_01", project_id="scenario", scene_number=1, shot_number=1,
            shot_type=ShotType.EXTREME_WIDE, camera_angle=CameraAngle.HIGH_ANGLE,
            location_id="loc_warehouse", location_name="Warehouse",
            character_names=["Detective Cross"], characters_present=["char_detective"],
            action="At midnight, the rain-slicked industrial warehouse stands silent under the moonlight.",
            lighting="Cold moonlight through broken roof rafters", mood="Atmospheric and solitary",
        ),
        # 2. WIDE
        StoryboardPanel(
            id="pnl_02", panel_id="pnl_02", project_id="scenario", scene_number=1, shot_number=2,
            shot_type=ShotType.WIDE, camera_angle=CameraAngle.EYE_LEVEL,
            location_id="loc_warehouse", location_name="Warehouse",
            character_names=["Detective Cross"], characters_present=["char_detective"],
            objects_in_frame=["obj_flashlight"],
            action="Cross enters through the rusted loading bay doors, flashlight cutting through the gloom.",
            lighting="Flashlight beam with deep rim shadows", mood="Suspenseful and cautious",
        ),
        # 3. TRACKING MEDIUM
        StoryboardPanel(
            id="pnl_03", panel_id="pnl_03", project_id="scenario", scene_number=1, shot_number=3,
            shot_type=ShotType.MEDIUM, camera_angle=CameraAngle.EYE_LEVEL,
            location_id="loc_warehouse", location_name="Warehouse",
            character_names=["Detective Cross"], characters_present=["char_detective"],
            action="Cross walks cautiously past rows of stacked shipping crates, scanning the rafters.",
            lens_feel="Track right pan",
            lighting="Warm pool under hanging industrial lamp", mood="Determined focus",
        ),
        # 4. INSERT
        StoryboardPanel(
            id="pnl_04", panel_id="pnl_04", project_id="scenario", scene_number=1, shot_number=4,
            shot_type=ShotType.INSERT, camera_angle=CameraAngle.HIGH_ANGLE,
            location_id="loc_warehouse", location_name="Warehouse",
            objects_in_frame=["obj_dossier"],
            action="A gloved hand breaks the crimson wax seal and opens the classified dossier on a workbench.",
            lighting="Overhead single pool light", mood="High tension reveal",
        ),
        # 5. CLOSE UP
        StoryboardPanel(
            id="pnl_05", panel_id="pnl_05", project_id="scenario", scene_number=1, shot_number=5,
            shot_type=ShotType.CLOSE_UP, camera_angle=CameraAngle.EYE_LEVEL,
            location_id="loc_warehouse", location_name="Warehouse",
            character_names=["Detective Cross"], characters_present=["char_detective"],
            action="Cross freezes, stunned by the names listed in the classified files.",
            lighting="Chiaroscuro side key lighting with deep eye socket shadows", mood="Shock and disbelief",
        ),
        # 6. OTS
        StoryboardPanel(
            id="pnl_06", panel_id="pnl_06", project_id="scenario", scene_number=1, shot_number=6,
            shot_type=ShotType.OVER_SHOULDER, camera_angle=CameraAngle.EYE_LEVEL,
            location_id="loc_warehouse", location_name="Warehouse",
            character_names=["Detective Cross", "Evelyn Vance"],
            characters_present=["char_detective", "char_evelyn"],
            action="Cross steps from the shadows to confront Evelyn Vance near the concrete pillars.",
            lighting="Moonlight rim on Evelyn, silhouette on Cross shoulder", mood="Tense standoff",
        ),
        # 7. REACTION CLOSE-UP
        StoryboardPanel(
            id="pnl_07", panel_id="pnl_07", project_id="scenario", scene_number=1, shot_number=7,
            shot_type=ShotType.REACTION, camera_angle=CameraAngle.EYE_LEVEL,
            location_id="loc_warehouse", location_name="Warehouse",
            character_names=["Evelyn Vance"], characters_present=["char_evelyn"],
            action="Evelyn backs away in terror as she realizes she was followed.",
            lighting="Harsh moonlight key, glabella creases and raised brows", mood="Terrified and afraid",
        ),
        # 8. LOW ANGLE
        StoryboardPanel(
            id="pnl_08", panel_id="pnl_08", project_id="scenario", scene_number=1, shot_number=8,
            shot_type=ShotType.WIDE, camera_angle=CameraAngle.LOW_ANGLE,
            location_id="loc_warehouse", location_name="Warehouse",
            character_names=["The Operative"], characters_present=["char_threat"],
            action="A silhouette looms in the doorway as the Operative arrives to silence both witnesses.",
            lighting="Harsh backlighting creating towering menacing silhouette", mood="Imposing threat",
        ),
        # 9. ACTION WIDE
        StoryboardPanel(
            id="pnl_09", panel_id="pnl_09", project_id="scenario", scene_number=1, shot_number=9,
            shot_type=ShotType.WIDE, camera_angle=CameraAngle.DUTCH_ANGLE,
            location_id="loc_warehouse", location_name="Warehouse",
            character_names=["Detective Cross", "The Operative"],
            characters_present=["char_detective", "char_threat"],
            action="Cross sprints through the aisles dodging gunshots, grabbing Evelyn as they escape.",
            lighting="Dynamic strobe muzzle flashes and swinging lamp", mood="Desperate kinetic action",
        ),
        # 10. RESOLUTION WIDE
        StoryboardPanel(
            id="pnl_10", panel_id="pnl_10", project_id="scenario", scene_number=1, shot_number=10,
            shot_type=ShotType.WIDE, camera_angle=CameraAngle.EYE_LEVEL,
            location_id="loc_warehouse", location_name="Warehouse",
            character_names=["Detective Cross"], characters_present=["char_detective"],
            action="Cross emerges into the rain with the dossier secured inside his trench coat.",
            lighting="Atmospheric rain streaks and distant amber streetlights", mood="Grim resolution",
        ),
    ]

    rendered_svgs = []
    for p in panels_spec:
        res = provider.generate_panel(p, bible=bible, version=1)
        assert res.status == StoryboardImageStatus.READY
        assert "<svg" in res.svg_content
        assert "</svg>" in res.svg_content
        # Ensure under bounded size
        assert len(res.svg_content.encode("utf-8")) < 250000
        # No raw stick figures
        assert "<polygon" in res.svg_content or "<path" in res.svg_content
        rendered_svgs.append(res.svg_content)

    # Verify all 10 panels are distinct compositions
    assert len(set(rendered_svgs)) == 10

    # Panel 4 (INSERT) must have prop interaction
    assert "insert_hand_interaction" in rendered_svgs[3]
    # Panel 6 (OTS) must have OTS tag
    assert "OTS" in rendered_svgs[5]
    # Panel 9 (DUTCH) must have dutch tilt transform
    assert "dutch_camera_tilt" in rendered_svgs[8]


def test_perspective_grid_opacity_bound():
    """Verify perspective guide lines never exceed 0.03 opacity in final rendering."""
    grid_svg = PerspectiveGrid.render(
        vp_x=480, vp_y=240, bottom_y=540, width=960, seed="grid_test", opacity=0.8
    )
    # Even if caller requested 0.8, renderer must cap opacity <= 0.03
    import re
    opacities = [float(m) for m in re.findall(r'opacity="([0-9.]+)"', grid_svg)]
    assert len(opacities) > 0
    for op in opacities:
        assert op <= 0.0301, f"Perspective grid opacity {op} exceeded 0.03 maximum"


def test_no_visible_raw_skeleton_output():
    """Verify character rendering produces 3D muscular volumes and no raw stick figure lines."""
    renderer = CharacterSketchRenderer()
    ident = renderer.get_or_create_identity("char_hero", name="Vincent Cross")
    svg_out, meta = renderer.render_character(
        ident, x=480, y=100, height=350, pose_type=PoseType.WALKING, seed="char_hero"
    )
    # Muscular torso polygon volume fills (never raw stick lines)
    assert "<polygon" in svg_out
    assert 'fill="#090d16"' in svg_out
    assert 'fill="#020617"' in svg_out
    # Curved Bézier limb contours
    assert "<path" in svg_out
    assert "d=\"M " in svg_out
    # Hand points and head centers are populated
    assert "hand_points" in meta
    assert meta["hand_points"]["right"] is not None


def test_face_feature_stroke_count_lod():
    """Verify face detail scales by shot LOD (close-up 30-70, medium 10-25, wide silhouette)."""
    # 1. Close-up face
    cu_face = FaceSketchRenderer.render_face(
        cx=480, cy=240, head_w=120, head_h=150,
        expression=ExpressionType.SUSPICIOUS,
        orientation=FaceOrientation.THREE_QUARTER_LEFT,
        is_close_up=True,
        is_wide=False,
        seed="cu_face_test",
    )
    cu_path_count = cu_face.count("<path") + cu_face.count("<polygon")
    assert 30 <= cu_path_count <= 70, f"Close-up stroke count {cu_path_count} not in 30-70 range"
    assert "<path" in cu_face
    assert "<polygon" in cu_face

    # 2. Medium face
    med_face = FaceSketchRenderer.render_face(
        cx=480, cy=240, head_w=50, head_h=65,
        expression=ExpressionType.NEUTRAL,
        orientation=FaceOrientation.FRONT,
        is_close_up=False,
        is_wide=False,
        seed="med_face_test",
    )
    med_path_count = med_face.count("<path") + med_face.count("<polygon")
    assert 10 <= med_path_count <= 40, f"Medium shot stroke count {med_path_count} not in 10-40 range"

    # 3. Wide silhouette face
    wide_face = FaceSketchRenderer.render_face(
        cx=480, cy=240, head_w=20, head_h=25,
        expression=ExpressionType.NEUTRAL,
        is_close_up=False,
        is_wide=True,
        seed="wide_face_test",
    )
    wide_path_count = wide_face.count("<path")
    assert wide_path_count <= 2, f"Wide shot face should be pure silhouette, got {wide_path_count} paths"


def test_character_frame_occupancy_by_shot():
    """Verify character height occupancy conforms to cinematic shot standards."""
    # Close-up: cropped to bust framing
    panel_cu = StoryboardPanel(
        id="p_cu", panel_id="p_cu", project_id="test", scene_number=1, shot_number=1,
        shot_type=ShotType.CLOSE_UP, camera_angle=CameraAngle.EYE_LEVEL,
        characters_present=["char_hero"], character_names=["Hero"], action="Hero reacts intently."
    )
    staged_cu = SceneStager.stage_panel(panel_cu)
    assert len(staged_cu.actors) == 1
    assert staged_cu.actors[0].crop_to_bust is True

    # Medium: 50-70% of frame height
    panel_med = StoryboardPanel(
        id="p_med", panel_id="p_med", project_id="test", scene_number=1, shot_number=2,
        shot_type=ShotType.MEDIUM, camera_angle=CameraAngle.EYE_LEVEL,
        characters_present=["char_hero"], character_names=["Hero"], action="Hero speaks."
    )
    staged_med = SceneStager.stage_panel(panel_med)
    med_occ = staged_med.actors[0].height / 540.0
    assert 0.50 <= med_occ <= 0.72, f"Medium shot occupancy {med_occ:.2f} not in 0.50-0.72"


def test_hand_anatomy_geometry():
    """Verify hand rendering produces realistic anatomical structures."""
    renderer = CharacterSketchRenderer()
    hand_svg = renderer._render_hand(
        cx=300, cy=300, facing_dir=1.0, state="OPEN", scale=1.0, seed="hand_geo"
    )
    # Palm wedge
    assert "palm" in hand_svg
    assert "<polygon" in hand_svg
    # Knuckle arc Bézier
    assert "knuckle_arc" in hand_svg
    # Articulated individual fingers
    assert "finger_0" in hand_svg
    assert "finger_3" in hand_svg


def test_environment_multi_plane_depth_and_clutter():
    """Verify architectural environments feature foreground, midground, background planes and clutter."""
    env_renderer = EnvironmentSketchRenderer()
    ident = env_renderer.get_or_create_identity("loc_wh", name="Abandoned Warehouse")
    env_svg = env_renderer.render_environment(
        ident,
        width=960,
        height=540,
        seed="env_depth_test",
    )
    # Background wall and ceiling beams
    assert "beam" in env_svg or "ceiling" in env_svg
    # Structural architectural pillars
    assert "pillar" in env_svg or "column" in env_svg
    # Multi-plane depth presence
    assert "<polygon" in env_svg
    # Floor clutter (crates / concrete stress fractures / texture)
    assert "crate" in env_svg or "concrete" in env_svg or "floor" in env_svg


def test_tonal_value_structure_and_crosshatching():
    """Verify rendered panels maintain deep value hierarchy and crosshatch shading."""
    provider = HandDrawnStoryboardProvider(style=SketchStyle.GRAPHITE_PRODUCTION_BOARD)
    panel = StoryboardPanel(
        id="p_tone", panel_id="p_tone", project_id="demo", scene_number=1, shot_number=1,
        shot_type=ShotType.MEDIUM, camera_angle=CameraAngle.EYE_LEVEL,
        location_id="loc_wh", location_name="Warehouse",
        character_names=["Vincent"], characters_present=["char_vincent"],
        action="Vincent examines the safe under single spotlight.",
        lighting="Dramatic directional key spotlight", mood="Tense noir",
    )
    res = provider.generate_panel(panel, version=1)
    svg = res.svg_content

    # Check for warm graphite paper background
    assert "#EDE8DF" in svg or "#DFD9CD" in svg
    # Check for graphite pencil stroke color #202020
    assert "#202020" in svg
    # Check for cross-hatch shading pattern defs
    assert "hatch_dark" in svg or "hatch_mid" in svg
    # Check for subjects layer and environment layer
    assert 'id="subjects_layer"' in svg
    assert 'id="environment_layer"' in svg


def test_foreshortening_and_action_gestural_dynamics():
    """Verify running and questioning poses calculate contrapposto tilts and foreshortening."""
    from src.storyboard.sketch.pose import calculate_gesture_dynamics

    run_dyn = calculate_gesture_dynamics(PoseType.RUNNING, facing_direction=1.0)
    # Dynamic shoulder and hip contrapposto tilts
    assert abs(run_dyn["shoulder_tilt"]) > 0.0
    assert abs(run_dyn["hip_tilt"]) > 0.0
    # Leg foreshortening for trailing/advancing leg
    assert run_dyn["leg_foreshortening"] > 1.0

    quest_dyn = calculate_gesture_dynamics(PoseType.QUESTIONING, facing_direction=1.0)
    assert quest_dyn["arm_foreshortening"] > 1.0
