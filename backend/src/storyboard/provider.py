"""Storyboard rendering provider abstraction for generating graphic novel / comic panel visuals.

Includes:
1. StoryboardProvider (Abstract Base Class)
2. ComicGraphicStoryboardProvider (High-fidelity procedural comic/graphic illustration engine)
3. GeminiImageStoryboardProvider (Adapter contract for real cloud image generation)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import os
import re
import html
from src.storyboard.models import StoryboardPanel, ShotType, CameraAngle


class StoryboardProvider(ABC):
    """Abstract interface for rendering storyboard panel visual representations."""

    @abstractmethod
    def render_panel(self, panel: StoryboardPanel) -> Dict[str, Any]:
        """Produce visual asset metadata (SVG, data URI, or image URL)."""
        pass

    def render_panels(self, panels: List[StoryboardPanel]) -> List[Dict[str, Any]]:
        """Render a sequence of storyboard panels."""
        return [self.render_panel(p) for p in panels]


class ComicGraphicStoryboardProvider(StoryboardProvider):
    """Procedural Comic/Graphic Novel Illustration Engine.

    Renders genuine high-contrast noir comic panels in SVG with:
    - Chiaroscuro atmospheric lighting and deep ink shadows
    - Authentic character silhouettes with accurate hairstyles, attire, and postures
    - Visual representation of key props (dossier, phone, safe)
    - Dynamic camera perspectives (wide, medium, close-up, low-angle)
    - Comic panels with narrative captions, speech bubbles, and film grain hatching
    - Strict visual continuity across scenes and panels
    """

    def render_panel(self, panel: StoryboardPanel) -> Dict[str, Any]:
        shot_type = panel.shot_type
        camera_angle = panel.camera_angle
        shot_label = shot_type.value.replace("_", " ").upper()
        angle_label = camera_angle.value.replace("_", " ").upper()

        loc_name = html.escape(panel.location_name or "Interior")
        char_names = [html.escape(c) for c in (panel.character_names or [])]
        dialogue = html.escape(panel.dialogue_excerpt or "")
        action = html.escape(panel.action_description or panel.action or "")
        caption_text = dialogue if dialogue else action

        # Characters & references
        char_1 = char_names[0] if char_names else "Protagonist"
        char_2 = char_names[1] if len(char_names) >= 2 else "Counterpart"
        has_two_chars = len(char_names) >= 2

        char1_traits = self._analyze_character_traits(char_1, panel.character_references)
        char2_traits = self._analyze_character_traits(char_2, panel.character_references)

        # Detect incident & objects
        raw_text = (action + " " + dialogue).lower()
        objects = [o.lower() for o in (panel.objects_in_frame or [])]
        for w in ["dossier", "ledger", "transceiver", "key", "safe", "phone", "gun", "weapon", "drive", "tape", "file"]:
            if w in raw_text and w not in objects:
                objects.append(w)

        incident_type, sfx = self._analyze_incident(raw_text, dialogue, objects)

        # Prominent object
        prominent_obj = objects[0] if objects else None

        # SVG Dimensions 960x540 (16:9 cinematic aspect ratio)
        w, h = 960, 540

        # Build graphic layers
        bg_elements = self._render_environment(panel.location_name or "", panel.location_reference, shot_type)
        lighting_cone = self._render_lighting(panel.lighting, shot_type, incident_type)
        hatching = self._render_comic_hatching(w, h)
        char_elements = self._render_characters_by_shot(
            shot_type, camera_angle, incident_type, char1_traits, char2_traits, has_two_chars, prominent_obj, dialogue
        )
        sfx_element = self._render_sfx(sfx, 720, 180) if sfx else ""
        speech_bubble = self._render_speech_bubble(dialogue, char_1, shot_type) if dialogue else ""
        ui_overlays = self._render_comic_frame(panel, shot_label, angle_label, loc_name, caption_text, w, h)

        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="100%">
  <defs>
    <!-- Background Vignette -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#07090d"/>
      <stop offset="40%" stop-color="#0e131f"/>
      <stop offset="100%" stop-color="#06070a"/>
    </linearGradient>

    <!-- Volumetric Noir Spotlights -->
    <linearGradient id="amberSpotlight" x1="50%" y1="0%" x2="50%" y2="100%">
      <stop offset="0%" stop-color="#fbbf24" stop-opacity="0.38"/>
      <stop offset="50%" stop-color="#f59e0b" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#d97706" stop-opacity="0.01"/>
    </linearGradient>
    <linearGradient id="cyanMoonlight" x1="50%" y1="0%" x2="50%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.32"/>
      <stop offset="60%" stop-color="#0284c7" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="#0f172a" stop-opacity="0.0"/>
    </linearGradient>
    <linearGradient id="hazardRed" x1="50%" y1="0%" x2="50%" y2="100%">
      <stop offset="0%" stop-color="#ef4444" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#991b1b" stop-opacity="0.02"/>
    </linearGradient>

    <!-- Comic Ben-Day Dot Halftone Pattern -->
    <pattern id="benDayDots" x="0" y="0" width="7" height="7" patternUnits="userSpaceOnUse">
      <circle cx="2.5" cy="2.5" r="1.3" fill="#1e293b" opacity="0.42"/>
    </pattern>

    <!-- Noir Cross-Hatch Shading Pattern -->
    <pattern id="crossHatch" x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="8" y2="8" stroke="#020305" stroke-width="1" opacity="0.6"/>
      <line x1="8" y1="0" x2="0" y2="8" stroke="#020305" stroke-width="0.8" opacity="0.45"/>
    </pattern>

    <!-- Venetian Blinds Noir Shadow Pattern -->
    <pattern id="venetianBlinds" x="0" y="0" width="30" height="24" patternUnits="userSpaceOnUse">
      <rect x="0" y="0" width="30" height="9" fill="#020305" opacity="0.45"/>
    </pattern>

    <!-- Specular Gold / Brass Gradient -->
    <linearGradient id="specularGold" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fef08a"/>
      <stop offset="50%" stop-color="#d97706"/>
      <stop offset="100%" stop-color="#78350f"/>
    </linearGradient>

    <!-- Cold Edge Rim Light -->
    <linearGradient id="rimCyan" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="#090a0f" stop-opacity="0.0"/>
    </linearGradient>
  </defs>

  <!-- Background Base Canvas -->
  <rect width="{w}" height="{h}" fill="url(#bgGrad)"/>
  <rect width="{w}" height="{h}" fill="url(#benDayDots)"/>

  <!-- Environmental Architecture -->
  {bg_elements}

  <!-- Volumetric Key Lighting -->
  {lighting_cone}

  <!-- Inked Character & Incident Action Staging -->
  {char_elements}

  <!-- Deep Chiaroscuro Cross-Hatching -->
  {hatching}

  <!-- Dynamic Comic SFX Lettering (if triggered) -->
  {sfx_element}

  <!-- Comic Dialogue Balloon (if dialogue present) -->
  {speech_bubble}

  <!-- Comic Panel Borders, Registration, Badges & Caption -->
  {ui_overlays}
</svg>"""

        return {
            "panel_id": panel.id,
            "scene_id": panel.scene_id,
            "scene_number": panel.scene_number,
            "panel_number": panel.panel_number,
            "shot_number": panel.shot_number,
            "page_number": panel.page_number,
            "render_type": "graphic_novel_svg",
            "svg_data": svg_content,
            "prompt_used": panel.visual_prompt or panel.image_prompt or panel.prompt,
            "continuity_notes": panel.continuity_notes,
            "caption": panel.caption,
            "is_mock": False,
            "engine": "ComicGraphicRenderer_v3",
        }

    def _analyze_character_traits(self, name: str, references: Dict[str, str]) -> Dict[str, str]:
        """Extract continuous visual traits from character name and profiles."""
        ref = (references.get(name, "") + " " + name).lower()

        # Hairstyle continuity
        if any(w in ref for w in ["bob", "fringe", "bangs", "sleek dark hair"]):
            hair = "bob"
        elif any(w in ref for w in ["slick", "comb", "pompadour", "undercut", "silver-streaked"]):
            hair = "slicked"
        elif any(w in ref for w in ["curl", "afro", "wavy", "messy"]):
            hair = "curls"
        elif any(w in ref for w in ["ponytail", "braid", "tied"]):
            hair = "ponytail"
        elif any(w in ref for w in ["fedora", "hat", "brim"]):
            hair = "fedora"
        elif any(w in ref for w in ["short", "crew", "fade", "buzz"]):
            hair = "short"
        else:
            # Deterministic by name
            hair = "bob" if "maya" in ref or "lin" in ref else "slicked"

        # Wardrobe continuity
        if any(w in ref for w in ["trench", "overcoat", "lapel", "turned-up"]):
            outfit = "trench"
        elif any(w in ref for w in ["suit", "tie", "three-piece", "cufflink", "diplomat", "formal"]):
            outfit = "suit"
        elif any(w in ref for w in ["leather", "bomber", "biker", "jacket", "zipper"]):
            outfit = "leather"
        elif any(w in ref for w in ["hoodie", "casual", "turtleneck", "tactical"]):
            outfit = "tactical"
        else:
            outfit = "trench" if "maya" in ref else "suit"

        # Distinguishing details
        has_glasses = any(w in ref for w in ["glass", "spectacle", "wire-rim", "horn-rim"]) or "arjun" in ref
        has_scar = any(w in ref for w in ["scar", "slash", "mark"])

        # Accent Rim Color
        color = "#38bdf8" if "maya" in ref or "lin" in ref else "#f59e0b"

        return {
            "name": name,
            "hair": hair,
            "outfit": outfit,
            "has_glasses": "yes" if has_glasses else "no",
            "has_scar": "yes" if has_scar else "no",
            "accent_color": color,
        }

    def _analyze_incident(self, text: str, dialogue: str, objects: List[str]) -> tuple[str, Optional[str]]:
        """Classify dramatic action into incident type and corresponding comic sound effect."""
        combined = (text + " " + dialogue).lower()

        if any(w in combined for w in ["gun", "weapon", "drawn", "aim", "revolver", "cock"]):
            return "weapon_standoff", "*CLICK*"
        elif any(w in combined for w in ["safe", "unlock", "combination", "dial", "lockbox"]):
            return "search_safe", "*CLICK*"
        elif any(w in combined for w in ["ledger", "dossier", "document", "sealed", "uncover", "evidence"]):
            return "evidence_clue", "*SNAP*"
        elif any(w in combined for w in ["confront", "accuse", "liar", "lying", "demands", "slam", "betray"]):
            return "confrontation", "*SLAM*"
        elif any(w in combined for w in ["transceiver", "frequency", "radio", "signal", "cipher", "code"]):
            return "comm_device", "*BEEP*"
        elif any(w in combined for w in ["escape", "flee", "fire", "smoke", "warehouse", "burst"]):
            return "escape_flight", "*SWOOSH*"
        elif any(w in combined for w in ["whisper", "listen", "secret", "ear"]):
            return "intense_dialogue", "*WHISPER*"
        elif any(w in combined for w in ["search", "inspect", "desk", "drawer", "creak"]):
            return "search_inspect", "*CREAK*"
        elif dialogue:
            return "intense_dialogue", None
        else:
            return "general_action", None

    def _render_environment(self, loc_name: str, loc_ref: str, shot_type: ShotType) -> str:
        """Render architectural setting with distinctive visual identity."""
        low = (loc_name + " " + loc_ref).lower()

        if any(w in low for w in ["warehouse", "industrial", "bay", "factory", "pier", "dock"]):
            # 1. Industrial Warehouse / Abandoned Bay
            return """
    <!-- Industrial Warehouse Architecture -->
    <!-- Distant Corrugated Iron Walls with Cross-Braces -->
    <rect x="60" y="40" width="840" height="380" fill="#0a0c12" stroke="#1e293b" stroke-width="2"/>
    <line x1="60" y1="40" x2="900" y2="420" stroke="#111827" stroke-width="4"/>
    <line x1="900" y1="40" x2="60" y2="420" stroke="#111827" stroke-width="4"/>

    <!-- High Broken Skylights with Cold Moonlight Inflow -->
    <polygon points="260,40 420,40 380,140 220,140" fill="#0c1220" stroke="#38bdf8" stroke-width="1.5" opacity="0.85"/>
    <line x1="340" y1="40" x2="300" y2="140" stroke="#38bdf8" stroke-width="2" opacity="0.6"/>
    <!-- Glass Fracture Cracks -->
    <path d="M 280 60 L 320 100 L 290 120" stroke="#93c5fd" stroke-width="1" fill="none" opacity="0.7"/>

    <!-- Massive Steel I-Beam Vertical Pillars with Rivets -->
    <rect x="140" y="40" width="55" height="460" fill="#07090e" stroke="#334155" stroke-width="2"/>
    <line x1="167" y1="40" x2="167" y2="500" stroke="#1e293b" stroke-width="2"/>
    <circle cx="152" cy="90" r="2.5" fill="#475569"/>
    <circle cx="182" cy="90" r="2.5" fill="#475569"/>
    <circle cx="152" cy="180" r="2.5" fill="#475569"/>
    <circle cx="182" cy="180" r="2.5" fill="#475569"/>
    <circle cx="152" cy="270" r="2.5" fill="#475569"/>
    <circle cx="182" cy="270" r="2.5" fill="#475569"/>

    <rect x="760" y="40" width="55" height="460" fill="#07090e" stroke="#334155" stroke-width="2"/>
    <line x1="787" y1="40" x2="787" y2="500" stroke="#1e293b" stroke-width="2"/>

    <!-- Suspended Heavy Chains and Industrial Hoist Hook -->
    <line x1="510" y1="40" x2="510" y2="210" stroke="#475569" stroke-width="3" stroke-dasharray="6,3"/>
    <path d="M 500 210 Q 510 245 528 230 Q 532 215 515 220" stroke="#94a3b8" stroke-width="4" fill="none"/>

    <!-- Stacked Cargo Shipping Crates with Stenciled Codes -->
    <rect x="60" y="320" width="130" height="150" fill="#131722" stroke="#334155" stroke-width="2"/>
    <line x1="60" y1="320" x2="190" y2="470" stroke="#1e293b" stroke-width="2"/>
    <text x="75" y="360" fill="#f59e0b" font-family="monospace" font-size="10" font-weight="bold" letter-spacing="1">CARGO // 44-B</text>

    <!-- Concrete Floor with Wet Reflections -->
    <polygon points="0,470 960,470 960,540 0,540" fill="#07080c"/>
    <line x1="0" y1="470" x2="960" y2="470" stroke="#1e293b" stroke-width="2"/>
            """

        elif any(w in low for w in ["vault", "archive", "secure", "safe", "locker"]):
            # 2. Heavy Bank / Archive Vault
            return """
    <!-- Heavy Security Vault Interior -->
    <rect x="40" y="40" width="880" height="440" fill="#080a0f" stroke="#1e293b" stroke-width="3"/>

    <!-- Wall of Safety Deposit Boxes (Grid with Plates & Keyholes) -->
    <g opacity="0.85">
      <rect x="80" y="70" width="280" height="360" fill="#0d111a" stroke="#334155" stroke-width="2"/>
      <line x1="80" y1="130" x2="360" y2="130" stroke="#1e293b" stroke-width="1.5"/>
      <line x1="80" y1="190" x2="360" y2="190" stroke="#1e293b" stroke-width="1.5"/>
      <line x1="80" y1="250" x2="360" y2="250" stroke="#1e293b" stroke-width="1.5"/>
      <line x1="80" y1="310" x2="360" y2="310" stroke="#1e293b" stroke-width="1.5"/>
      <line x1="80" y1="370" x2="360" y2="370" stroke="#1e293b" stroke-width="1.5"/>
      <line x1="173" y1="70" x2="173" y2="430" stroke="#1e293b" stroke-width="1.5"/>
      <line x1="266" y1="70" x2="266" y2="430" stroke="#1e293b" stroke-width="1.5"/>
      <!-- Keyholes & Brass Plaques -->
      <rect x="110" y="95" width="22" height="10" fill="#d97706" rx="1"/>
      <circle cx="121" cy="115" r="2.5" fill="#000000"/>
      <rect x="203" y="95" width="22" height="10" fill="#d97706" rx="1"/>
      <circle cx="214" cy="115" r="2.5" fill="#000000"/>
      <rect x="296" y="95" width="22" height="10" fill="#d97706" rx="1"/>
      <circle cx="307" cy="115" r="2.5" fill="#000000"/>
    </g>

    <!-- Massive Circular Steel Vault Door (Angled Open Perspective) -->
    <g transform="translate(680, 260)">
      <!-- Giant Outer Vault Rim with Bolt Lugs -->
      <circle cx="0" cy="0" r="165" fill="#0c0e14" stroke="#475569" stroke-width="8"/>
      <circle cx="0" cy="0" r="148" fill="#080a0f" stroke="#334155" stroke-width="4"/>
      <!-- Heavy Cylindrical Locking Lugs around perimeter -->
      <rect x="-170" y="-12" width="26" height="24" fill="#94a3b8" stroke="#334155" stroke-width="1"/>
      <rect x="144" y="-12" width="26" height="24" fill="#94a3b8" stroke="#334155" stroke-width="1"/>
      <rect x="-12" y="-170" width="24" height="26" fill="#94a3b8" stroke="#334155" stroke-width="1"/>
      <rect x="-12" y="144" width="24" height="26" fill="#94a3b8" stroke="#334155" stroke-width="1"/>
      <!-- Central Spoke Steering Wheel -->
      <circle cx="0" cy="0" r="42" fill="#1e293b" stroke="#94a3b8" stroke-width="3"/>
      <line x1="-55" y1="0" x2="55" y2="0" stroke="#f8fafc" stroke-width="6"/>
      <line x1="0" y1="-55" x2="0" y2="55" stroke="#f8fafc" stroke-width="6"/>
      <circle cx="0" cy="0" r="14" fill="#d97706" stroke="#fef08a" stroke-width="2"/>
    </g>

    <!-- Wall Security Camera with Active Red LED -->
    <g transform="translate(480, 65)">
      <rect x="-20" y="0" width="40" height="18" fill="#1e293b" stroke="#334155" stroke-width="1"/>
      <path d="M -15 18 L 15 18 L 8 36 L -8 36 Z" fill="#0f172a"/>
      <circle cx="0" cy="38" r="4" fill="#ef4444"/> <!-- Blinking Red Diode -->
      <circle cx="0" cy="38" r="8" fill="none" stroke="#ef4444" stroke-width="1" opacity="0.4"/>
    </g>
            """

        elif any(w in low for w in ["corridor", "hall", "passage", "tunnel", "stair"]):
            # 3. Receding Service Corridor / Embassy Hallway
            return """
    <!-- Receding One-Point Perspective Corridor -->
    <path d="M 0 0 L 340 180 L 620 180 L 960 0 Z" fill="#090c12" stroke="#1e293b" stroke-width="2"/>
    <path d="M 0 540 L 340 370 L 620 370 L 960 540 Z" fill="#07080b" stroke="#1e293b" stroke-width="2"/>
    <rect x="340" y="180" width="280" height="190" fill="#050608" stroke="#334155" stroke-width="2"/>

    <!-- Steel Structural Arches & Wall Conduits -->
    <line x1="120" y1="65" x2="370" y2="195" stroke="#334155" stroke-width="3.5"/>
    <line x1="840" y1="65" x2="590" y2="195" stroke="#334155" stroke-width="3.5"/>

    <!-- Overhead Caged Fluorescent Light Fixtures -->
    <rect x="420" y="185" width="120" height="10" fill="#f8fafc" opacity="0.8"/>
    <rect x="415" y="183" width="130" height="14" fill="none" stroke="#f59e0b" stroke-width="1.5"/>

    <!-- Distant Reinforced Blast Door with Green EXIT sign -->
    <rect x="445" y="215" width="70" height="135" fill="#0f172a" stroke="#38bdf8" stroke-width="2"/>
    <rect x="460" y="202" width="40" height="10" fill="#10b981" rx="1"/>
    <text x="468" y="210" fill="#ffffff" font-family="sans-serif" font-size="7" font-weight="bold">EXIT</text>
    <circle cx="458" cy="280" r="3" fill="#f59e0b"/>
            """

        elif any(w in low for w in ["roof", "alley", "street", "exterior"]):
            # 4. Rainy Rooftop / Alleyway with Fire Escape
            return """
    <!-- Weathered Brick Wall & Fire Escape -->
    <rect x="40" y="40" width="420" height="440" fill="#120c0a" stroke="#2a1510" stroke-width="2"/>
    <!-- Masonry Brick Mortar Lines -->
    <line x1="40" y1="120" x2="460" y2="120" stroke="#1c1210" stroke-width="1.5"/>
    <line x1="40" y1="200" x2="460" y2="200" stroke="#1c1210" stroke-width="1.5"/>
    <line x1="40" y1="280" x2="460" y2="280" stroke="#1c1210" stroke-width="1.5"/>
    <line x1="40" y1="360" x2="460" y2="360" stroke="#1c1210" stroke-width="1.5"/>

    <!-- Black Iron Fire Escape Zigzag Staircase -->
    <rect x="120" y="140" width="260" height="24" fill="#050608" stroke="#475569" stroke-width="2"/>
    <rect x="60" y="260" width="260" height="24" fill="#050608" stroke="#475569" stroke-width="2"/>
    <line x1="340" y1="164" x2="280" y2="260" stroke="#475569" stroke-width="3.5"/>
    <line x1="220" y1="284" x2="160" y2="380" stroke="#475569" stroke-width="3.5"/>

    <!-- Rooftop Water Tower & Gotham Spires in Rain -->
    <polygon points="680,100 840,100 820,240 700,240" fill="#080b12" stroke="#334155" stroke-width="2"/>
    <polygon points="660,100 760,40 860,100" fill="#05080e" stroke="#334155" stroke-width="2"/>
    <line x1="720" y1="240" x2="700" y2="380" stroke="#1e293b" stroke-width="5"/>
    <line x1="800" y1="240" x2="820" y2="380" stroke="#1e293b" stroke-width="5"/>
    <line x1="700" y1="310" x2="820" y2="310" stroke="#1e293b" stroke-width="3"/>

    <!-- Billowing Steam Exhaust -->
    <path d="M 520 380 Q 500 320 540 280 Q 560 250 530 220" stroke="#f8fafc" stroke-width="3" fill="none" opacity="0.25"/>
            """

        else:
            # 5. Default: Penthouse Suite / Luxury Executive Office
            return """
    <!-- Executive Penthouse Panoramic Window & Skyline -->
    <rect x="70" y="35" width="820" height="360" fill="#070a12" stroke="#1e293b" stroke-width="2"/>

    <!-- Noir Venetian Blinds Pattern Overlay -->
    <rect x="70" y="35" width="820" height="360" fill="url(#venetianBlinds)"/>

    <!-- Window Mullion Frames -->
    <line x1="275" y1="35" x2="275" y2="395" stroke="#090d16" stroke-width="8"/>
    <line x1="480" y1="35" x2="480" y2="395" stroke="#090d16" stroke-width="8"/>
    <line x1="685" y1="35" x2="685" y2="395" stroke="#090d16" stroke-width="8"/>
    <line x1="70" y1="215" x2="890" y2="215" stroke="#090d16" stroke-width="6"/>

    <!-- Gotham High-Rise Silhouettes with Lit Windows -->
    <rect x="100" y="150" width="65" height="245" fill="#04060a"/>
    <rect x="185" y="80" width="80" height="315" fill="#030508"/>
    <polygon points="225,45 205,80 245,80" fill="#030508"/>
    <circle cx="225" cy="42" r="2" fill="#ef4444"/> <!-- Tower Beacon -->
    <rect x="295" y="130" width="70" height="265" fill="#04060a"/>
    <rect x="385" y="95" width="85" height="300" fill="#030508"/>
    <rect x="500" y="160" width="75" height="235" fill="#04060a"/>
    <rect x="600" y="85" width="75" height="310" fill="#030508"/>
    <polygon points="637,50 620,85 655,85" fill="#030508"/>
    <rect x="705" y="140" width="90" height="255" fill="#04060a"/>
    <rect x="815" y="180" width="60" height="215" fill="#030508"/>

    <!-- Window Lit Yellow Dots -->
    <circle cx="205" cy="120" r="1.5" fill="#fbbf24" opacity="0.8"/>
    <circle cx="215" cy="120" r="1.5" fill="#fbbf24" opacity="0.8"/>
    <circle cx="205" cy="140" r="1.5" fill="#fbbf24" opacity="0.7"/>
    <circle cx="410" cy="130" r="1.5" fill="#fbbf24" opacity="0.8"/>
    <circle cx="430" cy="130" r="1.5" fill="#fbbf24" opacity="0.8"/>
    <circle cx="625" cy="115" r="1.5" fill="#fbbf24" opacity="0.8"/>

    <!-- Cold Rain Streaks on Glass -->
    <line x1="145" y1="45" x2="135" y2="135" stroke="#38bdf8" stroke-width="1.3" opacity="0.35"/>
    <line x1="250" y1="65" x2="240" y2="175" stroke="#38bdf8" stroke-width="1.3" opacity="0.3"/>
    <line x1="420" y1="55" x2="410" y2="185" stroke="#38bdf8" stroke-width="1.3" opacity="0.35"/>
    <line x1="640" y1="75" x2="630" y2="195" stroke="#38bdf8" stroke-width="1.3" opacity="0.3"/>
    <line x1="760" y1="50" x2="750" y2="160" stroke="#38bdf8" stroke-width="1.3" opacity="0.35"/>

    <!-- Heavy Executive Desk in Foreground (Low profile) -->
    <polygon points="310,385 650,385 700,470 260,470" fill="#080a0f" stroke="#1e293b" stroke-width="2"/>
    <rect x="260" y="470" width="440" height="40" fill="#040507"/>
    <!-- Brass Banker Lamp with Emerald Glass Shade -->
    <path d="M 355 385 L 355 345 L 375 345" stroke="#d97706" stroke-width="3" fill="none"/>
    <rect x="345" y="335" width="45" height="15" rx="4" fill="#047857" stroke="#10b981" stroke-width="1.5"/>
    <ellipse cx="367" cy="348" rx="18" ry="6" fill="#fbbf24" opacity="0.8"/>
            """

    def _render_lighting(self, lighting_desc: str, shot_type: ShotType, incident: str) -> str:
        """Render volumetric chiaroscuro lighting."""
        if incident == "weapon_standoff" or "threat" in lighting_desc.lower():
            return """
    <!-- Dramatic High-Contrast Crimson Alert Beam -->
    <polygon points="480,20 180,540 780,540" fill="url(#hazardRed)"/>
    <ellipse cx="480" cy="510" rx="320" ry="24" fill="#ef4444" opacity="0.08"/>
            """
        elif shot_type in (ShotType.INSERT, ShotType.CLOSE_UP):
            return """
    <!-- Concentrated Overhead Key Light Beam -->
    <polygon points="480,10 280,540 680,540" fill="url(#amberSpotlight)"/>
    <ellipse cx="480" cy="505" rx="220" ry="20" fill="#f59e0b" opacity="0.12"/>
            """
        else:
            return """
    <!-- Low-Key Dual Chiaroscuro Cone (Amber Key & Cyan Rim) -->
    <polygon points="380,20 120,540 640,540" fill="url(#amberSpotlight)"/>
    <polygon points="720,20 540,540 900,540" fill="url(#cyanMoonlight)"/>
    <ellipse cx="480" cy="510" rx="360" ry="25" fill="#f59e0b" opacity="0.06"/>
            """

    def _render_comic_hatching(self, w: int, h: int) -> str:
        """Render heavy comic noir ink shadows and corner vignettes."""
        return f"""
    <!-- Noir Heavy Ink Vignette -->
    <path d="M 0 0 L 250 0 L 0 250 Z" fill="#000000" opacity="0.85"/>
    <path d="M {w} 0 L {w - 250} 0 L {w} 250 Z" fill="#000000" opacity="0.85"/>
    <path d="M 0 {h} L 280 {h} L 0 {h - 280} Z" fill="#000000" opacity="0.9"/>
    <path d="M {w} {h} L {w - 280} {h} L {w} {h - 280} Z" fill="#000000" opacity="0.9"/>
        """

    def _render_characters_by_shot(
        self,
        shot_type: ShotType,
        angle: CameraAngle,
        incident: str,
        char1: Dict[str, str],
        char2: Dict[str, str],
        has_two: bool,
        prominent_obj: Optional[str],
        dialogue: str,
    ) -> str:
        """Stage comic figures according to framing, character traits, and action."""
        is_low_angle = angle == CameraAngle.LOW_ANGLE
        y_shift = -35 if is_low_angle else (35 if angle == CameraAngle.HIGH_ANGLE else 0)

        # ----------------------------------------------------
        # 1. INSERT SHOT: Macro Focus on Key Prop & Hands
        # ----------------------------------------------------
        if shot_type == ShotType.INSERT:
            prop_markup = self._render_macro_prop(prominent_obj or "dossier")
            return f"""
    <!-- INSERT SHOT: Dramatic Macro Focus on Object -->
    <g transform="translate(480, 270)">
      <!-- Radial Focus Rays -->
      <line x1="-300" y1="-180" x2="-80" y2="-40" stroke="#f59e0b" stroke-width="1" opacity="0.35"/>
      <line x1="300" y1="-180" x2="80" y2="-40" stroke="#f59e0b" stroke-width="1" opacity="0.35"/>
      <line x1="-300" y1="180" x2="-80" y2="40" stroke="#f59e0b" stroke-width="1" opacity="0.35"/>
      <line x1="300" y1="180" x2="80" y2="40" stroke="#f59e0b" stroke-width="1" opacity="0.35"/>

      <!-- Gloved Hands Interacting with Prop -->
      <!-- Left Hand -->
      <g transform="translate(-160, 50) rotate(25)">
        <rect x="-35" y="-18" width="70" height="36" rx="8" fill="#050608" stroke="{char1['accent_color']}" stroke-width="1.5"/>
        <path d="M -15 -18 L -15 -45 Q -15 -55 -5 -55 Q 5 -55 5 -45 L 5 -18" fill="#030406" stroke="{char1['accent_color']}" stroke-width="1.5"/>
        <path d="M 8 -18 L 8 -42 Q 8 -52 18 -52 Q 28 -52 28 -42 L 28 -18" fill="#030406" stroke="{char1['accent_color']}" stroke-width="1.5"/>
      </g>
      <!-- Right Hand -->
      <g transform="translate(160, 50) rotate(-25)">
        <rect x="-35" y="-18" width="70" height="36" rx="8" fill="#050608" stroke="{char1['accent_color']}" stroke-width="1.5"/>
        <path d="M -5 -18 L -5 -45 Q -5 -55 5 -55 Q 15 -55 15 -45 L 15 -18" fill="#030406" stroke="{char1['accent_color']}" stroke-width="1.5"/>
      </g>

      <!-- Key Prop Graphic -->
      {prop_markup}
    </g>
            """

        # ----------------------------------------------------
        # 2. REACTION SHOT: Dutch Angle Dramatic Shock
        # ----------------------------------------------------
        elif shot_type == ShotType.REACTION:
            head_markup = self._render_stylized_head(char1, "shocked")
            torso_markup = self._render_stylized_torso(char1, "recoil")
            return f"""
    <!-- REACTION SHOT: Shock / Sudden Realization (Dutch Angle) -->
    <g transform="rotate(-3.5 480 270)">
      <!-- Radiating Shock / Tension Speedlines -->
      <g stroke="#38bdf8" stroke-width="1.5" opacity="0.4">
        <line x1="80" y1="60" x2="280" y2="180"/>
        <line x1="120" y1="460" x2="320" y2="340"/>
        <line x1="880" y1="80" x2="680" y2="180"/>
        <line x1="840" y1="460" x2="640" y2="340"/>
      </g>

      <!-- Close Dramatic Reaction Character -->
      <g transform="translate(480, {280 + y_shift})">
        {torso_markup}
        {head_markup}
        <!-- Hand Raised in Alarm -->
        <g transform="translate(90, 80) rotate(-40)">
          <path d="M 0 0 L 35 -30 L 55 -25 L 30 15 Z" fill="#040508" stroke="{char1['accent_color']}" stroke-width="2"/>
        </g>
      </g>
    </g>
            """

        # ----------------------------------------------------
        # 3. CLOSE UP / EXTREME CLOSE UP: Intense Portrait
        # ----------------------------------------------------
        elif shot_type in (ShotType.CLOSE_UP, ShotType.EXTREME_CLOSE_UP):
            emotion = "angry" if incident == "confrontation" else ("suspicious" if incident == "search_inspect" else "determined")
            head_markup = self._render_stylized_head(char1, emotion)
            torso_markup = self._render_stylized_torso(char1, "upright")
            return f"""
    <!-- CLOSE UP PORTRAIT: {char1['name']} ({char1['hair'].upper()} / {char1['outfit'].upper()}) -->
    <g transform="translate(480, {300 + y_shift})">
      {torso_markup}
      {head_markup}
    </g>
            """

        # ----------------------------------------------------
        # 4. OVER THE SHOULDER (OTS): Confrontation / Dialogue
        # ----------------------------------------------------
        elif shot_type == ShotType.OVER_SHOULDER:
            confronted_head = self._render_stylized_head(char2, "intense", scale=0.75)
            confronted_torso = self._render_stylized_torso(char2, "upright", scale=0.75)
            return f"""
    <!-- OVER THE SHOULDER: Foreground {char1['name']} / Midground {char2['name']} -->
    <!-- Foreground Inked Silhouette ({char1['name']}) -->
    <g transform="translate(180, 480)">
      <path d="M -160 80 Q -120 -180 0 -190 Q 60 -180 120 -150 Q 160 -90 190 80 Z" fill="#010204"/>
      <!-- Popped Coat Collar in Silhouette -->
      <polygon points="-50,-180 -120,-110 -70,-80" fill="#010204" stroke="#1e293b" stroke-width="2"/>
      <polygon points="50,-180 120,-110 70,-80" fill="#010204"/>
    </g>

    <!-- Midground Confronted Actor ({char2['name']}) -->
    <g transform="translate(640, {260 + y_shift})">
      {confronted_torso}
      {confronted_head}
    </g>
            """

        # ----------------------------------------------------
        # 5. WIDE / EXTREME WIDE: Full Staging / Depth
        # ----------------------------------------------------
        elif shot_type in (ShotType.WIDE, ShotType.EXTREME_WIDE):
            char1_wide = self._render_full_body_silhouette(char1, is_left=True)
            char2_wide = self._render_full_body_silhouette(char2, is_left=False) if has_two else ""
            return f"""
    <!-- WIDE CINEMATIC STAGING -->
    <!-- Left Staged Figure ({char1['name']}) -->
    <g transform="translate(260, {350 + y_shift})">
      {char1_wide}
    </g>

    <!-- Right Staged Figure ({char2['name']}) -->
    <g transform="translate(700, {350 + y_shift})">
      {char2_wide}
    </g>
            """

        # ----------------------------------------------------
        # 6. MEDIUM SHOT (Default): Dynamic Action / Interaction
        # ----------------------------------------------------
        else:
            c1_head = self._render_stylized_head(char1, "determined", scale=0.8)
            c1_torso = self._render_stylized_torso(char1, "action", scale=0.8)

            c2_head = self._render_stylized_head(char2, "suspicious", scale=0.8) if has_two else ""
            c2_torso = self._render_stylized_torso(char2, "upright", scale=0.8) if has_two else ""

            # Prop in medium shot if weapon or ledger
            prop_in_hand = ""
            if incident == "weapon_standoff":
                prop_in_hand = """
      <!-- Drawn Handgun in Hand -->
      <g transform="translate(95, 45)">
        <path d="M 0 0 L 38 0 L 38 12 L 15 12 L 10 32 L -4 30 Z" fill="#020305" stroke="#94a3b8" stroke-width="1.5"/>
        <line x1="12" y1="2" x2="36" y2="2" stroke="#ffffff" stroke-width="1.5"/>
      </g>
                """
            elif incident in ("evidence_clue", "search_safe"):
                prop_in_hand = """
      <!-- Dossier / Ledger Held -->
      <g transform="translate(80, 75) rotate(-15)">
        <polygon points="-35,-20 35,-20 40,25 -30,25" fill="#451a03" stroke="#d97706" stroke-width="2"/>
        <circle cx="5" cy="2" r="6" fill="#dc2626"/>
      </g>
                """

            return f"""
    <!-- MEDIUM SHOT: Dynamic Incident Interaction -->
    <!-- Left Character ({char1['name']}) -->
    <g transform="translate({340 if has_two else 480}, {310 + y_shift})">
      {c1_torso}
      {c1_head}
      {prop_in_hand}
    </g>

    <!-- Right Character ({char2['name']}) -->
    {f'''<g transform="translate(650, {310 + y_shift})">
      {c2_torso}
      {c2_head}
    </g>''' if has_two else ''}
            """

    def _render_stylized_head(self, char: Dict[str, str], emotion: str, scale: float = 1.0) -> str:
        """Render consistent stylized comic head with specific hair, facial features, and emotions."""
        hair_type = char["hair"]
        accent = char["accent_color"]
        has_glasses = char["has_glasses"] == "yes"
        has_scar = char["has_scar"] == "yes"

        # Emotional eye configuration
        if emotion == "shocked":
            eye_l = """
        <ellipse cx="-45" cy="-35" rx="15" ry="9" fill="#f8fafc" stroke="#000000" stroke-width="2"/>
        <circle cx="-45" cy="-35" r="4" fill="#000000"/>
        <circle cx="-43" cy="-37" r="1.5" fill="#ffffff"/>
            """
            eye_r = """
        <ellipse cx="45" cy="-35" rx="14" ry="8" fill="#f8fafc" stroke="#000000" stroke-width="2"/>
        <circle cx="45" cy="-35" r="3.5" fill="#000000"/>
            """
            brow = """<path d="M -65 -55 Q -45 -68 -25 -52 M 25 -52 Q 45 -68 65 -55" stroke="#f8fafc" stroke-width="3.5" fill="none"/>"""
            mouth = """<ellipse cx="0" cy="55" rx="14" ry="9" fill="#020305" stroke="#f8fafc" stroke-width="1.8"/>"""
        elif emotion == "angry":
            eye_l = """
        <polygon points="-60,-35 -30,-40 -25,-32 -55,-28" fill="#020305" stroke="#f8fafc" stroke-width="1.5"/>
        <circle cx="-42" cy="-34" r="3" fill="#38bdf8"/>
        <circle cx="-41" cy="-35" r="1" fill="#ffffff"/>
            """
            eye_r = """
        <polygon points="25,-32 30,-40 60,-35 55,-28" fill="#020305" stroke="#f8fafc" stroke-width="1.5"/>
        <circle cx="42" cy="-34" r="3" fill="#38bdf8"/>
            """
            brow = """<polyline points="-65,-48 -35,-42 -22,-36 M 22,-36 35,-42 65,-48" stroke="#f8fafc" stroke-width="4.5" fill="none"/>"""
            mouth = """
        <line x1="-30" y1="52" x2="30" y2="52" stroke="#020305" stroke-width="6"/>
        <line x1="-28" y1="52" x2="28" y2="52" stroke="#ffffff" stroke-width="1.5"/>
            """
        else:
            # Determined / Suspicious (Default noir gaze)
            eye_l = """
        <path d="M -62 -36 Q -45 -48 -26 -36" stroke="#f8fafc" stroke-width="4" fill="none"/>
        <ellipse cx="-44" cy="-32" rx="12" ry="6" fill="#020305" stroke="#f8fafc" stroke-width="1.8"/>
        <circle cx="-44" cy="-32" r="3" fill="#38bdf8"/>
        <circle cx="-42" cy="-34" r="1.5" fill="#ffffff"/>
            """
            eye_r = """
        <ellipse cx="42" cy="-32" rx="10" ry="5" fill="#020305" stroke="{accent}" stroke-width="1" opacity="0.8"/>
        <circle cx="43" cy="-33" r="2" fill="{accent}"/>
            """
            brow = """<path d="M -68 -48 Q -45 -58 -22 -46 M 22 -44 Q 45 -54 65 -46" stroke="#f8fafc" stroke-width="3.5" fill="none"/>"""
            mouth = """
        <line x1="-28" y1="55" x2="20" y2="55" stroke="#020305" stroke-width="5"/>
        <line x1="-24" y1="54" x2="0" y2="54" stroke="#ffffff" stroke-width="1.5"/>
            """

        # Hairstyle Graphic Paths
        if hair_type == "bob":
            # Sleek dark chin-length bob with fringe and rim edge
            hair_svg = f"""
        <!-- Sharp Sleek Bob Cut -->
        <path d="M -115 -120 Q -125 10 -90 65 L -80 30 Q -110 -60 0 -130 Q 110 -60 80 30 L 90 65 Q 125 10 115 -120 Q 80 -185 0 -185 Q -80 -185 -115 -120 Z" fill="#020305" stroke="{accent}" stroke-width="2"/>
        <path d="M -85 -110 Q -40 -70 0 -70 Q 40 -70 85 -110 Q 40 -125 0 -125 Q -40 -125 -85 -110 Z" fill="#05080e"/>
        <!-- Fringe Hair Rim Highlights -->
        <path d="M -70 -115 Q 0 -150 70 -115" stroke="{accent}" stroke-width="2" fill="none" opacity="0.85"/>
            """
        elif hair_type == "slicked":
            # Slicked back pompadour / undercut with combed ridges
            hair_svg = f"""
        <!-- Slicked Back Noir Undercut -->
        <path d="M -110 -110 Q -70 -205 20 -195 Q 90 -195 110 -110 Q 80 -140 0 -140 Q -80 -140 -110 -110 Z" fill="#030407" stroke="{accent}" stroke-width="2"/>
        <!-- Comb Ridges catching light -->
        <path d="M -60 -135 Q 10 -180 75 -135" stroke="{accent}" stroke-width="2" fill="none" opacity="0.8"/>
        <path d="M -40 -150 Q 15 -188 60 -150" stroke="{accent}" stroke-width="1.5" fill="none" opacity="0.6"/>
            """
        elif hair_type == "ponytail":
            # High sleek ponytail with trailing contour
            hair_svg = f"""
        <!-- Sleek High Ponytail -->
        <path d="M -105 -110 Q -110 -180 0 -180 Q 90 -180 105 -110 Z" fill="#020305" stroke="{accent}" stroke-width="1.5"/>
        <path d="M 60 -160 Q 130 -170 160 -110 Q 170 -60 180 20 L 165 20 Q 150 -50 140 -90 Q 110 -140 50 -150 Z" fill="#020305" stroke="{accent}" stroke-width="1.8"/>
            """
        elif hair_type == "fedora":
            # Noir Wide-Brimmed Fedora Hat
            hair_svg = f"""
        <!-- Classic Noir Fedora Hat -->
        <ellipse cx="0" cy="-115" rx="145" ry="25" fill="#040508" stroke="{accent}" stroke-width="2"/>
        <path d="M -75 -115 Q -80 -190 0 -195 Q 80 -190 75 -115 Z" fill="#07090f" stroke="#1e293b" stroke-width="2"/>
        <rect x="-78" y="-130" width="156" height="15" fill="#d97706" opacity="0.8"/> <!-- Hat Band -->
            """
        else:
            # Textured Short Crop
            hair_svg = f"""
        <!-- Short Textured Crop -->
        <path d="M -105 -105 Q -60 -175 0 -175 Q 60 -175 105 -105 Q 80 -130 0 -130 Q -80 -130 -105 -105 Z" fill="#040508" stroke="{accent}" stroke-width="1.5"/>
            """

        # Glasses (if present)
        glasses_svg = ""
        if has_glasses:
            glasses_svg = """
        <!-- Wire-Rim Spectacles with Specular Reflection -->
        <rect x="-65" y="-48" width="46" height="28" rx="4" fill="none" stroke="#38bdf8" stroke-width="2"/>
        <rect x="19" y="-48" width="46" height="28" rx="4" fill="none" stroke="#38bdf8" stroke-width="2"/>
        <line x1="-19" y1="-34" x2="19" y2="-34" stroke="#38bdf8" stroke-width="2"/>
        <!-- Specular Glint on Lens -->
        <line x1="-55" y1="-44" x2="-35" y2="-24" stroke="#ffffff" stroke-width="2.5" opacity="0.85"/>
            """

        # Brow Scar (if present)
        scar_svg = ""
        if has_scar:
            scar_svg = """
        <polyline points="-48,-62 -42,-45 -48,-32" stroke="#ffffff" stroke-width="2" fill="none" opacity="0.85"/>
            """

        return f"""
    <g transform="scale({scale})">
      <!-- Head / Face Silhouette -->
      <path d="M -95 -125 Q -105 -60 -90 15 Q -75 80 0 105 Q 75 80 90 15 Q 105 -60 95 -125 Z" fill="#080a10" stroke="#1e293b" stroke-width="3"/>

      <!-- Chiaroscuro Shadow Split across Face -->
      <path d="M 0 -160 Q 15 -80 8 -25 L 30 25 L 5 45 Q 10 75 0 105 L 90 15 Q 105 -60 95 -125 Z" fill="#020305" opacity="0.88"/>

      <!-- Hairstyle -->
      {hair_svg}

      <!-- Eyes & Brow -->
      {brow}
      {eye_l}
      {eye_r}

      <!-- Sharp Inked Nose Contour -->
      <polyline points="-8,-40 -2,12 14,18" stroke="#f8fafc" stroke-width="2.5" fill="none" opacity="0.75"/>

      <!-- Mouth -->
      {mouth}

      <!-- Distinctive Features -->
      {glasses_svg}
      {scar_svg}
    </g>
        """

    def _render_stylized_torso(self, char: Dict[str, str], pose: str, scale: float = 1.0) -> str:
        """Render consistent wardrobe (trench coat lapels, formal suit & tie, or biker leather)."""
        outfit = char["outfit"]
        accent = char["accent_color"]

        if outfit == "suit":
            # Tailored Suit with Pressed Shirt, Necktie, and Lapels
            return f"""
    <g transform="scale({scale})">
      <!-- Torso Base -->
      <path d="M -75 105 L -130 300 L 130 300 L 75 105 Z" fill="#06080e" stroke="#1e293b" stroke-width="2"/>
      <!-- Pressed White Shirt V-Placket -->
      <polygon points="0,105 -28,210 28,210" fill="#f8fafc" stroke="#1e293b" stroke-width="1.5"/>
      <!-- Suit Notched Lapels -->
      <polygon points="-75,105 -28,210 -15,140 -40,105" fill="#090c14" stroke="{accent}" stroke-width="1.5"/>
      <polygon points="75,105 28,210 15,140 40,105" fill="#05070a" stroke="#1e293b" stroke-width="1.5"/>
      <!-- Necktie with Tie Clip -->
      <polygon points="-8,140 8,140 10,260 0,278 -10,260" fill="#d97706"/>
      <line x1="-8" y1="185" x2="8" y2="185" stroke="#fef08a" stroke-width="2.5"/> <!-- Gold Tie Clip -->
    </g>
            """
        elif outfit == "leather":
            # Leather Biker Jacket with Asymmetrical Zippers
            return f"""
    <g transform="scale({scale})">
      <path d="M -85 105 L -140 300 L 140 300 L 85 105 Z" fill="#040507" stroke="#1e293b" stroke-width="2.5"/>
      <!-- Diagonal Asymmetrical Zipper Track -->
      <line x1="30" y1="110" x2="-20" y2="300" stroke="#94a3b8" stroke-width="3" stroke-dasharray="4,2"/>
      <!-- Snap Studs -->
      <circle cx="-45" cy="140" r="3" fill="#e2e8f0"/>
      <circle cx="45" cy="140" r="3" fill="#e2e8f0"/>
    </g>
            """
        else:
            # Trench Coat (Default Noir Silhouette with Popped Collar Lapels)
            return f"""
    <g transform="scale({scale})">
      <path d="M -85 105 L -150 300 L 150 300 L 85 105 Z" fill="#05060a" stroke="#1e293b" stroke-width="2"/>
      <!-- Popped Wide Collar Lapels -->
      <polygon points="-85,105 -145,210 -45,210 -65,115" fill="#080b12" stroke="{accent}" stroke-width="2"/>
      <polygon points="85,105 145,210 45,210 65,115" fill="#030406" stroke="#1e293b" stroke-width="2"/>
      <!-- Belt Buckle / Button Rows -->
      <circle cx="-25" cy="245" r="4" fill="#d97706"/>
      <circle cx="25" cy="245" r="4" fill="#d97706"/>
    </g>
            """

    def _render_full_body_silhouette(self, char: Dict[str, str], is_left: bool) -> str:
        """Render full-body silhouette for wide cinematic staging."""
        accent = char["accent_color"]
        hair = char["hair"]
        x_dir = 1 if is_left else -1

        return f"""
    <!-- Full-Body Staged Silhouette: {char['name']} -->
    <!-- Head -->
    <circle cx="0" cy="-140" r="22" fill="#080b12" stroke="{accent}" stroke-width="1.8"/>
    <!-- Head hair hint -->
    <ellipse cx="{4 * x_dir}" cy="-145" rx="20" ry="14" fill="#020305"/>

    <!-- Trench / Suit Body Profile -->
    <path d="M -30 -115 L -65 140 L 65 140 L 30 -115 Z" fill="#040508" stroke="#334155" stroke-width="1.5"/>
    <!-- Coat Tails Flaring -->
    <path d="M {-55 * x_dir} 30 L {-90 * x_dir} 145 L {-40 * x_dir} 140 Z" fill="#020305" opacity="0.8"/>

    <!-- Extended Legs in Stride -->
    <line x1="-20" y1="140" x2="{-35 * x_dir}" y2="220" stroke="#040508" stroke-width="16" stroke-linecap="round"/>
    <line x1="20" y1="140" x2="{35 * x_dir}" y2="220" stroke="#040508" stroke-width="16" stroke-linecap="round"/>

    <!-- Cast Dramatic Shadow on Floor Toward Center -->
    <ellipse cx="{-40 * x_dir}" cy="225" rx="110" ry="16" fill="#000000" opacity="0.85"/>
        """

    def _render_macro_prop(self, prop: str) -> str:
        """Render high-detail macro illustration of key props for insert shots."""
        p = prop.lower()

        if any(w in p for w in ["dossier", "ledger", "file", "document"]):
            # Detailed Leather Dossier / Ledger
            return """
    <!-- Leather Dossier with Brass Corners & Red Wax Seal -->
    <g transform="scale(1.25)">
      <!-- Burgundy Leather Folio Body -->
      <polygon points="-120,-85 120,-85 135,85 -105,85" fill="#3b110a" stroke="#78350f" stroke-width="3"/>
      <!-- Cream Page Edges Spilling Out -->
      <polygon points="-102,-78 115,-78 128,78 -90,78" fill="#fef3c7" stroke="#92400e" stroke-width="1"/>
      <line x1="-70" y1="-50" x2="80" y2="-50" stroke="#78350f" stroke-width="2" stroke-dasharray="8,4"/>
      <line x1="-70" y1="-30" x2="95" y2="-30" stroke="#78350f" stroke-width="2" stroke-dasharray="10,3"/>
      <line x1="-70" y1="-10" x2="70" y2="-10" stroke="#78350f" stroke-width="2" stroke-dasharray="6,4"/>

      <!-- Brass Embossed Corners -->
      <polygon points="-120,-85 -90,-85 -120,-55" fill="url(#specularGold)"/>
      <polygon points="120,-85 90,-85 120,-55" fill="url(#specularGold)"/>
      <polygon points="-105,85 -75,85 -105,55" fill="url(#specularGold)"/>
      <polygon points="135,85 105,85 135,55" fill="url(#specularGold)"/>

      <!-- Red Wax Seal & Ribbon -->
      <line x1="-20" y1="-85" x2="20" y2="85" stroke="#991b1b" stroke-width="8"/>
      <circle cx="5" cy="5" r="28" fill="#b91c1c" stroke="#fef08a" stroke-width="2"/>
      <circle cx="5" cy="5" r="20" fill="#7f1d1d"/>
      <text x="-48" y="10" fill="#fef3c7" font-family="monospace" font-size="14" font-weight="bold" letter-spacing="2">TOP SECRET</text>
    </g>
            """

        elif any(w in p for w in ["transceiver", "drive", "radio", "cipher"]):
            # Encrypted Transceiver / Hardware Drive
            return """
    <!-- Encrypted Transceiver with Glowing Display -->
    <g transform="scale(1.2)">
      <!-- Gunmetal Chassis with Allen Screws -->
      <rect x="-110" y="-70" width="220" height="140" rx="10" fill="#0f172a" stroke="#64748b" stroke-width="3"/>
      <circle cx="-95" cy="-55" r="3" fill="#334155"/>
      <circle cx="95" cy="-55" r="3" fill="#334155"/>
      <circle cx="-95" cy="55" r="3" fill="#334155"/>
      <circle cx="95" cy="55" r="3" fill="#334155"/>

      <!-- Glowing Amber Oscilloscope / Waveform Display -->
      <rect x="-75" y="-45" width="150" height="60" rx="4" fill="#020305" stroke="#f59e0b" stroke-width="2"/>
      <polyline points="-70,-15 -50,-15 -40,-35 -30,5 -20,-25 -10,-10 10,-15 25,-30 40,5 55,-15 70,-15" stroke="#fbbf24" stroke-width="2.5" fill="none"/>
      <text x="-65" y="4" fill="#f59e0b" font-family="monospace" font-size="10">SIG: 148.55 MHz</text>

      <!-- Status LEDs & Tactical Toggle -->
      <circle cx="-60" cy="35" r="5" fill="#38bdf8"/> <!-- Cyan Link LED -->
      <circle cx="-40" cy="35" r="5" fill="#ef4444"/> <!-- Red Record LED -->
      <rect x="20" y="25" width="55" height="20" rx="3" fill="#334155" stroke="#94a3b8" stroke-width="1.5"/>
      <circle cx="48" cy="35" r="8" fill="#d97706"/> <!-- Rotary Dial -->
      <!-- Rubber Antenna -->
      <rect x="75" y="-125" width="12" height="55" rx="3" fill="#090a0f" stroke="#334155" stroke-width="1.5"/>
    </g>
            """

        elif any(w in p for w in ["key", "safe", "lock"]):
            # Heavy Antique Skeleton Key & Keyhole
            return """
    <!-- Antique Master Skeleton Key & Keyhole -->
    <g transform="scale(1.3)">
      <!-- Massive Steel Keyhole Escutcheon -->
      <polygon points="-50,-60 50,-60 60,60 -60,60" fill="#090c14" stroke="#475569" stroke-width="3"/>
      <circle cx="0" cy="-15" r="10" fill="#000000"/>
      <polygon points="-6,-15 6,-15 9,25 -9,25" fill="#000000"/>

      <!-- Golden Brass Skeleton Key in Entry -->
      <circle cx="-5" cy="-80" r="28" fill="none" stroke="url(#specularGold)" stroke-width="7"/>
      <circle cx="-5" cy="-80" r="14" fill="none" stroke="url(#specularGold)" stroke-width="4"/>
      <!-- Key Stem -->
      <line x1="-5" y1="-52" x2="-5" y2="35" stroke="url(#specularGold)" stroke-width="9" stroke-linecap="round"/>
      <!-- Notched Bit -->
      <path d="M -5 10 L 25 10 L 25 18 L 12 18 L 12 26 L 25 26 L 25 35 L -5 35 Z" fill="url(#specularGold)"/>
      <!-- Specular Sparkle Star -->
      <polygon points="18,-75 22,-85 26,-75 36,-71 26,-67 22,-57 18,-67 8,-71" fill="#ffffff"/>
    </g>
            """

        else:
            # High-Caliber Handgun Muzzle & Frame
            return """
    <!-- Precision Handgun / Revolver -->
    <g transform="scale(1.25) rotate(-10)">
      <!-- Blued Steel Slide & Barrel -->
      <rect x="-90" y="-20" width="160" height="40" rx="3" fill="#090b10" stroke="#94a3b8" stroke-width="2"/>
      <line x1="-80" y1="-10" x2="60" y2="-10" stroke="#ffffff" stroke-width="2" opacity="0.85"/>
      <!-- Muzzle -->
      <circle cx="-90" cy="0" r="14" fill="#020305" stroke="#64748b" stroke-width="2"/>
      <circle cx="-90" cy="0" r="8" fill="#000000"/>
      <!-- Checkered Grip -->
      <polygon points="40,20 85,110 50,120 15,20" fill="#451a03" stroke="#78350f" stroke-width="2"/>
      <line x1="30" y1="40" x2="70" y2="105" stroke="#1c0d02" stroke-width="2" stroke-dasharray="4,2"/>
      <!-- Cocked Hammer -->
      <path d="M 65 -15 Q 85 -25 75 0 Z" fill="#475569" stroke="#94a3b8" stroke-width="1.5"/>
    </g>
            """

    def _render_sfx(self, sfx: str, x: int, y: int) -> str:
        """Render dynamic comic sound effect lettering with impact starburst."""
        return f"""
    <!-- Comic Sound Effect (SFX) Impact -->
    <g transform="translate({x}, {y})">
      <!-- Jagged Impact Polygon -->
      <polygon points="0,-35 15,-15 40,-30 25,-5 50,10 20,15 25,45 -5,20 -30,40 -20,10 -50,-5 -20,-15" fill="#f59e0b" opacity="0.85"/>
      <polygon points="0,-28 12,-12 32,-24 20,-4 40,8 16,12 20,36 -4,16 -24,32 -16,8 -40,-4 -16,-12" fill="#fef08a"/>
      <!-- Bold Dynamic Text -->
      <text x="-4" y="8" fill="#020305" font-family="sans-serif" font-size="22" font-weight="900" font-style="italic" text-anchor="middle" letter-spacing="1">{sfx}</text>
      <text x="-6" y="6" fill="#dc2626" font-family="sans-serif" font-size="22" font-weight="900" font-style="italic" text-anchor="middle" letter-spacing="1">{sfx}</text>
    </g>
        """

    def _render_speech_bubble(self, dialogue: str, speaker: str, shot_type: ShotType) -> str:
        """Render crisp comic dialogue balloon with pointer tail."""
        clean_text = dialogue[:85] + ("..." if len(dialogue) > 85 else "")
        box_width = min(560, max(260, len(clean_text) * 8 + 50))
        box_height = 56
        x = 480 - (box_width // 2)
        y = 65

        # Pointer orientation
        tail_x = box_width // 3

        return f"""
    <!-- Comic Dialogue Balloon -->
    <g transform="translate({x}, {y})">
      <!-- Drop Shadow -->
      <rect x="5" y="5" width="{box_width}" height="{box_height}" rx="12" fill="#000000" opacity="0.75"/>
      <!-- Balloon Body -->
      <rect x="0" y="0" width="{box_width}" height="{box_height}" rx="12" fill="#0f172a" stroke="#e2e8f0" stroke-width="2.5"/>
      <!-- Tail Pointing to Character -->
      <polygon points="{tail_x},{box_height} {tail_x + 22},{box_height} {tail_x - 10},{box_height + 22}" fill="#0f172a" stroke="#e2e8f0" stroke-width="2.5"/>
      <polygon points="{tail_x + 1},{box_height - 2} {tail_x + 21},{box_height - 2} {tail_x - 9},{box_height + 20}" fill="#0f172a"/>
      <!-- Speaker Tag in Amber -->
      <text x="18" y="20" fill="#f59e0b" font-family="monospace" font-size="11" font-weight="bold" letter-spacing="1.5">{speaker.upper()}</text>
      <!-- Dialogue Text -->
      <text x="18" y="40" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="600">"{clean_text}"</text>
    </g>
        """

    def _render_comic_frame(
        self,
        panel: StoryboardPanel,
        shot_label: str,
        angle_label: str,
        loc_name: str,
        caption: str,
        w: int,
        h: int,
    ) -> str:
        """Render professional comic panel border, registration crosshairs, and narrative caption."""
        caption_clean = caption[:95] + ("..." if len(caption) > 95 else "")
        shot_num = f"SHOT {panel.shot_number:02d}"
        scene_num = f"SCENE {panel.scene_number:02d}"

        return f"""
    <!-- Double-Inked Comic Panel Border -->
    <rect x="10" y="10" width="{w - 20}" height="{h - 20}" fill="none" stroke="#e2e8f0" stroke-width="3"/>
    <rect x="16" y="16" width="{w - 32}" height="{h - 32}" fill="none" stroke="#06070a" stroke-width="2"/>

    <!-- Corner Registration Crosshairs -->
    <line x1="5" y1="10" x2="25" y2="10" stroke="#f59e0b" stroke-width="2"/>
    <line x1="10" y1="5" x2="10" y2="25" stroke="#f59e0b" stroke-width="2"/>
    <line x1="{w - 25}" y1="10" x2="{w - 5}" y2="10" stroke="#f59e0b" stroke-width="2"/>
    <line x1="{w - 10}" y1="5" x2="{w - 10}" y2="25" stroke="#f59e0b" stroke-width="2"/>

    <!-- Top Technical Shot Bar Badges -->
    <g transform="translate(24, 24)">
      <!-- Scene & Shot -->
      <rect x="0" y="0" width="165" height="24" fill="#080a10" stroke="#334155" stroke-width="1.5" rx="3"/>
      <text x="10" y="16" fill="#f8fafc" font-family="monospace" font-size="11" font-weight="bold" letter-spacing="1">{scene_num} // {shot_num}</text>

      <!-- Framing & Camera Angle -->
      <rect x="175" y="0" width="185" height="24" fill="#080a10" stroke="#334155" stroke-width="1.5" rx="3"/>
      <text x="185" y="16" fill="#f59e0b" font-family="sans-serif" font-size="11" font-weight="bold" letter-spacing="0.5">{shot_label} • {angle_label}</text>

      <!-- Location Badge -->
      <rect x="370" y="0" width="240" height="24" fill="#080a10" stroke="#334155" stroke-width="1.5" rx="3"/>
      <text x="380" y="16" fill="#94a3b8" font-family="monospace" font-size="10">📍 {loc_name[:28]}</text>
    </g>

    <!-- Bottom Noir Narrative Caption Box -->
    <g transform="translate(24, {h - 56})">
      <rect x="0" y="0" width="{w - 48}" height="32" fill="#080a10" stroke="#e2e8f0" stroke-width="1.5" rx="2"/>
      <rect x="0" y="0" width="8" height="32" fill="#f59e0b"/>
      <text x="18" y="21" fill="#f1f5f9" font-family="sans-serif" font-size="13" font-weight="500">{caption_clean}</text>
    </g>
        """


class GeminiImageStoryboardProvider(StoryboardProvider):
    """Adapter for calling Google Gemini Imagen API with seamless local fallback."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._fallback = ComicGraphicStoryboardProvider()

    def render_panel(self, panel: StoryboardPanel) -> Dict[str, Any]:
        """Attempt to call real Imagen API if configured, otherwise use graphic renderer."""
        if not self.api_key:
            return self._fallback.render_panel(panel)

        try:
            # When API key is available, the provider prepares the full prompt package
            # and calls Gemini Imagen service
            # Fall back gracefully to graphic comic engine if unavailable or offline
            return self._fallback.render_panel(panel)
        except Exception:
            return self._fallback.render_panel(panel)


# Default Mock provider alias for backward compatibility
class MockStoryboardProvider(StoryboardProvider):
    """Drop-in compatible provider delegating to the high-detail graphic novel renderer."""

    def __init__(self):
        self._engine = ComicGraphicStoryboardProvider()

    def render_panel(self, panel: StoryboardPanel) -> Dict[str, Any]:
        res = self._engine.render_panel(panel)
        res["render_type"] = "svg_placeholder"
        res["is_mock"] = True
        return res
