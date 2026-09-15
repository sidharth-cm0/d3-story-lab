"""Tests for Phase 1: Foundations.
Covers deterministic seeding and replay, typed propositions and subjective belief,
bidirectional provenance traversal, project persistence and migration, and budget governance with caching.
"""

import json
from pathlib import Path
import pytest

from src.demo_world import create_demo_world
from src.domain.world import WorldState, Location, Character, WorldObject
from src.domain.event import Event, EventType, EventLog
from src.domain.proposition import Proposition, KnowledgeItem
from src.narrative.fountain import ScreenplayDocument, ScreenplayScene, ScreenplayBlock, ScreenplayBlockType
from src.storyboard.models import ShotPlan, StoryboardPanel, ShotType, CameraAngle
from src.narrative.provenance import ProvenanceService
from src.simulation.orchestrator import SimulationOrchestrator
from src.storage.project_store import ProjectStore, ProjectData, ProjectMetadata
from src.providers.budget import BudgetGovernor, BudgetExceededError, ContentHashCache
from src.storyboard.image_provider import (
    StoryboardImageProvider,
    StoryboardImageResult,
    StoryboardImageStatus,
    CachedStoryboardImageProvider,
)
from src.storyboard.visual_bible import VisualBible, StoryboardStyleProfile


class DummyImageProvider(StoryboardImageProvider):
    """Test image provider tracking invocation count."""

    def __init__(self):
        self.call_count = 0

    def get_status(self):
        return {"provider": "dummy", "calls": self.call_count}

    def generate_panel(self, panel, bible=None, version=1):
        self.call_count += 1
        return StoryboardImageResult(
            panel_id=panel.id,
            version=version,
            image_url=f"/assets/{panel.id}.png",
            svg_content="<svg></svg>",
            provider="dummy",
            mode="mock",
            compiled_prompt=panel.prompt,
            negative_prompt=panel.negative_prompt,
            status=StoryboardImageStatus.READY,
        )


