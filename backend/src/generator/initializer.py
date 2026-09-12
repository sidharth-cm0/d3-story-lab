"""World Initializer service transforming unstructured seeds into validated WorldState with visual continuity."""
import uuid
import re
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
    ActorVisualProfile,
    ObjectVisualProfile,
    LocationVisualProfile,
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
from ..narrative.completion import StoryCompletionEngine, StoryOutline, StoryInputType


class WorldInitializerService:
    """Transforms raw text seeds into structured WorldInitializationPlans and canonical WorldStates."""

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or MockLLMProvider()
        self.completion_engine = StoryCompletionEngine(provider=self.provider)

    def generate_plan(
        self,
        seed_text: str,
        declared_type: Optional[str] = None,
        target_duration_minutes: int = 20,
    ) -> WorldInitializationPlan:
        """Generate a WorldInitializationPlan with completed dramatic outline and visual continuity."""
        # 1. Complete narrative arc structure first
        outline = self.completion_engine.complete_story(
            seed_text=seed_text,
            declared_type=declared_type,
            target_duration_minutes=target_duration_minutes,
        )

        prompt = (
            f"Analyze the following narrative seed and generate a complete structured world initialization plan.\n"
            f"Input Type: {outline.input_type.value}\n"
            f"Premise: {outline.premise}\n"
            f"Explicitly distinguish facts as SOURCE_FACT, DERIVED_PREMISE, or SIMULATION_INVENTION.\n\n"
            f"SEED TEXT:\n{seed_text}"
        )
        system_prompt = (
            "You are the world initialization architect for D3 Story Lab. Create rich, consistent sandbox simulation "
            "plans with distinct character secrets, goals, beliefs, visual profiles, and locations."
        )

        # If using MockLLMProvider without custom registration, build a high quality deterministic plan
        if isinstance(self.provider, MockLLMProvider) and WorldInitializationPlan not in self.provider._structured_handlers:
            return self._build_deterministic_mock_plan(seed_text, outline)

        try:
            plan = self.provider.generate_structured(
                WorldInitializationPlan, prompt, system_prompt=system_prompt
            )
        except Exception as e:
            logger.warning(
                f"Structured plan generation with provider failed ({e}), falling back to deterministic plan."
            )
            plan = self._build_deterministic_mock_plan(seed_text, outline)

        if not plan or not plan.characters or not plan.locations:
            logger.warning("Provider returned incomplete plan, falling back to deterministic plan.")
            plan = self._build_deterministic_mock_plan(seed_text, outline)

        # Ensure story_outline is bound to plan
        if not plan.story_outline:
            object.__setattr__(plan, "story_outline", outline)
        return plan

    def instantiate_world(self, plan: WorldInitializationPlan) -> WorldState:
        """Convert a WorldInitializationPlan into a canonically validated WorldState."""
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
                visual_profile=loc_plan.visual_profile,
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
                visual_profile=obj_plan.visual_profile,
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
                visual_profile=char_plan.visual_profile,
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

    def initialize_from_seed(
        self,
        seed_text: str,
        declared_type: Optional[str] = None,
        target_duration_minutes: int = 20,
    ) -> WorldState:
        """End-to-end helper generating plan and creating valid WorldState."""
        plan = self.generate_plan(seed_text, declared_type, target_duration_minutes)
        return self.instantiate_world(plan)

    def _build_deterministic_mock_plan(
        self, seed_text: str, outline: Optional[StoryOutline] = None
    ) -> WorldInitializationPlan:
        """Deterministic mock plan based on seed text parsing and completed story outline."""
        if not outline:
            outline = self.completion_engine.complete_story(seed_text)

        slug = uuid.uuid4().hex[:6]
        text_lower = seed_text.lower()

        # Adapt characters and props contextually based on user prompt
        if "abandoned building" in text_lower or "enters an abandoned" in text_lower:
            char_a_name, char_a_role = "Vincent Cross", "Infiltrator"
            char_b_name, char_b_role = "Evelyn Vance", "Clandestine Custodian"
            char_a_hair, char_a_cloth = "Shaggy dark hair, damp", "Weathered field jacket, heavy boots"
            char_b_hair, char_b_cloth = "Tied-back silver-streaked hair", "Work coveralls with utility belt"
            loc_main_name = "Abandoned Industrial Bay"
            loc_main_desc = "A sprawling decaying warehouse bay with broken skylights and rusted catwalks"
            loc_sub_name = "Subterranean Archive Vault"
            loc_sub_desc = "Reinforced concrete storage bunker tucked beneath the crumbling floorboards"
            obj_name = "Sealed Transit Dossier"
            obj_mat = "Rusted aluminum lockbox stamped with hazard stencils"
        elif "detective" in text_lower or "partner is lying" in text_lower:
            char_a_name, char_a_role = "Detective Clara Ramos", "Senior Investigator"
            char_b_name, char_b_role = "Detective David Vance", "Undercover Partner"
            char_a_hair, char_a_cloth = "Sharp black bob", "Dark charcoal trench coat, badge on belt"
            char_b_hair, char_b_cloth = "Close-cropped brown hair", "Leather bomber jacket, concealed holster"
            loc_main_name = "Precinct Evidence Room"
            loc_main_desc = "Dimly lit archival room stacked high with cold case boxes under buzzing neon"
            loc_sub_name = "Observation Corridor"
            loc_sub_desc = "One-way mirrored hallway overlooking the interrogation suite"
            obj_name = "Redacted Wiretap Transcript"
            obj_mat = "Manila folio stamped TOP SECRET with red wax binder"
        elif "warehouse" in text_lower or "escapes" in text_lower or "fire" in text_lower:
            char_a_name, char_a_role = "Marcus Cole", "Escaped Courier"
            char_b_name, char_b_role = "Agent Raymond Kane", "Syndicate Enforcer"
            char_a_hair, char_a_cloth = "Disheveled dark curls, soot-smudged", "Singed tactical jacket"
            char_b_hair, char_b_cloth = "Military buzzcut", "Reinforced Kevlar vest over dark fatigues"
            loc_main_name = "Burning Depot Floor"
            loc_main_desc = "Industrial storage depot surrounded by spreading chemical flames and thick smoke"
            loc_sub_name = "Emergency Loading Dock"
            loc_sub_desc = "Heavy rolling iron shutter gate leading to the wet rain-slicked alleyway"
            obj_name = "Charred Ledger"
            obj_mat = "Fire-resistant safe canister with glowing red biometric latch"
        else:
            char_a_name, char_a_role = "Maya Lin", "Investigative Journalist"
            char_b_name, char_b_role = "Arjun Mehta", "Corporate Envoy"
            char_a_hair, char_a_cloth = "Sleek jet-black hair with damp strands", "Tailored dark trench coat"
            char_b_hair, char_b_cloth = "Parted silver-templed hair", "Crisp bespoke charcoal three-piece suit"
            loc_main_name = "Penthouse Suite 402"
            loc_main_desc = "A lavish penthouse living room with floor-to-ceiling panoramic glass facing the rain"
            loc_sub_name = "Service Corridor"
            loc_sub_desc = "A narrow dimly lit maintenance hallway with industrial pipes overhead"
            obj_name = "Offshore Ledger"
            obj_mat = "Heavy oxblood calfskin binder with polished brass clasp"

        # Construct visual profiles for continuity
        char_a_profile = ActorVisualProfile(
            character_id="char_alpha",
            name=char_a_name,
            age="Early 30s",
            face_traits="Sharp jawline, penetrating observant gaze, high cheekbones",
            hairstyle=char_a_hair,
            build="Lean athletic build, tense cautious posture",
            clothing=char_a_cloth,
            signature_items=["Silver mechanical wristwatch", "Encrypted audio recorder"],
            emotional_style="Calculating, watchful, disciplined intensity",
        )

        char_b_profile = ActorVisualProfile(
            character_id="char_beta",
            name=char_b_name,
            age="Late 40s",
            face_traits="Tired guarded eyes, aristocratic facial features, subtle tension at mouth",
            hairstyle=char_b_hair,
            build="Broad commanding frame, slightly rigid posture",
            clothing=char_b_cloth,
            signature_items=["Gold signet ring", "Vintage brass lighter"],
            emotional_style="Evasive, defensive, simmering inner panic",
        )

        loc_main_profile = LocationVisualProfile(
            location_id="loc_main",
            name=loc_main_name,
            environment_type="High-contrast noir interior",
            lighting="Chiaroscuro, rain streaks against panoramic glass, amber table lamp glow",
            layout="Open layout with central desk/console, wide floor perspective",
            palette="Charcoal, gunmetal slate, deep amber accent, midnight shadows",
            mood="Claustrophobic suspense, imminent reckoning",
        )

        loc_sub_profile = LocationVisualProfile(
            location_id="loc_corridor",
            name=loc_sub_name,
            environment_type="Industrial auxiliary passageway",
            lighting="Flickering overhead strip fluorescent, heavy cast shadows",
            layout="Narrow linear hall with exposed conduits and reinforced exit door",
            palette="Matte black, rusted steel, emergency amber flash",
            mood="Harsh, utilitarian, trapped",
        )

        obj_profile = ObjectVisualProfile(
            object_id="obj_dossier",
            name=obj_name,
            material=obj_mat,
            size="Folio sized, approximately 12x9 inches, 2 inches thick",
            color="Deep oxblood / charred dark tone",
            condition="Weathered with scuffed corners and official seal marks",
            unique_markers="Confidential red wax seal with diplomatic monogram",
        )

        return WorldInitializationPlan(
            world_id=f"world_init_{slug}",
            world_name=outline.episode_title if outline else "Generated Narrative Sandbox",
            genre=outline.genre if outline else "Suspense / Drama",
            tone=outline.tone if outline else "Tense, guarded",
            initial_situation=seed_text[:120] if seed_text else "Two actors in an enclosed space",
            facts=[
                TaggedFact(statement=seed_text[:80] if seed_text else "Seed scenario", fact_type=FactType.SOURCE_FACT),
                TaggedFact(statement=f"{char_a_name} and {char_b_name} have opposing hidden agendas", fact_type=FactType.DERIVED_PREMISE),
                TaggedFact(statement=f"{obj_name} contains compromising evidence of the syndicate", fact_type=FactType.SIMULATION_INVENTION),
            ],
            locations=[
                LocationPlan(
                    id="loc_main",
                    name=loc_main_name,
                    description=loc_main_desc,
                    connected_location_ids=["loc_corridor"],
                    capacity=5,
                    visual_profile=loc_main_profile,
                ),
                LocationPlan(
                    id="loc_corridor",
                    name=loc_sub_name,
                    description=loc_sub_desc,
                    connected_location_ids=["loc_main"],
                    capacity=5,
                    visual_profile=loc_sub_profile,
                ),
            ],
            characters=[
                CharacterPlan(
                    id="char_alpha",
                    name=char_a_name,
                    role=char_a_role,
                    description="Methodical and probing",
                    starting_location_id="loc_main",
                    personality_traits={"cautious": 0.8, "analytical": 0.9},
                    immediate_goals=[f"Inspect {obj_name} and verify validity"],
                    long_term_goals=["Retrieve classified intel and expose conspirators"],
                    secrets=["Possesses an undercover warrant authorizing immediate seizure"],
                    initial_beliefs=[f"{char_b_name} is actively withholding key information"],
                    emotional_state={"fear": 0.3, "trust": 0.1, "curiosity": 0.85},
                    visual_profile=char_a_profile,
                ),
                CharacterPlan(
                    id="char_beta",
                    name=char_b_name,
                    role=char_b_role,
                    description="Guarded and defensive",
                    starting_location_id="loc_main",
                    personality_traits={"evasive": 0.75, "cautious": 0.85},
                    immediate_goals=[f"Prevent {char_a_name} from seizing {obj_name}"],
                    long_term_goals=["Secure an exit route before security lockdown"],
                    secrets=[f"The documents inside {obj_name} implicate their own superiors"],
                    initial_beliefs=[f"{char_a_name} will not hesitate to use leverage"],
                    emotional_state={"fear": 0.6, "trust": 0.15, "curiosity": 0.5},
                    visual_profile=char_b_profile,
                ),
            ],
            objects=[
                ObjectPlan(
                    id="obj_dossier",
                    name=obj_name,
                    description=f"{obj_mat} holding sensitive records",
                    starting_location_id="loc_main",
                    portable=True,
                    properties={"sealed": "true", "classified": "true"},
                    visual_profile=obj_profile,
                ),
            ],
            relationships=[
                RelationshipPlan(
                    id="rel_alpha_beta",
                    character_a_id="char_alpha",
                    character_b_id="char_beta",
                    affinity=0.1,
                    trust=0.0,
                    history="Met under tense diplomatic and investigative auspices",
                ),
            ],
            possible_conflicts=[
                f"Contestation over physical possession of {obj_name}",
                "Director environmental intervention triggering lockdown or blackout",
            ],
            story_outline=outline,
        )
