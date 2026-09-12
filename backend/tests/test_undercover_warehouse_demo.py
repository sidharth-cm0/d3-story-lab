"""End-to-end verification of the undercover warehouse dossier recovery scenario.

Tests the full canonical pipeline:
User Prompt -> World + Actors -> Autonomous Simulation -> Immutable Event History
-> Observer -> Scribe -> Screenplay -> Shot Planner -> Hand-Drawn Storyboard
"""

import pytest
from src.generator.initializer import WorldInitializerService
from src.simulation.orchestrator import SimulationOrchestrator
from src.providers.mock import MockLLMProvider
from src.narrative.observer import Observer
from src.narrative.scribe import Scribe
from src.narrative.framer import FramingMode
from src.narrative.screenplay_validator import ScreenplayQualityValidator
from src.narrative.fountain import ScreenplayBlockType
from src.storyboard.planner import StoryboardPlanner
from src.storyboard.visual_bible import VisualBible
from src.storyboard.sketch.renderer import HandDrawnStoryboardProvider
from src.storyboard.storyboard_validator import StoryboardQualityValidator


def test_undercover_warehouse_dossier_scenario():
    """Verify the undercover detective warehouse dossier scenario end-to-end."""
    prompt = "An undercover detective infiltrates an abandoned warehouse at midnight to recover a stolen classified dossier."

    # 1. World Initialization
    provider = MockLLMProvider()
    initializer = WorldInitializerService(provider=provider)
    plan = initializer.generate_plan(prompt, target_duration_minutes=20)
    world = initializer.instantiate_world(plan)

    assert len(world.characters) >= 2
    assert len(world.locations) >= 2
    assert len(world.objects) >= 1

    # Verify secret exists and is confidential
    assert len(world.secrets) >= 2
    assert any("warrant" in s.statement.lower() or "document" in s.statement.lower() or "seizure" in s.statement.lower() for s in world.secrets.values())

    # 2. Autonomous Simulation Run
    orchestrator = SimulationOrchestrator(world=world, provider=provider)
    results = orchestrator.run(max_ticks=10)

    assert len(results) >= 5
    assert world.current_tick >= 10
    total_events = len(world.events)
    assert total_events >= 5

    # 3. Observer Event Selection
    observer = Observer(provider=provider)
    events_list = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
    selection = observer.observe_events(events_list, world)
    assert len(selection.filtered_beats) >= 2

    # 4. Scribe Screenplay Composition (Chronological)
    scribe = Scribe(provider=provider)
    screenplay = scribe.compose_screenplay(selection, world, title="THE MIDNIGHT DOSSIER", framing_mode=FramingMode.CHRONOLOGICAL)

    assert len(screenplay.scenes) >= 2
    fountain_text = screenplay.to_fountain()
    assert "THE MIDNIGHT DOSSIER" in fountain_text
    assert "EXT." in fountain_text or "INT." in fountain_text

    # Verify subtext, performance cues, and no secret leakage
    has_performance_cue = False
    for scene in screenplay.scenes:
        for block in scene.blocks:
            if block.block_type == ScreenplayBlockType.PARENTHETICAL:
                if block.is_performance_cue:
                    has_performance_cue = True
                    assert block.cue_type is not None

    # Quality validation of screenplay
    screenplay_validator = ScreenplayQualityValidator()
    sp_report = screenplay_validator.validate(screenplay, world)
    assert sp_report.knowledge_leak_count == 0, "No secrets may leak into dialogue"
    assert sp_report.parenthetical_ratio <= 0.6
    assert sp_report.overall_quality_score >= 75.0

    # 5. In-Media-Res Alternate Framing
    screenplay_in_media = scribe.compose_screenplay(
        selection, world, title="THE MIDNIGHT DOSSIER (FLASHFORWARD)", framing_mode=FramingMode.IN_MEDIA_RES
    )
    assert screenplay_in_media.scenes[0].framing_type.lower() == "in_media_res"
    # Verify canonical simulation state was NOT mutated by framing
    assert len(world.events) == total_events

    # 6. Shot Planning with Psychological Camera, Transitions, and Lighting Profiles
    bible = VisualBible.from_world(world)
    planner = StoryboardPlanner(panels_per_page=4, density_mode="standard")
    shot_plan = planner.plan_shots(screenplay, world, bible=bible, project_id=world.id)

    assert len(shot_plan.panels) >= 4

    # Verify presence of cinematic attributes on planned panels
    shot_types = {p.shot_type for p in shot_plan.panels}
    camera_angles = {p.camera_angle for p in shot_plan.panels}
    lighting_profiles = {p.lighting_profile_id for p in shot_plan.panels if p.lighting_profile_id}
    transitions = {p.transition_type for p in shot_plan.panels if p.transition_type}

    assert len(shot_types) >= 2, "Shot variety should include multiple shot types"
    assert len(camera_angles) >= 2, "Camera variety should include multiple angles"
    assert len(lighting_profiles) >= 1, "At least one lighting profile should be assigned"
    assert len(transitions) >= 1, "Cinematic transitions should be planned between shots"

    # 7. Hand-Drawn SVG Storyboard Rendering
    renderer = HandDrawnStoryboardProvider()
    rendered_panels = []
    for panel in shot_plan.panels:
        res = renderer.generate_panel(panel, bible=bible, version=1)
        assert res.status.value == "ready"
        assert res.mode == "hand_drawn"
        assert res.provider == "hand_drawn_storyboard"
        assert res.svg_content is not None
        assert "<svg" in res.svg_content
        assert "</svg>" in res.svg_content
        assert "feTurbulence" in res.svg_content, "SVG must contain graphite texture filters"
        assert "paper_grain" in res.svg_content, "SVG must contain paper grain overlay"
        rendered_panels.append(res)

    assert len(rendered_panels) == len(shot_plan.panels)

    # 8. Storyboard Quality Validation
    storyboard_validator = StoryboardQualityValidator()
    sb_report = storyboard_validator.validate(shot_plan.panels, screenplay=screenplay, bible=bible)

    assert sb_report.total_panels == len(shot_plan.panels)
    assert sb_report.shot_variety_score > 0.0
    assert sb_report.overall_storyboard_score >= 60.0
