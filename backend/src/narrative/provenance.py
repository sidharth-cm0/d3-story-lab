"""Provenance Service providing bidirectional traversal between panels, screenplay blocks, and world events."""
from __future__ import annotations
from typing import List, Optional, Set, Dict, Any
from ..domain import WorldState, Event
from .fountain import ScreenplayDocument, ScreenplayBlock
from ..storyboard.models import ShotPlan, StoryboardPanel


class ProvenanceService:
    """Bidirectional provenance index traversing World Events <-> Screenplay Blocks <-> Storyboard Panels."""

    def __init__(
        self,
        world: WorldState,
        screenplay: Optional[ScreenplayDocument] = None,
        shot_plan: Optional[ShotPlan] = None,
    ):
        self.world = world
        self.screenplay = screenplay
        self.shot_plan = shot_plan

    def events_for_block(self, block_id: str) -> List[Event]:
        """Retrieve all canonical world events that triggered a screenplay block."""
        if not self.screenplay:
            return []
        target_block = None
        for scene in self.screenplay.scenes:
            for block in scene.blocks:
                if block.id == block_id:
                    target_block = block
                    break
            if target_block:
                break
        if not target_block:
            return []

        event_ids: Set[str] = set(target_block.source_event_ids)
        if target_block.derived_from_event_id:
            event_ids.add(target_block.derived_from_event_id)

        events = [self.world.events[eid] for eid in event_ids if eid in self.world.events]
        return sorted(events, key=lambda e: (e.tick, e.id))

    def blocks_for_event(self, event_id: str) -> List[ScreenplayBlock]:
        """Retrieve all screenplay blocks generated from or derived from a specific world event."""
        if not self.screenplay:
            return []
        matching_blocks: List[ScreenplayBlock] = []
        for scene in self.screenplay.scenes:
            for block in scene.blocks:
                if event_id in block.source_event_ids or block.derived_from_event_id == event_id:
                    matching_blocks.append(block)
        return matching_blocks

    def events_for_panel(self, panel_id: str) -> List[Event]:
        """Retrieve all canonical world events that contributed to a storyboard panel.
        Traverses panel.source_event_ids directly and panel.source_screenplay_block_ids -> block.source_event_ids.
        """
        if not self.shot_plan:
            return []
        target_panel = None
        for panel in self.shot_plan.panels:
            if panel.panel_id == panel_id or panel.id == panel_id:
                target_panel = panel
                break
        if not target_panel:
            return []

        event_ids: Set[str] = set(target_panel.source_event_ids)

        # Traverse through linked screenplay blocks
        if self.screenplay:
            for block_id in target_panel.source_screenplay_block_ids:
                for ev in self.events_for_block(block_id):
                    event_ids.add(ev.id)

        events = [self.world.events[eid] for eid in event_ids if eid in self.world.events]
        return sorted(events, key=lambda e: (e.tick, e.id))

    def panels_for_event(self, event_id: str) -> List[StoryboardPanel]:
        """Retrieve all storyboard panels depicting or derived from a specific world event."""
        if not self.shot_plan:
            return []

        # Find all blocks tied to this event
        associated_block_ids = {b.id for b in self.blocks_for_event(event_id)}

        matching_panels: List[StoryboardPanel] = []
        for panel in self.shot_plan.panels:
            if event_id in panel.source_event_ids:
                matching_panels.append(panel)
            elif any(bid in associated_block_ids for bid in panel.source_screenplay_block_ids):
                matching_panels.append(panel)

        return matching_panels

    def panels_for_block(self, block_id: str) -> List[StoryboardPanel]:
        """Retrieve all storyboard panels derived from a screenplay block."""
        if not self.shot_plan:
            return []
        return [
            p for p in self.shot_plan.panels
            if block_id in p.source_screenplay_block_ids
        ]
