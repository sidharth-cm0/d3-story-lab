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


# =============================================================================
# CINEMATIC STORYBOARD LINE WEIGHT HIERARCHY (Section 13)
# =============================================================================
LINE_WEIGHT_CONSTRUCTION = 0.5   # Very light layout guides (< 0.12 opacity)
LINE_WEIGHT_BACKGROUND = 0.9     # Distant architecture, high trusses, windows
LINE_WEIGHT_INTERIOR = 1.3       # Facial features, clothing seams, folds
LINE_WEIGHT_CHARACTER = 1.9      # Main actor silhouette, anatomical contours
LINE_WEIGHT_FOREGROUND = 2.8     # Foreground framing elements, close-up silhouettes
LINE_WEIGHT_SHADOW = 2.4         # Deep shadow boundary edges

# =============================================================================
# 5-VALUE GRAYSCALE TONAL HIERARCHY (Section 14)
# =============================================================================
VALUE_0 = "#ffffff"              # Pure highlight / paper white
VALUE_1 = "#cbd5e1"              # Light gray wash
VALUE_2 = "#64748b"              # Midtone gray
VALUE_3 = "#334155"              # Dark shadow gray
VALUE_4 = "#090d16"              # Near black / deep ink

# =============================================================================
# RESTRAINED SELECTIVE COLOR ACCENTS (Section 16)
# =============================================================================
ACCENT_COOL_WASH = "#1e293b"     # 20% environmental cool wash
ACCENT_BLUE_HAZE = "#38bdf8"     # Moonbeam window tint
ACCENT_WARM_LAMP = "#f59e0b"     # Practical lamp / flashlight tint
ACCENT_STORY_RED = "#dc2626"     # Critical narrative cue (wax seal, warning)
ACCENT_SEPIA = "#78350f"         # Weathered paper/dossier tone


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
            p_opacity = max(0.005, min(1.0, opacity * (0.8 + p_rng.random() * 0.3)))

            d = f"M {sx:.1f} {sy:.1f} C {c1x:.1f} {c1y:.1f}, {c2x:.1f} {c2y:.1f}, {ex:.1f} {ey:.1f}"
            paths.append(
                f'<path d="{d}" fill="none" stroke="{stroke_color}" stroke-width="{p_width:.2f}" '
                f'stroke-linecap="round" stroke-linejoin="round" opacity="{p_opacity:.2f}"/>'
            )

        return "\n  ".join(paths)


