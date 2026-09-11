"""World Initializer service transforming unstructured seeds into validated WorldState"""
import uuid
from typing import Optional, List
from ..domain import (
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
from ..providers import LLMProvider, MockLLMProvider
from .schemas import (
    FactType,
    TaggedFact,
    CharacterPlan,
    LocationPlan,
    ObjectPlan,
    RelationshipPlan,
    WorldInitializationPlan,
)


class WorldInitializerService:
    """Transforms raw text seeds into structured WorldInitializationPlans and canonical WorldStates"""

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or MockLLMProvider()

    def generate_plan(self, seed_text: str) -> WorldInitializationPlan:
        """Generate a WorldInitializationPlan from raw seed text"""
        prompt = (
            f"Analyze the following narrative seed and generate a complete structured world initialization plan.\n"
            f"Explicitly distinguish facts as SOURCE_FACT, DERIVED_PREMISE, or SIMULATION_INVENTION.\n\n"
            f"SEED TEXT:\n{seed_text}"
        )
        system_prompt = (
            "You are the world initialization architect for D3 Story Lab. Create rich, consistent sandbox simulation "
            "plans with distinct character secrets, goals, beliefs, and locations."
        )

        # If using MockLLMProvider without custom registration, build a high quality deterministic plan
        if isinstance(self.provider, MockLLMProvider) and WorldInitializationPlan not in self.provider._structured_handlers:
            return self._build_deterministic_mock_plan(seed_text)

        return self.provider.generate_structured(
            WorldInitializationPlan, prompt, system_prompt=system_prompt
        )

    def instantiate_world(self, plan: WorldInitializationPlan) -> WorldState:
        """Convert a WorldInitializationPlan into a canonically validated WorldState"""
        world = WorldState(
            id=plan.world_id,
            name=plan.world_name,
            description=f"{plan.initial_situation} (Genre: {plan.genre}, Tone: {plan.tone})",
            current_tick=0,
        )

        # 1. Locations
        for loc_plan in plan.locations:
            loc = Location(
                id=loc_plan.id,
                name=loc_plan.name,
                description=loc_plan.description,
                connected_locations=list(loc_plan.connected_location_ids),
                capacity=loc_plan.capacity,
            )
            world.locations[loc.id] = loc

        # 2. Objects
        for obj_plan in plan.objects:
            obj = WorldObject(
                id=obj_plan.id,
                name=obj_plan.name,
                description=obj_plan.description,
                location_id=obj_plan.starting_location_id,
                holder_id=obj_plan.starting_holder_id,
                portable=obj_plan.portable,
                properties=dict(obj_plan.properties),
            )
            world.objects[obj.id] = obj

        # 3. Characters & their inner states
        for char_plan in plan.characters:
            char = Character(
                id=char_plan.id,
                name=char_plan.name,
                role=char_plan.role,
                description=char_plan.description,
                personality_traits=dict(char_plan.personality_traits),
                emotional_state=EmotionalState(
                    happiness=char_plan.emotional_state.get("happiness", 0.0),
                    fear=char_plan.emotional_state.get("fear", 0.0),
                    anger=char_plan.emotional_state.get("anger", 0.0),
                    trust=char_plan.emotional_state.get("trust", 0.0),
                    curiosity=char_plan.emotional_state.get("curiosity", 0.0),
                ),
                current_location_id=char_plan.starting_location_id,
            )
            world.characters[char.id] = char

            # Immediate Goals
            for g_idx, goal_desc in enumerate(char_plan.immediate_goals):
                goal = Goal(
                    id=f"goal_{char.id}_imm_{g_idx}",
                    character_id=char.id,
                    description=goal_desc,
                    priority=0.9,
                    status=GoalStatus.ACTIVE,
                    reason="Immediate objective",
                )
                world.goals[goal.id] = goal
                char.goals.append(goal.id)

            # Long Term Goals
            for g_idx, goal_desc in enumerate(char_plan.long_term_goals):
                goal = Goal(
                    id=f"goal_{char.id}_lt_{g_idx}",
                    character_id=char.id,
                    description=goal_desc,
                    priority=0.7,
                    status=GoalStatus.ACTIVE,
                    reason="Strategic objective",
                )
                world.goals[goal.id] = goal
                char.goals.append(goal.id)

            # Secrets
            for s_idx, sec_stmt in enumerate(char_plan.secrets):
                secret = Secret(
                    id=f"sec_{char.id}_{s_idx}",
                    character_id=char.id,
                    statement=sec_stmt,
                    known_by=[],
                    importance=1.0,
                )
                world.secrets[secret.id] = secret
                char.secrets.append(secret.id)

            # Beliefs
            for b_idx, bel_stmt in enumerate(char_plan.initial_beliefs):
                belief = Belief(
                    id=f"bel_{char.id}_{b_idx}",
                    character_id=char.id,
                    statement=bel_stmt,
                    confidence=0.85,
                    source="initial_knowledge",
                )
                world.beliefs[belief.id] = belief
                char.beliefs.append(belief.id)

        # 4. Relationships
        for rel_plan in plan.relationships:
            rel = Relationship(
                id=rel_plan.id,
                character_a_id=rel_plan.character_a_id,
                character_b_id=rel_plan.character_b_id,
                affinity=rel_plan.affinity,
                trust=rel_plan.trust,
                history=rel_plan.history,
            )
            world.relationships[rel.id] = rel
            if rel.character_a_id in world.characters:
                world.characters[rel.character_a_id].relationships.append(rel.id)
            if rel.character_b_id in world.characters:
                world.characters[rel.character_b_id].relationships.append(rel.id)

        # Validate reference integrity
        errors = world.validate_references()
        if errors:
            raise ValueError(f"Instantiated world has dangling references: {errors}")

        return world

    def initialize_from_seed(self, seed_text: str) -> WorldState:
        """End-to-end helper generating plan and creating valid WorldState"""
        plan = self.generate_plan(seed_text)
        return self.instantiate_world(plan)

    def _build_deterministic_mock_plan(self, seed_text: str) -> WorldInitializationPlan:
        """Deterministic mock plan based on seed text parsing"""
        slug = uuid.uuid4().hex[:6]
        return WorldInitializationPlan(
            world_id=f"world_init_{slug}",
            world_name="Generated Narrative Sandbox",
            genre="Suspense / Drama",
            tone="Tense, guarded",
            initial_situation=seed_text[:120] if seed_text else "Two actors in an enclosed space",
            facts=[
                TaggedFact(statement=seed_text[:80] if seed_text else "Seed scenario", fact_type=FactType.SOURCE_FACT),
                TaggedFact(statement="Both characters have opposing hidden motivations", fact_type=FactType.DERIVED_PREMISE),
                TaggedFact(statement="An encrypted document is located in the room", fact_type=FactType.SIMULATION_INVENTION),
            ],
            locations=[
                LocationPlan(
                    id="loc_main",
                    name="Private Suite",
                    description="A quiet suite with modern furniture",
                    connected_location_ids=["loc_corridor"],
                    capacity=5,
                ),
                LocationPlan(
                    id="loc_corridor",
                    name="Service Corridor",
                    description="A narrow dimly-lit corridor",
                    connected_location_ids=["loc_main"],
                    capacity=5,
                ),
            ],
            characters=[
                CharacterPlan(
                    id="char_alpha",
                    name="Jordan",
                    role="Investigator",
                    description="Methodical and probing",
                    starting_location_id="loc_main",
                    personality_traits={"cautious": 0.8, "analytical": 0.9},
                    immediate_goals=["Verify identity of companion"],
                    long_term_goals=["Retrieve classified intel"],
                    secrets=["Possesses an undercover warrant"],
                    initial_beliefs=["The other person is withholding information"],
                    emotional_state={"fear": 0.3, "trust": 0.1, "curiosity": 0.8},
                ),
                CharacterPlan(
                    id="char_beta",
                    name="Morgan",
                    role="Courier",
                    description="Guarded and defensive",
                    starting_location_id="loc_main",
                    personality_traits={"evasive": 0.7, "cautious": 0.85},
                    immediate_goals=["Prevent luggage from being searched"],
                    long_term_goals=["Complete transfer without incident"],
                    secrets=["The dossier inside is counterfeit"],
                    initial_beliefs=["Jordan is a federal agent"],
                    emotional_state={"fear": 0.6, "trust": 0.2, "curiosity": 0.5},
                ),
            ],
            objects=[
                ObjectPlan(
                    id="obj_dossier",
                    name="Dossier",
                    description="A sealed leather case",
                    starting_location_id="loc_main",
                    portable=True,
                    properties={"sealed": "true"},
                ),
            ],
            relationships=[
                RelationshipPlan(
                    id="rel_alpha_beta",
                    character_a_id="char_alpha",
                    character_b_id="char_beta",
                    affinity=0.1,
                    trust=0.0,
                    history="Met through a third party broker",
                ),
            ],
            possible_conflicts=["Discovery of counterfeit document", "Intervention by outside security"],
        )
