"""Tests for Milestone 7: World Initializer"""
import pytest
from src.generator import (
    WorldInitializerService,
    WorldInitializationPlan,
    FactType,
    TaggedFact,
    LocationPlan,
    CharacterPlan,
    ObjectPlan,
    RelationshipPlan,
)
from src.providers import MockLLMProvider


class TestWorldInitializer:
    """Tests for transforming unstructured text into validated WorldState"""

    def test_mock_plan_generation_and_provenance_tagging(self):
        """Test generating plan and verifying fact provenance tags"""
        service = WorldInitializerService()
        plan = service.generate_plan("Two diplomats meet in a train car to trade confidential maps.")

        assert isinstance(plan, WorldInitializationPlan)
        assert len(plan.facts) >= 3

        fact_types = {f.fact_type for f in plan.facts}
        assert FactType.SOURCE_FACT in fact_types
        assert FactType.DERIVED_PREMISE in fact_types
        assert FactType.SIMULATION_INVENTION in fact_types

        assert len(plan.characters) >= 2
        assert len(plan.locations) >= 2

    def test_instantiate_world_zero_dangling_references(self):
        """Test that instantiated world has 100% reference integrity"""
        service = WorldInitializerService()
        world = service.initialize_from_seed("A scientist and an investor meet in an abandoned lab.")

        assert world is not None
        # Must have zero dangling references
        errors = world.validate_references()
        assert errors == [], f"Dangling references detected: {errors}"

        # Verify character inner states are registered in WorldState
        for char_id, char in world.characters.items():
            assert len(char.goals) > 0
            for gid in char.goals:
                assert gid in world.goals
                assert world.goals[gid].character_id == char_id

            assert len(char.secrets) > 0
            for sid in char.secrets:
                assert sid in world.secrets
                assert world.secrets[sid].character_id == char_id

            assert len(char.beliefs) > 0
            for bid in char.beliefs:
                assert bid in world.beliefs

    def test_custom_plan_instantiation(self):
        """Test instantiating a custom plan"""
        plan = WorldInitializationPlan(
            world_id="custom_world",
            world_name="Custom Lab",
            genre="Sci-Fi",
            tone="Eerie",
            initial_situation="A lone robot guards a console",
            facts=[TaggedFact(statement="Facility is offline", fact_type=FactType.SOURCE_FACT)],
            locations=[
                LocationPlan(id="loc_hub", name="Control Hub", description="Dark room", connected_location_ids=[]),
            ],
            characters=[
                CharacterPlan(
                    id="char_unit",
                    name="Unit 7",
                    role="Sentry",
                    description="Automaton",
                    starting_location_id="loc_hub",
                    immediate_goals=["Keep reactor safe"],
                    secrets=["Reactor is unstable"],
                )
            ],
            objects=[
                ObjectPlan(id="obj_core", name="Core", description="Glowing power source", starting_location_id="loc_hub")
            ],
            relationships=[],
        )

        service = WorldInitializerService()
        world = service.instantiate_world(plan)

        assert world.id == "custom_world"
        assert "char_unit" in world.characters
        assert "loc_hub" in world.locations
        assert "obj_core" in world.objects
        assert world.validate_references() == []
