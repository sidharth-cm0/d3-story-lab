"""Spatial reasoning engine for deriving deterministic tactical and geometric scene context.

Derives spatial context from canonical WorldState without mutating it:
- LocationGeometry: zones, entrances, exits, obstacles, cover, visibility links, elevations
- ActorSpatialState: zone, nearest exit, line of sight, cover, visible objects, room control
- Computes:
  - sightlines and blind spots
  - distance bands
  - positional advantage
  - room control
  - tactical tension facts (e.g., hidden observer, exit cutoff, prop sightline)
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any, Set
from pydantic import BaseModel, ConfigDict, Field

from src.domain.world import WorldState, Location
from src.domain.character import Character


class DistanceBand(str, Enum):
    """Cinematic distance categories between actors."""
    INTIMATE = "intimate"    # Within arm's reach (whisper, grapple)
    CLOSE = "close"          # 1-3 meters (conversational, confrontation)
    MEDIUM = "medium"        # Across the room (4-8 meters, shouted)
    FAR = "far"              # Across large depot/gallery (> 10 meters)


class CoverState(str, Enum):
    """Cover / concealment posture."""
    EXPOSED = "exposed"
    PARTIAL = "partial"
    FULL = "full"


class PositionalAdvantage(str, Enum):
    """Tactical dominance classification."""
    HIGH_GROUND = "high_ground"
    CONTROLS_EXIT = "controls_exit"
    COVER_ADVANTAGE = "cover_advantage"
    SURROUNDING = "surrounding"
    NONE = "none"


class LocationGeometry(BaseModel):
    """Lightweight scene geometry representation for a simulation location."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    location_id: str
    name: str
    zones: List[str] = Field(default_factory=list)
    entrances: List[str] = Field(default_factory=list)
    exits: List[str] = Field(default_factory=list)
    obstacles: List[str] = Field(default_factory=list)
    cover_points: Dict[str, str] = Field(default_factory=dict)
    visibility_links: Dict[str, List[str]] = Field(default_factory=dict)
    adjacency: Dict[str, List[str]] = Field(default_factory=dict)
    elevation: Dict[str, float] = Field(default_factory=dict)
    focal_objects: List[str] = Field(default_factory=list)
    blocked_exits: List[str] = Field(default_factory=list)


class ActorSpatialState(BaseModel):
    """Spatial context of a single actor inside a location."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    actor_id: str
    location_id: str
    zone: str
    nearest_exit: Optional[str] = None
    line_of_sight_targets: List[str] = Field(default_factory=list)
    blind_spots: List[str] = Field(default_factory=list)
    cover_state: CoverState = CoverState.EXPOSED
    blocked_paths: List[str] = Field(default_factory=list)
    visible_objects: List[str] = Field(default_factory=list)
    audible_actors: List[str] = Field(default_factory=list)
    positional_advantage: PositionalAdvantage = PositionalAdvantage.NONE
    controls_exit: Optional[str] = None


class SpatialContext(BaseModel):
    """Complete computed spatial and tactical context for a scene."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    location_id: str
    geometry: LocationGeometry
    actor_states: Dict[str, ActorSpatialState] = Field(default_factory=dict)
    room_controller_id: Optional[str] = None
    sightlines: Dict[str, List[str]] = Field(default_factory=dict)
    mutual_sightlines: List[Tuple[str, str]] = Field(default_factory=list)
    distance_matrix: Dict[str, Dict[str, DistanceBand]] = Field(default_factory=dict)
    spatial_tensions: List[str] = Field(default_factory=list)
    narrative_spatial_notes: List[str] = Field(default_factory=list)


