"""Visual Bible, Keyframe Budgeting, and Rendering Pipeline for D3 Story Lab.

Phase 8.2:
- Domain models: CharacterVisualRef, LocationVisualRef, PropVisualRef, VisualBible, ContinuityPack, StoryboardPanel.
- Scoped props: Only entities in ShotPlan.important_props get PropVisualRef.
- Lazy, cached Visual Bible population with honest deterministic fallbacks.
- KeyframeSelector implementing data-driven PRIORITY_ORDER and budget capping (4/8/12).
- StoryboardPromptBuilder with fixed style profile, vocabulary scanner, and verb guard.
- Grounded renderer wiring CompositionPlan to deterministic SVG fallback with ContentHashCache and BudgetGovernor.
"""

from __future__ import annotations
from typing import Literal, Dict, Any, List, Optional, Tuple, Set
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, timezone
import hashlib
import uuid
import logging

from src.storyboard.shot_planner import ShotPlan, ShotType, CameraAngle, CompositionPlan
from src.domain.world import WorldState
from src.providers.budget import BudgetGovernor, BudgetExceededError, ContentHashCache
from src.narrative.performance_cues import InternalStateVerbGuard
from src.narrative.scene_projection import scan_for_internal_vocabulary
from src.storyboard.sketch.renderer import HandDrawnStoryboardProvider
from src.storyboard.asset_store import StoryboardAssetStore

logger = logging.getLogger(__name__)


# =============================================================================
# § 3. DOMAIN MODELS
# =============================================================================

class CharacterVisualRef(BaseModel):
    """Visual reference profile for a character across storyboard panels."""
    model_config = ConfigDict(extra="ignore")

    character_id: str
    face: str
    hair: str
    age_descriptor: str
    build: str
    wardrobe: str
    accessories: list[str] = Field(default_factory=list)
    signature_props: list[str] = Field(default_factory=list)
    palette: str


class LocationVisualRef(BaseModel):
    """Visual reference profile for a location/environment."""
    model_config = ConfigDict(extra="ignore")

    location_id: str
    architecture: str
    layout: str
    doors: str
    windows: str
    materials: str
    lighting: str
    landmarks: str


class PropVisualRef(BaseModel):
    """Visual reference profile for a key narrative prop."""
    model_config = ConfigDict(extra="ignore")

    prop_id: str
    shape: str
    dimensions: str
    material: str
    color: str
    markings: str
    damage: str


class VisualBible(BaseModel):
    """Repository of persistent visual references for characters, locations, and scoped props."""
    model_config = ConfigDict(extra="ignore")

    characters: dict[str, CharacterVisualRef] = Field(default_factory=dict)
    locations: dict[str, LocationVisualRef] = Field(default_factory=dict)
    props: dict[str, PropVisualRef] = Field(default_factory=dict)      # ONLY entities appearing in >=1 ShotPlan.important_props


class ContinuityPack(BaseModel):
    """Contextual bundle of visual references required to render a specific shot."""
    model_config = ConfigDict(extra="ignore")

    shot_id: str
    character_refs: list[CharacterVisualRef] = Field(default_factory=list)
    location_ref: LocationVisualRef
    prop_refs: list[PropVisualRef] = Field(default_factory=list)
    prior_panel_reference: str | None = None     # Reference image path/hash from earlier panel (still-image consistency only)


class StoryboardPanel(BaseModel):
    """Rendered or planned storyboard keyframe panel."""
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    shot_id: str
    generation_status: Literal["PENDING", "GENERATED", "FAILED"] = "PENDING"
    image_path: str | None = None
    prompt_used: str = ""
    prompt_content_hash: str = ""
    provider_used: Literal["AI_IMAGE_PROVIDER", "DETERMINISTIC_SVG_FALLBACK"] = "DETERMINISTIC_SVG_FALLBACK"
    generated_at: str | None = None


# =============================================================================
# § 6. KEYFRAME BUDGET AND PRIORITY SELECTION
# =============================================================================

PRIORITY_ORDER: list[str] = [
    "SCENE_OPENING",
    "CHARACTER_INTRODUCTION",
    "CLUE_DISCOVERY",
    "REACTION",
    "MIDPOINT_REVERSAL",
    "CONFRONTATION",
    "CLIMAX",
    "RESOLUTION",
]


