"""Deterministic hand-drawn sketch primitives for SVG storyboard rendering.

Provides organic, jittered strokes, cross-hatching, scribble shading,
perspective grids, speed lines, and motion arrows with deterministic PRNG seeding.
"""

from __future__ import annotations
import math
import hashlib
import random
from typing import List, Tuple, Optional, Dict, Any


def get_seed_hash(seed_str: str) -> int:
    """Generate a consistent 32-bit integer seed from any arbitrary string."""
    return int(hashlib.md5(seed_str.encode("utf-8")).hexdigest()[:8], 16)


def get_rng(seed_str: str) -> random.Random:
    """Return a deterministic Random generator instance for a specific element seed."""
    return random.Random(get_seed_hash(seed_str))


class SketchStroke:
    """Hand-drawn stroke generator that creates 1-3 organic, slightly offset lines.
    
    Simulates a storyboard artist's graphite pencil or ink brush with variable jitter,
    curving control points, and overlapping passes.
    """

    @staticmethod
    def render_line(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        seed: str,
        stroke_color: str = "#d1d5db",
        stroke_width: float = 1.6,
        opacity: float = 0.85,
        passes: int = 2,
        jitter_amount: float = 1.2,
    ) -> str:
        """Render a hand-drawn line connecting (x1, y1) to (x2, y2) with jittered passes."""
        rng = get_rng(seed)
        paths = []
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 0.5:
            return ""

        # Normal vector for lateral jitter
        nx = -dy / dist
        ny = dx / dist

        for p in range(passes):
            p_seed = f"{seed}_pass{p}"
            p_rng = get_rng(p_seed)

            # Jitter start and end points slightly
            start_j = (p_rng.random() - 0.5) * jitter_amount * 0.8
            end_j = (p_rng.random() - 0.5) * jitter_amount * 0.8

            sx = x1 + nx * start_j
            sy = y1 + ny * start_j
            ex = x2 + nx * end_j
            ey = y2 + ny * end_j

            # Intermediate cubic bezier control points for hand tremor
            c1_j = (p_rng.random() - 0.5) * jitter_amount * 1.8
            c2_j = (p_rng.random() - 0.5) * jitter_amount * 1.8

            c1x = x1 + (dx * 0.33) + nx * c1_j
            c1y = y1 + (dy * 0.33) + ny * c1_j
            c2x = x1 + (dx * 0.66) + nx * c2_j
            c2y = y1 + (dy * 0.66) + ny * c2_j

            p_width = max(0.5, stroke_width + (p_rng.random() - 0.5) * 0.5)
            p_opacity = max(0.2, min(1.0, opacity * (0.8 + p_rng.random() * 0.3)))

            d = f"M {sx:.1f} {sy:.1f} C {c1x:.1f} {c1y:.1f}, {c2x:.1f} {c2y:.1f}, {ex:.1f} {ey:.1f}"
            paths.append(
                f'<path d="{d}" fill="none" stroke="{stroke_color}" stroke-width="{p_width:.2f}" '
                f'stroke-linecap="round" stroke-linejoin="round" opacity="{p_opacity:.2f}"/>'
            )

        return "\n  ".join(paths)


class SketchPolyline:
    """Hand-drawn polyline with organic corner rounding and offset graphite passes."""

    @staticmethod
    def render(
        points: List[Tuple[float, float]],
        seed: str,
        stroke_color: str = "#e2e8f0",
        stroke_width: float = 1.5,
        opacity: float = 0.8,
        closed: bool = False,
        passes: int = 2,
    ) -> str:
        if len(points) < 2:
            return ""

        output = []
        for i in range(len(points) - (0 if closed else 1)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            seg_seed = f"{seed}_seg_{i}"
            line_svg = SketchStroke.render_line(
                p1[0], p1[1], p2[0], p2[1],
                seed=seg_seed,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                opacity=opacity,
                passes=passes,
            )
            if line_svg:
                output.append(line_svg)

        return "\n  ".join(output)


class SketchPolygon:
    """Hand-drawn filled or framed polygon with organic contour strokes."""

    @staticmethod
    def render(
        points: List[Tuple[float, float]],
        seed: str,
        fill_color: Optional[str] = None,
        fill_opacity: float = 0.4,
        stroke_color: str = "#cbd5e1",
        stroke_width: float = 1.5,
        stroke_opacity: float = 0.85,
    ) -> str:
        if len(points) < 3:
            return ""

        elements = []
        # Render base fill shape if requested
        if fill_color and fill_color != "none":
            pts_str = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in points)
            elements.append(
                f'<polygon points="{pts_str}" fill="{fill_color}" fill-opacity="{fill_opacity:.2f}"/>'
            )

        # Render organic sketched outline
        outline = SketchPolyline.render(
            points=points,
            seed=seed,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            opacity=stroke_opacity,
            closed=True,
            passes=2,
        )
        if outline:
            elements.append(outline)

        return "\n  ".join(elements)


