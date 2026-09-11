"""End-to-end integration test for the Hotel Intrigue demo scenario."""

from src.demo_world import create_demo_world
from src.simulation.orchestrator import SimulationOrchestrator
from src.narrative.observer import Observer
from src.narrative.scribe import Scribe
from src.narrative.fountain import ScreenplayBlockType
from src.providers.mock import MockLLMProvider


class TestHotelIntrigueEndToEnd:
    def test_hotel_intrigue_full_narrative_pipeline(self):
        # 1. Initialize demo world
        world = create_demo_world()
        assert "char_arjun" in world.characters
        assert "char_maya" in world.characters
        assert "loc_room307" in world.locations
        assert world.validate_references() == []

        # 2. Run simulation in deterministic mock mode
        provider = MockLLMProvider()
        orchestrator = SimulationOrchestrator(world=world, provider=provider)

        # Run 6 ticks
        results = orchestrator.run(max_ticks=6)
        assert len(results) >= 1
        assert world.current_tick >= 1
        assert len(world.events) >= 1

        # 3. Narrative Observer filters and clusters beats
        observer = Observer(provider=provider)
        all_events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
        selection = observer.observe_events(all_events, world)

        assert selection.total_events_observed == len(all_events)
        assert len(selection.filtered_beats) >= 1

        # Check provenance
        for beat in selection.filtered_beats:
            assert len(beat.source_event_ids) >= 1
            for eid in beat.source_event_ids:
                assert eid in world.events

        # 4. Scribe generates Fountain screenplay
        scribe = Scribe(provider=provider)
        doc = scribe.compose_screenplay(selection, world, title="HOTEL INTRIGUE")

        assert doc.title == "HOTEL INTRIGUE"
        assert len(doc.scenes) >= 1
        assert "INT." in doc.scenes[0].heading

        # Check Fountain formatting
        fountain_txt = doc.to_fountain()
        assert "Title: HOTEL INTRIGUE" in fountain_txt
        assert "Author: D3 Story Lab Simulation" in fountain_txt
        assert len(fountain_txt) > 50

        # Check block provenance integrity
        prov_map = doc.get_provenance_map()
        for block_id, source_ids in prov_map.items():
            for sid in source_ids:
                assert sid in world.events
