"""Simulation Sovereignty and Architectural Invariant Tests.

Phase G Invariant Verification:
1. Canonical simulation sovereignty: Differing CharacterReferenceProfiles, visual anchors,
   continuity states, or analytics metadata MUST yield byte-identical action scoring, proposals,
   executed events, and event log hashes.
2. AST / Import-graph isolation: Decision, motivation, perception, and executor modules
   MUST NOT import reference-profile, continuity, storyboard, or analytics modules.
3. CharacterWorldView firewall: CharacterWorldView must contain zero visual, analytics, or hidden story metadata.
4. No write paths: VisualBible and continuity modules must be strictly read-only relative to WorldState.
"""

import ast
import hashlib
import os
from pathlib import Path
import pytest

from src.domain.world import WorldState, Location, WorldObject, Relationship, Goal, Proposition
from src.domain.character import Character, EmotionalState
from src.domain.character_reference import CharacterReferenceProfile
from src.domain.world_view import CharacterWorldView, project_view
from src.simulation.orchestrator import SimulationOrchestrator
from src.storyboard.continuity_projector import ContinuityProjector
from src.storyboard.keyframe_rendering import VisualBibleBuilder


def _build_test_world(character_reference: CharacterReferenceProfile | None = None) -> WorldState:
    """Construct a deterministic baseline world with one or two characters."""
    loc_office = Location(id="loc_office", name="Director's Office")
    loc_hall = Location(id="loc_hall", name="Corridor")
    loc_office.connected_locations.append("loc_hall")
    loc_hall.connected_locations.append("loc_office")

    char_elena = Character(
        id="char_elena",
        name="Elena",
        role="Archivist",
        location_id="loc_office",
        reference_profile=character_reference,
        emotional_state=EmotionalState(fear=0.2, anger=0.1, curiosity=0.8),
    )
    char_elena.goals.append("goal_find_truth")

    dossier = WorldObject(
        id="obj_dossier",
        name="Classified Dossier",
        location_id="loc_office",
        portable=True,
    )

    goal = Goal(
        id="goal_find_truth",
        character_id="char_elena",
        description="Secure the classified dossier",
        priority=1.0,
        status="active",
    )

    world = WorldState(
        id="world_sovereignty_test",
        name="Sovereignty Test World",
        current_tick=0,
        locations={"loc_office": loc_office, "loc_hall": loc_hall},
        characters={"char_elena": char_elena},
        objects={"obj_dossier": dossier},
        goals={"goal_find_truth": goal},
    )
    return world


def _hash_event_log(world: WorldState) -> str:
    """Compute deterministic SHA-256 hash over executed events."""
    hasher = hashlib.sha256()
    events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
    for e in events:
        actors = ",".join(e.actor_ids)
        target = e.metadata.get("target_id") or e.metadata.get("object_id") or ""
        entry = f"{e.tick}:{e.event_type.value}:{actors}:{target}:{e.location_id}:{e.description}"
        hasher.update(entry.encode("utf-8"))
    return hasher.hexdigest()


def test_simulation_sovereignty_divergent_visual_profiles_yield_identical_simulation():
    """Invariant #7 & #22: Differing CharacterReferenceProfiles must yield identical simulation traces."""
    # Profile A: Young, athletic, modern flight suit
    ref_a = CharacterReferenceProfile(
        apparent_age_range="early 20s",
        build="athletic",
        baseline_wardrobe="synthetic flight suit",
        signature_objects=["silver lighter"],
    )

    # Profile B: Elderly, frail, Victorian formal wear
    ref_b = CharacterReferenceProfile(
        apparent_age_range="late 70s",
        build="frail, stooped",
        baseline_wardrobe="frayed velvet frock coat",
        signature_objects=["carved ivory cane"],
    )

    world_a = _build_test_world(character_reference=ref_a)
    world_b = _build_test_world(character_reference=ref_b)

    orch_a = SimulationOrchestrator(world=world_a, seed=42)
    orch_b = SimulationOrchestrator(world=world_b, seed=42)

    # Step both simulations for 3 ticks
    events_a = []
    results_a = []
    results_b = []
    for _ in range(3):
        results_a.extend(orch_a.step())
        results_b.extend(orch_b.step())

    # 1. Action results must match identically
    assert len(results_a) == len(results_b)
    for ra, rb in zip(results_a, results_b):
        assert ra.status == rb.status
        assert ra.events_created == rb.events_created

    # 2. Executed events must match identically
    events_a = sorted(world_a.events.values(), key=lambda e: (e.tick, e.id))
    events_b = sorted(world_b.events.values(), key=lambda e: (e.tick, e.id))
    assert len(events_a) == len(events_b)
    for ea, eb in zip(events_a, events_b):
        assert ea.event_type == eb.event_type
        assert ea.actor_ids == eb.actor_ids
        assert ea.location_id == eb.location_id
        assert ea.description == eb.description

    # 3. Overall event log hashes must be byte-identical
    hash_a = _hash_event_log(world_a)
    hash_b = _hash_event_log(world_b)
    assert hash_a == hash_b


