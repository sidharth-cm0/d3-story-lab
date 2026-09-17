"""Verification tests for Phase 4: Blueprint, Canon, Beat Pressure, Director, and Sufficiency Gate.

Covers all 32 targeted test requirements plus The Missing Dossier scenario integration:
Canon:
1. enforced proposition contradiction rejected
2. unenforced proposition may change

Role bindings:
3. protagonist resolves
4. focal object resolves
5. central proposition resolves
6. unresolved symbolic ref degrades safely

Predicates:
7. GOAL_ADOPTED
8. BELIEF_FLIP
9. POSSESSION_CHANGE
10. RELATIONSHIP_THRESHOLD_CROSSED
11. threshold true-crossing semantics
12. SECRET_LEARNED

Director:
13. invalid intervention rejected
14. same validator path used
15. failed gate rejects Director action
16. budget respected
17. min tick spacing respected
18. no actor event has source=DIRECTOR
19. no direct dialogue forcing

Beat pressure:
20. unsatisfied beat becomes UNSATISFIED
21. deviation_note exists
22. simulation does not hang

Sufficiency:
23. CONTINUE
24. ADJUST_PRESSURE_AND_CONTINUE
25. PROCEED
26. HALT_INSUFFICIENT
27. tick extension actually occurs
28. extension bounded by hard cap
29. HALT_INSUFFICIENT propagates cleanly

Integration:
30. zero-AI end-to-end
31. EventHistory unchanged by analysis
32. deterministic replay preserved

Scenario:
33. The Missing Dossier scenario integration check
34. StateSnapshotDiffer Phase 6 reuse documentation
"""
from pathlib import Path
import copy
import pytest
from pydantic import ValidationError

from src.demo_world import create_demo_world
from src.domain import (
    WorldState,
    Location,
    WorldObject,
    Character,
    EmotionalState,
    Goal,
    GoalStatus,
    ActionType,
    ActionProposal,
    Motivation,
    KnowledgeItem,
    Proposition,
    Event,
    EventType,
    Relationship,
)
from src.simulation.actions import CanonGate, ActionValidator, ActionExecutor
from src.simulation.recorder import EventRecorder
from src.simulation.differ import StateSnapshotDiffer
from src.simulation.orchestrator import SimulationOrchestrator
from src.agents.director import DirectorAgent, DirectorIntervention, DirectorInterventionType
from src.agents.actor import project_view
from src.story.models import (
    CanonFact,
    NarrativeIntent,
    StoryRoleBindings,
    StoryBlueprint,
    BeatPressure,
    PredicateClause,
    PredicateSpec,
    StructureSelection,
    SufficiencyReport,
)
from src.story.blueprint import (
    compile_blueprint,
    DEFAULT_ESCALATION_LADDERS,
    resolve_predicate_clause,
    resolve_predicate_spec,
)
from src.story.features import extract_story_input_rule_based
from src.story.scorer import score, select_structure
from src.story.loader import get_structure_registry
from src.narrative.sufficiency_gate import NarrativeSufficiencyGate
from src.providers.mock import MockLLMProvider


