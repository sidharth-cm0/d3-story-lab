"""Versioned Evaluation Corpus for Narrative Intelligence & Baseline Evaluation (Phase 3).

Provides deterministic, reproducible test scenarios with:
1. Initial world state (locations, characters, objects, propositions, secrets, relationships).
2. Character goals and knowledge boundaries (what each actor can and cannot know).
3. Expected state transitions and event milestones.
4. Expected dramatic signals and pattern IDs.
5. Known no-answer questions (questions where RAG/Advisor must acknowledge lack of evidence).
6. Expected intervention outcomes (e.g., quiet period block, cooldown block, valid execution).
7. Expected temporal graph states at selected ticks.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Callable
from pydantic import BaseModel, ConfigDict, Field

from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.secret import Secret
from src.domain.goal import Goal, GoalStatus
from src.domain.belief import Belief
from src.domain.relationship import Relationship
from src.domain.proposition import Proposition


class VersionedScenario(BaseModel):
    """Specification of a versioned evaluation scenario."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    scenario_id: str
    version: str
    title: str
    description: str

    character_ids: List[str]
    location_ids: List[str]
    object_ids: List[str]

    character_knowledge_boundaries: Dict[str, List[str]] = Field(
        ..., description="Map of char_id -> secrets/facts they are strictly NOT allowed to know initially"
    )
    character_initial_goals: Dict[str, List[str]] = Field(
        ..., description="Map of char_id -> initial active goal descriptions"
    )

    known_no_answer_queries: List[str] = Field(
        ..., description="Queries where grounded system must return INSUFFICIENT_EVIDENCE or explicit no-answer"
    )
    relevant_pattern_ids: List[str] = Field(
        ..., description="Narrative Genome pattern IDs expected to match"
    )
    expected_dramatic_signals: List[str] = Field(
        ..., description="Expected dramatic tension and conflict signals"
    )
    expected_intervention_outcomes: Dict[str, str] = Field(
        ..., description="Map of condition -> expected recommendation lifecycle status"
    )
    expected_graph_ticks: List[int] = Field(
        ..., description="Ticks at which temporal character graph should be evaluated"
    )


def create_missing_dossier_world() -> WorldState:
    """Build the canonical initial WorldState for 'The Missing Dossier' scenario."""
    loc_vault = Location(id="loc_vault", name="Archives Vault", description="High-security subterranean vault")
    loc_hallway = Location(id="loc_hallway", name="Vault Hallway", description="Dimly lit corridor outside vault")
    loc_office = Location(id="loc_office", name="Director Office", description="Command station with CCTV monitors")

    # Connect locations
    loc_vault.connected_locations = ["loc_hallway"]
    loc_hallway.connected_locations = ["loc_vault", "loc_office"]
    loc_office.connected_locations = ["loc_hallway"]

    obj_safe = WorldObject(
        id="obj_safe",
        name="Titanium Safe",
        location_id="loc_vault",
        description="A locked titanium vault safe containing classified documents",
        is_container=True,
    )
    obj_dossier = WorldObject(
        id="obj_dossier",
        name="Missing Dossier",
        location_id="loc_vault",
        description="Folder of classified espionage documents",
    )

    goal_cross = Goal(
        id="goal_cross_extract",
        character_id="char_cross",
        description="Infiltrate the vault and secure the missing dossier",
        status=GoalStatus.ACTIVE,
    )
    goal_vane = Goal(
        id="goal_vane_patrol",
        character_id="char_vane",
        description="Monitor the archives and intercept intruders",
        status=GoalStatus.ACTIVE,
    )

    char_cross = Character(
        id="char_cross",
        name="Evelyn Cross",
        role="Undercover Infiltrator",
        current_location_id="loc_hallway",
        goals=["goal_cross_extract"],
        known_facts={"fact_vault_layout", "fact_alarm_cycle"},
    )
    char_vane = Character(
        id="char_vane",
        name="Vincent Vane",
        role="Security Director",
        current_location_id="loc_office",
        goals=["goal_vane_patrol"],
        secrets=["sec_dossier_content"],
        known_facts={"fact_safe_passcode", "fact_guard_schedule"},
    )

    secret_dossier = Secret(
        id="sec_dossier_content",
        character_id="char_vane",
        statement="The dossier proves the agency director is funding the syndicate",
        known_by=["char_vane"],
        importance=0.9,
    )

    prop_locked = Proposition(
        id="prop_safe_locked",
        subject="obj_safe",
        predicate="locked",
        object="true",
        truth_value=True,
        enforced=True,
    )

    rel_rivalry = Relationship(
        id="rel_cross_vane",
        character_a_id="char_cross",
        character_b_id="char_vane",
        affinity=-0.4,
        trust=-0.6,
    )

    return WorldState(
        id="world_missing_dossier_v1",
        name="The Missing Dossier",
        current_tick=0,
        locations={"loc_vault": loc_vault, "loc_hallway": loc_hallway, "loc_office": loc_office},
        objects={"obj_safe": obj_safe, "obj_dossier": obj_dossier},
        characters={"char_cross": char_cross, "char_vane": char_vane},
        goals={"goal_cross_extract": goal_cross, "goal_vane_patrol": goal_vane},
        secrets={"sec_dossier_content": secret_dossier},
        propositions={"prop_safe_locked": prop_locked},
        relationships={"rel_cross_vane": rel_rivalry},
    )