def test_simulation_sovereignty_ast_import_isolation():
    """Static AST check: Core simulation modules must NEVER import visual, continuity, or analytics modules."""
    forbidden_import_substrings = [
        "character_reference",
        "continuity_projector",
        "keyframe_rendering",
        "shot_planner",
        "sketch",
        "storyboard",
        "analytics",
    ]

    sim_files = [
        "src/simulation/orchestrator.py",
        "src/simulation/policy.py",
        "src/simulation/action_validator.py",
        "src/simulation/action_executor.py",
        "src/simulation/perception.py",
        "src/domain/world_view.py",
    ]

    repo_backend = Path("/workspaces/d3-story-lab/backend")

    for rel_path in sim_files:
        full_path = repo_backend / rel_path
        if not full_path.exists():
            continue

        tree = ast.parse(full_path.read_text(encoding="utf-8"), filename=str(full_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_import_substrings:
                        assert forbidden not in alias.name, (
                            f"Illegal import '{alias.name}' in simulation module {rel_path} violates simulation sovereignty!"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for forbidden in forbidden_import_substrings:
                    assert forbidden not in module, (
                        f"Illegal from-import '{module}' in simulation module {rel_path} violates simulation sovereignty!"
                    )


def test_simulation_sovereignty_character_world_view_firewall():
    """Firewall check: CharacterWorldView must contain no visual profile, continuity, or analytics fields."""
    forbidden_field_fragments = [
        "reference_profile",
        "visual_profile",
        "continuity",
        "dramatic_need",
        "archetype",
        "conflict_graph",
        "image",
        "camera",
        "shot",
    ]

    wv_fields = CharacterWorldView.model_fields.keys()
    for field_name in wv_fields:
        for forbidden in forbidden_field_fragments:
            assert forbidden not in field_name.lower(), (
                f"Forbidden field '{field_name}' in CharacterWorldView leaks presentation/analytics into actor knowledge!"
            )


def test_simulation_sovereignty_visual_bible_and_continuity_no_write_path():
    """Verify that VisualBibleBuilder and ContinuityProjector cannot mutate WorldState."""
    world = _build_test_world()
    orig_chars = {k: v.model_dump() for k, v in world.characters.items()}
    orig_objs = {k: v.model_dump() for k, v in world.objects.items()}
    orig_locs = {k: v.model_dump() for k, v in world.locations.items()}

    # Run VisualBibleBuilder
    builder = VisualBibleBuilder(world=world)
    builder.get_or_create_character("char_elena")
    builder.get_or_create_location("loc_office")
    builder.get_or_create_prop("obj_dossier")

    # Run ContinuityProjector
    events = list(world.events.values())
    ContinuityProjector.project_character_continuity("char_elena", events, tick=1)
    ContinuityProjector.project_scene_continuity(world, events, scene_id="scene_01")

    # Verify WorldState structures are byte-identical
    assert {k: v.model_dump() for k, v in world.characters.items()} == orig_chars
    assert {k: v.model_dump() for k, v in world.objects.items()} == orig_objs
    assert {k: v.model_dump() for k, v in world.locations.items()} == orig_locs
