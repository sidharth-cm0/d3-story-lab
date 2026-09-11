"""Tests for Storyboard preparation and shot planner."""

from src.narrative.fountain import ScreenplayDocument, ScreenplayScene, ScreenplayBlock, ScreenplayBlockType
from src.domain.world import WorldState, Location
from src.domain.character import Character
from src.storyboard.models import ShotType, CameraAngle
from src.storyboard.planner import StoryboardPlanner
from src.storyboard.provider import MockStoryboardProvider


class TestStoryboardPlanner:
    def test_shot_planning_from_screenplay(self):
        world = WorldState(id="w1", name="Hotel World")
        loc = Location(id="loc_suite", name="Hotel Suite", description="High floor luxury suite")
        world.locations[loc.id] = loc
        char = Character(id="char_maya", name="Maya", role="Journalist", location_id="loc_suite")
        world.characters[char.id] = char

        screenplay = ScreenplayDocument(
            title="SUITE CONFRONTATION",
            scenes=[
                ScreenplayScene(
                    scene_number=1,
                    location_id="loc_suite",
                    heading="INT. HOTEL SUITE - NIGHT",
                    source_event_ids=["evt_01"],
                    blocks=[
                        ScreenplayBlock(
                            block_type=ScreenplayBlockType.ACTION,
                            text="Maya locks the deadbolt and checks her recorder.",
                            source_event_ids=["evt_01"],
                            character_id="char_maya",
                        ),
                        ScreenplayBlock(
                            block_type=ScreenplayBlockType.CHARACTER,
                            text="MAYA",
                            source_event_ids=["evt_02"],
                            character_id="char_maya",
                        ),
                        ScreenplayBlock(
                            block_type=ScreenplayBlockType.DIALOGUE,
                            text="Is the frequency secure?",
                            source_event_ids=["evt_02"],
                            character_id="char_maya",
                        ),
                    ],
                )
            ],
        )

        planner = StoryboardPlanner()
        shot_plan = planner.plan_shots(screenplay, world)

        assert shot_plan.project_title == "SUITE CONFRONTATION"
        assert shot_plan.total_panels == 3  # Establishing shot + Action shot + Dialogue shot

        # 1. Establishing panel
        est_panel = shot_plan.panels[0]
        assert est_panel.shot_type == ShotType.WIDE
        assert "establishing" in est_panel.visual_prompt.lower()
        assert "evt_01" in est_panel.source_event_ids

        # 2. Action panel
        action_panel = shot_plan.panels[1]
        assert "Maya locks the deadbolt" in action_panel.action_description
        assert "char_maya" in action_panel.characters_present

        # 3. Dialogue panel
        dial_panel = shot_plan.panels[2]
        assert dial_panel.dialogue_excerpt == "Is the frequency secure?"
        assert "MAYA" in dial_panel.visual_prompt

    def test_mock_storyboard_provider_render(self):
        planner = StoryboardPlanner()
        screenplay = ScreenplayDocument(
            title="TEST",
            scenes=[
                ScreenplayScene(
                    scene_number=1,
                    location_id="loc_1",
                    heading="INT. OFFICE - DAY",
                    blocks=[
                        ScreenplayBlock(
                            block_type=ScreenplayBlockType.ACTION,
                            text="Someone enters.",
                            source_event_ids=["e1"],
                        )
                    ],
                )
            ],
        )
        plan = planner.plan_shots(screenplay)
        provider = MockStoryboardProvider()

        rendered = provider.render_panel(plan.panels[0])
        assert rendered["render_type"] == "svg_placeholder"
        assert "<svg" in rendered["svg_data"]
        assert "</svg>" in rendered["svg_data"]
        assert rendered["is_mock"] is True

    def test_explicit_storyboard_panel_fields(self):
        world = WorldState(id="w_test", name="Grand Hotel")
        loc = Location(id="loc_lobby", name="Hotel Lobby", description="Marble entrance lobby")
        world.locations[loc.id] = loc
        char = Character(id="char_jordan", name="Jordan", role="Inspector", location_id="loc_lobby")
        world.characters[char.id] = char

        screenplay = ScreenplayDocument(
            title="LOBBY ARRIVAL",
            scenes=[
                ScreenplayScene(
                    scene_number=1,
                    location_id="loc_lobby",
                    heading="INT. HOTEL LOBBY - NIGHT",
                    source_event_ids=["evt_001"],
                    blocks=[
                        ScreenplayBlock(
                            id="blk_01",
                            block_type=ScreenplayBlockType.ACTION,
                            text="Jordan steps cautiously across the marble lobby.",
                            source_event_ids=["evt_001"],
                            character_id="char_jordan",
                        )
                    ],
                )
            ],
        )

        planner = StoryboardPlanner()
        shot_plan = planner.plan_shots(screenplay, world)

        assert len(shot_plan.panels) >= 2
        for panel in shot_plan.panels:
            # Check explicit clean string and list fields
            assert isinstance(panel.shot_number, int)
            assert panel.shot_number >= 1
            assert isinstance(panel.shot_type, ShotType)
            assert isinstance(panel.camera_angle, CameraAngle)
            assert panel.location_name == "Hotel Lobby"
            assert isinstance(panel.character_names, list)
            assert isinstance(panel.action, str)
            assert isinstance(panel.visual_description, str)
            assert isinstance(panel.lighting, str)
            assert len(panel.lighting) > 0
            assert isinstance(panel.mood, str)
            assert len(panel.mood) > 0
            assert isinstance(panel.prompt, str)
            assert len(panel.prompt) > 0
            assert isinstance(panel.source_screenplay_block_ids, list)