SCENARIO_MISSING_DOSSIER_V1 = VersionedScenario(
    scenario_id="scenario_missing_dossier_v1",
    version="1.0.0",
    title="The Missing Dossier",
    description="Undercover operative Evelyn Cross attempts to extract classified dossier while evading Director Vane.",
    character_ids=["char_cross", "char_vane"],
    location_ids=["loc_vault", "loc_hallway", "loc_office"],
    object_ids=["obj_safe", "obj_dossier"],
    character_knowledge_boundaries={
        "char_cross": ["sec_dossier_content", "fact_safe_passcode"],
        "char_vane": ["fact_alarm_cycle"],
    },
    character_initial_goals={
        "char_cross": ["Infiltrate the vault and secure the missing dossier"],
        "char_vane": ["Monitor the archives and intercept intruders"],
    },
    known_no_answer_queries=[
        "Did Evelyn Cross open the safe before arriving at the archives?",
        "What is the name of Marcus Reyes's handler in Moscow?",
        "How many times did Vincent Vane defect to the syndicate in 1998?",
    ],
    relevant_pattern_ids=["NG-001", "NG-003", "NG-008"],
    expected_dramatic_signals=["information_asymmetry", "impending_confrontation", "ticking_clock"],
    expected_intervention_outcomes={
        "tick_0_attempt": "BLOCKED_QUIET_PERIOD",
        "consecutive_attempt": "BLOCKED_COOLDOWN",
        "valid_environmental_attempt": "EXECUTED",
    },
    expected_graph_ticks=[0, 2, 5],
)


def create_hotel_intrigue_world() -> WorldState:
    """Build the canonical initial WorldState for 'Hotel Intrigue' scenario."""
    loc_suite = Location(id="loc_suite", name="Suite 307", description="Luxury suite with balcony")
    loc_corridor = Location(id="loc_corridor", name="3rd Floor Corridor", description="Carpeted hotel hallway")

    loc_suite.connected_locations = ["loc_corridor"]
    loc_corridor.connected_locations = ["loc_suite"]

    obj_phone = WorldObject(
        id="obj_burner_phone",
        name="Burner Phone",
        location_id="loc_suite",
        description="Encrypted cellular device on desk",
    )

    goal_maya = Goal(
        id="goal_maya_contact",
        character_id="char_maya",
        description="Wait for encrypted offshore confirmation call",
        status=GoalStatus.ACTIVE,
    )
    goal_arjun = Goal(
        id="goal_arjun_wiretap",
        character_id="char_arjun",
        description="Record Maya Lin's conversation",
        status=GoalStatus.ACTIVE,
    )

    char_maya = Character(
        id="char_maya",
        name="Maya Lin",
        role="Corporate Executive",
        current_location_id="loc_suite",
        goals=["goal_maya_contact"],
        secrets=["sec_hostile_takeover"],
        known_facts={"fact_offshore_account"},
    )
    char_arjun = Character(
        id="char_arjun",
        name="Arjun Patel",
        role="Private Investigator",
        current_location_id="loc_corridor",
        goals=["goal_arjun_wiretap"],
        known_facts={"fact_room_number"},
    )

    sec_deal = Secret(
        id="sec_hostile_takeover",
        character_id="char_maya",
        statement="Maya Lin is orchestrating the hostile acquisition of her brother's firm",
        known_by=["char_maya"],
        importance=0.8,
    )

    rel_suspect = Relationship(
        id="rel_maya_arjun",
        character_a_id="char_arjun",
        character_b_id="char_maya",
        affinity=0.0,
        trust=-0.5,
    )

    return WorldState(
        id="world_hotel_intrigue_v1",
        name="Hotel Intrigue",
        current_tick=0,
        locations={"loc_suite": loc_suite, "loc_corridor": loc_corridor},
        objects={"obj_burner_phone": obj_phone},
        characters={"char_maya": char_maya, "char_arjun": char_arjun},
        goals={"goal_maya_contact": goal_maya, "goal_arjun_wiretap": goal_arjun},
        secrets={"sec_hostile_takeover": sec_deal},
        relationships={"rel_maya_arjun": rel_suspect},
    )


SCENARIO_HOTEL_INTRIGUE_V1 = VersionedScenario(
    scenario_id="scenario_hotel_intrigue_v1",
    version="1.0.0",
    title="Hotel Intrigue",
    description="Corporate investigator Arjun Patel monitors executive Maya Lin outside her suite.",
    character_ids=["char_maya", "char_arjun"],
    location_ids=["loc_suite", "loc_corridor"],
    object_ids=["obj_burner_phone"],
    character_knowledge_boundaries={
        "char_arjun": ["sec_hostile_takeover", "fact_offshore_account"],
        "char_maya": ["fact_room_number"],
    },
    character_initial_goals={
        "char_maya": ["Wait for encrypted offshore confirmation call"],
        "char_arjun": ["Record Maya Lin's conversation"],
    },
    known_no_answer_queries=[
        "What did Maya Lin order for dinner at room service?",
        "Who assassinated Arjun Patel's former partner?",
    ],
    relevant_pattern_ids=["NG-002", "NG-005"],
    expected_dramatic_signals=["eavesdropping_tension", "suspicion", "distance_barrier"],
    expected_intervention_outcomes={
        "tick_0_attempt": "BLOCKED_QUIET_PERIOD",
        "door_knock_attempt": "EXECUTED",
    },
    expected_graph_ticks=[0, 3],
)


EVALUATION_CORPUS: Dict[str, VersionedScenario] = {
    SCENARIO_MISSING_DOSSIER_V1.scenario_id: SCENARIO_MISSING_DOSSIER_V1,
    SCENARIO_HOTEL_INTRIGUE_V1.scenario_id: SCENARIO_HOTEL_INTRIGUE_V1,
}

EVALUATION_WORLD_FACTORIES: Dict[str, Callable[[], WorldState]] = {
    SCENARIO_MISSING_DOSSIER_V1.scenario_id: create_missing_dossier_world,
    SCENARIO_HOTEL_INTRIGUE_V1.scenario_id: create_hotel_intrigue_world,
}
