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
        lens_feel = (panel.lens_feel or "").lower()
        narrative_purpose = (panel.narrative_purpose or "").lower()
        sfx = panel.sfx_label or ""

        # 1. Actor Running / Walking / Turning Motion
        for idx, actor in enumerate(staged.actors):
            actor_seed = f"{seed}_actor_{idx}"
            if actor.pose == PoseType.RUNNING:
                # Speed lines trailing behind actor
                trail_x = actor.x - (actor.facing_direction * 70.0)
                trail_y = actor.y + (actor.height * 0.4)
                elements.append(
                    SpeedLines.render(
                        origin_x=trail_x,
                        origin_y=trail_y,
                        length=90.0,
                        angle_deg=180.0 if actor.facing_direction > 0 else 0.0,
                        seed=f"{actor_seed}_runner_speed",
                        num_lines=7,
                        spread_px=50.0,
                        stroke_color="#94a3b8",
                        opacity=0.65,
                    )
                )

            elif actor.pose == PoseType.WALKING:
                # Ground movement arrow under feet
                ground_y = actor.y + actor.height - 4
                ax1 = actor.x - (actor.facing_direction * 40.0)
                ax2 = actor.x + (actor.facing_direction * 35.0)
                elements.append(
                    MotionArrow.render_straight(
                        x1=ax1, y1=ground_y,
                        x2=ax2, y2=ground_y,
                        seed=f"{actor_seed}_walk_arrow",
                        arrow_color="#f59e0b",
                        stroke_width=2.2,
                        head_size=10.0,
                        opacity=0.85,
                    )
                )

            elif actor.pose == PoseType.TURNING:
                # Curved turn arrow indicating body rotation
                ty = actor.y + actor.height * 0.4
                elements.append(
                    MotionArrow.render_curved(
                        x1=actor.x - (actor.facing_direction * 35), y1=ty - 20,
                        x2=actor.x + (actor.facing_direction * 25), y2=ty + 20,
                        bend_x=actor.x + (actor.facing_direction * 45), bend_y=ty,
                        seed=f"{actor_seed}_turn_arrow",
                        arrow_color="#f59e0b",
                        stroke_width=2.2,
                        head_size=10.0,
                        opacity=0.85,
                    )
                )

        # 2. Camera Motion Annotations
        # Detect movement type
        full_context = f"{action_text} {lens_feel} {narrative_purpose}"

        has_zoom_in = "zoom in" in full_context or "push in" in lens_feel
        has_zoom_out = "zoom out" in full_context or "pull out" in lens_feel
        has_dolly_in = ("dolly in" in full_context or "dolly" in lens_feel) and not has_zoom_in
        has_dolly_out = "dolly out" in full_context or "pull back" in full_context
        has_tilt_up = "tilt up" in full_context or "crane up" in full_context
        has_tilt_down = "tilt down" in full_context or "crane down" in full_context
        has_track_left = "track left" in full_context or "pan left" in full_context
        has_track_right = "track right" in full_context or "pan right" in full_context or (
            ("pan" in full_context or "track" in full_context) and not has_track_left
        )

        badge_color = "#38bdf8"

        # A. ZOOM IN: Dashed inner frame with inward diagonal arrows
        if has_zoom_in:
            zx1, zy1 = 180.0, 100.0
            zx2, zy2 = 780.0, 440.0
            elements.append(
                f'<rect x="{zx1}" y="{zy1}" width="{zx2-zx1}" height="{zy2-zy1}" '
                f'fill="none" stroke="{badge_color}" stroke-width="1.6" stroke-dasharray="6,4" opacity="0.6"/>'
            )
            # 4 Corner inward pointers
            for (cx, cy, dx, dy) in [
                (140, 75, 40, 25),
                (820, 75, -40, 25),
                (140, 465, 40, -25),
                (820, 465, -40, -25),
            ]:
                elements.append(
                    MotionArrow.render_straight(
                        x1=cx, y1=cy, x2=cx+dx, y2=cy+dy,
                        seed=f"{seed}_zoom_in_{cx}_{cy}",
                        arrow_color=badge_color,
                        stroke_width=1.8,
                        head_size=8.0,
                        opacity=0.75,
                    )
                )
            elements.append(
                f'<g opacity="0.85">'
                f'<rect x="420" y="24" width="120" height="20" rx="3" fill="#090d16" fill-opacity="0.8" stroke="{badge_color}" stroke-width="1"/>'
                f'<text x="480" y="38" text-anchor="middle" fill="{badge_color}" font-family="monospace" font-size="10" font-weight="700" letter-spacing="1.5">ZOOM IN 🔍</text>'
                f'</g>'
            )

        # B. DOLLY IN / PUSH IN: Corner crop marks angled inward
        elif has_dolly_in:
            # 4 Corner perspective brackets pointing toward center (480, 270)
            corners = [
                (100.0, 60.0, 40.0, 25.0),
                (860.0, 60.0, -40.0, 25.0),
                (100.0, 480.0, 40.0, -25.0),
                (860.0, 480.0, -40.0, -25.0),
            ]
            for (cx, cy, dx, dy) in corners:
                elements.append(
                    MotionArrow.render_straight(
                        x1=cx, y1=cy, x2=cx+dx, y2=cy+dy,
                        seed=f"{seed}_dolly_in_{cx}_{cy}",
                        arrow_color=badge_color,
                        stroke_width=1.9,
                        head_size=9.0,
                        opacity=0.8,
                    )
                )
            elements.append(
                f'<g opacity="0.85">'
                f'<rect x="415" y="24" width="130" height="20" rx="3" fill="#090d16" fill-opacity="0.8" stroke="{badge_color}" stroke-width="1"/>'
                f'<text x="480" y="38" text-anchor="middle" fill="{badge_color}" font-family="monospace" font-size="10" font-weight="700" letter-spacing="1.5">DOLLY IN ↘ ↙</text>'
                f'</g>'
            )

        # C. TILT UP / CRANE UP
        elif has_tilt_up:
            elements.append(
                MotionArrow.render_straight(
                    x1=900.0, y1=380.0, x2=900.0, y2=160.0,
                    seed=f"{seed}_tilt_up",
                    arrow_color=badge_color,
                    stroke_width=2.2,
                    head_size=11.0,
                    opacity=0.85,
                )
            )
            # Speed ticks behind arrow tail
            for t_y in [400.0, 415.0, 430.0]:
                elements.append(
                    f'<line x1="894" y1="{t_y}" x2="906" y2="{t_y}" stroke="{badge_color}" stroke-width="1.6" opacity="0.6"/>'
                )
            elements.append(
                f'<g opacity="0.85">'
                f'<rect x="830" y="125" width="110" height="20" rx="3" fill="#090d16" fill-opacity="0.8" stroke="{badge_color}" stroke-width="1"/>'
                f'<text x="885" y="139" text-anchor="middle" fill="{badge_color}" font-family="monospace" font-size="10" font-weight="700" letter-spacing="1.2">TILT UP ↑</text>'
                f'</g>'
            )

        # D. TILT DOWN / CRANE DOWN
        elif has_tilt_down:
            elements.append(
                MotionArrow.render_straight(
                    x1=900.0, y1=160.0, x2=900.0, y2=380.0,
                    seed=f"{seed}_tilt_down",
                    arrow_color=badge_color,
                    stroke_width=2.2,
                    head_size=11.0,
                    opacity=0.85,
                )
            )
            # Speed ticks behind arrow tail
            for t_y in [140.0, 125.0, 110.0]:
                elements.append(
                    f'<line x1="894" y1="{t_y}" x2="906" y2="{t_y}" stroke="{badge_color}" stroke-width="1.6" opacity="0.6"/>'
                )
            elements.append(
                f'<g opacity="0.85">'
                f'<rect x="825" y="400" width="120" height="20" rx="3" fill="#090d16" fill-opacity="0.8" stroke="{badge_color}" stroke-width="1"/>'
                f'<text x="885" y="414" text-anchor="middle" fill="{badge_color}" font-family="monospace" font-size="10" font-weight="700" letter-spacing="1.2">TILT DOWN ↓</text>'
                f'</g>'
            )

        # E. TRACK / PAN (RIGHT or LEFT)
        elif has_track_left:
            elements.append(
                MotionArrow.render_straight(
                    x1=600.0, y1=45.0, x2=360.0, y2=45.0,
                    seed=f"{seed}_track_l",
                    arrow_color=badge_color,
                    stroke_width=2.0,
                    head_size=11.0,
                    opacity=0.85,
                )
            )
            # Speed ticks
            for t_x in [620.0, 635.0, 650.0]:
                elements.append(
                    f'<line x1="{t_x}" y1="39" x2="{t_x}" y2="51" stroke="{badge_color}" stroke-width="1.6" opacity="0.6"/>'
                )
            elements.append(
                f'<g opacity="0.85">'
                f'<rect x="410" y="24" width="140" height="20" rx="3" fill="#090d16" fill-opacity="0.8" stroke="{badge_color}" stroke-width="1"/>'
                f'<text x="480" y="38" text-anchor="middle" fill="{badge_color}" font-family="monospace" font-size="10" font-weight="700" letter-spacing="1.5">◀ TRACK LEFT</text>'
                f'</g>'
            )

        elif has_track_right:
            elements.append(
                MotionArrow.render_straight(
                    x1=360.0, y1=45.0, x2=600.0, y2=45.0,
                    seed=f"{seed}_cam_pan",
                    arrow_color=badge_color,
                    stroke_width=2.0,
                    head_size=11.0,
                    opacity=0.85,
                )
            )
            # Speed ticks behind arrow tail
            for t_x in [340.0, 325.0, 310.0]:
                elements.append(
                    f'<line x1="{t_x}" y1="39" x2="{t_x}" y2="51" stroke="{badge_color}" stroke-width="1.6" opacity="0.6"/>'
                )
            elements.append(
                f'<g opacity="0.85">'
                f'<rect x="405" y="24" width="150" height="20" rx="3" fill="#090d16" fill-opacity="0.8" stroke="{badge_color}" stroke-width="1"/>'
                f'<text x="480" y="38" text-anchor="middle" fill="{badge_color}" font-family="monospace" font-size="10" font-weight="700" letter-spacing="1.5">TRACK RIGHT ➔</text>'
                f'</g>'
            )

        # 3. SFX Impact Burst (e.g. BANG, THUD, CLICK, SLAM)
        if sfx or any(w in action_text for w in ["bang", "slam", "crash", "shoot", "drop"]):
            cx = 480.0
            cy = 270.0
            if staged.props:
                cx = staged.props[0].cx
                cy = staged.props[0].cy
            elif staged.actors:
                cx = staged.actors[0].x + 30.0
                cy = staged.actors[0].y + (staged.actors[0].height * 0.5)

            # Radiating starburst lines
            for i in range(12):
                angle = i * (360.0 / 12.0)
                rad = math.radians(angle)
                r1 = 14.0
                r2 = 32.0 + ((i % 3) * 18.0)
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
