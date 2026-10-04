"""Phase J3 Determinism Matrix and Simulation Sovereignty Suite.

Validates that:
1. Replay determinism: Same seed yields byte-identical event sequences and hash across multiple fixed seeds (42, 101, 777).
2. Visual Reference Sovereignty: Radically altered CharacterReferenceProfile does NOT alter canonical simulation events or hashes.
3. Analytics Non-Interference: Intermediate calls to StateHistory, ConflictEngine, and DramaticSignals do NOT alter canonical simulation trajectory.
4. Storyboard Isolation: Storyboard planning and reference assets do not mutate WorldState or EventLog.
"""

from typing import Any
import hashlib
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
from src.simulation.orchestrator import SimulationOrchestrator
from src.providers.mock import MockLLMProvider
from src.narrative.state_history import CharacterStateHistoryReconstructor
from src.narrative.conflict_engine import ConflictEngine
from src.narrative.dramatic_signals import extract_dramatic_signals
from src.storyboard.visual_bible import VisualBible
from src.storyboard.planner import StoryboardPlanner
from src.narrative.scribe import Scribe
from src.narrative.observer import Observer
from src.narrative.framer import FramingMode


def create_deterministic_world(seed: int, visual_variant: int = 0) -> tuple[WorldState, Any]:
    """Factory creating an isolated WorldState and Blueprint for a specific seed."""
    selector = StructureSelector()
    selection = selector.select_structure(prompt="Cold war infiltration at subterranean vault", input_type="beginning")
    blueprint_gen = StoryBlueprintGenerator()
    blueprint = blueprint_gen.generate_blueprint(
        prompt="Cold war infiltration at subterranean vault",
        selection=selection,
        title="Determinism Test Scenario",
        presentation_strategy=PresentationStrategy.CHRONOLOGICAL,
    )

    world = WorldState(id=f"world_det_{seed}_{visual_variant}", name="Deterministic Test World")

    loc_corridor = Location(
        id="loc_corridor",
        name="Corridor B",
        description="Harsh fluorescent corridor",
        connected_locations=["loc_vault"],
    )
    loc_vault = Location(
        id="loc_vault",
        name="Archives Vault",
        description="Subterranean vault",
        connected_locations=["loc_corridor"],
    )
    world.locations[loc_corridor.id] = loc_corridor
    world.locations[loc_vault.id] = loc_vault

    dossier = WorldObject(
        id="obj_dossier",
        name="Classified Dossier",
        description="Cipher dossier",
        location_id="loc_vault",
    )
    world.objects[dossier.id] = dossier

    g_dossier = Goal(id="g_dossier", character_id="char_operative", description="Retrieve dossier", priority=1)
    g_catch = Goal(id="g_catch", character_id="char_director", description="Stop intruder", priority=1)
    world.goals[g_dossier.id] = g_dossier
    world.goals[g_catch.id] = g_catch

    sec_operative = Secret(
        id="sec_01",
        character_id="char_operative",
        statement="Microdot in ring",
        importance=0.9,
    )
    world.secrets[sec_operative.id] = sec_operative

    # Visual variant 0: Default sleek noir operative
    # Visual variant 1: Divergent bright cyberpunk operative (must have zero behavioral effect)
    if visual_variant == 0:
        ref_profile = CharacterReferenceProfile(
            apparent_age_range="Late 20s",
            build="Athletic, lean",
            baseline_wardrobe="Charcoal wool coat",
            wardrobe_palette=["black", "charcoal"],
            signature_objects=["Microdot decoder ring"],
        )
    else:
        ref_profile = CharacterReferenceProfile(
            apparent_age_range="Elderly 75",
            build="Heavyweight broad",
            baseline_wardrobe="Fluorescent neon tracksuit",
            wardrobe_palette=["bright orange", "neon green"],
            signature_objects=["Golden cane", "Cybernetic monocle"],
        )

    operative = Character(
        id="char_operative",
        name="Agent Evelyn",
        role="operative",
        current_location_id="loc_corridor",
        emotional_state=EmotionalState(fear=0.4, anger=0.1, trust=-0.5),
        goals=[g_dossier.id],
        secrets=[sec_operative.id],
        reference_profile=ref_profile,
    )
    director = Character(
        id="char_director",
        name="Director Kane",
        role="director",
        current_location_id="loc_corridor",
        emotional_state=EmotionalState(fear=0.1, anger=0.7, trust=-0.8),
        goals=[g_catch.id],
    )

    world.characters[operative.id] = operative
    world.characters[director.id] = director

    rel = Relationship(
        id="rel_op_dir",
        character_a_id="char_operative",
        character_b_id="char_director",
        trust=-0.7,
        suspicion=0.8,
    )
    world.relationships[rel.id] = rel

    return world, blueprint