class SketchCurve:
    """Organic Bézier curve renderer simulating hand-drawn anatomical contours and gestures."""

    @staticmethod
    def render_quad(
        x1: float, y1: float,
        cx: float, cy: float,
        x2: float, y2: float,
        seed: str,
        stroke_color: str = "#202020",
        stroke_width: float = 1.6,
        opacity: float = 0.85,
        passes: int = 2,
        jitter_amount: float = 1.0,
    ) -> str:
        """Render a hand-drawn quadratic Bézier curve with organic artist tremor."""
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 0.5:
            return ""
        nx = -dy / dist
        ny = dx / dist

        paths = []
        for p in range(passes):
            p_seed = f"{seed}_qpass{p}"
            rng = get_rng(p_seed)

            sj = (rng.random() - 0.5) * jitter_amount * 0.7
            ej = (rng.random() - 0.5) * jitter_amount * 0.7
            cj = (rng.random() - 0.5) * jitter_amount * 1.5

            sx = x1 + nx * sj
            sy = y1 + ny * sj
            ex = x2 + nx * ej
            ey = y2 + ny * ej
            mcx = cx + nx * cj
            mcy = cy + ny * cj

            pw = max(0.5, stroke_width + (rng.random() - 0.5) * 0.4)
            pop = max(0.005, min(1.0, opacity * (0.85 + rng.random() * 0.25)))

            d = f"M {sx:.1f} {sy:.1f} Q {mcx:.1f} {mcy:.1f}, {ex:.1f} {ey:.1f}"
            paths.append(
                f'<path d="{d}" fill="none" stroke="{stroke_color}" stroke-width="{pw:.2f}" '
                f'stroke-linecap="round" stroke-linejoin="round" opacity="{pop:.2f}"/>'
            )
        return "\n  ".join(paths)

    @staticmethod
    def render_cubic(
        x1: float, y1: float,
        c1x: float, c1y: float,
        c2x: float, c2y: float,
        x2: float, y2: float,
        seed: str,
        stroke_color: str = "#202020",
        stroke_width: float = 1.6,
        opacity: float = 0.85,
        passes: int = 2,
        jitter_amount: float = 1.0,
    ) -> str:
        """Render a hand-drawn cubic Bézier curve with organic artist tremor."""
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 0.5:
            return ""
        nx = -dy / dist
        ny = dx / dist

        paths = []
        for p in range(passes):
            p_seed = f"{seed}_cpass{p}"
            rng = get_rng(p_seed)

            sj = (rng.random() - 0.5) * jitter_amount * 0.6
            ej = (rng.random() - 0.5) * jitter_amount * 0.6
            cj1 = (rng.random() - 0.5) * jitter_amount * 1.4
            cj2 = (rng.random() - 0.5) * jitter_amount * 1.4

            sx = x1 + nx * sj
            sy = y1 + ny * sj
            ex = x2 + nx * ej
            ey = y2 + ny * ej
            mc1x = c1x + nx * cj1
            mc1y = c1y + ny * cj1
            mc2x = c2x + nx * cj2
            mc2y = c2y + ny * cj2

            pw = max(0.5, stroke_width + (rng.random() - 0.5) * 0.4)
            pop = max(0.005, min(1.0, opacity * (0.85 + rng.random() * 0.25)))

            d = f"M {sx:.1f} {sy:.1f} C {mc1x:.1f} {mc1y:.1f}, {mc2x:.1f} {mc2y:.1f}, {ex:.1f} {ey:.1f}"
            paths.append(
                f'<path d="{d}" fill="none" stroke="{stroke_color}" stroke-width="{pw:.2f}" '
                f'stroke-linecap="round" stroke-linejoin="round" opacity="{pop:.2f}"/>'
            )
        return "\n  ".join(paths)


class GraphiteStrokeTier:
    """Three-tier stroke hierarchy per Section 10:
    1. PRIMARY CONTOUR: darkest, confident outline
    2. SECONDARY DETAIL: lighter interior form / fold
    3. GRAPHITE SCRATCH: thin broken marks simulating pencil rough
    """

    @staticmethod
    def render_stroke(
        x1: float, y1: float, x2: float, y2: float,
        seed: str,
        primary_color: str = "#202020",
        base_width: float = 1.8,
        include_scratch: bool = True,
    ) -> str:
        elements = []
        # 1. Primary contour (dark, confident, 2 passes)
        elements.append(
            SketchStroke.render_line(
                x1, y1, x2, y2,
                seed=f"{seed}_prim",
                stroke_color=primary_color,
                stroke_width=base_width,
                opacity=0.90,
                passes=2,
                jitter_amount=0.8,
            )
        )
        # 2. Secondary softer pencil tone
        elements.append(
            SketchStroke.render_line(
                x1, y1, x2, y2,
                seed=f"{seed}_sec",
                stroke_color="#55514B",
                stroke_width=base_width * 0.65,
                opacity=0.55,
                passes=1,
                jitter_amount=1.2,
            )
        )
        # 3. Graphite scratch: thin broken marks
        if include_scratch:
            rng = get_rng(f"{seed}_scratch")
            if rng.random() > 0.35:
                # Overshoot scratch tick
                dx = x2 - x1
                dy = y2 - y1
                dist = max(1.0, math.hypot(dx, dy))
                ux = dx / dist
                uy = dy / dist
                tick_len = min(18.0, dist * 0.25)
                elements.append(
                    SketchStroke.render_line(
                        x2, y2, x2 + ux * tick_len + (rng.random() - 0.5) * 4.0, y2 + uy * tick_len + (rng.random() - 0.5) * 4.0,
                        seed=f"{seed}_tick",
                        stroke_color="#77736A",
                        stroke_width=0.6,
                        opacity=0.35,
                        passes=1,
                        jitter_amount=1.4,
                    )
                )
        return "\n  ".join(elements)


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
        stroke_width: float = 0.8,
        opacity: float = 0.025,
    ) -> str:
        # Strict enforcement: Perspective guides must never exceed 0.03 opacity in final SVG (Section 1)
        eff_opacity = min(opacity, 0.03)
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
                    opacity=eff_opacity,
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
                    opacity=eff_opacity * (0.4 + 0.6 * t),
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