class SpatialReasoner:
    """Derives deterministic spatial geometry, sightlines, and tension from WorldState."""

    def __init__(self) -> None:
        self._geometry_cache: Dict[str, LocationGeometry] = {}

    def get_or_create_geometry(self, location_id: str, world: WorldState) -> LocationGeometry:
        """Derive or fetch deterministic scene geometry for a location."""
        if location_id in self._geometry_cache:
            return self._geometry_cache[location_id]

        loc = world.locations.get(location_id)
        name = loc.name if loc else location_id
        desc = (loc.description if loc else "").lower()

        # Deterministically parse or generate zones
        zones = ["main_floor", "entrance_threshold", "perimeter_shadows"]
        elevations = {"main_floor": 0.0, "entrance_threshold": 0.0, "perimeter_shadows": 0.0}
        cover_points = {}
        obstacles = []

        if "warehouse" in desc or "storage" in desc or "dock" in desc:
            zones = ["main_floor", "loading_bay", "catwalk", "alcove_office", "service_corridor"]
            elevations = {
                "main_floor": 0.0,
                "loading_bay": 0.0,
                "catwalk": 3.8,
                "alcove_office": 0.0,
                "service_corridor": 0.0,
            }
            obstacles = ["shipping_crates", "support_pillars", "conveyor_belt", "steel_cabinet"]
            cover_points = {
                "main_floor": "shipping_crates",
                "service_corridor": "support_pillars",
                "alcove_office": "steel_cabinet",
            }
        elif "suite" in desc or "hotel" in desc or "penthouse" in desc or "room" in desc:
            zones = ["foyer", "living_area", "balcony", "study_nook"]
            elevations = {"foyer": 0.0, "living_area": 0.0, "balcony": 0.0, "study_nook": 0.0}
            obstacles = ["mahogany_desk", "armchair", "bookshelf", "heavy_curtains"]
            cover_points = {
                "study_nook": "mahogany_desk",
                "living_area": "bookshelf",
            }
        elif "corridor" in desc or "hall" in desc or "tunnel" in desc:
            zones = ["north_end", "mid_hall", "south_end", "recessed_doorway"]
            elevations = {"north_end": 0.0, "mid_hall": 0.0, "south_end": 0.0, "recessed_doorway": 0.0}
            obstacles = ["utility_conduit", "door_frame", "fire_hose_cabinet"]
            cover_points = {"recessed_doorway": "door_frame"}

        # Exits from connected locations
        exits = []
        if loc and loc.connected_locations:
            for conn_id in loc.connected_locations:
                c_loc = world.locations.get(conn_id)
                c_name = c_loc.name if c_loc else conn_id
                exits.append(f"exit_to_{conn_id}")
        if not exits:
            exits = ["main_exit", "fire_door"]

        entrances = [f"entrance_{e}" for e in exits]

        # Adjacency and visibility links
        adjacency: Dict[str, List[str]] = {}
        visibility: Dict[str, List[str]] = {}

        for i, z in enumerate(zones):
            adj = []
            if i > 0:
                adj.append(zones[i - 1])
            if i < len(zones) - 1:
                adj.append(zones[i + 1])
            adjacency[z] = adj

            # High elevation can see everything; alcove/corridor only see adjacent
            if elevations.get(z, 0.0) > 2.0:
                visibility[z] = list(zones)
            elif "corridor" in z or "alcove" in z or "nook" in z:
                visibility[z] = list(adj) + [z]
            else:
                # Can see all non-elevated open zones
                visibility[z] = [other for other in zones if elevations.get(other, 0.0) <= 2.0]

        # Focal objects in this location
        focal_objs = [
            oid for oid, o in world.objects.items()
            if o.location_id == location_id
        ]

        blocked_exits: List[str] = []
        if "blocked" in desc or "locked" in desc or "barricade" in desc:
            blocked_exits.append(exits[-1])

        geometry = LocationGeometry(
            location_id=location_id,
            name=name,
            zones=zones,
            entrances=entrances,
            exits=exits,
            obstacles=obstacles,
            cover_points=cover_points,
            visibility_links=visibility,
            adjacency=adjacency,
            elevation=elevations,
            focal_objects=focal_objs,
            blocked_exits=blocked_exits,
        )
        self._geometry_cache[location_id] = geometry
        return geometry

    def compute_distance_band(self, zone_a: str, zone_b: str, geometry: LocationGeometry) -> DistanceBand:
        """Calculate cinematic distance band between two zones."""
        if zone_a == zone_b:
            return DistanceBand.CLOSE
        if zone_b in geometry.adjacency.get(zone_a, []):
            return DistanceBand.MEDIUM
        return DistanceBand.FAR

    def compute_spatial_context(
        self,
        location_id: str,
        world: WorldState,
        actor_zone_overrides: Optional[Dict[str, str]] = None,
        blocked_exit_overrides: Optional[List[str]] = None,
    ) -> SpatialContext:
        """Derive comprehensive spatial context and tactical tension for all actors in the location."""
        geometry = self.get_or_create_geometry(location_id, world)
        if blocked_exit_overrides:
            # Create a copy of geometry with updated blocked exits
            geometry = LocationGeometry(
                location_id=geometry.location_id,
                name=geometry.name,
                zones=geometry.zones,
                entrances=geometry.entrances,
                exits=geometry.exits,
                obstacles=geometry.obstacles,
                cover_points=geometry.cover_points,
                visibility_links=geometry.visibility_links,
                adjacency=geometry.adjacency,
                elevation=geometry.elevation,
                focal_objects=geometry.focal_objects,
                blocked_exits=list(set(geometry.blocked_exits + blocked_exit_overrides)),
            )

        # Identify actors in this location
        actors_here = [
            c for c in world.characters.values()
            if (getattr(c, "current_location_id", None) or getattr(c, "location_id", None)) == location_id
        ]

        zone_overrides = actor_zone_overrides or {}
        actor_states: Dict[str, ActorSpatialState] = {}

        # Default zone assignment based on role or index
        zones = geometry.zones
        for idx, actor in enumerate(actors_here):
            if actor.id in zone_overrides:
                z = zone_overrides[actor.id]
            else:
                role_lower = actor.role.lower()
                if "undercover" in role_lower or "detective" in role_lower or "infiltrat" in role_lower:
                    z = zones[min(1, len(zones) - 1)]
                elif "guard" in role_lower or "boss" in role_lower:
                    z = zones[0]  # Controls entrance / main
                else:
                    z = zones[idx % len(zones)]

            cover = CoverState.EXPOSED
            if z in geometry.cover_points:
                cover = CoverState.PARTIAL if "infiltrat" not in actor.role.lower() else CoverState.FULL

            advantage = PositionalAdvantage.NONE
            if geometry.elevation.get(z, 0.0) > 2.0:
                advantage = PositionalAdvantage.HIGH_GROUND
            elif z == zones[0] and ("guard" in actor.role.lower() or "boss" in actor.role.lower()):
                advantage = PositionalAdvantage.CONTROLS_EXIT
            elif cover in (CoverState.PARTIAL, CoverState.FULL):
                advantage = PositionalAdvantage.COVER_ADVANTAGE

            # Nearest exit
            nearest_exit = geometry.exits[0] if geometry.exits else None
            controlled_exit = geometry.exits[0] if advantage == PositionalAdvantage.CONTROLS_EXIT else None

            # Visible objects from this zone
            vis_objs = []
            for oid in geometry.focal_objects:
                # Objects on main floor or in same zone are visible
                vis_objs.append(oid)

            actor_states[actor.id] = ActorSpatialState(
                actor_id=actor.id,
                location_id=location_id,
                zone=z,
                nearest_exit=nearest_exit,
                cover_state=cover,
                blocked_paths=list(geometry.blocked_exits),
                visible_objects=vis_objs,
                positional_advantage=advantage,
                controls_exit=controlled_exit,
            )

        # Compute Sightlines, Blind Spots, Distances, and Audibility
        sightlines: Dict[str, List[str]] = {}
        mutual_sightlines: List[Tuple[str, str]] = []
        distance_matrix: Dict[str, Dict[str, DistanceBand]] = {}
        spatial_tensions: List[str] = []
        narrative_notes: List[str] = []

        for a1 in actors_here:
            s1 = actor_states[a1.id]
            visible_zones = geometry.visibility_links.get(s1.zone, [s1.zone])
            seen = []
            blind = []
            audible = []
            distance_matrix[a1.id] = {}

            for a2 in actors_here:
                if a1.id == a2.id:
                    continue
                s2 = actor_states[a2.id]
                dist = self.compute_distance_band(s1.zone, s2.zone, geometry)
                distance_matrix[a1.id][a2.id] = dist

                # Check if s2 is in a visible zone
                if s2.zone in visible_zones and s2.cover_state != CoverState.FULL:
                    seen.append(a2.id)
                else:
                    blind.append(a2.id)

                # Audible if close or medium
                if dist in (DistanceBand.CLOSE, DistanceBand.MEDIUM):
                    audible.append(a2.id)

            sightlines[a1.id] = seen

            # Update actor state with computed targets
            actor_states[a1.id] = ActorSpatialState(
                actor_id=s1.actor_id,
                location_id=s1.location_id,
                zone=s1.zone,
                nearest_exit=s1.nearest_exit,
                line_of_sight_targets=seen,
                blind_spots=blind,
                cover_state=s1.cover_state,
                blocked_paths=s1.blocked_paths,
                visible_objects=s1.visible_objects,
                audible_actors=audible,
                positional_advantage=s1.positional_advantage,
                controls_exit=s1.controls_exit,
            )

        # Compute mutual sightlines & asymmetric tactical tensions
        room_controller = None
        for a1 in actors_here:
            s1 = actor_states[a1.id]
            if s1.controls_exit:
                room_controller = a1.id
                spatial_tensions.append(f"{a1.name} controls {s1.controls_exit}.")
                narrative_notes.append(f"{a1.name} holds the clear exit line.")

            for a2 in actors_here:
                if a1.id >= a2.id:
                    continue
                a1_sees_a2 = a2.id in sightlines.get(a1.id, [])
                a2_sees_a1 = a1.id in sightlines.get(a2.id, [])

                if a1_sees_a2 and a2_sees_a1:
                    mutual_sightlines.append((a1.id, a2.id))
                elif a1_sees_a2 and not a2_sees_a1:
                    tension_str = f"{a1.name} has sightline on {a2.name}, but {a2.name} cannot see {a1.name}."
                    spatial_tensions.append(tension_str)
                    narrative_notes.append(f"{a1.name} watches from the shadows of {s1.zone}; {a2.name} has no line of sight.")
                elif a2_sees_a1 and not a1_sees_a2:
                    tension_str = f"{a2.name} has sightline on {a1.name}, but {a1.name} cannot see {a2.name}."
                    spatial_tensions.append(tension_str)
                    narrative_notes.append(f"{a2.name} maintains hidden observation over {a1.name}.")

        if geometry.blocked_exits:
            for b in geometry.blocked_exits:
                spatial_tensions.append(f"{b} is impassable.")
                narrative_notes.append(f"The route through {b.replace('exit_to_', '')} remains obstructed.")

        return SpatialContext(
            location_id=location_id,
            geometry=geometry,
            actor_states=actor_states,
            room_controller_id=room_controller,
            sightlines=sightlines,
            mutual_sightlines=mutual_sightlines,
            distance_matrix=distance_matrix,
            spatial_tensions=spatial_tensions,
            narrative_spatial_notes=narrative_notes,
        )
