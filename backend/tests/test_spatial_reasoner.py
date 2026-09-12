"""Tests for SpatialReasoner and LocationGeometry (Phase 2)."""

import pytest
from src.domain.world import WorldState, Location
from src.domain.character import Character, EmotionalState
from src.narrative.spatial import (
    SpatialReasoner,
    CoverState,
    PositionalAdvantage,
    DistanceBand,
)


@pytest.fixture
def warehouse_world():
    world = WorldState(
        id="w_spatial",
        name="Waterfront Depot",
        description="A dark waterfront warehouse with steel catwalks and service corridors",
    )
    loc = Location(
        id="loc_depot",
        name="Main Warehouse Floor",
        description="A cavernous storage depot with shipping crates and blocked south exit",
        connected_locations=["loc_dock", "loc_office"],
    )
    world.locations[loc.id] = loc

    evelyn = Character(
        id="char_evelyn",
        name="Evelyn",
        role="Undercover Infiltrator",
        current_location_id=loc.id,
    )
    vincent = Character(
        id="char_vincent",
        name="Vincent",
        role="Guard Commander",
        current_location_id=loc.id,
    )
    world.characters[evelyn.id] = evelyn
    world.characters[vincent.id] = vincent
    return world


def test_spatial_reasoner_geometry_generation(warehouse_world):
    reasoner = SpatialReasoner()
    geom = reasoner.get_or_create_geometry("loc_depot", warehouse_world)

    assert "main_floor" in geom.zones
    assert "catwalk" in geom.zones
    assert geom.elevation["catwalk"] > 2.0
    assert len(geom.obstacles) >= 2
    assert len(geom.exits) >= 2


def test_spatial_context_sightlines_and_cover(warehouse_world):
    reasoner = SpatialReasoner()
    # Staging: Evelyn hidden in alcove/corridor in cover, Vincent on main floor
    ctx = reasoner.compute_spatial_context(
        location_id="loc_depot",
        world=warehouse_world,
        actor_zone_overrides={
            "char_evelyn": "service_corridor",
            "char_vincent": "main_floor",
        },
    )

    ev_state = ctx.actor_states["char_evelyn"]
    assert ev_state.cover_state in (CoverState.PARTIAL, CoverState.FULL)
    assert ctx.distance_matrix["char_evelyn"]["char_vincent"] in (DistanceBand.MEDIUM, DistanceBand.FAR)


def test_spatial_room_control_and_exit_blocking(warehouse_world):
    reasoner = SpatialReasoner()
    ctx = reasoner.compute_spatial_context(
        location_id="loc_depot",
        world=warehouse_world,
        actor_zone_overrides={
            "char_vincent": "main_floor",
            "char_evelyn": "catwalk",
        },
        blocked_exit_overrides=["exit_to_dock"],
    )

    vincent_state = ctx.actor_states["char_vincent"]
    assert vincent_state.positional_advantage == PositionalAdvantage.CONTROLS_EXIT
    assert vincent_state.controls_exit is not None
    assert "exit_to_dock is impassable." in ctx.spatial_tensions


def test_tactical_tension_asymmetric_visibility(warehouse_world):
    reasoner = SpatialReasoner()
    # Catwalk elevation allows seeing service_corridor, but service_corridor cannot see elevated catwalk
    ctx = reasoner.compute_spatial_context(
        location_id="loc_depot",
        world=warehouse_world,
        actor_zone_overrides={
            "char_evelyn": "catwalk",
            "char_vincent": "service_corridor",
        },
    )

    # Evelyn on catwalk has high ground and sightline on Vincent
    assert "char_vincent" in ctx.sightlines["char_evelyn"]
    assert any("has sightline on Vincent" in t for t in ctx.spatial_tensions)
