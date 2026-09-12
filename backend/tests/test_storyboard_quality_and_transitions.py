"""Tests for TransitionPlanner, Graphite SVG rendering, and StoryboardQualityValidator (Phase 5 & 6)."""

import pytest
from src.storyboard.models import StoryboardPanel, ShotType, CameraAngle, ShotPurpose
from src.storyboard.transitions import TransitionPlanner, TransitionType
from src.storyboard.storyboard_validator import StoryboardQualityValidator
from src.storyboard.sketch.renderer import HandDrawnStoryboardProvider


def test_transition_planner_insert_to_reaction():
    p1 = StoryboardPanel(
        id="p1",
        shot_number=1,
        shot_type=ShotType.INSERT,
        narrative_purpose=ShotPurpose.CLUE,
        action="Evelyn slides open the secret drawer, exposing the classified dossier.",
    )
    p2 = StoryboardPanel(
        id="p2",
        shot_number=2,
        shot_type=ShotType.CLOSE_UP,
        narrative_purpose=ShotPurpose.REACTION,
        action="Vincent freezes, his gaze locking onto the revealed documents.",
    )
    links = TransitionPlanner.plan_transitions([p1, p2])

    assert len(links) == 1
    assert links[0].transition_type in (TransitionType.INSERT_TO_REACTION, TransitionType.RACK_FOCUS)
    assert p2.transition_type is not None


def test_transition_planner_action_match():
    p1 = StoryboardPanel(
        id="p1",
        shot_number=1,
        shot_type=ShotType.WIDE,
        narrative_purpose=ShotPurpose.ACTION,
        action="The detective sprints across the slippery warehouse floor.",
    )
    p2 = StoryboardPanel(
        id="p2",
        shot_number=2,
        shot_type=ShotType.MEDIUM,
        narrative_purpose=ShotPurpose.ACTION,
        action="He leaps over the conveyor belt and continues his run toward the north exit.",
    )
    links = TransitionPlanner.plan_transitions([p1, p2])

    assert len(links) == 1
    assert links[0].transition_type == TransitionType.ACTION_MATCH


def test_graphite_displacement_and_paper_grain_in_svg():
    panel = StoryboardPanel(
        id="p_test_graphite",
        shot_number=1,
        shot_type=ShotType.MEDIUM,
        camera_angle=CameraAngle.LOW_ANGLE,
        narrative_purpose=ShotPurpose.THREAT,
        action="Vincent raises his hand, ordering the guards to seal the exits.",
        lighting="Stark high-contrast noir lighting",
        sfx_label="SLAM!",
    )
    provider = HandDrawnStoryboardProvider()
    res = provider.generate_panel(panel, version=1)

    assert res.svg_content is not None
    # Verify graphite edge displacement filters
    assert "graphite_bg" in res.svg_content
    assert "graphite_subject" in res.svg_content
    assert "feDisplacementMap" in res.svg_content
    # Verify paper grain texture
    assert "paper_grain" in res.svg_content
    # Verify sound effect typography
    assert "SLAM!" in res.svg_content
    # Verify offline status and NO three.js
    assert "three" not in res.svg_content.lower()
    assert "webgl" not in res.svg_content.lower()


def test_storyboard_quality_validator_metrics():
    panels = [
        StoryboardPanel(id="p1", shot_number=1, shot_type=ShotType.WIDE, camera_angle=CameraAngle.EYE_LEVEL, narrative_purpose=ShotPurpose.ESTABLISH, action="Establishing waterfront dock."),
        StoryboardPanel(id="p2", shot_number=2, shot_type=ShotType.INSERT, camera_angle=CameraAngle.HIGH_ANGLE, narrative_purpose=ShotPurpose.CLUE, action="Dossier revealed on steel desk."),
        StoryboardPanel(id="p3", shot_number=3, shot_type=ShotType.CLOSE_UP, camera_angle=CameraAngle.DUTCH_ANGLE, narrative_purpose=ShotPurpose.REACTION, action="Detective gasps in realization."),
        StoryboardPanel(id="p4", shot_number=4, shot_type=ShotType.MEDIUM, camera_angle=CameraAngle.LOW_ANGLE, narrative_purpose=ShotPurpose.THREAT, action="Vincent draws gun, blocking exit."),
    ]
    TransitionPlanner.plan_transitions(panels)

    validator = StoryboardQualityValidator()
    report = validator.validate(panels)

    assert report.total_panels == 4
    assert report.shot_variety_score >= 0.5
    assert report.psychological_camera_coherence >= 0.7
    assert report.overall_storyboard_score > 70.0
    assert report.transition_coverage_ratio > 0.0