class InkWashPolygon:
    """Semi-transparent ink-wash shading polygon with organic edge variation (Section 15).

    Mixes with linework and cross-hatching to create genuine film storyboard tone.
    """

    @staticmethod
    def render(
        points: List[Tuple[float, float]],
        seed: str,
        fill_color: str = "#0f172a",
        opacity: float = 0.22,
        blend_mode: str = "normal",
        wash_color: Optional[str] = None,
    ) -> str:
        if len(points) < 3:
            return ""
        color = wash_color or fill_color
        rng = get_rng(seed)
        jittered = []
        for px, py in points:
            jx = (rng.random() - 0.5) * 1.8
            jy = (rng.random() - 0.5) * 1.8
            jittered.append(f"{px + jx:.1f},{py + jy:.1f}")
        pts_str = " ".join(jittered)
        mix = f'style="mix-blend-mode: {blend_mode};"' if blend_mode != "normal" else ""
        return (
            f'<polygon points="{pts_str}" fill="{color}" fill-opacity="{opacity:.3f}" '
            f'stroke="none" {mix}/>'
        )


class TextureRenderer:
    """Procedural material texture generator (Section 17: Concrete, Wood, Metal, Rain)."""

    @staticmethod
    def concrete_cracks(
        x: float,
        y: float,
        w: float,
        h: float,
        seed: str,
        stroke_color: str = "#334155",
        num_cracks: int = 3,
    ) -> str:
        """Render irregular hairline concrete stress fractures and expansion cuts."""
        rng = get_rng(seed)
        paths = []
        for c in range(num_cracks):
            cx_start = x + (rng.random() * w * 0.8)
            cy_start = y + (rng.random() * h * 0.8)
            cur_x, cur_y = cx_start, cy_start
            segs = []
            for s in range(4):
                next_x = cur_x + (rng.random() - 0.3) * (w * 0.15)
                next_y = cur_y + (rng.random() - 0.4) * (h * 0.12)
                segs.append(f"L {next_x:.1f} {next_y:.1f}")
                cur_x, cur_y = next_x, next_y
            d_str = f"M {cx_start:.1f} {cy_start:.1f} " + " ".join(segs)
            paths.append(
                f'<path d="{d_str}" fill="none" stroke="{stroke_color}" stroke-width="{LINE_WEIGHT_CONSTRUCTION:.2f}" '
                f'stroke-linecap="round" opacity="0.45"/>'
            )
        return "\n  ".join(paths)

    @staticmethod
    def wood_grain(
        x: float,
        y: float,
        w: float,
        h: float,
        seed: str,
        stroke_color: str = "#475569",
        num_planks: int = 3,
    ) -> str:
        """Render wood grain lines and plank borders for wooden crates or workbenches."""
        rng = get_rng(seed)
        elements = []
        plank_h = h / max(1, num_planks)
        for p in range(num_planks):
            py = y + p * plank_h
            # Plank seam
            elements.append(
                SketchStroke.render_line(
                    x, py, x + w, py,
                    seed=f"{seed}_plank_{p}",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                    opacity=0.6,
                    passes=1,
                )
            )
            # Subtle interior grain lines
            gy = py + (plank_h * 0.45) + (rng.random() - 0.5) * 4
            elements.append(
                SketchStroke.render_line(
                    x + 4, gy, x + w - 4, gy + (rng.random() - 0.5) * 3,
                    seed=f"{seed}_grain_{p}",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    opacity=0.35,
                    passes=1,
                )
            )
        return "\n  ".join(elements)

    @staticmethod
    def metal_highlights(
        x: float,
        y: float,
        length: float,
        seed: str,
        stroke_color: str = "#ffffff",
        angle_deg: float = -45.0,
    ) -> str:
        """Render sharp specular reflection slashes on metallic edges or flashlights."""
        rad = math.radians(angle_deg)
        ex = x + length * math.cos(rad)
        ey = y + length * math.sin(rad)
        return SketchStroke.render_line(
            x, y, ex, ey,
            seed=f"{seed}_metal_spec",
            stroke_color=stroke_color,
            stroke_width=1.1,
            opacity=0.85,
            passes=1,
        )

    @staticmethod
    def rain_streaks(
        width: float,
        height: float,
        seed: str,
        num_streaks: int = 24,
        stroke_color: str = "#94a3b8",
    ) -> str:
        """Render atmospheric angled rain streaks."""
        rng = get_rng(seed)
        lines = []
        angle_rad = math.radians(72.0)  # Slight slant
        dx = math.cos(angle_rad) * 45.0
        dy = math.sin(angle_rad) * 45.0
        for i in range(num_streaks):
            sx = rng.random() * width
            sy = rng.random() * height
            lines.append(
                SketchStroke.render_line(
                    sx, sy, sx + dx, sy + dy,
                    seed=f"{seed}_rain_{i}",
                    stroke_color=stroke_color,
                    stroke_width=0.7,
                    opacity=0.3 + rng.random() * 0.25,
                    passes=1,
                )
            )
        return "\n  ".join(lines)

    @staticmethod
    def glass_reflections(
        x: float,
        y: float,
        w: float,
        h: float,
        seed: str,
        stroke_color: str = "#ffffff",
        num_streaks: int = 3,
    ) -> str:
        """Render diagonal semi-transparent gloss reflection glares across glass panes."""
        rng = get_rng(seed)
        elements = []
        for g_idx in range(num_streaks):
            gx1 = x + (w * 0.2) + (g_idx * w * 0.25)
            gy1 = y + 4.0
            gx2 = gx1 - (w * 0.22)
            gy2 = y + h - 4.0
            elements.append(
                SketchStroke.render_line(
                    gx1, gy1, gx2, gy2,
                    seed=f"{seed}_glass_refl_{g_idx}",
                    stroke_color=stroke_color,
                    stroke_width=0.9,
                    opacity=0.45 + (rng.random() * 0.2),
                    passes=1,
                )
            )
        return "\n  ".join(elements)

    @staticmethod
    def fabric_folds(
        x: float,
        y: float,
        w: float,
        h: float,
        seed: str,
        stroke_color: str = "#334155",
        num_folds: int = 3,
    ) -> str:
        """Render compression folds and stretch crease lines on garments."""
        rng = get_rng(seed)
        lines = []
        step_y = h / max(1, num_folds)
        for i in range(num_folds):
            fy = y + i * step_y + (rng.random() - 0.5) * 4.0
            fx1 = x + (rng.random() - 0.5) * 3.0
            fx2 = x + w + (rng.random() - 0.5) * 3.0
            lines.append(
                SketchStroke.render_line(
                    fx1, fy, fx2, fy + (rng.random() - 0.5) * 6.0,
                    seed=f"{seed}_fabric_fold_{i}",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                    opacity=0.65,
                    passes=1,
                )
            )
        return "\n  ".join(lines)

    @staticmethod
    def paper_creases(
        x: float,
        y: float,
        w: float,
        h: float,
        seed: str,
        stroke_color: str = "#94a3b8",
    ) -> str:
        """Render subtle dog-eared corner and surface creases on paper dossiers."""
        elements = []
        # Diagonal corner crease
        elements.append(
            SketchStroke.render_line(
                x + w - 12, y, x + w, y + 12,
                seed=f"{seed}_dogear",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_CONSTRUCTION,
                opacity=0.6,
                passes=1,
            )
        )
        return "\n  ".join(elements)
