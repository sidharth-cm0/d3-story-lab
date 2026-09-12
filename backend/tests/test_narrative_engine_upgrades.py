"""Unit and integration tests for Narrative Engine upgrades:
- Story input classification (Beginning, Midpoint, Ending, Full Concept)
- Story completion logic
- Synopsis generation
- Visual continuity models and metadata
- Shot planning with multi-page layout
- Comic graphic storyboard rendering
- Image generation adapter contract
- API endpoints (outline, synopsis, panel/page regeneration, export)
"""

import pytest
from fastapi.testclient import TestClient

from src.narrative.completion import StoryCompletionEngine, StoryInputType, StoryOutline
from src.narrative.synopsis import SynopsisGenerator, StorySynopsis
from src.domain.continuity import ActorVisualProfile, ObjectVisualProfile, LocationVisualProfile
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character
from src.narrative.fountain import ScreenplayDocument, ScreenplayScene, ScreenplayBlock, ScreenplayBlockType
from src.storyboard.models import ShotPlan, StoryboardPanel, StoryboardPage, ShotType, CameraAngle
from src.storyboard.planner import StoryboardPlanner
from src.storyboard.provider import (
    ComicGraphicStoryboardProvider,
    GeminiImageStoryboardProvider,
    MockStoryboardProvider,
)
from src.generator.initializer import WorldInitializerService
from src.api.app import create_app


class TestStoryCompletionEngine:
    def test_story_input_classification(self):
        engine = StoryCompletionEngine()

        # Beginning
        assert engine.classify_input("A man enters an abandoned building") == StoryInputType.BEGINNING
        assert engine.classify_input("She walks into the dark archives") == StoryInputType.BEGINNING

        # Midpoint
        assert engine.classify_input("A detective discovers her partner is lying") == StoryInputType.MIDPOINT
        assert engine.classify_input("He realizes the ledger was swapped") == StoryInputType.MIDPOINT

        # Ending
        assert engine.classify_input("The hero escapes the burning warehouse but loses the evidence") == StoryInputType.ENDING
        assert engine.classify_input("She survives the night and walks away into the rain") == StoryInputType.ENDING

        # Full Concept (explicit or detailed multi-sentence)
        detailed_concept = (
            "In a rain-slicked luxury penthouse, investigative journalist Maya Lin confronts diplomat Arjun Mehta "
            "regarding a confidential offshore ledger before unknown forces intervene in the shadows."
        )
        assert engine.classify_input(detailed_concept) == StoryInputType.FULL_CONCEPT

        # Declared override takes precedence
        assert engine.classify_input("Random text", declared_type="midpoint") == StoryInputType.MIDPOINT
        assert engine.classify_input("Random text", declared_type="ending") == StoryInputType.ENDING

    def test_beginning_completion_generates_middle_and_ending(self):
        engine = StoryCompletionEngine()
        seed = "A man enters an abandoned building"
        outline = engine.complete_story(seed, declared_type="beginning", target_duration_minutes=20)

        assert outline.input_type == StoryInputType.BEGINNING
        assert "Act I" in outline.act_structure["act_1"]
        assert "Act II" in outline.act_structure["act_2"]
        assert "Act III" in outline.act_structure["act_3"]
        assert outline.dramatic_question
        assert len(outline.key_scenes) == 6
        assert outline.climax
        assert outline.resolution
        assert outline.target_duration_minutes == 20

    def test_midpoint_completion_generates_beginning_and_ending(self):
        engine = StoryCompletionEngine()
        seed = "A detective discovers her partner is lying"
        outline = engine.complete_story(seed, declared_type="midpoint", target_duration_minutes=20)

        assert outline.input_type == StoryInputType.MIDPOINT
        assert "Act I" in outline.act_structure["act_1"]
        assert "Act II" in outline.act_structure["act_2"]
        assert "Act III" in outline.act_structure["act_3"]
        assert "lying" in outline.premise.lower() or "partner" in outline.premise.lower()
        assert len(outline.key_scenes) >= 5

    def test_ending_completion_generates_beginning_and_middle(self):
        engine = StoryCompletionEngine()
        seed = "The hero escapes the burning warehouse but loses the evidence"
        outline = engine.complete_story(seed, declared_type="ending", target_duration_minutes=20)

        assert outline.input_type == StoryInputType.ENDING
        assert "Act I" in outline.act_structure["act_1"]
        assert "Act II" in outline.act_structure["act_2"]
        assert "Act III" in outline.act_structure["act_3"]
        assert "escapes" in outline.premise.lower() or "evidence" in outline.premise.lower()
        assert len(outline.key_scenes) >= 5


