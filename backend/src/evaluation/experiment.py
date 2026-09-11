"""Multi-seed experimentation harness for comparing simulation runs."""

from __future__ import annotations
from typing import List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from src.generator.initializer import WorldInitializerService
from src.simulation.orchestrator import SimulationOrchestrator
from src.narrative.observer import Observer
from src.narrative.scribe import Scribe
from src.evaluation.metrics import NarrativeEvaluator, SimulationReport
from src.providers.base import LLMProvider
from src.providers.mock import MockLLMProvider


class ExperimentRunResult(BaseModel):
    """Result of a single experiment seed run."""
    model_config = ConfigDict(frozen=True)

    seed_id: str
    seed_prompt: str
    total_events: int
    total_scenes: int
    report: SimulationReport


class ExperimentSummary(BaseModel):
    """Comparative summary across multiple seed runs."""
    model_config = ConfigDict(frozen=True)

    total_runs: int
    avg_action_diversity: float
    avg_autonomy_ratio: float
    avg_coherence_score: float
    runs: List[ExperimentRunResult]


class MultiSeedExperiment:
    """Runs batch simulation experiments to evaluate narrative stability and emergence."""

    def __init__(self, provider: LLMProvider | None = None):
        self.provider = provider or MockLLMProvider()
        self.initializer = WorldInitializerService(provider=self.provider)
        self.observer = Observer(provider=self.provider)
        self.scribe = Scribe(provider=self.provider)
        self.evaluator = NarrativeEvaluator()

    def run_experiment(
        self,
        seeds: List[Dict[str, str]],
        ticks_per_run: int = 5,
    ) -> ExperimentSummary:
        """Run each seed through initialization, simulation, observation, and evaluation."""
        run_results: List[ExperimentRunResult] = []

        for item in seeds:
            seed_id = item.get("id", "seed")
            prompt = item.get("prompt", "")

            # 1. Initialize
            plan = self.initializer.generate_plan(prompt)
            world = self.initializer.instantiate_world(plan)

            # 2. Simulate
            orchestrator = SimulationOrchestrator(world=world, provider=self.provider)
            orchestrator.run(max_ticks=ticks_per_run)

            # 3. Observe
            events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
            selection = self.observer.observe_events(events, world)

            # 4. Scribe
            screenplay = self.scribe.compose_screenplay(selection, world)

            # 5. Evaluate
            report = self.evaluator.evaluate_simulation(world, selection)

            run_results.append(
                ExperimentRunResult(
                    seed_id=seed_id,
                    seed_prompt=prompt,
                    total_events=len(world.events),
                    total_scenes=len(screenplay.scenes),
                    report=report,
                )
            )

        if not run_results:
            return ExperimentSummary(
                total_runs=0,
                avg_action_diversity=0.0,
                avg_autonomy_ratio=0.0,
                avg_coherence_score=0.0,
                runs=[],
            )

        avg_div = round(sum(r.report.action_diversity_score for r in run_results) / len(run_results), 3)
        avg_aut = round(sum(r.report.character_autonomy_ratio for r in run_results) / len(run_results), 3)
        avg_coh = round(sum(r.report.narrative_coherence_score for r in run_results) / len(run_results), 3)

        return ExperimentSummary(
            total_runs=len(run_results),
            avg_action_diversity=avg_div,
            avg_autonomy_ratio=avg_aut,
            avg_coherence_score=avg_coh,
            runs=run_results,
        )