class SketchEllipse:
    """Hand-drawn circle or ellipse rendered with overlapping loose artist loops."""

    @staticmethod
    def render(
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        seed: str,
        stroke_color: str = "#cbd5e1",
        stroke_width: float = 1.5,
        opacity: float = 0.85,
        fill_color: Optional[str] = None,
        fill_opacity: float = 0.3,
        loops: int = 2,
    ) -> str:
        rng = get_rng(seed)
        elements = []

        if fill_color and fill_color != "none":
            elements.append(
                f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
                f'fill="{fill_color}" fill-opacity="{fill_opacity:.2f}"/>'
            )

        k = 0.5522847
        for l in range(loops):
            l_seed = f"{seed}_loop{l}"
            l_rng = get_rng(l_seed)

            # Slight radius and center variance per loop
            dcx = (l_rng.random() - 0.5) * 1.5
            dcy = (l_rng.random() - 0.5) * 1.5
            lrx = rx + (l_rng.random() - 0.5) * 1.8
            lry = ry + (l_rng.random() - 0.5) * 1.8

            kx = lrx * k
            ky = lry * k

            p0 = (cx + dcx, cy + dcy - lry + (l_rng.random() - 0.5) * 1.0)
            p1 = (cx + dcx + lrx + (l_rng.random() - 0.5) * 1.0, cy + dcy)
            p2 = (cx + dcx, cy + dcy + lry + (l_rng.random() - 0.5) * 1.0)
            p3 = (cx + dcx - lrx + (l_rng.random() - 0.5) * 1.0, cy + dcy)

            d = (
                f"M {p0[0]:.1f} {p0[1]:.1f} "
                f"C {p0[0] + kx:.1f} {p0[1]:.1f}, {p1[0]:.1f} {p1[1] - ky:.1f}, {p1[0]:.1f} {p1[1]:.1f} "
                f"C {p1[0]:.1f} {p1[1] + ky:.1f}, {p2[0] + kx:.1f} {p2[1]:.1f}, {p2[0]:.1f} {p2[1]:.1f} "
                f"C {p2[0] - kx:.1f} {p2[1]:.1f}, {p3[0]:.1f} {p3[1] + ky:.1f}, {p3[0]:.1f} {p3[1]:.1f} "
                f"C {p3[0]:.1f} {p3[1] - ky:.1f}, {p0[0] - kx:.1f} {p0[1]:.1f}, {p0[0] + (l_rng.random()-0.5)*3:.1f} {p0[1] + (l_rng.random()-0.5)*3:.1f}"
            )
            l_width = max(0.6, stroke_width + (l_rng.random() - 0.5) * 0.4)
            l_op = max(0.3, min(1.0, opacity * (0.8 + l_rng.random() * 0.3)))
            elements.append(
                f'<path d="{d}" fill="none" stroke="{stroke_color}" stroke-width="{l_width:.2f}" '
                f'stroke-linecap="round" opacity="{l_op:.2f}"/>'
            )

        return "\n  ".join(elements)


