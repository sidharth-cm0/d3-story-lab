#!/usr/bin/env python3
"""Render 5 diverse high-quality film storyboard sketch samples for Visual QA.

Generates:
1. wide.svg: Detective enters warehouse (3 depth planes, solid columns, clutter, faint guides)
2. closeup_vincent.svg: Detective questions Evelyn (30-50 strokes, expressive planes, contrapposto)
3. closeup_evelyn.svg: Evelyn lies while glancing toward dossier (evasive eyes, cheek shading)
4. insert_dossier.svg: Hand holding/opening dossier (anatomical palm wedge, thumb, paper creases)
5. action.svg: Detective runs toward vault (running dynamics, dutch tilt, speed lines)

Outputs to:
- backend/data/visual_qa/*.svg
- backend/data/visual_qa/visual_qa_report.json
"""

from __future__ import annotations
import os
import sys
import json
from pathlib import Path

# Ensure backend source is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from src.storyboard.models import (
    StoryboardPanel,
    ShotType,
    CameraAngle,
    ShotPurpose,
)
from src.storyboard.visual_bible import (
    VisualBible,
    CharacterVisualReference,
    ObjectVisualReference,
    LocationVisualReference,
)
from src.storyboard.sketch import (
    HandDrawnStoryboardProvider,
    SketchStyle,
)


def create_qa_visual_bible() -> VisualBible:
    """Create canonical visual bible references for QA test scene."""
    char_vincent = CharacterVisualReference(
        character_id="char_vincent",
        name="Vincent Cross",
        role="protagonist",
        build="tall athletic frame with broad shoulders",
        face_features="chiseled square jawline, intense focused brow",
        hair="short parted dark hair",
        clothing="charcoal tailored trench coat with popped collar",
        signature_props=["flashlight"],
    )
    char_evelyn = CharacterVisualReference(
        character_id="char_evelyn",
        name="Evelyn Vance",
        role="antagonist",
        build="slender poised athletic build",
        face_features="high zygomatic cheekbones, sharp oval jaw, guarded eyes",
        hair="slicked back dark hair",
        clothing="tailored charcoal wool suit with lapel",
        signature_props=["dossier"],
    )
    loc_wh = LocationVisualReference(
        location_id="loc_wh",
        name="Abandoned Warehouse",
        environment_type="Industrial iron warehouse",
        architecture="heavy I-beam columns with rivets, triangular roof rafters, high clerestory windows",
    )
    obj_dossier = ObjectVisualReference(
        object_id="obj_dossier",
        name="Classified Dossier",
        visual_description="thick manila folder with red stamped classified seal and brass binding clip",
    )
    obj_flashlight = ObjectVisualReference(
        object_id="obj_flashlight",
        name="Heavy Duty Flashlight",
        visual_description="machined aluminum tactical torch emitting sharp directional beam",
    )

    return VisualBible(
        characters={
            "char_vincent": char_vincent,
            "char_evelyn": char_evelyn,
        },
        locations={
            "loc_wh": loc_wh,
        },
        objects={
            "obj_dossier": obj_dossier,
            "obj_flashlight": obj_flashlight,
        },
    )


