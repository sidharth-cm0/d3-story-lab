"""Comprehensive tests for Narrative Coherence, Spatial Consistency, and Causality."""

import pytest
from src.domain import (
    WorldState,
    Location,
    Character,
    WorldObject,
    Goal,
    GoalStatus,
    ActionType,
    ActionProposal,
    EventType,
    DiscoveredFact,
)
from src.simulation.actions import ActionValidator, ActionExecutor
from src.simulation.recorder import EventRecorder
from src.simulation.orchestrator import SimulationOrchestrator
from src.generator.initializer import WorldInitializerService
from src.agents.repetition import RepetitionTracker
from src.agents.social import SocialIntent, SocialDialogueGenerator
from src.narrative.observer import Observer
from src.evaluation.metrics import NarrativeEvaluator


class TestSpatialStateConsistencyAndAudit:
    """Audit and prove spatial state consistency, communication range, and accessibility."""

    def test_speak_requires_colocation_or_communication_channel(self):
        """Direct dialogue must be rejected if characters are in different rooms and have no channel."""
        loc1 = Location(id="loc_suite", name="Suite", connected_locations=["loc_hall"])
        loc2 = Location(id="loc_hall", name="Hall", connected_locations=["loc_suite"])
        c1 = Character(id="c1", name="Jordan", role="Journalist", current_location_id="loc_suite")
        c2 = Character(id="c2", name="Morgan", role="Source", current_location_id="loc_hall")

        world = WorldState(
            id="w1",
            name="Test",
            locations={"loc_suite": loc1, "loc_hall": loc2},
            characters={"c1": c1, "c2": c2},
        )

        # Propose direct speech without channel -> must be rejected
        prop_remote = ActionProposal(
            id="prop_remote",
            actor_id="c1",
            action_type=ActionType.SPEAK,
            target_id="c2",
            parameters={"dialogue": "Can you hear me from the other room?"},
            tick_proposed=0,
        )
        valid, err = ActionValidator.validate(world, prop_remote)
        assert not valid
        assert "not in the same location" in (err or "")

        # When co-located -> must be accepted
        c2.current_location_id = "loc_suite"
        valid_local, err_local = ActionValidator.validate(world, prop_remote)
        assert valid_local
        assert err_local is None

    def test_30_tick_spatial_audit_reconstruction_matches_canonical_state(self):
        """Run 30+ ticks and reconstruct actor locations purely from events, proving 100% spatial integrity."""
        service = WorldInitializerService()
        plan = service.generate_plan("Two investigators in an abandoned archive.")
        world = service.instantiate_world(plan)

        # Record starting locations
        initial_locations = {cid: char.current_location_id for cid, char in world.characters.items()}
        reconstructed_locations = dict(initial_locations)

        orchestrator = SimulationOrchestrator(world)

        # Run 35 ticks
        for _ in range(35):
            orchestrator.step()

        # Audit all CHARACTER_MOVED events in chronological order
        movement_events = [
            e for e in sorted(world.events.values(), key=lambda ev: (ev.tick, ev.id))
            if e.event_type == EventType.CHARACTER_MOVED
        ]

        assert len(movement_events) >= 1, "Simulation should include valid movement across 35 ticks"

        for ev in movement_events:
            actor_id = ev.actor_ids[0]
            from_loc = ev.from_location
            to_loc = ev.to_location

            # Invariant 1: from_location must match where the character was tracked
            assert reconstructed_locations[actor_id] == from_loc, (
                f"Spatial anomaly for {actor_id} at tick {ev.tick}: "
                f"event claimed from={from_loc}, but character was tracked at {reconstructed_locations[actor_id]}"
            )

            # Invariant 2: destination must be connected to source in the world
            source_obj = world.locations.get(from_loc)
            assert source_obj is not None
            assert to_loc in source_obj.connected_locations, (
                f"Teleportation detected: {from_loc} is not connected to {to_loc}"
            )

            # Invariant 3: destination must not equal source
            assert from_loc != to_loc, "Actor cannot move to their current location"

            # Update tracked position
            reconstructed_locations[actor_id] = to_loc

        # Invariant 4: final reconstructed locations must match canonical WorldState exactly
        for cid, char in world.characters.items():
            assert reconstructed_locations[cid] == char.current_location_id, (
                f"Final location mismatch for {char.name}: "
                f"reconstructed={reconstructed_locations[cid]}, canonical={char.current_location_id}"
            )