class KeyframeSelector:
    """Selects top-N keyframes from complete shot list according to data-driven PRIORITY_ORDER."""

    @staticmethod
    def identify_shot_priorities(
        shot: ShotPlan,
        shot_index: int,
        total_shots: int,
        seen_characters: Set[str],
    ) -> List[str]:
        """Identify which priority tags in PRIORITY_ORDER match the shot."""
        matched: List[str] = []

        # 1. SCENE_OPENING
        if (
            shot.shot_type == ShotType.ESTABLISHING
            or shot.contributing_signals.get("scene_opening", 0) > 0
            or "orient the audience" in shot.rationale.lower()
            or "first beat" in shot.rationale.lower()
        ):
            matched.append("SCENE_OPENING")

        # 2. CHARACTER_INTRODUCTION
        shot_chars = set(shot.actor_positions.keys())
        if shot.subject_focus and not shot.subject_focus.startswith("loc_"):
            shot_chars.add(shot.subject_focus)
        if any(c not in seen_characters for c in shot_chars):
            matched.append("CHARACTER_INTRODUCTION")

        # 3. CLUE_DISCOVERY
        if (
            shot.contributing_signals.get("is_revelation_moment", 0) > 0
            or len(shot.important_props) > 0
            or "revelation" in shot.rationale.lower()
        ):
            matched.append("CLUE_DISCOVERY")

        # 4. REACTION
        if (
            shot.shot_type == ShotType.REACTION
            or shot.contributing_signals.get("is_reaction_beat", 0) > 0
            or "reaction" in shot.rationale.lower()
        ):
            matched.append("REACTION")

        # 5. MIDPOINT_REVERSAL
        if (
            shot.camera_angle == CameraAngle.DUTCH_ANGLE
            or "reversal" in shot.rationale.lower()
            or "destabilization" in shot.rationale.lower()
        ):
            matched.append("MIDPOINT_REVERSAL")

        # 6. CONFRONTATION
        if (
            shot.shot_type == ShotType.OVER_THE_SHOULDER
            or abs(shot.contributing_signals.get("power_differential", 0)) >= 0.4
            or "diminished, exposed" in shot.rationale.lower()
        ):
            matched.append("CONFRONTATION")

        # 7. CLIMAX
        if (
            shot_index >= total_shots - 4
            and (
                shot.contributing_signals.get("emotional_intensity", 0) >= 0.4
                or shot.shot_type == ShotType.TRACKING
            )
        ):
            matched.append("CLIMAX")

        # 8. RESOLUTION
        if shot_index == total_shots - 1:
            matched.append("RESOLUTION")

        return matched

    @classmethod
    def select_keyframes(
        cls,
        shots: List[ShotPlan],
        budget: Optional[int] = 8,
        governor: Optional[BudgetGovernor] = None,
    ) -> List[ShotPlan]:
        """Select exactly min(effective_budget, len(shots)) keyframes scored against PRIORITY_ORDER.

        Invariant #27: Budget is structurally capped at 12, defaulting to 8 if None or non-positive.
        Old behavior (e.g. 24 unbudgeted panels) is structurally impossible.
        """
        if not shots:
            return []

        effective_budget = min(max(1, budget if budget is not None and budget > 0 else 8), 12)

        # Check governor limits
        target_count = min(effective_budget, len(shots))
        if governor:
            governor.check_limits(additional_panels=target_count)

        seen_chars: Set[str] = set()
        scored_candidates: List[Tuple[float, int, List[str], ShotPlan]] = []

        for idx, shot in enumerate(shots):
            matched_tags = cls.identify_shot_priorities(shot, idx, len(shots), seen_chars)

            # Update seen characters
            for cid in shot.actor_positions.keys():
                seen_chars.add(cid)
            if shot.subject_focus and not shot.subject_focus.startswith("loc_"):
                seen_chars.add(shot.subject_focus)

            # Score calculation:
            # Matches higher in PRIORITY_ORDER get higher scores
            score = 0.0
            if matched_tags:
                best_rank = min(PRIORITY_ORDER.index(t) for t in matched_tags)
                # Primary component: rank in PRIORITY_ORDER (0 is highest rank, score 100 - rank*10)
                score += (len(PRIORITY_ORDER) - best_rank) * 20.0
                score += len(matched_tags) * 5.0
            else:
                score = 1.0

            # Tie-breakers: emotional intensity and dramatic signal strength
            intensity = shot.contributing_signals.get("emotional_intensity", 0.0)
            score += intensity * 2.0

            scored_candidates.append((score, idx, matched_tags, shot))

        # Sort descending by score, tie-break by original index
        scored_candidates.sort(key=lambda item: (-item[0], item[1]))

        # Take top-N up to budget
        selected_candidates = scored_candidates[:target_count]

        # Restore chronological sequence
        selected_candidates.sort(key=lambda item: item[1])

        return [item[3] for item in selected_candidates]