class TestSynopsisGeneration:
    def test_synopsis_structure_and_grounding(self):
        engine = StoryCompletionEngine()
        outline = engine.complete_story("A man enters an abandoned building", declared_type="beginning")

        world = WorldState(id="w_test", name="Test World")
        world.characters["c1"] = Character(id="c1", name="Vincent", role="Explorer", location_id="loc1")
        world.characters["c2"] = Character(id="c2", name="Evelyn", role="Custodian", location_id="loc1")

        syn_gen = SynopsisGenerator()
        syn = syn_gen.generate_synopsis(outline=outline, world=world)

        assert syn.title
        assert syn.logline
        assert syn.paragraph_summary
        assert syn.full_synopsis
        assert "ACT I" in syn.full_synopsis
        assert "ACT II" in syn.full_synopsis
        assert "ACT III" in syn.full_synopsis
        assert syn.target_duration_minutes == 20
        assert "Vincent" in syn.paragraph_summary or "Vincent" in syn.logline


class TestVisualContinuityAndProfiles:
    def test_continuity_profiles_creation_and_summaries(self):
        actor_prof = ActorVisualProfile(
            character_id="char_1",
            name="Maya Lin",
            age="Early 30s",
            face_traits="Sharp jawline, observant eyes",
            hairstyle="Jet-black sleek hair",
            build="Lean athletic",
            clothing="Charcoal trench coat",
            signature_items=["Mechanical watch", "Leather notebook"],
            emotional_style="Calculating and guarded",
        )
        summary = actor_prof.summary_prompt()
        assert "Maya Lin" in summary
        assert "Charcoal trench coat" in summary
        assert "Mechanical watch" in summary

        obj_prof = ObjectVisualProfile(
            object_id="obj_1",
            name="Diplomatic Ledger",
            material="Oxblood leather",
            size="Folio",
            color="Brown",
            condition="Weathered",
            unique_markers="Red wax seal",
        )
        assert "Diplomatic Ledger" in obj_prof.summary_prompt()
        assert "Red wax seal" in obj_prof.summary_prompt()

        loc_prof = LocationVisualProfile(
            location_id="loc_1",
            name="Penthouse Suite",
            environment_type="High-rise interior",
            lighting="Chiaroscuro rain reflections",
            layout="Open executive room",
            palette="Charcoal, amber",
            mood="Tense noir",
        )
        assert "Penthouse Suite" in loc_prof.summary_prompt()
        assert "Chiaroscuro" in loc_prof.summary_prompt()

    def test_world_initializer_populates_visual_profiles(self):
        init_service = WorldInitializerService()
        plan = init_service.generate_plan("A man enters an abandoned building")
        world = init_service.instantiate_world(plan)

        # Check characters have visual profiles
        for char in world.characters.values():
            assert char.visual_profile is not None
            assert char.visual_profile.name == char.name
            assert char.visual_profile.clothing

        # Check locations have visual profiles
        for loc in world.locations.values():
            assert loc.visual_profile is not None
            assert loc.visual_profile.palette

        # Check objects have visual profiles
        for obj in world.objects.values():
            assert obj.visual_profile is not None
            assert obj.visual_profile.material