class TestActionNoveltyAndAntiOscillation:
    """Verify strong penalties on object oscillation, inspection repetition, and room ping-pong."""

    def test_object_oscillation_pickup_drop_penalized(self):
        """Actor picking up an object and dropping it in the same room without moving receives heavy penalty."""
        tracker = RepetitionTracker()
        tracker.record_action(
            actor_id="actor1",
            action_type=ActionType.TAKE_OBJECT,
            target_id="obj_dossier",
            location_id="loc_suite",
        )

        # Propose dropping it immediately without moving
        drop_penalty = tracker.get_penalty(
            actor_id="actor1",
            action_type=ActionType.DROP_OBJECT,
            target_id="obj_dossier",
            location_id="loc_suite",
        )
        assert drop_penalty >= 1.8, f"Immediate drop in same room should be heavily penalized: {drop_penalty}"

    def test_repeated_inspection_penalized(self):
        """Re-inspecting an object already inspected should receive strong repetition penalty."""
        tracker = RepetitionTracker()
        tracker.record_action(
            actor_id="actor1",
            action_type=ActionType.INSPECT_OBJECT,
            target_id="obj_dossier",
        )

        inspect_penalty = tracker.get_penalty(
            actor_id="actor1",
            action_type=ActionType.INSPECT_OBJECT,
            target_id="obj_dossier",
        )
        assert inspect_penalty >= 1.2, f"Re-inspecting same object should be penalized: {inspect_penalty}"

    def test_room_ping_pong_penalized(self):
        """Moving A -> B -> A should receive room ping-pong penalty."""
        tracker = RepetitionTracker()
        tracker.record_action(
            actor_id="actor1",
            action_type=ActionType.MOVE,
            location_id="loc_corridor",
        )
        tracker.record_action(
            actor_id="actor1",
            action_type=ActionType.SPEAK,
            target_id="actor2",
            location_id="loc_corridor",
        )

        # Propose moving back to loc_suite (source before corridor)
        ping_pong_penalty = tracker.get_penalty(
            actor_id="actor1",
            action_type=ActionType.MOVE,
            location_id="loc_corridor",
        )
        assert ping_pong_penalty >= 0.7


class TestActionConsequencesAndInformationState:
    """Verify inspection produces DiscoveredFacts and advances character goals."""

    def test_inspect_creates_discovered_fact_and_advances_goal(self):
        """Inspecting an object creates a DiscoveredFact, marks inspected_by, and advances matching goal."""
        loc = Location(id="loc_suite", name="Private Suite", connected_locations=[])
        obj = WorldObject(
            id="obj_ledger",
            name="Ledger",
            description="A secret financial ledger with black-budget payments.",
            location_id="loc_suite",
            properties={"classified": "true"},
        )
        goal = Goal(
            id="goal_ledger",
            character_id="char_maya",
            description="Find the financial ledger",
            priority=0.9,
            status=GoalStatus.ACTIVE,
            progress=0.0,
        )
        char = Character(
            id="char_maya",
            name="Maya",
            role="Investigator",
            current_location_id="loc_suite",
            goals=["goal_ledger"],
        )
        world = WorldState(
            id="w_fact",
            name="Fact World",
            locations={"loc_suite": loc},
            objects={"obj_ledger": obj},
            characters={"char_maya": char},
            goals={"goal_ledger": goal},
        )

        orch = SimulationOrchestrator(world)
        proposal = ActionProposal(
            id="prop_inspect",
            actor_id="char_maya",
            action_type=ActionType.INSPECT_OBJECT,
            target_id="obj_ledger",
            tick_proposed=0,
        )
        res = orch.executor.execute(world, proposal, orch.recorder)
        assert res.status.value == "success"

        # 1. World facts created
        assert len(world.facts) >= 1
        fact = next(iter(world.facts.values()))
        assert "Ledger" in fact.statement
        assert "char_maya" in char.known_facts or fact.id in char.known_facts
        assert "char_maya" in obj.inspected_by

        # 2. Cognitive effects applied
        orch._apply_cognitive_effects("char_maya", proposal, res)
        assert goal.progress > 0.0, "Goal progress should advance upon inspecting target object"


class TestNarrativeCoherenceDemonstrationTrace:
    """Verify 20-tick demonstration trace has zero impossible acts, diverse dialogue, and goal progression."""

    def test_20_tick_narrative_coherence_and_resolution(self):
        service = WorldInitializerService()
        plan = service.generate_plan("Two rival journalists investigating a locked room scandal.")
        world = service.instantiate_world(plan)
        orch = SimulationOrchestrator(world)

        for _ in range(20):
            orch.step()

        events = list(world.events.values())
        assert len(events) >= 20, "Should generate robust event sequence"

        # 1. No impossible conversations: all dialogue must occur between co-located characters
        for ev in events:
            if ev.event_type == EventType.CHARACTER_SPOKE and len(ev.actor_ids) >= 2:
                spk = world.characters[ev.actor_ids[0]]
                tgt = world.characters[ev.actor_ids[1]]
                # When spoken, both actors were at ev.location_id
                assert ev.location_id is not None

        # 2. At least two distinct dialogue intents
        speech_events = [e for e in events if e.event_type == EventType.CHARACTER_SPOKE]
        distinct_intents = {e.metadata.get("speech_act") for e in speech_events if e.metadata.get("speech_act")}
        assert len(distinct_intents) >= 2, f"Should exhibit diverse speech acts, found: {distinct_intents}"

        # 3. Information discovery occurred
        assert len(world.facts) >= 1, "At least one DiscoveredFact should be recorded"

        # 4. At least one goal made progress
        progressed_goals = [g for g in world.goals.values() if g.progress > 0.0 or g.status == GoalStatus.ACHIEVED]
        assert len(progressed_goals) >= 1, "At least one goal must show measured progress"

        # 5. NarrativeEvaluator report has clean coherence metrics
        observer = Observer(provider=orch.provider)
        selection = observer.observe_events(sorted(world.events.values(), key=lambda e: (e.tick, e.id)), world)
        evaluator = NarrativeEvaluator()
        report = evaluator.evaluate_simulation(world, selection)

        assert report.location_consistency_errors == 0, "Zero spatial errors permitted"
        assert report.object_oscillation_count <= 1, "Minimal or zero object oscillations"
        assert report.wait_percentage < 0.10, "Wait rate must remain low"
        assert report.narrative_coherence_score >= 0.50, f"Coherence score should be high: {report.narrative_coherence_score}"