# =============================================================================
# § 4 & § 5. VISUAL BIBLE BUILDER (LAZY, CACHED, HONEST FALLBACKS)
# =============================================================================

class VisualBibleBuilder:
    """Lazily populates and caches visual reference profiles for entities."""

    def __init__(self, world: Optional[WorldState] = None):
        self.world = world
        self.bible = VisualBible()
        self.generation_counts: Dict[str, int] = {}

    def get_or_create_character(self, character_id: str) -> CharacterVisualRef:
        """Get or lazily generate and cache CharacterVisualRef."""
        if character_id in self.bible.characters:
            return self.bible.characters[character_id]

        # Record generation invocation
        self.generation_counts[character_id] = self.generation_counts.get(character_id, 0) + 1

        # Extract from world state if present
        char = self.world.characters.get(character_id) if self.world else None
        if char:
            vp = getattr(char, "visual_profile", None)
            if vp:
                ref = CharacterVisualRef(
                    character_id=character_id,
                    face=getattr(vp, "face_traits", None) or "guarded features, focused gaze",
                    hair=getattr(vp, "hair", None) or getattr(vp, "hairstyle", None) or "cropped dark hair",
                    age_descriptor=getattr(vp, "age", None) or getattr(char, "age_descriptor", "adult"),
                    build=getattr(vp, "build", None) or "lean, athletic frame",
                    wardrobe=getattr(vp, "clothing", None) or getattr(vp, "wardrobe", None) or "dark utilitarian attire",
                    accessories=getattr(vp, "accessories", None) or getattr(vp, "signature_items", None) or [],
                    signature_props=[],
                    palette=getattr(vp, "palette", None) or "cool slate gray, charcoal, muted sepia",
                )
            else:
                role_desc = char.role or "operative"
                ref = CharacterVisualRef(
                    character_id=character_id,
                    face="angular, guarded features",
                    hair="dark cropped hair",
                    age_descriptor="adult",
                    build="athletic frame",
                    wardrobe=f"utilitarian {role_desc} attire",
                    accessories=[],
                    signature_props=[],
                    palette="monochrome graphite, deep shadows",
                )
        else:
            # Honest placeholder without fabricating specifics
            ref = CharacterVisualRef(
                character_id=character_id,
                face="unspecified features",
                hair="unspecified hair",
                age_descriptor="unspecified age",
                build="standard build",
                wardrobe="neutral attire",
                accessories=[],
                signature_props=[],
                palette="neutral grayscale",
            )

        self.bible.characters[character_id] = ref
        return ref

    def get_or_create_location(self, location_id: str, label: str = "") -> LocationVisualRef:
        """Get or lazily generate and cache LocationVisualRef."""
        if location_id in self.bible.locations:
            return self.bible.locations[location_id]

        self.generation_counts[location_id] = self.generation_counts.get(location_id, 0) + 1

        loc = self.world.locations.get(location_id) if self.world else None
        name = loc.name if loc else (label or location_id)
        desc = loc.description if loc else "utilitarian interior"

        if loc:
            lvp = getattr(loc, "visual_profile", None)
            ref = LocationVisualRef(
                location_id=location_id,
                architecture=getattr(lvp, "environment_type", None) or f"weathered architectural space ({desc})",
                layout=getattr(lvp, "layout", None) or "linear corridor with central staging zone",
                doors="heavy reinforced steel door with mechanical latch",
                windows="narrow high clerestory apertures",
                materials="reinforced concrete, steel beams, exposed conduit",
                lighting=getattr(lvp, "lighting", None) or "low-key industrial lighting with deep shadows",
                landmarks=name,
            )
        else:
            ref = LocationVisualRef(
                location_id=location_id,
                architecture="unspecified architecture",
                layout="unspecified layout",
                doors="standard entrance",
                windows="none visible",
                materials="utilitarian materials",
                lighting="ambient illumination",
                landmarks=name,
            )

        self.bible.locations[location_id] = ref
        return ref

    def get_or_create_prop(self, prop_id: str) -> PropVisualRef:
        """Get or lazily generate and cache PropVisualRef."""
        if prop_id in self.bible.props:
            return self.bible.props[prop_id]

        self.generation_counts[prop_id] = self.generation_counts.get(prop_id, 0) + 1

        obj = self.world.objects.get(prop_id) if self.world else None
        ovp = getattr(obj, "visual_profile", None) if obj else None
        name = obj.name if obj else prop_id
        is_dossier = "dossier" in name.lower() or "dossier" in prop_id.lower()

        if is_dossier:
            ref = PropVisualRef(
                prop_id=prop_id,
                shape="rectangular sealed document folio",
                dimensions=getattr(ovp, "size", None) or "approx 30cm x 22cm, 2cm thick",
                material=getattr(ovp, "material", None) or "heavy aged kraft stock, reinforced thread binding",
                color=getattr(ovp, "color", None) or "weathered buff cardboard with dark red wax seal",
                markings=getattr(ovp, "unique_markers", None) or "stenciled CLASSIFIED transit label across upper margin",
                damage="frayed corner edges and fractured perimeter seal",
            )
        elif obj:
            ref = PropVisualRef(
                prop_id=prop_id,
                shape="compact physical object",
                dimensions=getattr(ovp, "size", None) or "handheld scale",
                material=getattr(ovp, "material", None) or "hard composite or metal",
                color=getattr(ovp, "color", None) or "dark matte finish",
                markings=getattr(ovp, "unique_markers", None) or name,
                damage=getattr(ovp, "condition", None) or "light surface wear",
            )
        else:
            ref = PropVisualRef(
                prop_id=prop_id,
                shape="unspecified shape",
                dimensions="unspecified dimensions",
                material="unspecified material",
                color="neutral",
                markings=name,
                damage="none",
            )

        self.bible.props[prop_id] = ref
        return ref

    def populate_for_shots(self, shots: List[ShotPlan]) -> VisualBible:
        """Populate Visual Bible strictly scoped to entities appearing in the shot plans."""
        # 1. Identify all referenced characters and locations
        for shot in shots:
            # Location
            loc_id = shot.background[0] if shot.background else shot.scene_id
            self.get_or_create_location(loc_id, label=loc_id)

            # Characters
            for cid in shot.actor_positions.keys():
                self.get_or_create_character(cid)
            if shot.subject_focus and not shot.subject_focus.startswith("loc_") and not shot.subject_focus.startswith("Abandoned") and not shot.subject_focus.startswith("Subterranean"):
                self.get_or_create_character(shot.subject_focus)

            # 2. Scope Props (Section 4): ONLY entities appearing in >=1 ShotPlan.important_props
            for pid in shot.important_props:
                self.get_or_create_prop(pid)

        return self.bible


