"""Smoke test script for Visual Bible, Character Reference, and Storyboard Panels.

Tests:
1. Derivation of Visual Bible and Vincent Cross character reference.
2. Compilation through StoryboardPromptCompiler (character, prop, environment).
3. CloudImagenStoryboardProvider execution (checks live API key or reports NO_API_KEY).
4. Simulated AI raster execution validating raster MIME, asset store persistence, and stable frontend URL.
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.project_store import ProjectStore
from src.storyboard.visual_bible import VisualBible
from src.storyboard.compiler import StoryboardPromptCompiler, ContinuityValidator
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.models import StoryboardPanel, ShotType, CameraAngle, ShotPurpose, StoryboardImageStatus
from src.storyboard.image_provider import (
    CloudImagenStoryboardProvider,
    MockStoryboardImageProvider,
    ProviderState,
    FallbackReason,
)

def run_smoke_test():
    print("=== D3 STORY LAB — IMAGE PIPELINE SMOKE TEST ===")
    store = ProjectStore("data/projects")
    project_id = "world_init_63aa17"
    proj = store.load_project(project_id)
    if not proj:
        print(f"Error: Project {project_id} not found!")
        return

    asset_store = StoryboardAssetStore("data/projects")
    bible = VisualBible.from_world(proj.world)
    compiler = StoryboardPromptCompiler()

    # 1. Inspect Vincent Cross character reference
    vincent_ref = bible.characters.get("char_alpha")
    print("\n--- 1. CHARACTER VISUAL REFERENCE ---")
    print(f"Name: {vincent_ref.name}")
    print(f"Role: {vincent_ref.role}")
    print(f"Prompt Snippet: {vincent_ref.prompt_snippet()}")
    print(f"Continuity Mode: TEXTUAL CONTINUITY ONLY (Google Generative Language API does not support reference image conditioning for Imagen 3)")

    # 2. Panel A: Establishing shot of abandoned industrial bay
    panel_a = StoryboardPanel(
        id="pnl_smoke_est_01",
        panel_id="pnl_smoke_est_01",
        project_id=project_id,
        scene_number=1,
        panel_number=1,
        shot_type=ShotType.WIDE,
        camera_angle=CameraAngle.EYE_LEVEL,
        narrative_purpose=ShotPurpose.ESTABLISH,
        location_id="loc_alpha",
        location_name="Abandoned Industrial Bay",
        action="Establishing shot of the cavernous abandoned industrial bay. Rain pools on cracked concrete.",
    )
    loc_ref = bible.locations.get(panel_a.location_id) or (list(bible.locations.values())[0] if bible.locations else None)
    panel_a.location_reference = loc_ref.prompt_snippet() if loc_ref else "Abandoned industrial bay"
    compiled_prompt_a = compiler.compile_panel_prompt(panel_a, bible)
    print("\n--- 2. PANEL A: ESTABLISHING SHOT ---")
    print(f"Compiled Prompt:\n{compiled_prompt_a}")

    # 3. Panel B: Vincent Cross close-up / dialogue shot with Sealed Transit Dossier
    panel_b = StoryboardPanel(
        id="pnl_smoke_dia_02",
        panel_id="pnl_smoke_dia_02",
        project_id=project_id,
        scene_number=1,
        panel_number=2,
        shot_type=ShotType.CLOSE_UP,
        camera_angle=CameraAngle.EYE_LEVEL,
        narrative_purpose=ShotPurpose.REVELATION,
        location_id="loc_alpha",
        location_name="Abandoned Industrial Bay",
        characters_present=["char_alpha"],
        character_names=["Vincent Cross"],
        objects_in_frame=["obj_dossier"],
        action="Vincent Cross holds the sealed transit dossier close to his chest.",
        dialogue_excerpt="The evidence in this file is real.",
        dialogue_bubble_type="speech",
        character_references={"Vincent Cross": vincent_ref.prompt_snippet()},
        object_references={"obj_dossier": bible.objects["obj_dossier"].prompt_snippet()} if "obj_dossier" in bible.objects else {},
    )
    compiled_prompt_b = compiler.compile_panel_prompt(panel_b, bible)
    print("\n--- 3. PANEL B: VINCENT CROSS CLOSE-UP ---")
    print(f"Compiled Prompt:\n{compiled_prompt_b}")

    # 4. Check Cloud Provider Configuration
    cloud_provider = CloudImagenStoryboardProvider(asset_store=asset_store)
    status = cloud_provider.get_status()
    print("\n--- 4. CLOUD PROVIDER STATUS ---")
    for k, v in status.items():
        print(f"{k}: {v}")

    # 5. Execute with Cloud Provider
    res_a = cloud_provider.generate_panel(panel_a, bible)
    res_b = cloud_provider.generate_panel(panel_b, bible)
    print("\n--- 5. CLOUD GENERATION RESULTS ---")
    print(f"Panel A Result: mode={res_a.mode}, status={res_a.provider_status}, fallback_reason={res_a.fallback_reason}, label={res_a.render_metadata.get('label')}")
    print(f"Panel B Result: mode={res_b.mode}, status={res_b.provider_status}, fallback_reason={res_b.fallback_reason}, label={res_b.render_metadata.get('label')}")

    # 6. Offline Mock AI Raster Test (Verifying Raster MIME & Asset Persistence)
    mock_ai = MockStoryboardImageProvider(asset_store=asset_store, simulate_ai_mode=True)
    ai_res = mock_ai.generate_panel(panel_b, bible, version=2)
    print("\n--- 6. VERIFIED RASTER ASSET GENERATION ---")
    print(f"Raster Asset URL: {ai_res.image_url}")
    print(f"MIME Type: {ai_res.mime_type}")
    print(f"Mode: {ai_res.mode} (Badge: {ai_res.render_metadata.get('label')})")
    
    # Verify file on disk
    loaded_bytes, mime = asset_store.load_asset(project_id, "panels", "pnl_smoke_dia_02_v2.png")
    print(f"Disk Persistence Verified: {len(loaded_bytes)} bytes loaded, MIME={mime}")
    assert mime == "image/png"
    assert len(loaded_bytes) > 0

    # 7. Continuity Audit on these shots
    continuity = ContinuityValidator.validate_shot_plan([panel_a, panel_b], bible)
    print("\n--- 7. CONTINUITY AUDIT ---")
    print(f"Overall Score: {continuity.score * 100}%")
    print(f"Character Consistency: {continuity.character_consistency_score * 100}%")
    print(f"Prop Tracking: {continuity.prop_tracking_score * 100}%")
    print(f"Shot Variety: {continuity.shot_variety_score * 100}%")
    print(f"Total Issues: {len(continuity.issues)}")

if __name__ == "__main__":
    run_smoke_test()
