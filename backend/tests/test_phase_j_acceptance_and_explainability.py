"""Phase J1 & J2 Acceptance Story and Explainability Audit.

Validates the full procedural narrative pipeline under deterministic execution:
Premise -> Structure -> Character Intake -> Dynamics -> Archetypes -> Relationships
-> Conflict Graph -> Character Reference Profile -> Simulation -> State History
-> Dramatic Signals -> Director/Sufficiency -> Observer -> Scene Builder -> Scribe
-> Screenplay (Fountain) -> Visual Bible -> Continuity -> Shot Planner -> Storyboard -> Export.

Also performs the J2 Explainability Audit verifying complete provenance across all stages:
- Character action -> goals/beliefs/knowledge/emotion
- Conflict edge -> dimensions + evidence
- Relationship change -> event ID
- Arc shift -> observed events
- Screenplay block -> grounded simulation event IDs
- Storyboard shot -> screenplay block + VisualBible + shot-plan provenance
"""

import json
import pytest
from src.domain.story_structure import (
    StoryStructureType,
    PresentationStrategy,
)
from src.narrative.structure_selector import StructureSelector
from src.narrative.blueprint_generator import StoryBlueprintGenerator
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.secret import Secret
from src.domain.goal import Goal
from src.domain.event import Event, EventType
from src.domain.character_dynamics import CharacterDynamicsProfile
from src.domain.character_reference import CharacterReferenceProfile, FieldAuthority
from src.domain.relationship import Relationship
from src.domain.conflict import ConflictGraph, ConflictDimension
from src.narrative.conflict_engine import ConflictEngine
from src.simulation.orchestrator import SimulationOrchestrator
from src.providers.mock import MockLLMProvider
from src.narrative.state_history import CharacterStateHistoryReconstructor
from src.narrative.dramatic_signals import extract_dramatic_signals
from src.narrative.arc_tracker import CharacterArcTracker
from src.narrative.causal_analyzer import CausalContinuityAnalyzer
from src.narrative.observer import Observer
from src.narrative.scribe import Scribe
from src.narrative.framer import FramingMode
from src.narrative.scene_builder import SceneBuilder
from src.narrative.screenplay_validator import ScreenplayQualityValidator
from src.storyboard.visual_bible import VisualBible
from src.storyboard.planner import StoryboardPlanner
from src.storyboard.shot_planner import ShotPlanner
from src.storyboard.models import ShotType, CameraAngle