class TestStoryboardMultiPageAndRendering:
    def test_shot_plan_multi_page_grouping(self):
        screenplay = ScreenplayDocument(
            title="EPISODE 01",
            scenes=[
                ScreenplayScene(
                    scene_number=1,
                    location_id="loc_main",
                    heading="INT. ABANDONED BAY - NIGHT",
                    blocks=[
                        ScreenplayBlock(block_type=ScreenplayBlockType.ACTION, text="Vincent enters through rusted doors."),
                        ScreenplayBlock(block_type=ScreenplayBlockType.CHARACTER, text="VINCENT"),
                        ScreenplayBlock(block_type=ScreenplayBlockType.DIALOGUE, text="Anyone still here?"),
                        ScreenplayBlock(block_type=ScreenplayBlockType.ACTION, text="A shadow darts across the catwalk."),
                        ScreenplayBlock(block_type=ScreenplayBlockType.ACTION, text="Vincent raises his lantern."),
                        ScreenplayBlock(block_type=ScreenplayBlockType.CHARACTER, text="EVELYN"),
                        ScreenplayBlock(block_type=ScreenplayBlockType.DIALOGUE, text="Step back from that console."),
                    ],
                )
            ],
        )

        planner = StoryboardPlanner(panels_per_page=3)
        shot_plan = planner.plan_shots(screenplay)

        assert shot_plan.total_panels >= 5
        assert shot_plan.panels_per_page == 3
        assert shot_plan.total_pages >= 2
        assert len(shot_plan.pages) == shot_plan.total_pages

        # Check page numbers on panels
        for pnl in shot_plan.panels:
            assert pnl.page_number >= 1
            assert pnl.continuity_notes
            assert pnl.image_prompt
            assert pnl.style_tags

    def test_comic_graphic_rendering_produces_valid_svg_artwork(self):
        panel = StoryboardPanel(
            scene_number=1,
            panel_number=1,
            shot_number=1,
            page_number=1,
            shot_type=ShotType.CLOSE_UP,
            camera_angle=CameraAngle.LOW_ANGLE,
            location_name="Penthouse Suite",
            character_names=["MAYA"],
            action="MAYA: 'Where is the ledger?'",
            action_description="MAYA speaks.",
            dialogue_excerpt="Where is the ledger?",
            lighting="Chiaroscuro amber lighting",
            objects_in_frame=["dossier"],
            continuity_notes="Matches Maya trench coat and sharp profile",
        )

        provider = ComicGraphicStoryboardProvider()
        res = provider.render_panel(panel)

        assert res["render_type"] == "graphic_novel_svg"
        assert "<svg" in res["svg_data"]
        assert "</svg>" in res["svg_data"]
        assert "MAYA" in res["svg_data"]
        assert "Where is the ledger?" in res["svg_data"]
        assert res["panel_id"] == panel.id

    def test_image_adapter_contract_fallback(self):
        panel = StoryboardPanel(
            scene_number=1,
            panel_number=1,
            shot_number=1,
            shot_type=ShotType.WIDE,
            camera_angle=CameraAngle.EYE_LEVEL,
            location_name="Archive",
            action="Detective searches drawer",
        )

        adapter = GeminiImageStoryboardProvider(api_key=None)
        res = adapter.render_panel(panel)
        assert "<svg" in res["svg_data"]

    def test_insert_shot_and_macro_prop_rendering(self):
        # 1. Dossier insert
        pnl_dossier = StoryboardPanel(
            scene_number=1,
            panel_number=1,
            shot_number=1,
            shot_type=ShotType.INSERT,
            camera_angle=CameraAngle.HIGH_ANGLE,
            location_name="Executive Penthouse",
            character_names=["MAYA"],
            action="Maya examines the confidential ledger with a red seal.",
            objects_in_frame=["ledger"],
        )
        provider = ComicGraphicStoryboardProvider()
        res_dossier = provider.render_panel(pnl_dossier)
        assert "TOP SECRET" in res_dossier["svg_data"]
        assert "specularGold" in res_dossier["svg_data"]

        # 2. Transceiver insert
        pnl_transceiver = StoryboardPanel(
            scene_number=1,
            panel_number=2,
            shot_number=2,
            shot_type=ShotType.INSERT,
            camera_angle=CameraAngle.EYE_LEVEL,
            location_name="Embassy Safe House",
            character_names=["VINCENT"],
            action="Vincent powers up the encrypted transceiver.",
            objects_in_frame=["transceiver"],
        )
        res_transceiver = provider.render_panel(pnl_transceiver)
        assert "SIG: 148.55 MHz" in res_transceiver["svg_data"]

    def test_reaction_shot_and_character_continuity_rendering(self):
        pnl_reaction = StoryboardPanel(
            scene_number=1,
            panel_number=3,
            shot_number=3,
            shot_type=ShotType.REACTION,
            camera_angle=CameraAngle.DUTCH_ANGLE,
            location_name="Penthouse Suite",
            character_names=["MAYA LIN"],
            action="Maya freezes as footsteps approach the doorway.",
            character_references={
                "MAYA LIN": "Sleek dark bob cut, charcoal trench coat with turned-up lapels, sharp jaw"
            },
        )
        provider = ComicGraphicStoryboardProvider()
        res = provider.render_panel(pnl_reaction)
        assert "rotate(-3.5" in res["svg_data"]  # Dutch angle tilt
        assert "benDayDots" in res["svg_data"]

    def test_distinct_environment_architecture_rendering(self):
        provider = ComicGraphicStoryboardProvider()

        # Warehouse
        pnl_wh = StoryboardPanel(
            scene_number=1,
            panel_number=1,
            shot_number=1,
            shot_type=ShotType.WIDE,
            camera_angle=CameraAngle.EYE_LEVEL,
            location_name="Industrial Abandoned Warehouse",
            action="Establishing view of the warehouse.",
        )
        res_wh = provider.render_panel(pnl_wh)
        assert "CARGO // 44-B" in res_wh["svg_data"]

        # Vault
        pnl_vault = StoryboardPanel(
            scene_number=1,
            panel_number=2,
            shot_number=2,
            shot_type=ShotType.WIDE,
            camera_angle=CameraAngle.EYE_LEVEL,
            location_name="Secure Bank Vault",
            action="Heavy vault door stands open.",
        )
        res_vault = provider.render_panel(pnl_vault)
        assert "Vault Door" in res_vault["svg_data"] or "Vault" in res_vault["svg_data"]
        assert "Security Camera" in res_vault["svg_data"] or "circle" in res_vault["svg_data"]