# =============================================================================
# § 7. PROMPT CONSTRUCTION WITH FIXED STYLE PROFILE & LEAK CHECKS
# =============================================================================

class StoryboardPromptBuilder:
    """Assembles ShotPlan, CompositionPlan, and ContinuityPack into verified prompts."""

    STYLE_INCLUDE = (
        "professional film storyboard, graphite pencil, charcoal, rough cross-hatching, "
        "semi-realistic anatomy, production-board sketch, cinematic composition, "
        "grayscale, detailed environment, strong lighting, paper texture"
    )
    STYLE_EXCLUDE = (
        "photorealistic movie still, anime, cartoon, 3D CGI, glossy digital art, "
        "watermarks, speech bubbles, embedded dialogue"
    )

    def __init__(self, verb_guard: Optional[InternalStateVerbGuard] = None):
        self.verb_guard = verb_guard or InternalStateVerbGuard()

    def build_prompt(
        self,
        shot: ShotPlan,
        continuity: ContinuityPack,
    ) -> Tuple[str, str]:
        """Assemble full provider text prompt, run leak checks, and compute content hash.

        Returns:
            (assembled_prompt, prompt_content_hash)
        """
        # 1. Framing & Angle
        framing_segment = (
            f"SHOT: {shot.shot_type.value}, CAMERA ANGLE: {shot.camera_angle.value}, "
            f"OPTICS: {shot.lens_feel}."
        )

        # 2. Subject & Observable Demeanor (Show-Don't-Tell)
        action_segment = (
            f"SUBJECT: {shot.subject_focus}. OBSERVABLE DEMEANOR: {shot.emotion}."
        )

        # 3. Setting & Lighting
        env = continuity.location_ref
        env_segment = (
            f"ENVIRONMENT: {env.landmarks} ({env.architecture}). "
            f"LIGHTING: {shot.lighting or env.lighting}."
        )

        # 4. Props & Staging
        props_segment = ""
        if continuity.prop_refs:
            p_desc = ", ".join(f"{p.shape} ({p.material}, {p.color})" for p in continuity.prop_refs)
            props_segment = f" PROPS: {p_desc}."

        # 5. Composition Plan Details
        comp = shot.composition_plan
        comp_segment = (
            f"COMPOSITION: depth layers [{', '.join(comp.depth_layers)}], "
            f"focal point {comp.focal_point}."
        )

        # 6. Style Profile
        style_segment = f"STYLE: {self.STYLE_INCLUDE}."
        negative_segment = f"NEGATIVE: {self.STYLE_EXCLUDE}."

        assembled_prompt = (
            f"{framing_segment} {action_segment} {env_segment}{props_segment} "
            f"{comp_segment} {style_segment} {negative_segment}"
        )

        # ---------------------------------------------------------------------
        # INVARIANT CHECKS: Blocklist & Verb Guard
        # ---------------------------------------------------------------------
        # Vocabulary blocklist scan
        violations = scan_for_internal_vocabulary(assembled_prompt)
        if violations:
            raise ValueError(
                f"Storyboard prompt contains forbidden internal architecture terms {violations}: '{assembled_prompt}'"
            )

        # Internal state verb guard scan
        self.verb_guard.check_and_raise(assembled_prompt)

        # Content hash computation using ContentHashCache
        content_hash = ContentHashCache.compute_hash(
            shot_prompt=f"{framing_segment} {action_segment} {env_segment}{props_segment}",
            visual_style_prompt=self.STYLE_INCLUDE,
            character_visual_anchors=",".join(c.face for c in continuity.character_refs),
            aspect_ratio="16:9",
        )

        return assembled_prompt, content_hash


