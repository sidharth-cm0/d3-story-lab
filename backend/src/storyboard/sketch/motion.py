"""Traditional storyboard motion language and camera annotations.

Generates actor movement arrows, camera direction cues, speed lines,
and impact bursts to depict dynamic narrative action.
"""

from __future__ import annotations
import math
from typing import Optional, List
from src.storyboard.models import StoryboardPanel, CameraAngle
from src.storyboard.sketch.staging import StagedScene
from src.storyboard.sketch.pose import PoseType
from src.storyboard.sketch.stroke import (
    MotionArrow,
    SpeedLines,
    SketchStroke,
    SketchPolygon,
    get_rng,
)


class MotionSketchRenderer:
    """Renders storyboard motion arrows, speed lines, and camera annotations."""

    @staticmethod
    def render_motion(
        panel: StoryboardPanel,
        staged: StagedScene,
        seed: str = "motion",
    ) -> str:
        elements: List[str] = []
        action_text = (panel.action_description or panel.action or "").lower()
        sfx = panel.sfx_label or ""

        # 1. Actor Running Speed Lines
        for actor in staged.actors:
            if actor.pose == PoseType.RUNNING:
                # Speed lines trailing behind actor
                trail_x = actor.x - (actor.facing_direction * 70.0)
                trail_y = actor.y + (actor.height * 0.4)
                elements.append(
                    SpeedLines.render(
                        origin_x=trail_x,
                        origin_y=trail_y,
                        length=80.0,
                        angle_deg=180.0 if actor.facing_direction > 0 else 0.0,
                        seed=f"{seed}_runner_speed",
                        num_lines=6,
                        spread_px=45.0,
                        stroke_color="#94a3b8",
                        opacity=0.65,
                    )
                )

            elif actor.pose == PoseType.WALKING:
                # Ground movement arrow under feet
                ground_y = actor.y + actor.height - 4
                ax1 = actor.x - (actor.facing_direction * 40.0)
                ax2 = actor.x + (actor.facing_direction * 30.0)
                elements.append(
                    MotionArrow.render_straight(
                        x1=ax1, y1=ground_y,
                        x2=ax2, y2=ground_y,
                        seed=f"{seed}_walk_arrow",
                        arrow_color="#f59e0b",
                        stroke_width=2.2,
                        head_size=10.0,
                        opacity=0.85,
                    )
                )

            elif actor.pose == PoseType.TURNING:
                # Curved turn arrow
                ty = actor.y + actor.height * 0.4
                elements.append(
                    MotionArrow.render_curved(
                        x1=actor.x - (actor.facing_direction * 35), y1=ty - 20,
                        x2=actor.x + (actor.facing_direction * 25), y2=ty + 20,
                        bend_x=actor.x + (actor.facing_direction * 45), bend_y=ty,
                        seed=f"{seed}_turn_arrow",
                        arrow_color="#f59e0b",
                        stroke_width=2.2,
                        head_size=10.0,
                        opacity=0.85,
                    )
                )

        # 2. Camera Motion Annotations
        lens_feel = panel.lens_feel.lower()
        if "pan" in action_text or "track" in action_text or "dolly" in lens_feel:
            # Top frame camera tracking arrow
            elements.append(
                MotionArrow.render_straight(
                    x1=340.0, y1=45.0,
                    x2=620.0, y2=45.0,
                    seed=f"{seed}_cam_pan",
                    arrow_color="#38bdf8",
                    stroke_width=2.0,
                    head_size=11.0,
                    opacity=0.85,
                )
            )
            elements.append(
                f'<text x="480" y="38" text-anchor="middle" fill="#38bdf8" '
                f'font-family="monospace" font-size="11" font-weight="700" letter-spacing="1.5">TRACK / PAN ➔</text>'
            )

        # 3. SFX Impact Burst (e.g. BANG, THUD, CLICK)
        if sfx or any(w in action_text for w in ["bang", "slam", "crash", "shoot", "drop"]):
            # Starburst impact lines
            cx = 480.0
            cy = 270.0
            if staged.props:
                cx = staged.props[0].cx
                cy = staged.props[0].cy
            elif staged.actors:
                cx = staged.actors[0].x + 30.0
                cy = staged.actors[0].y + (staged.actors[0].height * 0.5)

            for i in range(8):
                angle = i * (360.0 / 8.0)
                rad = math.radians(angle)
                r1 = 12.0
                r2 = 28.0 + ((i % 2) * 16.0)
                p1x = cx + math.cos(rad) * r1
                p1y = cy + math.sin(rad) * r1
                p2x = cx + math.cos(rad) * r2
                p2y = cy + math.sin(rad) * r2
                elements.append(
                    SketchStroke.render_line(
                        p1x, p1y, p2x, p2y,
                        seed=f"{seed}_impact_{i}",
                        stroke_color="#ef4444",
                        stroke_width=2.4,
                        opacity=0.9,
                        passes=1,
                    )
                )

        return "\n  ".join(elements)