class TestAPIEndpointsUpgrades:
    @pytest.fixture
    def client(self, tmp_path):
        app = create_app(store_dir=str(tmp_path))
        return TestClient(app)

    def test_project_creation_with_input_type_and_duration(self, client):
        payload = {
            "seed_prompt": "A detective discovers her partner is lying",
            "input_type": "midpoint",
            "target_duration_minutes": 20,
        }
        res = client.post("/api/projects", json=payload)
        assert res.status_code == 200
        data = res.json()
        pid = data["id"]
        assert data["input_type"] == "midpoint"
        assert data["target_duration_minutes"] == 20

        # Check outline endpoint
        out_res = client.get(f"/api/projects/{pid}/outline")
        assert out_res.status_code == 200
        outline = out_res.json()
        assert outline["input_type"] == "midpoint"
        assert "act_1" in outline["act_structure"]

        # Check synopsis endpoint
        syn_res = client.get(f"/api/projects/{pid}/synopsis")
        assert syn_res.status_code == 200
        syn = syn_res.json()
        assert syn["logline"]
        assert syn["paragraph_summary"]

    def test_screenplay_and_storyboard_regeneration_lifecycle(self, client):
        # 1. Create project
        create_res = client.post(
            "/api/projects",
            json={"seed_prompt": "A man enters an abandoned building", "input_type": "beginning"},
        )
        pid = create_res.json()["id"]

        # 2. Run simulation ticks
        run_res = client.post(f"/api/projects/{pid}/run", json={"num_ticks": 5})
        assert run_res.status_code == 200

        # 3. Generate screenplay
        scr_res = client.post(f"/api/projects/{pid}/generate-screenplay")
        assert scr_res.status_code == 200
        scr_data = scr_res.json()
        assert scr_data["total_scenes"] >= 1
        assert scr_data["total_panels"] >= 1

        # 4. Fetch storyboard
        sb_res = client.get(f"/api/projects/{pid}/storyboard")
        assert sb_res.status_code == 200
        sb_data = sb_res.json()
        panels = sb_data["shot_plan"]["panels"]
        assert len(panels) >= 1
        first_panel_id = panels[0]["id"]

        # 5. Regenerate specific panel
        regen_res = client.post(
            f"/api/projects/{pid}/storyboard/regenerate-panel",
            json={"panel_id": first_panel_id},
        )
        assert regen_res.status_code == 200
        assert regen_res.json()["panel_id"] == first_panel_id

        # 6. Regenerate specific page
        regen_page_res = client.post(
            f"/api/projects/{pid}/storyboard/regenerate-page",
            json={"page_number": 1},
        )
        assert regen_page_res.status_code == 200
        assert regen_page_res.json()["page_number"] == 1

        # 7. Test Exports
        exp_fountain = client.get(f"/api/projects/{pid}/export/screenplay")
        assert exp_fountain.status_code == 200
        assert len(exp_fountain.text) > 0

        exp_syn = client.get(f"/api/projects/{pid}/export/synopsis")
        assert exp_syn.status_code == 200
        assert "**LOGLINE**" in exp_syn.text

        exp_csv = client.get(f"/api/projects/{pid}/export/shots_csv")
        assert exp_csv.status_code == 200
        assert "Shot Type" in exp_csv.text

        exp_json = client.get(f"/api/projects/{pid}/export/shots_json")
        assert exp_json.status_code == 200
        assert "panels" in exp_json.json()