class CrossHatch:
    """Dense layered diagonal cross-hatching for chiaroscuro shadow regions."""

    @staticmethod
    def render(
        x: float,
        y: float,
        width: float,
        height: float,
        seed: str,
        spacing: float = 9.0,
        angle_deg: float = 45.0,
        double_hatch: bool = True,
        stroke_color: str = "#94a3b8",
        stroke_width: float = 0.9,
        opacity: float = 0.65,
    ) -> str:
        rng = get_rng(seed)
        lines = []

        rad1 = math.radians(angle_deg)
        cos1 = math.cos(rad1)
        sin1 = math.sin(rad1)

        extent = width + height
        count = int(extent / max(3.0, spacing))

        for i in range(count):
            offset = (i - count // 2) * spacing
            cx = x + width / 2 + offset * cos1
            cy = y + height / 2 + offset * sin1

            lx1 = cx - 0.6 * extent * sin1
            ly1 = cy + 0.6 * extent * cos1
            lx2 = cx + 0.6 * extent * sin1
            ly2 = cy - 0.6 * extent * cos1

            lx1 = max(x, min(x + width, lx1))
            ly1 = max(y, min(y + height, ly1))
            lx2 = max(x, min(x + width, lx2))
            ly2 = max(y, min(y + height, ly2))

            if math.hypot(lx2 - lx1, ly2 - ly1) > 4:
                seg_seed = f"{seed}_hatch1_{i}"
                lines.append(
                    SketchStroke.render_line(
                        lx1, ly1, lx2, ly2,
                        seed=seg_seed,
                        stroke_color=stroke_color,
                        stroke_width=stroke_width,
                        opacity=opacity,
                        passes=1,
                        jitter_amount=0.8,
                    )
                )

        if double_hatch:
            rad2 = math.radians(angle_deg + 80.0)
            cos2 = math.cos(rad2)
            sin2 = math.sin(rad2)
            spacing2 = spacing * 1.3
            count2 = int(extent / max(3.0, spacing2))

            for i in range(count2):
                offset = (i - count2 // 2) * spacing2
                cx = x + width / 2 + offset * cos2
                cy = y + height / 2 + offset * sin2

                lx1 = cx - 0.5 * extent * sin2
                ly1 = cy + 0.5 * extent * cos2
                lx2 = cx + 0.5 * extent * sin2
                ly2 = cy - 0.5 * extent * cos2

                lx1 = max(x, min(x + width, lx1))
                ly1 = max(y, min(y + height, ly1))
                lx2 = max(x, min(x + width, lx2))
                ly2 = max(y, min(y + height, ly2))

                if math.hypot(lx2 - lx1, ly2 - ly1) > 5:
                    seg_seed = f"{seed}_hatch2_{i}"
                    lines.append(
                        SketchStroke.render_line(
                            lx1, ly1, lx2, ly2,
                            seed=seg_seed,
                            stroke_color=stroke_color,
                            stroke_width=stroke_width * 0.85,
                            opacity=opacity * 0.8,
                            passes=1,
                            jitter_amount=0.8,
                        )
                    )

        return "\n  ".join(lines)


class ScribbleShadow:
    """Rough organic scribble shading simulating quick pencil fill."""

    @staticmethod
    def render(
        x: float,
        y: float,
        width: float,
        height: float,
        seed: str,
        density: int = 12,
        stroke_color: str = "#64748b",
        stroke_width: float = 1.1,
        opacity: float = 0.55,
    ) -> str:
        rng = get_rng(seed)
        step_y = height / max(1, density)
        pts = []

        for row in range(density + 1):
            cy = y + row * step_y + (rng.random() - 0.5) * 2.0
            if row % 2 == 0:
                cx = x + width + (rng.random() - 0.5) * 3.0
            else:
                cx = x + (rng.random() - 0.5) * 3.0
            pts.append((cx, cy))

        d_parts = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
        for i in range(1, len(pts)):
            prev = pts[i - 1]
            curr = pts[i]
            c1x = (prev[0] + curr[0]) / 2 + (rng.random() - 0.5) * 4.0
            c1y = (prev[1] + curr[1]) / 2 + (rng.random() - 0.5) * 4.0
            d_parts.append(f"Q {c1x:.1f} {c1y:.1f}, {curr[0]:.1f} {curr[1]:.1f}")

        d = " ".join(d_parts)
        return (
            f'<path d="{d}" fill="none" stroke="{stroke_color}" stroke-width="{stroke_width:.2f}" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="{opacity:.2f}"/>'
        )


class PerspectiveGrid:
    """Perspective grid with convergence toward a vanishing point."""

    @staticmethod
    def render(
        vp_x: float,
        vp_y: float,
        bottom_y: float,
        width: float,
        seed: str,
        num_radials: int = 9,
        num_horizontals: int = 5,
        stroke_color: str = "#475569",
        stroke_width: float = 1.0,
        opacity: float = 0.5,
    ) -> str:
        lines = []
        step_x = width / max(1, (num_radials - 1))
        for i in range(num_radials):
            bx = i * step_x
            line_seed = f"{seed}_vp_rad_{i}"
            lines.append(
                SketchStroke.render_line(
                    vp_x, vp_y, bx, bottom_y,
                    seed=line_seed,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    opacity=opacity,
                    passes=1,
                    jitter_amount=0.9,
                )
            )

        for j in range(1, num_horizontals + 1):
            t = (j / num_horizontals) ** 2.2
            hy = vp_y + (bottom_y - vp_y) * t
            w_at_h = width * t
            x_left = vp_x - (w_at_h / 2)
            x_right = vp_x + (w_at_h / 2)

            line_seed = f"{seed}_vp_horiz_{j}"
            lines.append(
                SketchStroke.render_line(
                    x_left, hy, x_right, hy,
                    seed=line_seed,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width * (0.6 + 0.4 * t),
                    opacity=opacity * (0.4 + 0.6 * t),
                    passes=1,
                    jitter_amount=0.8,
                )
            )

        return "\n  ".join(lines)


class MotionArrow:
    """Hand-drawn directional storyboard arrow for actor movement or camera cues."""

    @staticmethod
    def render_straight(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        seed: str,
        arrow_color: str = "#f59e0b",
        stroke_width: float = 2.4,
        head_size: float = 12.0,
        opacity: float = 0.9,
    ) -> str:
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 5.0:
            return ""

        shaft = SketchStroke.render_line(
            x1, y1, x2, y2,
            seed=f"{seed}_shaft",
            stroke_color=arrow_color,
            stroke_width=stroke_width,
            opacity=opacity,
            passes=2,
            jitter_amount=1.0,
        )

        angle = math.atan2(dy, dx)
        wing_angle = math.radians(28.0)

        w1x = x2 - head_size * math.cos(angle - wing_angle)
        w1y = y2 - head_size * math.sin(angle - wing_angle)
        w2x = x2 - head_size * math.cos(angle + wing_angle)
        w2y = y2 - head_size * math.sin(angle + wing_angle)

        wing1 = SketchStroke.render_line(
            x2, y2, w1x, w1y,
            seed=f"{seed}_w1",
            stroke_color=arrow_color,
            stroke_width=stroke_width,
            opacity=opacity,
            passes=2,
            jitter_amount=0.8,
        )
        wing2 = SketchStroke.render_line(
            x2, y2, w2x, w2y,
            seed=f"{seed}_w2",
            stroke_color=arrow_color,
            stroke_width=stroke_width,
            opacity=opacity,
            passes=2,
            jitter_amount=0.8,
        )

        return f"{shaft}\n  {wing1}\n  {wing2}"

    @staticmethod
    def render_curved(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        bend_x: float,
        bend_y: float,
        seed: str,
        arrow_color: str = "#f59e0b",
        stroke_width: float = 2.4,
        head_size: float = 12.0,
        opacity: float = 0.9,
    ) -> str:
        d = f"M {x1:.1f} {y1:.1f} Q {bend_x:.1f} {bend_y:.1f}, {x2:.1f} {y2:.1f}"
        curve_path = (
            f'<path d="{d}" fill="none" stroke="{arrow_color}" stroke-width="{stroke_width:.2f}" '
            f'stroke-linecap="round" opacity="{opacity:.2f}"/>'
        )

        dx = x2 - bend_x
        dy = y2 - bend_y
        angle = math.atan2(dy, dx)
        wing_angle = math.radians(28.0)

        w1x = x2 - head_size * math.cos(angle - wing_angle)
        w1y = y2 - head_size * math.sin(angle - wing_angle)
        w2x = x2 - head_size * math.cos(angle + wing_angle)
        w2y = y2 - head_size * math.sin(angle + wing_angle)

        wing1 = SketchStroke.render_line(
            x2, y2, w1x, w1y,
            seed=f"{seed}_cw1",
            stroke_color=arrow_color,
            stroke_width=stroke_width,
            opacity=opacity,
            passes=2,
        )
        wing2 = SketchStroke.render_line(
            x2, y2, w2x, w2y,
            seed=f"{seed}_cw2",
            stroke_color=arrow_color,
            stroke_width=stroke_width,
            opacity=opacity,
            passes=2,
        )

        return f"{curve_path}\n  {wing1}\n  {wing2}"


class SpeedLines:
    """Action speed lines emanating from a subject or along a motion vector."""

    @staticmethod
    def render(
        origin_x: float,
        origin_y: float,
        length: float,
        angle_deg: float,
        seed: str,
        num_lines: int = 7,
        spread_px: float = 30.0,
        stroke_color: str = "#e2e8f0",
        stroke_width: float = 1.2,
        opacity: float = 0.75,
    ) -> str:
        rng = get_rng(seed)
        rad = math.radians(angle_deg)
        dx = math.cos(rad)
        dy = math.sin(rad)
        nx = -dy
        ny = dx

        lines = []
        for i in range(num_lines):
            offset = (i - num_lines // 2) * (spread_px / max(1, num_lines - 1))
            line_len = length * (0.6 + rng.random() * 0.6)

            sx = origin_x + nx * offset + (rng.random() - 0.5) * 4.0
            sy = origin_y + ny * offset + (rng.random() - 0.5) * 4.0
            ex = sx + dx * line_len
            ey = sy + dy * line_len

            l_seed = f"{seed}_speed_{i}"
            lines.append(
                SketchStroke.render_line(
                    sx, sy, ex, ey,
                    seed=l_seed,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width * (0.8 + rng.random() * 0.4),
                    opacity=opacity * (0.6 + rng.random() * 0.4),
                    passes=1,
                    jitter_amount=1.0,
                )
            )

        return "\n  ".join(lines)