def main():
    out_dir = backend_dir / "data" / "visual_qa"
    out_dir.mkdir(parents=True, exist_ok=True)

    bible = create_qa_visual_bible()
    provider = HandDrawnStoryboardProvider(style=SketchStyle.GRAPHITE_PRODUCTION_BOARD)

    panels = [
        # 1. WIDE SHOT
        (
            "wide.svg",
            StoryboardPanel(
                id="qa_pnl_01_wide",
                panel_id="qa_pnl_01_wide",
                project_id="qa_visual_audit",
                scene_number=1,
                shot_number=1,
                shot_type=ShotType.WIDE,
                camera_angle=CameraAngle.EYE_LEVEL,
                narrative_purpose=ShotPurpose.ESTABLISH,
                location_id="loc_wh",
                location_name="Abandoned Warehouse",
                character_names=["Vincent Cross"],
                characters_present=["char_vincent"],
                action="Detective Vincent Cross steps cautiously through the iron warehouse doorway, scanning the vast interior of concrete pillars and roof rafters.",
                lighting="High contrast moonlight streaming through broken clerestory windows",
                mood="Atmospheric, tense, cautious",
            ),
        ),
        # 2. CLOSE-UP VINCENT
        (
            "closeup_vincent.svg",
            StoryboardPanel(
                id="qa_pnl_02_cu_vincent",
                panel_id="qa_pnl_02_cu_vincent",
                project_id="qa_visual_audit",
                scene_number=1,
                shot_number=2,
                shot_type=ShotType.CLOSE_UP,
                camera_angle=CameraAngle.EYE_LEVEL,
                narrative_purpose=ShotPurpose.THREAT,
                location_id="loc_wh",
                location_name="Abandoned Warehouse",
                character_names=["Vincent Cross"],
                characters_present=["char_vincent"],
                action="Detective Cross leans forward with sharp intensity, demanding the truth about the missing documents.",
                dialogue_excerpt="VINCENT: Who authorized the transfer, Evelyn?",
                lighting="Chiaroscuro single key lamp casting strong shadow on jawline",
                mood="Suspicious, commanding, intense",
            ),
        ),
        # 3. CLOSE-UP EVELYN
        (
            "closeup_evelyn.svg",
            StoryboardPanel(
                id="qa_pnl_03_cu_evelyn",
                panel_id="qa_pnl_03_cu_evelyn",
                project_id="qa_visual_audit",
                scene_number=1,
                shot_number=3,
                shot_type=ShotType.CLOSE_UP,
                camera_angle=CameraAngle.EYE_LEVEL,
                narrative_purpose=ShotPurpose.REVEAL,
                location_id="loc_wh",
                location_name="Abandoned Warehouse",
                character_names=["Evelyn Vance"],
                characters_present=["char_evelyn"],
                action="Evelyn avoids direct eye contact, speaking defensive lies while her gaze nervously darts toward the corner table.",
                dialogue_excerpt="EVELYN: I don't know what files you're talking about.",
                lighting="Subtle rim light catching cheekbone and evasive eyes",
                mood="Evasive, deceptive, guilty, guarded",
            ),
        ),
        # 4. INSERT DOSSIER
        (
            "insert_dossier.svg",
            StoryboardPanel(
                id="qa_pnl_04_insert_dossier",
                panel_id="qa_pnl_04_insert_dossier",
                project_id="qa_visual_audit",
                scene_number=1,
                shot_number=4,
                shot_type=ShotType.INSERT,
                camera_angle=CameraAngle.HIGH_ANGLE,
                narrative_purpose=ShotPurpose.DISCOVERY,
                location_id="loc_wh",
                location_name="Abandoned Warehouse",
                character_names=["Vincent Cross"],
                characters_present=["char_vincent"],
                objects_in_frame=["obj_dossier"],
                action="A gloved hand unclasps the weathered leather dossier, revealing classified surveillance photographs and stamped secret reports.",
                lighting="Direct overhead spotlight illuminating paper creases and red wax stamp",
                mood="Meticulous discovery, high stakes",
            ),
        ),
        # 5. ACTION SHOT
        (
            "action.svg",
            StoryboardPanel(
                id="qa_pnl_05_action",
                panel_id="qa_pnl_05_action",
                project_id="qa_visual_audit",
                scene_number=1,
                shot_number=5,
                shot_type=ShotType.WIDE,
                camera_angle=CameraAngle.DUTCH_ANGLE,
                narrative_purpose=ShotPurpose.ACTION,
                location_id="loc_wh",
                location_name="Abandoned Warehouse",
                character_names=["Vincent Cross"],
                characters_present=["char_vincent"],
                action="Cross sprints with desperate speed through the warehouse corridor toward the heavy steel vault as alarms flash.",
                lighting="Strobe warning light cutting through dust",
                mood="Kinetic action, urgent desperation",
            ),
        ),
    ]

    report = {
        "visual_qa_version": "2.0_graphite_production_board",
        "style": provider.style.value,
        "panels": [],
    }

    print("==================================================")
    print("D3 STORY LAB: GENERATING VISUAL QA SAMPLE PANELS")
    print("==================================================")

    for filename, panel in panels:
        res = provider.generate_panel(panel, bible=bible, version=1)
        filepath = out_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(res.svg_content)

        svg_bytes = len(res.svg_content.encode("utf-8"))
        path_count = res.svg_content.count("<path")
        polygon_count = res.svg_content.count("<polygon")
        total_drawn_elements = path_count + polygon_count

        panel_meta = {
            "filename": filename,
            "filepath": str(filepath),
            "shot_type": panel.shot_type.value,
            "camera_angle": panel.camera_angle.value,
            "characters": res.render_metadata.get("actors_rendered", []),
            "props": res.render_metadata.get("props_rendered", []),
            "environment": res.render_metadata.get("environment", ""),
            "style": res.render_metadata.get("style", ""),
            "file_size_bytes": svg_bytes,
            "file_size_kb": round(svg_bytes / 1024.0, 1),
            "path_count": path_count,
            "polygon_count": polygon_count,
            "total_drawn_elements": total_drawn_elements,
            "dutch_angle_deg": res.render_metadata.get("dutch_angle_deg", 0.0),
        }
        report["panels"].append(panel_meta)

        print(f"[OK] {filename:<22} | {panel_meta['shot_type']:<10} | {panel_meta['file_size_kb']:>6.1f} KB | {total_drawn_elements:>4} elements")

    report_path = out_dir / "visual_qa_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("--------------------------------------------------")
    print(f"Report saved to: {report_path}")
    print("Visual QA generation completed successfully.")


if __name__ == "__main__":
    main()