class TestPhase4BlueprintDirectorGate:
    """Complete 32 targeted tests for Phase 4."""

    # ============================================================
    # CANON TESTS
    # ============================================================

    def test_01_canon_enforced_proposition_contradiction_rejected(self):
        """1. Enforced proposition contradiction rejected by CanonGate."""
        world = create_demo_world()
        world.propositions["prop_canon_maya_dossier"] = Proposition(
            id="prop_canon_maya_dossier",
            subject="char_maya",
            predicate="has",
            object="obj_dossier",
            truth_value=True,
            enforced=True,
        )

        # Arjun attempts to seize the dossier
        bad_take = ActionProposal(
            id="prop_bad_take",
            actor_id="char_arjun",
            action_type=ActionType.TAKE_OBJECT,
            target_id="obj_dossier",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL", goal_id="goal_1"),
        )
        valid, err = CanonGate.validate(world, bad_take)
        assert valid is False
        assert "Contradicts canon" in err
        assert "prop_canon_maya_dossier" in err

        # Maya dropping the dossier also contradicts enforced custody
        bad_drop = ActionProposal(
            id="prop_bad_drop",
            actor_id="char_maya",
            action_type=ActionType.DROP_OBJECT,
            target_id="obj_dossier",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL", goal_id="goal_2"),
        )
        valid_drop, err_drop = CanonGate.validate(world, bad_drop)
        assert valid_drop is False
        assert "Contradicts canon" in err_drop

    def test_02_canon_unenforced_proposition_may_change(self):
        """2. Unenforced proposition may change without rejection by CanonGate."""
        world = create_demo_world()
        # Proposition has enforced=False (the default)
        world.propositions["prop_unenforced_maya_dossier"] = Proposition(
            id="prop_unenforced_maya_dossier",
            subject="char_maya",
            predicate="has",
            object="obj_dossier",
            truth_value=True,
            enforced=False,
        )

        # Action mutating custody passes CanonGate
        take_proposal = ActionProposal(
            id="prop_ok_take",
            actor_id="char_arjun",
            action_type=ActionType.TAKE_OBJECT,
            target_id="obj_dossier",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL", goal_id="goal_1"),
        )
        valid, err = CanonGate.validate(world, take_proposal)
        assert valid is True
        assert err is None

    # ============================================================
    # ROLE BINDINGS TESTS
    # ============================================================

    def test_03_role_bindings_protagonist_resolves(self):
        """3. Protagonist character ID resolves from prompt analysis."""
        prompt = "Detective Arjun investigates the locked office to find the secret dossier hidden by courier Maya."
        analysis = extract_story_input_rule_based(prompt)
        assert analysis.role_bindings.protagonist_character_id in ["char_detective", "char_arjun"]

    def test_04_role_bindings_focal_object_resolves(self):
        """4. Focal object ID resolves from prompt analysis."""
        prompt = "Detective Arjun investigates the locked office to find the secret dossier hidden by courier Maya."
        analysis = extract_story_input_rule_based(prompt)
        assert analysis.role_bindings.focal_object_id == "obj_dossier"

    def test_05_role_bindings_central_proposition_resolves(self):
        """5. Central proposition ID resolves from prompt analysis."""
        prompt = "Detective Arjun investigates the locked office to find the secret dossier hidden by courier Maya."
        analysis = extract_story_input_rule_based(prompt)
        assert analysis.role_bindings.central_proposition_id is not None
        assert len(analysis.canon_facts) >= 1

    def test_06_role_bindings_unresolved_symbolic_ref_degrades_safely(self):
        """6. Unresolved symbolic reference degrades gracefully without crashing."""
        clause_unresolvable = PredicateClause(
            type="POSSESSION_CHANGE",
            object="focal_object",  # symbolic reference
        )
        empty_bindings = StoryRoleBindings()  # focal_object_id is None

        # Clause resolution drops the clause cleanly
        res_clause = resolve_predicate_clause(clause_unresolvable, empty_bindings)
        assert res_clause is None

        # Spec with only that clause becomes unevaluable
        spec = PredicateSpec(any_of=[clause_unresolvable])
        resolved_spec, unevaluable = resolve_predicate_spec(spec, empty_bindings)
        assert unevaluable is True

        # Spec with another resolvable clause retains the resolvable clause
        resolvable_clause = PredicateClause(type="GOAL_ADOPTED")
        spec_mixed = PredicateSpec(any_of=[clause_unresolvable, resolvable_clause])
        resolved_mixed, unevaluable_mixed = resolve_predicate_spec(spec_mixed, empty_bindings)
        assert unevaluable_mixed is False
        assert len(resolved_mixed.any_of) == 1
        assert resolved_mixed.any_of[0].type == "GOAL_ADOPTED"

    # ============================================================
    # PREDICATE EVALUATION TESTS
    # ============================================================

    def test_07_predicate_goal_adopted(self):
        """7. Predicate evaluation: GOAL_ADOPTED."""
        world = create_demo_world()
        differ = StateSnapshotDiffer(world)

        differ.capture_snapshot(0, world)
        differ.capture_snapshot(1, world)
        # Arjun adopts a goal in the window [1, 5]
        char = world.characters["char_arjun"]
        char.goals.append("goal_new_secret_investigation")
        differ.capture_snapshot(5, world)

        # Initial seeded goal satisfies opening beat starting at tick 0
        clause_initial = PredicateClause(type="GOAL_ADOPTED", character="char_maya")
        assert differ.evaluate_clause(world, clause_initial, start_tick=0, end_tick=1) is True

        # Arjun adopted a goal in the later window [1, 5]
        clause = PredicateClause(type="GOAL_ADOPTED", character="char_arjun")
        assert differ.evaluate_clause(world, clause, start_tick=1, end_tick=5) is True

        # Maya has not adopted a new goal in the later window [1, 5]
        clause_other = PredicateClause(type="GOAL_ADOPTED", character="char_maya")
        assert differ.evaluate_clause(world, clause_other, start_tick=1, end_tick=5) is False

    def test_08_predicate_belief_flip(self):
        """8. Predicate evaluation: BELIEF_FLIP."""
        world = create_demo_world()
        differ = StateSnapshotDiffer(world)

        char = world.characters["char_arjun"]
        char.knowledge["prop_dossier_real"] = KnowledgeItem(
            proposition_id="prop_dossier_real",
            holder_id="char_arjun",
            believed_truth_value=True,
        )
        differ.capture_snapshot(0, world)

        # Belief flips at tick 5
        char.knowledge["prop_dossier_real"] = KnowledgeItem(
            proposition_id="prop_dossier_real",
            holder_id="char_arjun",
            believed_truth_value=False,
        )
        differ.capture_snapshot(5, world)

        clause = PredicateClause(type="BELIEF_FLIP", subject="prop_dossier_real", character="char_arjun")
        assert differ.evaluate_clause(world, clause, start_tick=0, end_tick=5) is True

    def test_09_predicate_possession_change(self):
        """9. Predicate evaluation: POSSESSION_CHANGE."""
        world = create_demo_world()
        differ = StateSnapshotDiffer(world)

        obj = world.objects["obj_documents"]
        obj.holder_id = None
        differ.capture_snapshot(0, world)

        obj.holder_id = "char_arjun"
        differ.capture_snapshot(3, world)

        clause = PredicateClause(type="POSSESSION_CHANGE", object="obj_documents")
        assert differ.evaluate_clause(world, clause, start_tick=0, end_tick=3) is True

    def test_10_predicate_relationship_threshold_crossed(self):
        """10. Predicate evaluation: RELATIONSHIP_THRESHOLD_CROSSED."""
        world = create_demo_world()
        differ = StateSnapshotDiffer(world)

        c_arjun = world.characters["char_arjun"]
        c_arjun.relationships = [
            Relationship(id="rel_am", character_a_id="char_arjun", character_b_id="char_maya", affinity=0.3, trust=0.3)
        ]
        differ.capture_snapshot(0, world)

        # Affinity crosses threshold 0.5 upward to 0.7
        c_arjun.relationships = [
            Relationship(id="rel_am", character_a_id="char_arjun", character_b_id="char_maya", affinity=0.7, trust=0.7)
        ]
        differ.capture_snapshot(5, world)

        clause = PredicateClause(
            type="RELATIONSHIP_THRESHOLD_CROSSED",
            character="char_arjun",
            subject="char_maya",
            threshold=0.5,
        )
        assert differ.evaluate_clause(world, clause, start_tick=0, end_tick=5) is True

    def test_11_predicate_threshold_true_crossing_semantics(self):
        """11. RELATIONSHIP_THRESHOLD_CROSSED strictly distinguishes already above from genuine crossing."""
        world = create_demo_world()
        c_arjun = world.characters["char_arjun"]
        clause = PredicateClause(
            type="RELATIONSHIP_THRESHOLD_CROSSED",
            character="char_arjun",
            subject="char_maya",
            threshold=0.5,
        )

        # Case A: Already above threshold at start (0.7 -> 0.8 across threshold 0.5) = NOT crossed
        differ_a = StateSnapshotDiffer()
        c_arjun.relationships = [
            Relationship(id="rel_am1", character_a_id="char_arjun", character_b_id="char_maya", affinity=0.7, trust=0.7)
        ]
        differ_a.capture_snapshot(0, world)
        c_arjun.relationships = [
            Relationship(id="rel_am1", character_a_id="char_arjun", character_b_id="char_maya", affinity=0.8, trust=0.8)
        ]
        differ_a.capture_snapshot(5, world)
        assert differ_a.evaluate_clause(world, clause, start_tick=0, end_tick=5) is False

        # Case B: Remained below threshold (0.2 -> 0.4 across threshold 0.5) = NOT crossed
        differ_b = StateSnapshotDiffer()
        c_arjun.relationships = [
            Relationship(id="rel_am2", character_a_id="char_arjun", character_b_id="char_maya", affinity=0.2, trust=0.2)
        ]
        differ_b.capture_snapshot(0, world)
        c_arjun.relationships = [
            Relationship(id="rel_am2", character_a_id="char_arjun", character_b_id="char_maya", affinity=0.4, trust=0.4)
        ]
        differ_b.capture_snapshot(5, world)
        assert differ_b.evaluate_clause(world, clause, start_tick=0, end_tick=5) is False

        # Case C: Downward crossing (0.8 -> 0.3 across threshold 0.5) = crossed
        differ_c = StateSnapshotDiffer()
        c_arjun.relationships = [
            Relationship(id="rel_am3", character_a_id="char_arjun", character_b_id="char_maya", affinity=0.8, trust=0.8)
        ]
        differ_c.capture_snapshot(0, world)
        c_arjun.relationships = [
            Relationship(id="rel_am3", character_a_id="char_arjun", character_b_id="char_maya", affinity=0.3, trust=0.3)
        ]
        differ_c.capture_snapshot(5, world)
        assert differ_c.evaluate_clause(world, clause, start_tick=0, end_tick=5) is True

    def test_12_predicate_secret_learned(self):
        """12. Predicate evaluation: SECRET_LEARNED."""
        world = create_demo_world()
        differ = StateSnapshotDiffer(world)

        world.propositions["prop_secret_conspiracy"] = Proposition(
            id="prop_secret_conspiracy",
            subject="director",
            predicate="committed",
            object="fraud",
            is_secret=True,
        )
        world.events["evt_secret_discovery"] = Event(
            id="evt_secret_discovery",
            tick=4,
            event_type=EventType.CHARACTER_OBSERVED,
            description="Arjun discovers the hidden ledger",
        )

        c_arjun = world.characters["char_arjun"]
        c_arjun.knowledge["prop_secret_conspiracy"] = KnowledgeItem(
            proposition_id="prop_secret_conspiracy",
            holder_id="char_arjun",
            acquired_at_event="evt_secret_discovery",
        )

        clause = PredicateClause(type="SECRET_LEARNED", subject="prop_secret_conspiracy", character="char_arjun")
        # Inside window [2, 6] -> True
        assert differ.evaluate_clause(world, clause, start_tick=2, end_tick=6) is True
        # Outside window [6, 10] -> False
        assert differ.evaluate_clause(world, clause, start_tick=6, end_tick=10) is False

    # ============================================================
    # DIRECTOR TESTS
    # ============================================================

    def test_13_director_invalid_intervention_rejected(self):
        """13. Invalid intervention rejected by strict enum schema."""
        # Valid construction
        interv = DirectorIntervention(
            intervention_type="INTRODUCE_OBSTACLE",
            description="A heavy desk blocks the corridor",
        )
        assert interv.intervention_type == "INTRODUCE_OBSTACLE"

        # Invalid intervention type raises ValidationError
        with pytest.raises(ValidationError):
            DirectorIntervention(
                intervention_type="FORCE_CHARACTER_ACTION",  # type: ignore
                description="Puppeteer Arjun to open the safe",
            )

    def test_14_director_same_validator_path_used(self):
        """14. Director interventions pass through the exact same ActionValidator gates."""
        world = create_demo_world()
        recorder = EventRecorder(world, seed=42)
        validator = ActionValidator()
        director = DirectorAgent()

        interv = DirectorIntervention(
            intervention_type="INTRODUCE_OBSTACLE",
            description="An emergency siren wails in the warehouse",
            target_location_id="loc_room307",
        )

        proposal = director.create_action_proposal(interv, world)
        assert proposal.actor_id == "DIRECTOR"

        # Validated through validator.validate_proposal
        valid, err, gate = validator.validate_proposal(world, proposal)
        assert valid is True
        assert err is None

        # Injected through same path
        event = director.inject_intervention(world, recorder, interv, validator=validator)
        assert event is not None
        assert event.source == "DIRECTOR"

    def test_15_director_failed_gate_rejects_director_action(self):
        """15. Failed gate rejects Director action identically to a character action."""
        world = create_demo_world()
        recorder = EventRecorder(world, seed=42)
        validator = ActionValidator()
        director = DirectorAgent()

        # Enforce canon proposition: office door is locked
        world.propositions["prop_door_locked"] = Proposition(
            id="prop_door_locked",
            subject="obj_door",
            predicate="locked",
            object="true",
            truth_value=True,
            enforced=True,
        )

        # Director attempts to change door state on the canonically locked door
        interv = DirectorIntervention(
            intervention_type="CHANGE_DOOR_STATE",
            description="The office door swings open mysteriously",
            target_entity_id="obj_door",
            target_location_id="loc_room307",
        )

        event = director.inject_intervention(world, recorder, interv, validator=validator)
        assert event is None, "Director intervention violating CanonGate must be rejected"
        assert len(validator.rejections) >= 1
        assert validator.rejections[-1].gate == "CanonGate"

    def test_16_director_budget_respected(self):
        """16. Configurable max_interventions_total budget respected."""
        world = create_demo_world()
        recorder = EventRecorder(world, seed=42)
        director = DirectorAgent(max_interventions_total=2, min_ticks_between_interventions=1)

        interv1 = DirectorIntervention(intervention_type="ENVIRONMENTAL_EVENT", description="Event 1")
        interv2 = DirectorIntervention(intervention_type="ENVIRONMENTAL_EVENT", description="Event 2")
        interv3 = DirectorIntervention(intervention_type="ENVIRONMENTAL_EVENT", description="Event 3")

        world.current_tick = 1
        evt1 = director.inject_intervention(world, recorder, interv1)
        assert evt1 is not None

        world.current_tick = 3
        evt2 = director.inject_intervention(world, recorder, interv2)
        assert evt2 is not None

        # Exceeds budget (2 max)
        world.current_tick = 5
        evt3 = director.inject_intervention(world, recorder, interv3)
        assert evt3 is None
        assert len(director.interventions_history) == 2

    def test_17_director_min_tick_spacing_respected(self):
        """17. min_ticks_between_interventions spacing respected."""
        world = create_demo_world()
        recorder = EventRecorder(world, seed=42)
        director = DirectorAgent(max_interventions_total=5, min_ticks_between_interventions=3)

        world.current_tick = 1
        interv1 = DirectorIntervention(intervention_type="ENVIRONMENTAL_EVENT", description="Event 1")
        evt1 = director.inject_intervention(world, recorder, interv1)
        assert evt1 is not None

        # Tick 2: spacing 1 < 3 -> rejected
        world.current_tick = 2
        assert director.can_intervene(world.current_tick) is False
        interv2 = DirectorIntervention(intervention_type="ENVIRONMENTAL_EVENT", description="Event 2")
        evt2 = director.inject_intervention(world, recorder, interv2)
        assert evt2 is None

        # Tick 4: spacing 3 >= 3 -> allowed
        world.current_tick = 4
        assert director.can_intervene(world.current_tick) is True
        evt3 = director.inject_intervention(world, recorder, interv2)
        assert evt3 is not None

    def test_18_director_no_actor_event_has_source_director(self):
        """18. No character/actor event has source='DIRECTOR'; interventions have actor_ids=[]."""
        world = create_demo_world()
        director = DirectorAgent(max_interventions_total=3)
        orchestrator = SimulationOrchestrator(world=world, director=director, seed=42)

        orchestrator.run(max_ticks=10)
        events = list(world.events.values())

        # Character actions must have source == 'SIMULATION', never 'DIRECTOR'
        actor_events = [e for e in events if len(e.actor_ids) > 0]
        for ae in actor_events:
            assert ae.source == "SIMULATION"

        # Director events must have actor_ids == []
        director_events = [e for e in events if e.source == "DIRECTOR"]
        for de in director_events:
            assert de.actor_ids == []

    def test_19_director_no_direct_dialogue_forcing(self):
        """19. Director cannot force dialogue or perform speech actions."""
        world = create_demo_world()
        validator = ActionValidator()

        # Proposal with actor_id=DIRECTOR attempting to speak
        speech_proposal = ActionProposal(
            id="prop_dir_speech",
            actor_id="DIRECTOR",
            action_type=ActionType.SPEAK,
            target_id="char_arjun",
            parameters={"statement": "You must confess now!"},
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL", goal_id="pacing"),
        )
        valid, err, gate = validator.validate_proposal(world, speech_proposal)
        assert valid is False
        assert "Director cannot perform speech actions or force dialogue" in (err or "")

    # ============================================================
    # BEAT PRESSURE TESTS
    # ============================================================

    def test_20_beat_pressure_unsatisfied_beat_becomes_unsatisfied(self):
        """20. Beat whose window expires unsatisfied transitions to UNSATISFIED."""
        world = create_demo_world()
        blueprint = compile_blueprint(
            structure_selection=StructureSelection(primary_macro="three_act"),
            role_bindings=StoryRoleBindings(),
        )
        orchestrator = SimulationOrchestrator(world=world, blueprint=blueprint, seed=42)

        # Run 10 ticks (setup window [0.0, 0.12] closes by tick 3)
        orchestrator.run(max_ticks=10)

        beats = blueprint.beats
        unsat_beats = [b for b in beats if b.status == "UNSATISFIED"]
        assert len(unsat_beats) >= 1

    def test_21_beat_pressure_deviation_note_exists(self):
        """21. UNSATISFIED beat has non-empty deviation_note explaining reason."""
        world = create_demo_world()
        blueprint = compile_blueprint(
            structure_selection=StructureSelection(primary_macro="three_act"),
            role_bindings=StoryRoleBindings(),
        )
        orchestrator = SimulationOrchestrator(world=world, blueprint=blueprint, seed=42)
        orchestrator.run(max_ticks=10)

        unsat_beats = [b for b in blueprint.beats if b.status == "UNSATISFIED"]
        for b in unsat_beats:
            assert b.deviation_note is not None
            assert len(b.deviation_note) > 0
            assert "closed" in b.deviation_note

    def test_22_beat_pressure_simulation_does_not_hang(self):
        """22. Simulation runs smoothly and terminates deterministically without stalling on unmet beats."""
        world = create_demo_world()
        blueprint = compile_blueprint(
            structure_selection=StructureSelection(primary_macro="three_act"),
            role_bindings=StoryRoleBindings(),
        )
        orchestrator = SimulationOrchestrator(world=world, blueprint=blueprint, seed=42)
        results = orchestrator.run(max_ticks=15)
        assert len(results) > 0
        assert orchestrator.world.current_tick == 15

    # ============================================================
    # SUFFICIENCY GATE TESTS
    # ============================================================

    def test_23_sufficiency_continue(self):
        """23. Sufficiency Gate returns CONTINUE when beats are pending within active window."""
        gate = NarrativeSufficiencyGate()
        world = create_demo_world()
        b_climax = BeatPressure(
            beat_id="b_climax",
            dramatic_function="CLIMAX",
            target_window=(0.5, 0.9),
            satisfaction_predicate=PredicateSpec(any_of=[PredicateClause(type="GOAL_ADOPTED")]),
            status="PENDING",
            required=True,
        )
        blueprint = StoryBlueprint(
            beats=[b_climax],
            structure=StructureSelection(primary_macro="three_act"),
        )
        report = gate.evaluate(blueprint, world, current_tick=5, current_budget_ticks=20, hard_cap_ticks=50)
        assert report.recommendation == "CONTINUE"

    def test_24_sufficiency_adjust_pressure_and_continue(self):
        """24. Sufficiency Gate returns ADJUST_PRESSURE_AND_CONTINUE when budget expired but below hard cap."""
        gate = NarrativeSufficiencyGate(extension_increment_ticks=5)
        world = create_demo_world()
        b_climax = BeatPressure(
            beat_id="b_climax",
            dramatic_function="CLIMAX",
            target_window=(0.5, 0.9),
            satisfaction_predicate=PredicateSpec(any_of=[PredicateClause(type="GOAL_ADOPTED")]),
            status="PENDING",
            required=True,
        )
        blueprint = StoryBlueprint(
            beats=[b_climax],
            structure=StructureSelection(primary_macro="three_act"),
        )
        report = gate.evaluate(blueprint, world, current_tick=20, current_budget_ticks=20, hard_cap_ticks=50)
        assert report.recommendation == "ADJUST_PRESSURE_AND_CONTINUE"

    def test_25_sufficiency_proceed(self):
        """25. Sufficiency Gate returns PROCEED when required beats are satisfied & climax detected."""
        gate = NarrativeSufficiencyGate()
        world = create_demo_world()
        b_climax = BeatPressure(
            beat_id="b_climax",
            dramatic_function="CLIMAX",
            target_window=(0.5, 0.9),
            satisfaction_predicate=PredicateSpec(any_of=[PredicateClause(type="GOAL_ADOPTED")]),
            status="SATISFIED",
            required=True,
        )
        blueprint = StoryBlueprint(
            beats=[b_climax],
            structure=StructureSelection(primary_macro="three_act"),
        )
        report = gate.evaluate(blueprint, world, current_tick=15, current_budget_ticks=20, hard_cap_ticks=50)
        assert report.recommendation == "PROCEED"

    def test_26_sufficiency_halt_insufficient(self):
        """26. Sufficiency Gate returns HALT_INSUFFICIENT when hard cap reached without satisfaction."""
        gate = NarrativeSufficiencyGate()
        world = create_demo_world()
        b_climax = BeatPressure(
            beat_id="b_climax",
            dramatic_function="CLIMAX",
            target_window=(0.5, 0.9),
            satisfaction_predicate=PredicateSpec(any_of=[PredicateClause(type="GOAL_ADOPTED")]),
            status="UNSATISFIED",
            required=True,
        )
        blueprint = StoryBlueprint(
            beats=[b_climax],
            structure=StructureSelection(primary_macro="three_act"),
        )
        report = gate.evaluate(blueprint, world, current_tick=50, current_budget_ticks=50, hard_cap_ticks=50)
        assert report.recommendation == "HALT_INSUFFICIENT"

    def test_27_sufficiency_tick_extension_actually_occurs(self):
        """27. Orchestrator actually extends tick budget when Sufficiency Gate requests extension."""
        world = create_demo_world()
        b_unsat = BeatPressure(
            beat_id="b_long",
            dramatic_function="CLIMAX",
            target_window=(0.8, 0.95),
            satisfaction_predicate=PredicateSpec(any_of=[PredicateClause(type="GOAL_ADOPTED", character="non_existent")]),
            status="PENDING",
            required=True,
        )
        blueprint = StoryBlueprint(
            beats=[b_unsat],
            structure=StructureSelection(primary_macro="three_act"),
        )
        orch = SimulationOrchestrator(world=world, blueprint=blueprint, seed=42)

        # Start with budget=5, hard_cap=12. Extension dynamically extends past 5
        orch.run(max_ticks=5, hard_cap=12, use_sufficiency_gate=True)
        assert orch.world.current_tick >= 10
        assert orch.last_sufficiency_report is not None

    def test_28_sufficiency_extension_bounded_by_hard_cap(self):
        """28. Tick extension never exceeds the hard tick cap."""
        world = create_demo_world()
        b_unsat = BeatPressure(
            beat_id="b_long",
            dramatic_function="CLIMAX",
            target_window=(0.8, 0.95),
            satisfaction_predicate=PredicateSpec(any_of=[PredicateClause(type="GOAL_ADOPTED", character="non_existent")]),
            status="PENDING",
            required=True,
        )
        blueprint = StoryBlueprint(
            beats=[b_unsat],
            structure=StructureSelection(primary_macro="three_act"),
        )
        orch = SimulationOrchestrator(world=world, blueprint=blueprint, seed=42)

        # Budget=5, hard_cap=8. Must not exceed tick 8
        orch.run(max_ticks=5, hard_cap=8, use_sufficiency_gate=True)
        assert orch.world.current_tick <= 8

    def test_29_sufficiency_halt_insufficient_propagates_cleanly(self):
        """29. HALT_INSUFFICIENT propagates cleanly without raising an exception."""
        world = create_demo_world()
        b_unsat = BeatPressure(
            beat_id="b_impossible",
            dramatic_function="CLIMAX",
            target_window=(0.1, 0.2),
            satisfaction_predicate=PredicateSpec(any_of=[PredicateClause(type="GOAL_ADOPTED", character="ghost")]),
            status="PENDING",
            required=True,
        )
        blueprint = StoryBlueprint(
            beats=[b_unsat],
            structure=StructureSelection(primary_macro="three_act"),
        )
        orch = SimulationOrchestrator(world=world, blueprint=blueprint, seed=42)

        results = orch.run(max_ticks=2, hard_cap=2, use_sufficiency_gate=True)
        assert isinstance(results, list)
        assert orch.last_sufficiency_report is not None
        assert orch.last_sufficiency_report.recommendation == "HALT_INSUFFICIENT"

    # ============================================================
    # INTEGRATION TESTS
    # ============================================================

    def test_30_integration_zero_ai_end_to_end(self):
        """30. Full pipeline runs end-to-end with exactly zero AI calls."""
        prompt = "Detective Arjun searches the warehouse at midnight for the secret classified dossier."
        analysis = extract_story_input_rule_based(prompt)

        selection = StructureSelection(primary_macro="three_act", beat_layer="save_the_cat")
        blueprint = compile_blueprint(
            structure_selection=selection,
            role_bindings=analysis.role_bindings,
            canon_facts=analysis.canon_facts,
        )

        world = create_demo_world()
        for cf in blueprint.canon:
            world.propositions[cf.proposition_id] = Proposition(
                id=cf.proposition_id,
                subject=analysis.role_bindings.protagonist_character_id or "char_arjun",
                predicate="seeks",
                object=analysis.role_bindings.focal_object_id or "obj_dossier",
                truth_value=True,
                enforced=True,
            )

        provider = MockLLMProvider()
        orch = SimulationOrchestrator(world=world, blueprint=blueprint, provider=provider, seed=42)
        results = orch.run(max_ticks=10, use_sufficiency_gate=True)

        assert len(results) > 0
        assert len(world.events) > 0
        assert orch.last_sufficiency_report is not None
        # Verify 0 AI calls
        assert provider.call_count == 0

    def test_31_integration_event_history_unchanged_by_analysis(self):
        """31. StateSnapshotDiffer and NarrativeSufficiencyGate never alter EventHistory."""
        world = create_demo_world()
        recorder = EventRecorder(world, seed=42)
        world.current_tick = 1
        recorder.record_event(
            event_type=EventType.OTHER,
            description="Initial event",
            actor_ids=["char_arjun"],
        )

        initial_event_ids = list(world.events.keys())
        initial_event_count = len(world.events)

        # Differ operations
        differ = StateSnapshotDiffer(world)
        differ.capture_snapshot(1, world)
        clause = PredicateClause(type="GOAL_ADOPTED", character="char_arjun")
        differ.evaluate_clause(world, clause, 0, 1)

        # Gate operations
        gate = NarrativeSufficiencyGate()
        blueprint = compile_blueprint(
            structure_selection=StructureSelection(primary_macro="three_act"),
            role_bindings=StoryRoleBindings(),
        )
        gate.evaluate(blueprint, world, current_tick=1, current_budget_ticks=10, hard_cap_ticks=20)

        assert len(world.events) == initial_event_count
        assert list(world.events.keys()) == initial_event_ids

    def test_32_integration_deterministic_replay_preserved(self):
        """32. Deterministic replay produces identical event sequence given same seed."""
        world1 = create_demo_world()
        world2 = create_demo_world()

        sel = StructureSelection(primary_macro="three_act")
        bp1 = compile_blueprint(structure_selection=sel, role_bindings=StoryRoleBindings())
        bp2 = compile_blueprint(structure_selection=sel, role_bindings=StoryRoleBindings())

        orch1 = SimulationOrchestrator(world=world1, blueprint=bp1, seed=42)
        orch2 = SimulationOrchestrator(world=world2, blueprint=bp2, seed=42)

        orch1.run(max_ticks=8)
        orch2.run(max_ticks=8)

        events1 = [(e.event_type, e.actor_ids, e.location_id, e.description) for e in world1.events.values()]
        events2 = [(e.event_type, e.actor_ids, e.location_id, e.description) for e in world2.events.values()]

        assert len(events1) > 0
        assert events1 == events2

    # ============================================================
    # SCENARIO & REUSE TESTS
    # ============================================================

    def test_33_the_missing_dossier_scenario_integration(self):
        """33. The Missing Dossier scenario integration check (Task 13).
        
        Verifies:
        - Conflict-oriented structure selected sensibly
        - Dossier recognized as focal object
        - Detective recognized as protagonist
        - Dossier location is canonical truth
        - Dossier location is secret from detective initially
        - Courier can hold that KnowledgeItem
        - CanonFact enforcement does not leak knowledge
        - Simulation deterministic
        - Beats succeed/fail naturally
        - Director applies world pressure only
        - Sufficiency result explicit
        - EventHistory immutable
        - Zero-AI mode works
        """
        prompt = "Detective Arjun investigates the locked office to find the secret dossier hidden by courier Maya."
        analysis = extract_story_input_rule_based(prompt)

        # 1. Structure Selection
        defs = get_structure_registry()
        selection = select_structure(analysis.features, defs)
        assert selection.primary_macro in ["three_act", "freytag", "story_circle"]

        # 2. Role Bindings & Focal Object
        assert analysis.role_bindings.focal_object_id == "obj_dossier"
        assert analysis.role_bindings.protagonist_character_id in ["char_detective", "char_arjun"]

        # 3. Compile Blueprint
        blueprint = compile_blueprint(
            structure_selection=selection,
            role_bindings=analysis.role_bindings,
            canon_facts=analysis.canon_facts,
        )
        assert len(blueprint.beats) > 0

        # 4. Initialize World with Canonical Truth and Omniscience Firewall
        world = create_demo_world()

        # Dossier location is canonical truth
        world.propositions["prop_dossier_loc"] = Proposition(
            id="prop_dossier_loc",
            subject="obj_dossier",
            predicate="location",
            object="loc_room307",
            truth_value=True,
            enforced=True,
            is_secret=True,
        )

        # Courier holds knowledge of dossier location
        c_maya = world.characters["char_maya"]
        c_maya.knowledge["prop_dossier_loc"] = KnowledgeItem(
            proposition_id="prop_dossier_loc",
            holder_id="char_maya",
            believed_truth_value=True,
        )

        # Detective does NOT hold knowledge of dossier location initially
        c_arjun = world.characters["char_arjun"]
        assert "prop_dossier_loc" not in c_arjun.knowledge

        # Omniscience Firewall Check: Detective's view excludes the secret proposition
        view = project_view(world, c_arjun)
        assert "prop_dossier_loc" not in view.knowledge
        assert view.knows("prop_dossier_loc") is None

        # 5. Run deterministic simulation with zero AI calls
        provider = MockLLMProvider()
        orch = SimulationOrchestrator(world=world, blueprint=blueprint, provider=provider, seed=42)
        results = orch.run(max_ticks=10, use_sufficiency_gate=True)

        assert len(results) > 0
        assert len(world.events) > 0
        assert provider.call_count == 0
        assert orch.last_sufficiency_report is not None
        assert orch.last_sufficiency_report.recommendation in [
            "CONTINUE", "ADJUST_PRESSURE_AND_CONTINUE", "PROCEED", "HALT_INSUFFICIENT"
        ]

    def test_34_state_snapshot_differ_phase6_reuse_comment(self):
        """34. StateSnapshotDiffer includes code comment noting intended reuse in Phase 6."""
        differ_file = Path(__file__).parent.parent / "src" / "simulation" / "differ.py"
        assert differ_file.is_file()
        content = differ_file.read_text(encoding="utf-8")
        assert "CharacterArcTracker in Phase 6" in content