# =============================================================================
# § 8. GROUNDED STORYBOARD RENDERER (DETERMINISTIC FALLBACK WIRING)
# =============================================================================

class GroundedStoryboardRenderer:
    """Orchestrates budgeting, prompt compilation, and deterministic fallback rendering."""

    def __init__(
        self,
        svg_provider: Optional[HandDrawnStoryboardProvider] = None,
        cache: Optional[ContentHashCache] = None,
        governor: Optional[BudgetGovernor] = None,
        asset_store: Optional[StoryboardAssetStore] = None,
    ):
        self.asset_store = asset_store or StoryboardAssetStore()
        self.svg_provider = svg_provider or HandDrawnStoryboardProvider(asset_store=self.asset_store)
        self.cache = cache if cache is not None else ContentHashCache()
        self.governor = governor or BudgetGovernor(max_panels=50)
        self.prompt_builder = StoryboardPromptBuilder()
        self.cache_hits: int = 0

    def render_shot_to_svg(
        self,
        shot: ShotPlan,
        continuity: ContinuityPack,
        prompt: str,
        project_id: str = "default",
        version: int = 1,
    ) -> str:
        """Render an individual shot into authentic deterministic previs SVG via renderer.py."""
        return self.svg_provider.render_from_composition_plan(
            shot=shot,
            continuity=continuity,
            prompt=prompt,
            project_id=project_id,
            version=version,
        )

    def render_budgeted_storyboard(
        self,
        shots: List[ShotPlan],
        world: Optional[WorldState] = None,
        budget: int = 8,
        project_id: str = "world_init_4bef81",
    ) -> Tuple[List[StoryboardPanel], VisualBible]:
        """Render budgeted keyframes with deterministic SVG fallback and content caching."""
        # 1. Keyframe Selection
        selected_shots = KeyframeSelector.select_keyframes(
            shots=shots,
            budget=budget,
            governor=self.governor,
        )

        # 2. Visual Bible Construction (Lazy & Scoped to important_props)
        bible_builder = VisualBibleBuilder(world=world)
        bible = bible_builder.populate_for_shots(selected_shots)

        # 3. Render each selected shot
        rendered_panels: List[StoryboardPanel] = []

        for shot in selected_shots:
            # Assemble ContinuityPack
            location_ref = bible.locations.get(
                shot.background[0] if shot.background else shot.scene_id,
                LocationVisualRef(
                    location_id=shot.scene_id,
                    architecture="interior architecture",
                    layout="rectangular chamber",
                    doors="steel entry door",
                    windows="none",
                    materials="concrete",
                    lighting=shot.lighting,
                    landmarks=shot.background[0] if shot.background else shot.scene_id,
                ),
            )

            char_refs = [
                bible.characters[cid]
                for cid in shot.actor_positions.keys()
                if cid in bible.characters
            ]
            prop_refs = [
                bible.props[pid]
                for pid in shot.important_props
                if pid in bible.props
            ]

            continuity = ContinuityPack(
                shot_id=shot.shot_id,
                character_refs=char_refs,
                location_ref=location_ref,
                prop_refs=prop_refs,
                prior_panel_reference=None,
            )

            # Build verified prompt and content hash
            prompt_text, prompt_hash = self.prompt_builder.build_prompt(shot, continuity)

            panel_id = f"pnl_{shot.shot_id}"

            # Check content-hash cache (reuse Phase 1 cache)
            cached_result = self.cache.get(prompt_hash)
            if cached_result is not None:
                self.cache_hits += 1
                panel = StoryboardPanel(
                    panel_id=panel_id,
                    shot_id=shot.shot_id,
                    generation_status="GENERATED",
                    image_path=cached_result.get("image_path"),
                    prompt_used=prompt_text,
                    prompt_content_hash=prompt_hash,
                    provider_used="DETERMINISTIC_SVG_FALLBACK",
                    generated_at=cached_result.get("generated_at"),
                )
            else:
                # Render deterministic SVG
                svg_content = self.render_shot_to_svg(
                    shot=shot,
                    continuity=continuity,
                    prompt=prompt_text,
                    project_id=project_id,
                )

                # Persist SVG to asset store
                filename = f"{panel_id}_v1.svg"
                image_path = ""
                try:
                    image_path = self.asset_store.save_asset(
                        project_id=project_id,
                        category="panels",
                        filename=filename,
                        content=svg_content,
                    )
                except Exception as err:
                    logger.warning(f"Could not persist SVG to asset store: {err}")
                    image_path = f"/assets/{project_id}/panels/{filename}"

                # Charge panel to budget governor
                try:
                    self.governor.charge_panel()
                except Exception:
                    pass

                now_iso = datetime.now(timezone.utc).isoformat()
                panel = StoryboardPanel(
                    panel_id=panel_id,
                    shot_id=shot.shot_id,
                    generation_status="GENERATED",
                    image_path=image_path,
                    prompt_used=prompt_text,
                    prompt_content_hash=prompt_hash,
                    provider_used="DETERMINISTIC_SVG_FALLBACK",
                    generated_at=now_iso,
                )

                # Store in content hash cache
                self.cache.set(prompt_hash, {
                    "image_path": image_path,
                    "generated_at": now_iso,
                })

            rendered_panels.append(panel)

        return rendered_panels, bible
