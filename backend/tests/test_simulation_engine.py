"""Tests for Milestone 2: Deterministic Sandbox Simulation"""
import pytest
from src.demo_world import create_demo_world
from src.domain import (
    ActionProposal,
    ActionType,
    ActionResultStatus,
    EventType,
    WorldObject,
    Motivation,
)
from src.simulation import (
    SimulationEngine,
    ActionValidator,
    ActionExecutor,
    EventRecorder,
    RuleBasedPolicy,
)


class TestActionValidatorAndExecutor:
    """Tests for deterministic action validation and execution rules"""

    def test_accepted_move_action(self):
        """Test valid movement between connected rooms"""
        world = create_demo_world()
        recorder = EventRecorder(world)

        # Arjun moves from room 307 to hallway
        proposal = ActionProposal(
            id="act_move_01",
            actor_id="char_arjun",
            action_type=ActionType.MOVE,
            location_id="loc_hallway",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL"),
        )

        is_valid, err = ActionValidator.validate(world, proposal)
        assert is_valid is True
        assert err is None

        result = ActionExecutor.execute(world, proposal, recorder)
        assert result.status == ActionResultStatus.SUCCESS
        assert world.characters["char_arjun"].current_location_id == "loc_hallway"
        assert len(result.events_created) == 1

        event_id = result.events_created[0]
        assert event_id in world.events
        assert world.events[event_id].event_type == EventType.CHARACTER_MOVED

    def test_rejected_move_to_unconnected_room(self):
        """Test movement to an unconnected or non-existent room is rejected"""
        world = create_demo_world()
        recorder = EventRecorder(world)

        # Attempt to move to non-existent room
        proposal = ActionProposal(
            id="act_move_bad",
            actor_id="char_arjun",
            action_type=ActionType.MOVE,
            location_id="loc_penthouse_999",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL"),
        )
        is_valid, err = ActionValidator.validate(world, proposal)
        assert is_valid is False
        assert "does not exist" in err

        result = ActionExecutor.execute(world, proposal, recorder)
        assert result.status == ActionResultStatus.INVALID
        assert len(result.events_created) == 0

    def test_take_and_drop_object(self):
        """Test taking an unheld portable object and then dropping it"""
        world = create_demo_world()
        recorder = EventRecorder(world)

        # Maya takes documents
        take_prop = ActionProposal(
            id="act_take_doc",
            actor_id="char_maya",
            action_type=ActionType.TAKE_OBJECT,
            target_id="obj_documents",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL"),
        )
        take_res = ActionExecutor.execute(world, take_prop, recorder)
        assert take_res.status == ActionResultStatus.SUCCESS
        assert world.objects["obj_documents"].holder_id == "char_maya"
        assert "obj_documents" in world.characters["char_maya"].inventory

        # Maya drops documents
        drop_prop = ActionProposal(
            id="act_drop_doc",
            actor_id="char_maya",
            action_type=ActionType.DROP_OBJECT,
            target_id="obj_documents",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL"),
        )
        drop_res = ActionExecutor.execute(world, drop_prop, recorder)
        assert drop_res.status == ActionResultStatus.SUCCESS
        assert world.objects["obj_documents"].holder_id is None
        assert world.objects["obj_documents"].location_id == "loc_room307"
        assert "obj_documents" not in world.characters["char_maya"].inventory

    def test_illegal_object_interaction(self):
        """Test illegal interactions: taking non-portable or already-held objects"""
        world = create_demo_world()
        recorder = EventRecorder(world)

        # 1. Attempt to take the non-portable door
        door_prop = ActionProposal(
            id="act_take_door",
            actor_id="char_arjun",
            action_type=ActionType.TAKE_OBJECT,
            target_id="obj_door",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL"),
        )
        is_valid, err = ActionValidator.validate(world, door_prop)
        assert is_valid is False
        assert "not portable" in err

        # 2. Maya takes the documents
        ActionExecutor.execute(
            world,
            ActionProposal(
                id="act_maya_take",
                actor_id="char_maya",
                action_type=ActionType.TAKE_OBJECT,
                target_id="obj_documents",
                tick_proposed=0,
                motivation=Motivation(kind="PURSUE_GOAL"),
            ),
            recorder,
        )

        # 3. Arjun attempts to take documents already held by Maya
        arjun_take = ActionProposal(
            id="act_arjun_take_held",
            actor_id="char_arjun",
            action_type=ActionType.TAKE_OBJECT,
            target_id="obj_documents",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL"),
        )
        is_valid, err = ActionValidator.validate(world, arjun_take)
        assert is_valid is False
        assert "currently held by 'Maya'" in err

    def test_give_object(self):
        """Test transferring an object from one character to another"""
        world = create_demo_world()
        recorder = EventRecorder(world)

        # Maya takes documents first
        ActionExecutor.execute(
            world,
            ActionProposal(
                id="t1",
                actor_id="char_maya",
                action_type=ActionType.TAKE_OBJECT,
                target_id="obj_documents",
                tick_proposed=0,
                motivation=Motivation(kind="PURSUE_GOAL"),
            ),
            recorder,
        )

        # Maya gives documents to Arjun
        give_prop = ActionProposal(
            id="g1",
            actor_id="char_maya",
            action_type=ActionType.GIVE_OBJECT,
            target_id="char_arjun",
            parameters={"object_id": "obj_documents"},
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL"),
        )
        res = ActionExecutor.execute(world, give_prop, recorder)
        assert res.status == ActionResultStatus.SUCCESS
        assert world.objects["obj_documents"].holder_id == "char_arjun"
        assert "obj_documents" not in world.characters["char_maya"].inventory
        assert "obj_documents" in world.characters["char_arjun"].inventory


class TestSimulationEngine:
    """Tests for the step and run simulation engine loops"""

    def test_single_engine_step(self):
        """Test engine advances tick and generates events for characters"""
        world = create_demo_world()
        engine = SimulationEngine(world)
        assert world.current_tick == 0

        results = engine.step()
        assert len(results) == 2  # Arjun and Maya
        assert world.current_tick == 1
        assert engine.clock.current_tick == 1
        assert len(world.events) >= 2

    def test_deterministic_multi_tick_run(self):
        """Test multi-tick run generates consistent deterministic results"""
        world_a = create_demo_world()
        engine_a = SimulationEngine(world_a)
        results_a = engine_a.run(max_ticks=3)

        world_b = create_demo_world()
        engine_b = SimulationEngine(world_b)
        results_b = engine_b.run(max_ticks=3)

        assert world_a.current_tick == 3
        assert world_b.current_tick == 3
        assert len(world_a.events) == len(world_b.events)

        events_a = sorted([e.description for e in world_a.events.values()])
        events_b = sorted([e.description for e in world_b.events.values()])
        assert events_a == events_b
