"""Simulation engine coordinating the core execution loop"""
from typing import List, Dict, Optional, Callable
from ..domain import (
    WorldState,
    SimulationClock,
    ActionProposal,
    ActionResult,
)
from .recorder import EventRecorder
from .actions import ActionValidator, ActionExecutor
from .policy import RuleBasedPolicy


class SimulationEngine:
    """Core runtime engine driving deterministic sandbox simulation ticks"""

    def __init__(
        self,
        world: WorldState,
        clock: Optional[SimulationClock] = None,
        recorder: Optional[EventRecorder] = None,
    ):
        self.world = world
        self.clock = clock or SimulationClock(
            current_tick=world.current_tick, total_ticks=world.current_tick
        )
        self.recorder = recorder or EventRecorder(world)
        self.validator = ActionValidator()
        self.executor = ActionExecutor()

    def step(
        self,
        custom_proposals: Optional[Dict[str, ActionProposal]] = None,
        policy_fn: Optional[Callable[[WorldState, str], ActionProposal]] = None,
    ) -> List[ActionResult]:
        """Execute a single simulation tick:
        1. Query proposals for active characters (sorted deterministically by ID)
        2. Validate each proposal
        3. Execute valid proposals and log events to WorldState
        4. Advance simulation clock and synchronize WorldState.current_tick
        """
        results: List[ActionResult] = []
        active_characters = sorted(self.world.characters.keys())

        for char_id in active_characters:
            # Determine proposal
            if custom_proposals and char_id in custom_proposals:
                proposal = custom_proposals[char_id]
            elif policy_fn:
                proposal = policy_fn(self.world, char_id)
            else:
                proposal = RuleBasedPolicy.decide_action(self.world, char_id)

            # Validate and execute
            result = self.executor.execute(self.world, proposal, self.recorder)
            results.append(result)

        # Advance tick
        self.clock.advance()
        self.world.current_tick = self.clock.current_tick

        return results

    def run(
        self,
        max_ticks: int = 5,
        policy_fn: Optional[Callable[[WorldState, str], ActionProposal]] = None,
    ) -> List[ActionResult]:
        """Run simulation for multiple ticks deterministically"""
        all_results: List[ActionResult] = []
        for _ in range(max_ticks):
            tick_results = self.step(policy_fn=policy_fn)
            all_results.extend(tick_results)
        return all_results
