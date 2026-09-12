"""Tests for PsychologicalCameraPlanner, LightingProfiles, and FocalDepthSystem (Phase 4)."""

import pytest
from src.domain.character import Character, EmotionalState
from src.storyboard.models import ShotType, CameraAngle, ShotPurpose
from src.storyboard.psychological_camera import PsychologicalCameraPlanner, PsychologicalState
from src.storyboard.lighting_profile import resolve_lighting_profile, LightingProfileType, LIGHTING_PROFILES
from src.storyboard.focal_depth import FocalDepthSystem, FocalDepthConfig, FocalDepthPlane


def test_psychological_camera_low_power_high_fear():
    planner = PsychologicalCameraPlanner()
    vulnerable_state = PsychologicalState(
        power=-0.6,
        fear=0.8,
        certainty=0.2,
        social_dominance=-0.5,
    )
    rec = planner.plan_camera(
        psych_state=vulnerable_state,
        action_text="Evelyn backs into the corner, trapped.",
        shot_purpose=ShotPurpose.ACTION,
    )

    assert rec.camera_angle == CameraAngle.HIGH_ANGLE
    assert rec.shot_type in (ShotType.CLOSE_UP, ShotType.MEDIUM)
    assert "vulnerability" in rec.psychological_rationale.lower()


def test_psychological_camera_high_dominance():
    planner = PsychologicalCameraPlanner()
    dominant_state = PsychologicalState(
        power=0.7,
        fear=0.1,
        certainty=0.8,
        social_dominance=0.7,
    )
    rec = planner.plan_camera(
        psych_state=dominant_state,
        action_text="Vincent steps forward, towering over the desk.",
        shot_purpose=ShotPurpose.THREAT,
    )

    assert rec.camera_angle == CameraAngle.LOW_ANGLE
    assert "dominance" in rec.psychological_rationale.lower()


def test_psychological_camera_sudden_realization_push_in():
    planner = PsychologicalCameraPlanner()
    shock_state = PsychologicalState(certainty=0.2, emotional_intensity=0.9)
    rec = planner.plan_camera(
        psych_state=shock_state,
        action_text="Evelyn gasps, recognizing the seal on the ledger.",
        shot_purpose=ShotPurpose.REVELATION,
    )

    assert rec.shot_type == ShotType.CLOSE_UP
    assert rec.camera_movement == "PUSH IN"


def test_lighting_profile_selection():
    # Emergency claxon / explosion
    prof_alarm = resolve_lighting_profile(mood="Tense", action="Alarm sirens wail as explosion erupts", scene_purpose="CLIMAX")
    assert prof_alarm.id == LightingProfileType.EMERGENCY_RED

    # Interrogation
    prof_interrogate = resolve_lighting_profile(mood="Hostile", action="Vincent questions the captured spy under the hanging lamp", scene_purpose="CONFRONTATION")
    assert prof_interrogate.id == LightingProfileType.INTERROGATION

    # Moonlit dock
    prof_dock = resolve_lighting_profile(mood="Atmospheric", action="Rain hits the waterfront dock at midnight", scene_purpose="SETUP")
    assert prof_dock.id == LightingProfileType.MOONLIT_INDUSTRIAL

    # Hard Noir
    prof_noir = resolve_lighting_profile(mood="Stark standoff", action="Armed confrontation in deep shadows", scene_purpose="CONFRONTATION")
    assert prof_noir.id == LightingProfileType.NOIR_HARD


def test_focal_depth_system():
    config = FocalDepthConfig(
        active_plane=FocalDepthPlane.FOCAL_PLANE,
        foreground_blur_px=1.8,
        background_blur_px=0.7,
    )
    # Subject is sharp (None filter), foreground and background are blurred
    assert FocalDepthSystem.get_layer_filter_id(FocalDepthPlane.FOCAL_PLANE, config) is None
    assert FocalDepthSystem.get_layer_filter_id(FocalDepthPlane.FOREGROUND, config) == "blur_foreground"
    assert FocalDepthSystem.get_layer_filter_id(FocalDepthPlane.BACKGROUND, config) == "blur_background"

    svg_defs = FocalDepthSystem.render_svg_defs(config)
    assert "blur_foreground" in svg_defs
    assert "feGaussianBlur" in svg_defs
