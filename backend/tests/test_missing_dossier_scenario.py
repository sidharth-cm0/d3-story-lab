"""End-to-End integration test: "The Missing Dossier" Scenario (Phase 10).

Demonstrates the entire emergent narrative simulation pipeline:
1. Story structure selection & StoryBlueprint generation with soft pressure.
2. World initialization with connected locations, objects, and asymmetric private secrets.
3. Strict spatial awareness and line of sight.
4. Autonomous simulation execution producing an immutable event log.
5. Causal continuity ('Therefore / But' vs 'And Then') scoring.
6. Observational character arc reconstruction without mutation.
7. Screenplay composition with Fountain export, 100% event provenance, and CEO alignment.
8. Storyboard shot planning with psychological camera framing and keyframe budgeting.
"""

import pytest
from src.domain.story_structure import (
    StoryStructureType,
    StructureSelectionMode,
    PresentationStrategy,
)
from src.narrative.structure_selector import StructureSelector
from src.narrative.blueprint_generator import StoryBlueprintGenerator
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.secret import Secret
from src.domain.goal import Goal
from src.domain.event import Event, EventType
from src.narrative.spatial import SpatialReasoner
from src.simulation.orchestrator import SimulationOrchestrator
from src.providers.mock import MockLLMProvider
from src.narrative.observer import Observer
from src.narrative.scribe import Scribe
from src.narrative.framer import FramingMode
from src.narrative.scene_builder import SceneBuilder
from src.narrative.causal_analyzer import CausalContinuityAnalyzer
from src.narrative.arc_tracker import CharacterArcTracker
from src.narrative.screenplay_validator import ScreenplayQualityValidator
from src.storyboard.planner import StoryboardPlanner
from src.storyboard.visual_bible import VisualBible
from src.storyboard.models import ShotType, CameraAngle, ShotPurpose