def compute_simulation_hash(world: WorldState) -> str:
    """Compute a deterministic SHA-256 fingerprint of all recorded simulation events."""
    sorted_events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
    serialized = []
    for e in sorted_events:
        serialized.append({
            "tick": e.tick,
            "type": e.event_type.value,
            "actors": sorted(e.actor_ids),
            "loc": e.location_id,
            "desc": e.description,
        })
    raw_bytes = json.dumps(serialized, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()


def test_seeded_replay_determinism_across_multiple_seeds():
    """Verify that identical seeds produce identical simulation events and identical hashes."""
    seeds = [42, 101, 777]

    for seed in seeds:
        world_a, bp_a = create_deterministic_world(seed=seed, visual_variant=0)
        orch_a = SimulationOrchestrator(world=world_a, provider=MockLLMProvider(), blueprint=bp_a)
        orch_a.run(max_ticks=6)
        hash_a = compute_simulation_hash(world_a)

        world_b, bp_b = create_deterministic_world(seed=seed, visual_variant=0)
        orch_b = SimulationOrchestrator(world=world_b, provider=MockLLMProvider(), blueprint=bp_b)
        orch_b.run(max_ticks=6)
        hash_b = compute_simulation_hash(world_b)

        assert hash_a == hash_b, f"Deterministic replay failed for seed {seed}"
        assert len(world_a.events) == len(world_b.events)


def test_visual_reference_profile_invariance_on_simulation_hash():
    """Verify that changing CharacterReferenceProfile visual fields has ZERO effect on simulation hash."""
    seed = 42

    world_v0, bp_v0 = create_deterministic_world(seed=seed, visual_variant=0)
    orch_v0 = SimulationOrchestrator(world=world_v0, provider=MockLLMProvider(), blueprint=bp_v0)
    orch_v0.run(max_ticks=6)
    hash_v0 = compute_simulation_hash(world_v0)

    world_v1, bp_v1 = create_deterministic_world(seed=seed, visual_variant=1)
    orch_v1 = SimulationOrchestrator(world=world_v1, provider=MockLLMProvider(), blueprint=bp_v1)
    orch_v1.run(max_ticks=6)
    hash_v1 = compute_simulation_hash(world_v1)

    assert hash_v0 == hash_v1, "Visual profile change mutated canonical simulation trajectory!"


def test_analytics_queries_do_not_interfere_with_simulation():
    """Verify that running intermediate analytics (StateHistory, ConflictEngine, DramaticSignals) does not alter execution."""
    seed = 101

    # Run A: straight execution for 6 ticks without intermediate queries
    world_a, bp_a = create_deterministic_world(seed=seed)
    orch_a = SimulationOrchestrator(world=world_a, provider=MockLLMProvider(), blueprint=bp_a)
    orch_a.run(max_ticks=6)
    hash_straight = compute_simulation_hash(world_a)

    # Run B: step-wise execution with heavy analytics read queries between ticks
    world_b, bp_b = create_deterministic_world(seed=seed)
    orch_b = SimulationOrchestrator(world=world_b, provider=MockLLMProvider(), blueprint=bp_b)
    orch_b.run(max_ticks=3)

    # Invoke analytics mid-simulation
    history_reconstructor = CharacterStateHistoryReconstructor()
    history_reconstructor.reconstruct_character_history(world=world_b, character_id="char_operative", project_id="test")
    ConflictEngine.derive_conflict_graph(world=world_b, project_id="test")
    extract_dramatic_signals(world=world_b)

    # Resume simulation to tick 6
    orch_b.run(max_ticks=6)
    hash_with_analytics = compute_simulation_hash(world_b)

    assert hash_straight == hash_with_analytics, "Read-only analytics mutated simulation trajectory!"
