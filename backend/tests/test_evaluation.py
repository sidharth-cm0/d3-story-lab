"""Tests for NarrativeEvaluator and MultiSeedExperiment."""

from src.domain.world import WorldState, Location
from src.domain.character import Character
from src.domain.event import Event, EventType
from src.narrative.observer import NarrativeEventSelection, NarrativeBeat, NarrativeBeatType
from src.evaluation.metrics import NarrativeEvaluator
from src.evaluation.experiment import MultiSeedExperiment


class TestNarrativeEvaluator:
    def test_evaluate_simulation_metrics(self):
        world = WorldState(id="w1", name="Test World")
        loc = Location(id="loc1", name="Room", description="A room")
        world.locations[loc.id] = loc

        events = [
            Event(id="e1", tick=1, event_type=EventType.CHARACTER_MOVED, description="A moves in.", location_id="loc1"),
            Event(id="e2", tick=2, event_type=EventType.CHARACTER_SPOKE, description="A says 'Hello'.", location_id="loc1"),
            Event(id="e3", tick=3, event_type=EventType.OBJECT_PICKED_UP, description="A takes key.", location_id="loc1"),
            Event(id="e4", tick=4, event_type=EventType.OTHER, description="Knock on door.", location_id="loc1", metadata={"incident_type": "KNOCK"}),
        ]
        for e in events:
            world.events[e.id] = e
        world.current_tick = 4

        selection = NarrativeEventSelection(
            total_events_observed=4,
            filtered_beats=[
                NarrativeBeat(
                    beat_type=NarrativeBeatType.RISING_ACTION,
                    start_tick=1,
                    end_tick=4,
                    location_id="loc1",
                    dramatic_score=0.75,
                    summary="Actions unfold",
                    source_event_ids=["e1", "e2", "e3", "e4"],
                )
            ],
            dramatic_arc_summary="Arc summary",
            tension_progression=[0.75],
        )

        evaluator = NarrativeEvaluator()
        report = evaluator.evaluate_simulation(world, selection)

        assert report.total_events == 4
        assert report.total_ticks == 4
        assert 0.0 < report.action_diversity_score <= 1.0
        assert report.character_autonomy_ratio == 0.75  # 3 character events, 1 director incident
        assert report.peak_tension == 0.75
        assert report.unique_locations_visited == 1
        assert report.repetition_count == 0
        assert 0.0 < report.narrative_coherence_score <= 1.0

    def test_evaluate_empty_simulation(self):
        world = WorldState(id="w_empty", name="Empty")
        selection = NarrativeEventSelection(total_events_observed=0, filtered_beats=[])
        evaluator = NarrativeEvaluator()
        report = evaluator.evaluate_simulation(world, selection)

        assert report.total_events == 0
        assert report.action_diversity_score == 0.0


class TestMultiSeedExperiment:
    def test_multi_seed_experiment_execution(self):
        experiment = MultiSeedExperiment()
        seeds = [
            {"id": "seed_art", "prompt": "Two rival curators fight over a forgery in a gallery."},
            {"id": "seed_hotel", "prompt": "A journalist discovers an offshore ledger in a luxury suite."},
        ]

        summary = experiment.run_experiment(seeds, ticks_per_run=3)

        assert summary.total_runs == 2
        assert len(summary.runs) == 2
        assert summary.runs[0].seed_id == "seed_art"
        assert summary.runs[1].seed_id == "seed_hotel"
        assert summary.avg_action_diversity > 0.0
        assert summary.avg_coherence_score > 0.0
        for run in summary.runs:
            assert run.total_events >= 1
            assert run.report.total_ticks >= 1
