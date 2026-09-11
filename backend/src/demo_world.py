"""Factory for creating demonstration world"""
from .domain import (
    WorldState,
    Location,
    Character,
    EmotionalState,
    WorldObject,
    Goal,
    GoalStatus,
    Belief,
    Secret,
    Relationship,
)


def create_demo_world() -> WorldState:
    """Create a demonstration world with Hotel Room 307 scenario"""

    world = WorldState(
        id="world_hotel_intrigue",
        name="Hotel Intrigue",
        description="A story of secrets and deception in a luxury hotel",
        current_tick=0,
    )

    # Create Location: Hotel Room 307
    room_307 = Location(
        id="loc_room307",
        name="Hotel Room 307",
        description="A modest hotel room on the third floor with a queen bed, desk, and bathroom",
        connected_locations=["loc_hallway"],
        capacity=5,
    )
    world.locations["loc_room307"] = room_307

    hallway = Location(
        id="loc_hallway",
        name="Third Floor Hallway",
        description="A long corridor with numbered doors and carpet",
        connected_locations=["loc_room307"],
        capacity=10,
    )
    world.locations["loc_hallway"] = hallway

    # Create Character: Arjun
    arjun = Character(
        id="char_arjun",
        name="Arjun",
        role="Corporate Investigator",
        description="A determined investigator searching for truth",
        personality_traits={
            "ambitious": 0.8,
            "loyal": 0.7,
            "cautious": 0.6,
            "analytical": 0.85,
        },
        emotional_state=EmotionalState(
            happiness=0.2, fear=0.6, anger=0.3, trust=0.4, curiosity=0.9
        ),
        current_location_id="loc_room307",
    )
    world.characters["char_arjun"] = arjun

    # Create Character: Maya
    maya = Character(
        id="char_maya",
        name="Maya",
        role="Corporate Attorney",
        description="A shrewd attorney protecting secrets",
        personality_traits={
            "ambitious": 0.9,
            "loyal": 0.5,
            "cautious": 0.8,
            "deceptive": 0.7,
        },
        emotional_state=EmotionalState(
            happiness=0.3, fear=0.7, anger=0.5, trust=0.2, curiosity=0.6
        ),
        current_location_id="loc_room307",
    )
    world.characters["char_maya"] = maya

    # Create Objects
    documents = WorldObject(
        id="obj_documents",
        name="Documents",
        description="Confidential project files and correspondence",
        location_id="loc_room307",
        portable=True,
        properties={"sensitive": "true", "value": "critical"},
    )
    world.objects["obj_documents"] = documents

    phone = WorldObject(
        id="obj_phone",
        name="Phone",
        description="A smartphone with encrypted messaging apps",
        location_id="loc_room307",
        portable=True,
        properties={"has_calls": "true", "has_messages": "true"},
    )
    world.objects["obj_phone"] = phone

    suitcase = WorldObject(
        id="obj_suitcase",
        name="Suitcase",
        description="A leather suitcase with hotel key cards",
        location_id="loc_room307",
        portable=True,
        properties={"locked": "true"},
    )
    world.objects["obj_suitcase"] = suitcase

    door = WorldObject(
        id="obj_door",
        name="Door",
        description="The room's main entrance door",
        location_id="loc_room307",
        portable=False,
        properties={"locked": "false", "material": "wood"},
    )
    world.objects["obj_door"] = door

    # Create Goals
    arjun_goal = Goal(
        id="goal_arjun_001",
        character_id="char_arjun",
        description="Recover and verify the confidential documents",
        priority=0.95,
        status=GoalStatus.ACTIVE,
        reason="Evidence needed to expose corporate fraud",
    )
    world.goals[arjun_goal.id] = arjun_goal
    world.characters["char_arjun"].goals.append(arjun_goal.id)

    maya_goal = Goal(
        id="goal_maya_001",
        character_id="char_maya",
        description="Protect the documents from investigation",
        priority=0.9,
        status=GoalStatus.ACTIVE,
        reason="Documents implicate her in fraudulent activities",
    )
    world.goals[maya_goal.id] = maya_goal
    world.characters["char_maya"].goals.append(maya_goal.id)

    # Create Beliefs
    arjun_belief = Belief(
        id="bel_arjun_001",
        character_id="char_arjun",
        statement="Maya has important documents that prove corporate fraud",
        confidence=0.85,
        source="investigation",
    )
    world.beliefs[arjun_belief.id] = arjun_belief
    world.characters["char_arjun"].beliefs.append(arjun_belief.id)

    maya_belief = Belief(
        id="bel_maya_001",
        character_id="char_maya",
        statement="Arjun is trying to expose our company's secrets",
        confidence=0.9,
        source="inference",
    )
    world.beliefs[maya_belief.id] = maya_belief
    world.characters["char_maya"].beliefs.append(maya_belief.id)

    # Create Secrets
    maya_secret = Secret(
        id="sec_maya_001",
        character_id="char_maya",
        statement="The documents contain evidence of corporate fraud that implicates the CEO",
        known_by=[],
        importance=1.0,
    )
    world.secrets[maya_secret.id] = maya_secret
    world.characters["char_maya"].secrets.append(maya_secret.id)

    # Create Relationship
    relationship = Relationship(
        id="rel_001",
        character_a_id="char_arjun",
        character_b_id="char_maya",
        affinity=0.3,
        trust=0.2,
        history="Colleagues at a consulting firm, now on opposing sides of an investigation",
    )
    world.relationships[relationship.id] = relationship
    arjun.relationships.append(relationship.id)
    maya.relationships.append(relationship.id)

    return world