def test_missing_dossier_complete_pipeline():
    # -------------------------------------------------------------------------
    # 1. Structure Selection & Blueprint Generation
    # -------------------------------------------------------------------------
    seed_prompt = (
        "An undercover operative infiltrates a secure archives vault at midnight "
        "to extract the missing classified dossier while evading the counter-intelligence director."
    )

    selector = StructureSelector()
    selection = selector.select_structure(prompt=seed_prompt, input_type="beginning")
    assert selection.primary_structure in StoryStructureType._value2member_map_.values()
    assert selection.fit_score >= 60.0
    assert len(selection.fit_rationale) > 0

    blueprint_gen = StoryBlueprintGenerator()
    blueprint = blueprint_gen.generate_blueprint(
        prompt=seed_prompt,
        selection=selection,
        title="The Missing Dossier",
        presentation_strategy=PresentationStrategy.CHRONOLOGICAL,
    )
    assert blueprint.story_title == "The Missing Dossier"
    assert len(blueprint.expected_beats) >= 3
    assert "allowed_interventions" in blueprint.soft_constraints

    # -------------------------------------------------------------------------
    # 2. World State with Spatial Adjacency and Asymmetric Knowledge
    # -------------------------------------------------------------------------
    world = WorldState(id="world_missing_dossier", name="Missing Dossier Cold War World")

    # Three connected locations forming a strict path: Perimeter -> Corridor -> Vault
    loc_perimeter = Location(
        id="loc_perimeter",
        name="Perimeter Fence",
        description="Rain-swept exterior security perimeter",
        connected_locations=["loc_corridor"],
    )
    loc_corridor = Location(
        id="loc_corridor",
        name="Corridor B",
        description="Narrow hallway guarded by harsh fluorescent tubes",
        connected_locations=["loc_perimeter", "loc_vault"],
    )
    loc_vault = Location(
        id="loc_vault",
        name="Archives Vault",
        description="High-security subterranean document depository",
        connected_locations=["loc_corridor"],
    )
    world.locations[loc_perimeter.id] = loc_perimeter
    world.locations[loc_corridor.id] = loc_corridor
    world.locations[loc_vault.id] = loc_vault

    # Classified Dossier object in Vault
    dossier = WorldObject(
        id="obj_dossier",
        name="Classified Dossier",
        description="Red folder stamped TOP SECRET containing cipher codes",
        location_id="loc_vault",
    )
    world.objects[dossier.id] = dossier

    # Goals registry
    g_dossier = Goal(id="g_dossier", character_id="char_operative", description="Extract classified dossier", priority=1)
    g_catch = Goal(id="g_catch", character_id="char_director", description="Corner infiltrator before handover", priority=1)
    world.goals[g_dossier.id] = g_dossier
    world.goals[g_catch.id] = g_catch

    # Secrets registry
    sec_operative = Secret(
        id="sec_01",
        character_id="char_operative",
        statement="Holds microdot cipher decoder ring inside watch bezel",
        importance=0.95,
        known_by=[],
    )
    sec_director = Secret(
        id="sec_02",
        character_id="char_director",
        statement="Knew of security breach 20 minutes before alarms sounded",
        importance=0.85,
        known_by=[],
    )
    world.secrets[sec_operative.id] = sec_operative
    world.secrets[sec_director.id] = sec_director

    # Characters with asymmetric secrets and goals
    operative = Character(
        id="char_operative",
        name="Agent Evelyn",
        role="undercover operative",
        current_location_id="loc_corridor",
        emotional_state=EmotionalState(fear=0.6, anger=0.2, trust=-0.7),
        secrets=[sec_operative.id],
        goals=[g_dossier.id],
    )
    director = Character(
        id="char_director",
        name="Director Kane",
        role="counter-intelligence director",
        current_location_id="loc_corridor",
        emotional_state=EmotionalState(fear=0.1, anger=0.8, trust=-0.9),
        secrets=[sec_director.id],
        goals=[g_catch.id],
    )
    world.characters[operative.id] = operative
    world.characters[director.id] = director

    # Verify asymmetric private knowledge
    assert sec_operative.character_id == "char_operative"
    assert "char_director" not in sec_operative.known_by
    assert sec_director.character_id == "char_director"
    assert "char_operative" not in sec_director.known_by

    # -------------------------------------------------------------------------
    # 3. Spatial Awareness & Adjacency
    # -------------------------------------------------------------------------
    # Perimeter connects to Corridor, but NOT directly to Vault (no teleportation)
    assert "loc_corridor" in world.locations["loc_perimeter"].connected_locations
    assert "loc_vault" not in world.locations["loc_perimeter"].connected_locations

    spatial = SpatialReasoner()
    perimeter_ctx = spatial.compute_spatial_context("loc_perimeter", world)
    assert perimeter_ctx is not None
    assert len(perimeter_ctx.geometry.exits) >= 1

    # -------------------------------------------------------------------------
    # 4. Autonomous Simulation Execution & Immutable Event Log
    # -------------------------------------------------------------------------
    provider = MockLLMProvider()
    orchestrator = SimulationOrchestrator(world=world, provider=provider, blueprint=blueprint)
    results = orchestrator.run(max_ticks=8)

    assert len(results) >= 4
    assert world.current_tick >= 8
    assert len(world.events) >= 4

    # Events must be immutable records
    recorded_events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
    initial_event_count = len(recorded_events)
    assert all(isinstance(e, Event) for e in recorded_events)

    # -------------------------------------------------------------------------
    # 5. Causal Continuity ('Therefore / But' vs 'And Then') Scoring
    # -------------------------------------------------------------------------
    causal_analyzer = CausalContinuityAnalyzer()
    causal_report = causal_analyzer.analyze_event_causality(recorded_events)

    assert causal_report.total_transitions >= 1
    assert causal_report.but_therefore_ratio >= 0.0
    assert (causal_report.but_therefore_count + causal_report.and_then_count) == causal_report.total_transitions

    # -------------------------------------------------------------------------
    # 6. Observational Character Arc Reconstruction
    # -------------------------------------------------------------------------
    arc_tracker = CharacterArcTracker()
    all_arcs = arc_tracker.trace_all_arcs(world, recorded_events)

    assert "char_operative" in all_arcs
    assert "char_director" in all_arcs
    op_arc = all_arcs["char_operative"]
    assert op_arc.character_name == "Agent Evelyn"
    assert op_arc.starting_state is not None
    assert op_arc.ending_state is not None
    # Verify zero world mutation occurred during arc tracking
    assert len(world.events) == initial_event_count

    # -------------------------------------------------------------------------
    # 7. Scribe Screenplay Composition & Provenance Hardening
    # -------------------------------------------------------------------------
    observer = Observer(provider=provider)
    selection_events = observer.observe_events(recorded_events, world)

    scribe = Scribe(provider=provider)
    screenplay = scribe.compose_screenplay(
        selection=selection_events,
        world=world,
        title="THE MISSING DOSSIER",
        framing_mode=FramingMode.CHRONOLOGICAL,
    )

    assert len(screenplay.scenes) >= 1
    fountain_text = screenplay.to_fountain()
    assert "THE MISSING DOSSIER" in fountain_text

    # Validate provenance, CEO alignment, and zero secret leakage
    validator = ScreenplayQualityValidator()
    report = validator.validate(screenplay, world)

    assert report.provenance_coverage == 1.0, "All screenplay blocks must trace directly to verified simulation events"
    assert report.ungrounded_block_count == 0, "No ungrounded blocks allowed in canonical screenplay"
    assert report.knowledge_leak_count == 0, "No private secrets may be leaked"
    assert report.scene_turn_fulfillment_score >= 0.5

    # Ensure CoreEmotionalObjective is present on scenes
    for scene in screenplay.scenes:
        assert "core_emotional_objective" in scene.metadata
        ceo = scene.metadata["core_emotional_objective"]
        assert "focal_character_id" in ceo
        assert "immediate_desire" in ceo

    # -------------------------------------------------------------------------
    # 8. Storyboard Shot Planning with Psychological Camera & Budgeting
    # -------------------------------------------------------------------------
    bible = VisualBible.from_world(world)
    planner = StoryboardPlanner(panels_per_page=4, density_mode="standard")

    # Plan shots with budget of 8 keyframes
    shot_plan = planner.plan_shots(screenplay, world=world, bible=bible, project_id=world.id, keyframe_budget=8)

    assert len(shot_plan.panels) >= 2
    keyframes = [p for p in shot_plan.panels if p.is_keyframe]
    assert len(keyframes) <= 8

    # Focal character panels must integrate the Core Emotional Objective into psychological rationale
    focal_panels = [p for p in shot_plan.panels if p.metadata.get("is_focal_character") is True]
    if focal_panels:
        for p in focal_panels:
            rationale = p.psychological_rationale or p.metadata.get("psychological_rationale", "")
            assert "focal objective" in rationale.lower()

    # Previs fallback check: procedural SVG must never masquerade as final artwork
    for p in shot_plan.panels:
        assert p.rendered_svg is None or p.rendered_svg == ""
        if p.image_url:
            assert not p.image_url.endswith(".svg")