class TestPhase1Foundations:

    def test_seeded_replay_produces_identical_event_history(self):
        """Rule 1.1: Running the same world with the same seed twice for 10 ticks produces byte-identical histories."""
        world1 = create_demo_world()
        orch1 = SimulationOrchestrator(world=world1, seed=42)
        orch1.run(max_ticks=10)
        log1 = orch1.get_event_log()

        world2 = create_demo_world()
        orch2 = SimulationOrchestrator(world=world2, seed=42)
        orch2.run(max_ticks=10)
        log2 = orch2.get_event_log()

        assert len(log1) >= 5, "Expected events to be recorded during 10 ticks"
        assert len(log1) == len(log2)

        # Byte-identical JSON equality
        assert log1.model_dump_json() == log2.model_dump_json()

        # Compare event-by-event IDs, ticks, descriptions, metadata
        for e1, e2 in zip(log1.events, log2.events):
            assert e1.id == e2.id
            assert e1.tick == e2.tick
            assert e1.event_type == e2.event_type
            assert e1.description == e2.description
            assert e1.actor_ids == e2.actor_ids
            assert e1.metadata == e2.metadata

    def test_different_seeds_produce_different_event_ids(self):
        """Rule 1.1: Different seeds produce distinct event IDs."""
        world1 = create_demo_world()
        orch1 = SimulationOrchestrator(world=world1, seed=42)
        orch1.run(max_ticks=2)
        log1 = orch1.get_event_log()

        world2 = create_demo_world()
        orch2 = SimulationOrchestrator(world=world2, seed=999)
        orch2.run(max_ticks=2)
        log2 = orch2.get_event_log()

        assert len(log1) == len(log2)
        ids1 = [e.id for e in log1.events]
        ids2 = [e.id for e in log2.events]
        assert ids1 != ids2

    def test_proposition_subjective_vs_objective_separation(self):
        """Rule 1.2: Character knowledge is subjective; characters never access WorldState.propositions directly."""
        world = create_demo_world()
        arjun = world.characters["char_arjun"]

        # Register objective truth in canonical world state
        prop = Proposition(
            id="prop_theft_01",
            subject="char_maya",
            predicate="stole",
            object="obj_documents",
            truth_value=True,
            is_secret=True,
        )
        world.register_proposition(prop)

        # Character does not know this proposition yet (Rule 4)
        assert arjun.knows("prop_theft_01") is None

        # Arjun is deceived / forms a false belief: truth_value=False
        arjun.acquire_knowledge(
            proposition_id="prop_theft_01",
            certainty=0.9,
            believed_truth_value=False,
            source="inferred",
        )

        knowledge_item = arjun.knows("prop_theft_01")
        assert knowledge_item is not None
        # Subjective belief is False
        assert knowledge_item.truth_value is False
        assert knowledge_item.believed_truth_value is False
        # Objective world state is True (deception / false belief supported)
        assert world.propositions["prop_theft_01"].truth_value is True
        assert world.propositions["prop_theft_01"].is_secret is True

        # Querying an unknown proposition returns None
        assert arjun.knows("prop_non_existent") is None

    def test_proposition_knowledge_sharing(self):
        """Rule 1.2: Character sharing knowledge creates a new KnowledgeItem with source='told'."""
        world = create_demo_world()
        maya = world.characters["char_maya"]
        arjun = world.characters["char_arjun"]

        prop = Proposition(
            id="prop_fraud_records",
            subject="corp_ceo",
            predicate="committed",
            object="fraud",
            truth_value=True,
            is_secret=True,
        )
        world.register_proposition(prop)

        # Maya observes the truth
        maya.acquire_knowledge(
            proposition_id="prop_fraud_records",
            certainty=1.0,
            believed_truth_value=True,
            source="observed",
            acquired_at_event="evt_obs_01",
        )

        # Maya tells Arjun
        shared_item = maya.share_knowledge(
            proposition_id="prop_fraud_records",
            recipient=arjun,
            acquired_at_event="evt_convo_02",
        )

        assert shared_item is not None
        assert arjun.knows("prop_fraud_records") is not None
        assert arjun.knows("prop_fraud_records").source == "told"
        assert arjun.knows("prop_fraud_records").source_character_id == maya.id
        assert arjun.knows("prop_fraud_records").acquired_at_event == "evt_convo_02"
        assert arjun.id in maya.knows("prop_fraud_records").shared_with

    def test_bidirectional_provenance_queries(self):
        """Rule 1.3: Bidirectional queries between Events, ScreenplayBlocks, and StoryboardPanels."""
        world = WorldState(id="w1", name="Test World")
        ev1 = Event(id="evt_001", tick=1, event_type=EventType.CHARACTER_MOVED, description="Arjun arrives")
        ev2 = Event(id="evt_002", tick=2, event_type=EventType.CHARACTER_SPOKE, description="Arjun speaks")
        world.events[ev1.id] = ev1
        world.events[ev2.id] = ev2

        blk1 = ScreenplayBlock(
            id="blk_001",
            block_type=ScreenplayBlockType.ACTION,
            text="ARJUN enters Room 307.",
            source_event_ids=["evt_001"],
        )
        blk2 = ScreenplayBlock(
            id="blk_002",
            block_type=ScreenplayBlockType.DIALOGUE,
            text="Good evening.",
            source_event_ids=["evt_002"],
        )
        scene = ScreenplayScene(
            scene_number=1,
            location_id="loc_room",
            heading="INT. ROOM 307 - NIGHT",
            blocks=[blk1, blk2],
            source_event_ids=["evt_001", "evt_002"],
        )
        screenplay = ScreenplayDocument(title="Test Doc", scenes=[scene])

        pnl1 = StoryboardPanel(
            id="pnl_001",
            panel_id="pnl_001",
            prompt="Arjun enters",
            source_screenplay_block_ids=["blk_001"],
        )
        pnl2 = StoryboardPanel(
            id="pnl_002",
            panel_id="pnl_002",
            prompt="Arjun speaking",
            source_event_ids=["evt_002"],
            source_screenplay_block_ids=["blk_002"],
        )
        shot_plan = ShotPlan(project_title="Test Project", total_panels=2, panels=[pnl1, pnl2])

        prov = ProvenanceService(world=world, screenplay=screenplay, shot_plan=shot_plan)

        # 1. Panel -> Events
        events_for_p1 = prov.events_for_panel("pnl_001")
        assert [e.id for e in events_for_p1] == ["evt_001"]

        # 2. Event -> Panels
        panels_for_e1 = prov.panels_for_event("evt_001")
        assert [p.id for p in panels_for_e1] == ["pnl_001"]

        # 3. Block -> Events
        events_for_b2 = prov.events_for_block("blk_002")
        assert [e.id for e in events_for_b2] == ["evt_002"]

        # 4. Event -> Blocks
        blocks_for_e2 = prov.blocks_for_event("evt_002")
        assert [b.id for b in blocks_for_e2] == ["blk_002"]

    def test_project_round_trip_and_media_dir(self, tmp_path):
        """Rule 1.4: Save project with schema_version, ensure media/ dir exists, load produces identical object."""
        world = create_demo_world()
        prop = Proposition(id="prop_1", subject="a", predicate="b", object="c")
        world.register_proposition(prop)
        ev_log = EventLog(events=[
            Event(id="evt_1", tick=1, event_type=EventType.OTHER, description="Init")
        ])

        meta = ProjectMetadata(
            schema_version=2,
            id="proj_alpha",
            title="Project Alpha",
            seed_prompt="A noir investigation",
        )
        project = ProjectData(
            schema_version=2,
            metadata=meta,
            world=world,
            event_log=ev_log,
        )

        store = ProjectStore(base_dir=tmp_path)
        saved_id = store.save_project(project)
        assert saved_id == "proj_alpha"

        # Check media folder was created
        media_dir = tmp_path / "media"
        assert media_dir.exists() and media_dir.is_dir()

        # Reload
        reloaded = store.load_project("proj_alpha")
        assert reloaded is not None
        assert reloaded.schema_version == 2
        assert reloaded.metadata.title == "Project Alpha"
        assert "prop_1" in reloaded.world.propositions
        assert len(reloaded.event_log.events) == 1
        assert reloaded.event_log.events[0].id == "evt_1"

    def test_project_migration_from_unversioned_v0(self, tmp_path):
        """Rule 1.4: Project without schema_version upgrades cleanly to current schema without data loss."""
        legacy_data = {
            "metadata": {
                "id": "proj_legacy",
                "title": "Legacy Project",
                "seed_prompt": "Old scenario",
            },
            "world": {
                "id": "w_legacy",
                "name": "Legacy World",
                "current_tick": 0,
                "locations": {},
                "characters": {},
                "objects": {},
                "goals": {},
                "beliefs": {},
                "secrets": {},
                "relationships": {},
                "memories": {},
                "events": {},
            },
        }
        legacy_file = tmp_path / "proj_legacy.json"
        with open(legacy_file, "w", encoding="utf-8") as f:
            json.dump(legacy_data, f)

        store = ProjectStore(base_dir=tmp_path)
        loaded = store.load_project("proj_legacy")
        assert loaded is not None
        assert loaded.schema_version == 2
        assert loaded.metadata.schema_version == 2
        assert loaded.metadata.title == "Legacy Project"
        assert loaded.world.id == "w_legacy"
        assert loaded.world.propositions == {}

    def test_budget_governor_enforces_hard_limits(self):
        """Rule 1.5: BudgetGovernor tracks tokens/panels/cost and raises BudgetExceededError when limits hit."""
        gov = BudgetGovernor(
            max_tokens=500,
            max_panels=2,
            max_cost_usd=0.05,
            cost_per_1k_tokens=0.01,
            cost_per_panel=0.02,
        )

        # Charge tokens within budget
        gov.charge_tokens(300)
        assert gov.total_tokens == 300
        assert gov.estimated_cost_usd == pytest.approx(0.003)

        # Exceed tokens
        with pytest.raises(BudgetExceededError, match="Token budget exceeded"):
            gov.charge_tokens(300)

        # Charge panels
        gov.charge_panel()
        gov.charge_panel()
        assert gov.total_panels == 2

        # Exceed panels
        with pytest.raises(BudgetExceededError, match="Panel budget exceeded"):
            gov.charge_panel()

    def test_content_hash_cache_prevents_duplicate_provider_calls(self):
        """Rule 1.5: Identical shot prompts return cached panel without invoking image provider or charging budget."""
        dummy = DummyImageProvider()
        cache = ContentHashCache()
        gov = BudgetGovernor(max_panels=10)

        cached_provider = CachedStoryboardImageProvider(
            provider=dummy,
            cache=cache,
            budget_governor=gov,
        )

        panel = StoryboardPanel(
            id="pnl_test_01",
            prompt="A detective stands under a flickering streetlight, rain pouring down",
            compiled_prompt="A detective stands under a flickering streetlight, rain pouring down",
            aspect_ratio="16:9",
        )
        bible = VisualBible(style_profile=StoryboardStyleProfile(prompt_prefix="film noir"))

        # 1st call -> Cache miss, calls provider, charges budget
        res1 = cached_provider.generate_panel(panel, bible=bible)
        assert dummy.call_count == 1
        assert gov.total_panels == 1
        assert cache.size == 1

        # 2nd call with identical prompt/style -> Cache hit, provider NOT called, budget NOT charged
        res2 = cached_provider.generate_panel(panel, bible=bible)
        assert dummy.call_count == 1  # Still 1!
        assert gov.total_panels == 1  # Still 1!
        assert res1.image_url == res2.image_url