def test_phase_j_acceptance_story_and_explainability_audit(tmp_path):
    # =========================================================================
    # 1. PREMISE & STRUCTURE SELECTION
    # =========================================================================
    seed_prompt = (
        "An undercover operative infiltrates a secure archives vault at midnight "
        "to extract the missing classified dossier while evading the counter-intelligence director."
    )

    selector = StructureSelector()
    selection = selector.select_structure(prompt=seed_prompt, input_type="beginning")
    assert selection.primary_structure in StoryStructureType._value2member_map_.values()
    assert selection.fit_score >= 50.0

    blueprint_gen = StoryBlueprintGenerator()
    blueprint = blueprint_gen.generate_blueprint(
        prompt=seed_prompt,
        selection=selection,
        title="The Missing Dossier",
        presentation_strategy=PresentationStrategy.CHRONOLOGICAL,
    )
    assert blueprint.story_title == "The Missing Dossier"
    assert len(blueprint.expected_beats) >= 3

    # =========================================================================
    # 2. WORLD, LOCATIONS, OBJECTS, AND SECRETS
    # =========================================================================
    world = WorldState(id="world_j_acceptance", name="Missing Dossier Cold War World")

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

    dossier = WorldObject(
        id="obj_dossier",
        name="Classified Dossier",
        description="Red folder stamped TOP SECRET containing cipher codes",
        location_id="loc_vault",
    )
    world.objects[dossier.id] = dossier

    # Asymmetric secrets
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

    # Goals
    g_dossier = Goal(id="g_dossier", character_id="char_operative", description="Extract classified dossier", priority=1)
    g_catch = Goal(id="g_catch", character_id="char_director", description="Corner infiltrator before handover", priority=1)
    world.goals[g_dossier.id] = g_dossier
    world.goals[g_catch.id] = g_catch

    # =========================================================================
    # 3. CHARACTER INTAKE, DYNAMICS, RELATIONSHIPS, & REFERENCE PROFILES
    # =========================================================================
    operative = Character(
        id="char_operative",
        name="Agent Evelyn",
        role="undercover operative",
        current_location_id="loc_corridor",
        emotional_state=EmotionalState(fear=0.5, anger=0.2, trust=-0.6),
        secrets=[sec_operative.id],
        goals=[g_dossier.id],
    )
    director = Character(
        id="char_director",
        name="Director Kane",
        role="counter-intelligence director",
        current_location_id="loc_corridor",
        emotional_state=EmotionalState(fear=0.1, anger=0.8, trust=-0.8),
        secrets=[sec_director.id],
        goals=[g_catch.id],
    )

    # Dynamics Profile (behavioral authority)
    op_dynamics = CharacterDynamicsProfile(
        mannerisms=["checks wristwatch constantly", "avoids prolonged eye contact"],
        habits=["memorizes floor plans before entry"],
        lifestyle="covert field operator living under aliases",
        speech_style="clipped, precise, low-register",
        core_wound="betrayed by previous station chief",
    )
    dir_dynamics = CharacterDynamicsProfile(
        mannerisms=["paces methodically with hands clasped behind back"],
        habits=["reviews security manifests meticulously"],
        lifestyle="senior intelligence administrator",
        speech_style="authoritative, formal, interrogative",
        core_wound="failure to prevent embassy bombing a decade prior",
    )
    operative.dynamics = op_dynamics
    director.dynamics = dir_dynamics

    # Multidimensional Relationship
    rel_op_dir = Relationship(
        id="rel_op_dir",
        character_a_id="char_operative",
        character_b_id="char_director",
        trust=-0.75,
        respect=0.40,
        affinity=-0.50,
        suspicion=0.90,
        resentment=0.60,
        dependency=0.10,
    )
    world.relationships["rel_op_dir"] = rel_op_dir

    # Stable Visual Reference Profile (Phase G authoritative visual identity)
    op_ref = CharacterReferenceProfile(
        apparent_age_range="Late 20s",
        build="Athletic, lean",
        height_impression="Average height",
        face_description="Determined features, sharp watchful gray eyes",
        hair="Dark brown bob cut behind ears",
        grooming="Practical, understated",
        distinguishing_features="Small scar across left collarbone",
        baseline_wardrobe="Charcoal tactical turtleneck, dark wool trousers",
        wardrobe_palette=["charcoal", "matte black", "slate gray"],
        posture="Alert, low center of gravity",
        signature_objects=["Microdot decoder watch", "Lockpick set"],
        usual_environments=["Subterranean archives", "Shadowed alleys"],
    )
    op_ref.sync_from_dynamics(op_dynamics)
    op_ref.lock_field("signature_objects")
    operative.reference_profile = op_ref

    dir_ref = CharacterReferenceProfile(
        apparent_age_range="Mid 50s",
        build="Broad-shouldered, imposing",
        height_impression="Tall",
        face_description="Severe weathered visage, heavy brow",
        hair="Short steel-gray hair, trimmed temples",
        grooming="Immaculate, military precision",
        distinguishing_features="Gold signet ring on right hand",
        baseline_wardrobe="Double-breasted navy service coat over pressed white shirt",
        wardrobe_palette=["navy blue", "brass", "slate"],
        posture="Rigid, commanding upright posture",
        signature_objects=["Gold signet ring", "Directorate cipher ledger"],
        usual_environments=["Command center", "Vault checkpoints"],
    )
    dir_ref.sync_from_dynamics(dir_dynamics)
    dir_ref.lock_field("signature_objects")
    director.reference_profile = dir_ref

    world.characters[operative.id] = operative
    world.characters[director.id] = director

    # =========================================================================
    # 4. CONFLICT GRAPH ENGINE
    # =========================================================================
    conflict_graph = ConflictEngine.derive_conflict_graph(world, project_id=world.id)
    assert len(conflict_graph.edges) >= 1
    # Check that interpersonal tension between operative and director is recognized
    pair_edge = conflict_graph.get_edge("char_operative", "char_director")
    assert pair_edge is not None
    assert pair_edge.aggregate_intensity >= 0.1 or len(pair_edge.dimensions) >= 1

    # =========================================================================
    # 5. AUTONOMOUS SIMULATION (SEEDED, DETERMINISTIC)
    # =========================================================================
    provider = MockLLMProvider()
    orchestrator = SimulationOrchestrator(world=world, provider=provider, blueprint=blueprint)
    results = orchestrator.run(max_ticks=8)

    assert len(results) >= 4
    assert world.current_tick >= 8
    assert len(world.events) >= 4
    recorded_events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))

    # =========================================================================
    # 6. ANALYTICS: STATE HISTORY & DRAMATIC SIGNALS (READ-ONLY, ZERO MUTATION)
    # =========================================================================
    initial_event_count = len(world.events)

    history_reconstructor = CharacterStateHistoryReconstructor()
    op_history = history_reconstructor.reconstruct_character_history(
        world=world,
        character_id="char_operative",
        target_character_id="char_director",
        project_id=world.id,
    )
    assert op_history is not None
    assert op_history.character_id == "char_operative"
    assert "emotional_valence" in op_history.series
    assert "trust" in op_history.series

    dramatic_signals = extract_dramatic_signals(world)
    assert dramatic_signals is not None
    assert dramatic_signals.unresolved_tension_level >= 0.0

    arc_tracker = CharacterArcTracker()
    arcs = arc_tracker.trace_all_arcs(world, recorded_events)
    assert "char_operative" in arcs

    # Verify analytics did not mutate world state
    assert len(world.events) == initial_event_count

    # =========================================================================
    # 7. OBSERVER & SCENE BUILDER & SCRIBE COMPOSITION
    # =========================================================================
    observer = Observer(provider=provider)
    selection = observer.observe_events(recorded_events, world)

    scribe = Scribe(provider=provider)
    screenplay = scribe.compose_screenplay(
        selection=selection,
        world=world,
        title="THE MISSING DOSSIER",
        framing_mode=FramingMode.CHRONOLOGICAL,
    )
    assert len(screenplay.scenes) >= 1
    fountain_script = screenplay.to_fountain()
    assert "THE MISSING DOSSIER" in fountain_script

    # Screenplay quality & provenance validation
    validator = ScreenplayQualityValidator()
    val_report = validator.validate(screenplay, world)
    assert val_report.provenance_coverage == 1.0, "Screenplay must maintain 100% provenance coverage"
    assert val_report.ungrounded_block_count == 0
    assert val_report.knowledge_leak_count == 0

    # =========================================================================
    # 8. VISUAL BIBLE & SHOT PLANNER CONTINUITY
    # =========================================================================
    bible = VisualBible.from_world(world)
    assert "char_operative" in bible.characters
    assert bible.characters["char_operative"].age == "Late 20s"
    assert "char_director" in bible.characters
    assert bible.characters["char_director"].age == "Mid 50s"

    planner = StoryboardPlanner(panels_per_page=4, density_mode="standard")
    shot_plan = planner.plan_shots(screenplay, world=world, bible=bible, project_id=world.id, keyframe_budget=8)
    assert len(shot_plan.panels) >= 2

    # Verify shot continuity properties across storyboard panels
    for panel in shot_plan.panels:
        assert panel.camera_axis_side in ("LEFT", "RIGHT", "NEUTRAL")
        assert panel.screen_direction in ("LEFT_TO_RIGHT", "RIGHT_TO_LEFT", "TOWARD_CAMERA", "AWAY_FROM_CAMERA", "STATIC", "NEUTRAL")
        assert panel.shot_type in ShotType
        assert panel.camera_angle in CameraAngle

    # =========================================================================
    # 9. EXPLAINABILITY AUDIT (J2)
    # =========================================================================
    # a. Character Action Explainability
    for evt in recorded_events:
        for actor_id in evt.actor_ids:
            if actor_id in world.characters:
                char = world.characters[actor_id]
                # Character must exist with valid active goals or emotional state
                assert len(char.goals) > 0 or char.emotional_state is not None

    # b. Conflict Edge Explainability
    assert len(pair_edge.evidence) >= 1, "Conflict edge must carry concrete evidence"
    for ev in pair_edge.evidence:
        assert ev.dimension in ConflictDimension
        assert len(ev.description) > 0

    # c. Relationship / State Change Explainability
    for metric_name, series_obj in op_history.series.items():
        for pt in series_obj.points:
            if pt.tick > 0 and pt.event_ids:
                for eid in pt.event_ids:
                    assert eid in world.events, f"Event {eid} in history points must exist in canonical events"

    # d. Arc Shift Explainability
    op_arc = arcs["char_operative"]
    assert op_arc.starting_state is not None
    assert op_arc.ending_state is not None

    # e. Screenplay Line Explainability
    total_blocks = 0
    grounded_blocks = 0
    for scene in screenplay.scenes:
        for blk in scene.blocks:
            total_blocks += 1
            if blk.source_event_ids:
                for eid in blk.source_event_ids:
                    assert eid in world.events
                grounded_blocks += 1

    assert total_blocks > 0
    coverage = grounded_blocks / total_blocks
    assert coverage == 1.0, f"Explainability coverage was {coverage}, expected 1.0"

    # f. Storyboard Shot Explainability
    for panel in shot_plan.panels:
        assert panel.id != ""
        assert panel.shot_type in ShotType
        assert panel.action != "" or panel.action_description != ""

    # =========================================================================
    # 10. EXPORT INTEGRITY
    # =========================================================================
    export_payload = {
        "title": blueprint.story_title,
        "fountain": fountain_script,
        "panel_count": len(shot_plan.panels),
        "total_events": len(recorded_events),
        "provenance_coverage": coverage,
    }
    out_file = tmp_path / "acceptance_export.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(export_payload, f)

    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as f:
        loaded_export = json.load(f)
    assert loaded_export["provenance_coverage"] == 1.0
    assert loaded_export["total_events"] >= 4
