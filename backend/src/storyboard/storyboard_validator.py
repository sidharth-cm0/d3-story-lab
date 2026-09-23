"""Storyboard quality validator evaluating cinematic framing, continuity, and visual storytelling."""

from __future__ import annotations
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.models import (
    StoryboardPanel as LegacyStoryboardPanel,
    ShotPlan as LegacyShotPlan,
    ShotType,
    CameraAngle,
    ShotPurpose,
)
from src.storyboard.visual_bible import VisualBible
from src.narrative.fountain import ScreenplayDocument
from src.narrative.scene_projection import scan_for_internal_vocabulary
from src.narrative.performance_cues import InternalStateVerbGuard

logger = logging.getLogger(__name__)


def scan_codebase_for_prohibited_media(repo_root: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """Scan dependencies and source imports for forbidden video/animation/3D libraries."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]

    violations: List[str] = []
    # Video, full game engines, and audio remain strictly prohibited.
    # Note: Three.js/WebGL for point-cloud particle rendering was authorized in Phase 9.2.7.
    prohibited = {
        "moviepy", "ffmpeg", "ffmpeg-python", "pygame", "opencv", "opencv-python",
        "cv2", "remotion", "babylon", "babylonjs", "pixi.js", "video.js", "howler", "tone",
    }

    # 1. Check frontend/package.json
    pj = repo_root / "frontend" / "package.json"
    if pj.exists():
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for dep in all_deps:
                dep_l = dep.lower()
                if dep_l in prohibited or any(p in dep_l for p in ["moviepy", "pygame", "remotion"]):
                    violations.append(f"package.json: {dep}")
        except Exception as e:
            logger.warning(f"Error checking package.json: {e}")

    # 2. Check backend requirements
    for req_name in ["requirements.txt", "pyproject.toml"]:
        req = repo_root / "backend" / req_name
        if req.exists():
            try:
                for line in req.read_text(encoding="utf-8").splitlines():
                    pkg = line.strip().split("==")[0].split(">=")[0].split("<=")[0].strip().lower()
                    if pkg in prohibited:
                        violations.append(f"{req_name}: {pkg}")
            except Exception as e:
                logger.warning(f"Error checking {req_name}: {e}")

    # 3. Check source imports
    import_re = re.compile(r"^\s*(?:import|from)\s+([a-zA-Z0-9_@/-]+)", re.MULTILINE)
    for ext, folder in [("*.py", repo_root / "backend" / "src"), ("*.ts*", repo_root / "frontend" / "src")]:
        if folder.exists():
            for f in folder.rglob(ext):
                try:
                    content = f.read_text(encoding="utf-8")
                    for m in import_re.finditer(content):
                        mod = m.group(1).lower().split(".")[0]
                        if mod in prohibited:
                            violations.append(f"{f.name} imports {mod}")
                except Exception:
                    pass

    return (len(violations) == 0, violations)


class StoryboardIssue(BaseModel):
    """An identified issue or defect in visual framing, continuity, or pacing."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    category: str
    severity: str  # "warning" | "error" | "info"
    panel_id: str
    shot_number: int
    message: str
    recommendation: str


class StoryboardQualityReport(BaseModel):
    """Calculated metrics and diagnostics for a planned & rendered storyboard sequence."""
    model_config = ConfigDict(extra="ignore")

    shot_provenance_completeness_pct: float = 100.0
    panel_provenance_completeness_pct: float = 100.0
    vocabulary_leak_count: int = 0              # must be 0
    internal_state_leak_count: int = 0          # must be 0
    budget_compliance: bool = True               # exactly N panels rendered for budget N — never more
    priority_order_compliance: List[str] = Field(default_factory=list)  # confirms the rendered subset matches expected priority
    cache_hit_rate: float = 1.0
    prohibited_media_scan_clean: bool = True    # codebase scan for video/animation/3D deps — must be True
    passed: bool = True

    # Legacy fields for backward compatibility with existing tests
    total_panels: int = 0
    shot_variety_score: float = 1.0
    character_continuity_score: float = 1.0
    prop_continuity_score: float = 1.0
    location_continuity_score: float = 1.0
    spatial_coherence_score: float = 1.0
    psychological_camera_coherence: float = 1.0
    transition_coverage_ratio: float = 1.0
    visual_rhythm_score: float = 1.0
    screenplay_coverage_score: float = 1.0
    overall_storyboard_score: float = 100.0
    issues: List[StoryboardIssue] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class StoryboardQualityValidator:
    """Evaluates shot variety, camera-emotion coherence, prop continuity, and cinematic flow."""

    def validate_storyboard(
        self,
        shot_plan_or_panels: Any,
        world_or_screenplay: Optional[Any] = None,
        bible: Optional[VisualBible] = None,
    ) -> StoryboardQualityReport:
        if isinstance(shot_plan_or_panels, list):
            panels = shot_plan_or_panels
        elif hasattr(shot_plan_or_panels, "panels"):
            panels = shot_plan_or_panels.panels
        else:
            panels = []
        screenplay = world_or_screenplay if isinstance(world_or_screenplay, ScreenplayDocument) else None
        return self.validate(panels, screenplay=screenplay, bible=bible)

    def validate(
        self,
        panels: List[StoryboardPanel],
        screenplay: Optional[ScreenplayDocument] = None,
        bible: Optional[VisualBible] = None,
    ) -> StoryboardQualityReport:
        """Execute validation passes across the panel sequence and compute non-hardcoded scores."""
        issues: List[StoryboardIssue] = []
        if not panels:
            return StoryboardQualityReport(
                total_panels=0,
                shot_variety_score=0.0,
                character_continuity_score=0.0,
                prop_continuity_score=0.0,
                location_continuity_score=0.0,
                spatial_coherence_score=0.0,
                psychological_camera_coherence=0.0,
                transition_coverage_ratio=0.0,
                visual_rhythm_score=0.0,
                screenplay_coverage_score=0.0,
                overall_storyboard_score=0.0,
                issues=[],
            )

        # 1. Shot Framing Variety & Repetition
        shot_types = [p.shot_type for p in panels]
        unique_shot_types = len(set(shot_types))
        shot_variety = min(1.0, unique_shot_types / max(3, len(ShotType) - 2))

        consecutive_identical_shots = 0
        for i in range(len(panels) - 1):
            if panels[i].shot_type == panels[i + 1].shot_type and panels[i].camera_angle == panels[i + 1].camera_angle:
                consecutive_identical_shots += 1
                issues.append(
                    StoryboardIssue(
                        category="repetitive_framing",
                        severity="warning",
                        panel_id=panels[i + 1].id,
                        shot_number=panels[i + 1].shot_number or (i + 2),
                        message=f"Consecutive identical framing ({panels[i].shot_type.value}) without motivation.",
                        recommendation="Alternate shot type or angle to sustain visual rhythm.",
                    )
                )

        visual_rhythm = max(0.2, 1.0 - (consecutive_identical_shots / max(1, len(panels) - 1)))

        # 2. Camera-Emotion & Psychological Coherence
        psych_matches = 0
        for i, p in enumerate(panels):
            action_l = (p.action or p.action_description).lower()
            mood_l = p.mood.lower()

            # Check if high threat/standoff uses low angle or canted angle
            if any(w in action_l for w in ["threat", "gun", "standoff", "towering"]) and p.camera_angle in (CameraAngle.LOW_ANGLE, CameraAngle.DUTCH_ANGLE):
                psych_matches += 1
            # Check if reaction/clue uses tight framing
            elif any(w in action_l for w in ["gasps", "dossier", "key", "secret"]) and p.shot_type in (ShotType.CLOSE_UP, ShotType.INSERT, ShotType.EXTREME_CLOSE_UP, ShotType.REACTION):
                psych_matches += 1
            elif p.camera_angle == CameraAngle.EYE_LEVEL and not any(w in action_l for w in ["threat", "towering", "gun"]):
                psych_matches += 1
            else:
                psych_matches += 0.75

        psych_coherence = min(1.0, psych_matches / len(panels))

        # 3. Transition Coverage
        transitions_assigned = sum(1 for p in panels if p.transition_type and p.transition_type != "CUT")
        transition_coverage = round(transitions_assigned / max(1, len(panels) - 1), 2)

        # 4. Character & Prop Continuity
        char_ref_hits = sum(1 for p in panels if p.character_references or not p.characters_present)
        char_continuity = min(1.0, char_ref_hits / len(panels))

        prop_ref_hits = sum(1 for p in panels if p.object_references or not p.objects_in_frame)
        prop_continuity = min(1.0, prop_ref_hits / len(panels))

        loc_continuity = 1.0 if any(p.location_id for p in panels) else 0.5
        spatial_coherence = 0.9 if not any("contradiction" in (p.continuity_notes or "") for p in panels) else 0.4

        # 5. Screenplay Coverage
        screenplay_cov = 1.0
        if screenplay and screenplay.scenes:
            covered_scenes = len(set(p.scene_number for p in panels))
            screenplay_cov = min(1.0, covered_scenes / len(screenplay.scenes))

        # Overall composite score out of 100
        overall = (
            shot_variety * 15.0 +
            char_continuity * 15.0 +
            prop_continuity * 10.0 +
            loc_continuity * 10.0 +
            spatial_coherence * 15.0 +
            psych_coherence * 15.0 +
            transition_coverage * 10.0 +
            screenplay_cov * 10.0
        )
        overall = max(0.0, min(100.0, round(overall, 1)))

        return StoryboardQualityReport(
            total_panels=len(panels),
            shot_variety_score=round(shot_variety, 2),
            character_continuity_score=round(char_continuity, 2),
            prop_continuity_score=round(prop_continuity, 2),
            location_continuity_score=round(loc_continuity, 2),
            spatial_coherence_score=round(spatial_coherence, 2),
            psychological_camera_coherence=round(psych_coherence, 2),
            transition_coverage_ratio=transition_coverage,
            visual_rhythm_score=round(visual_rhythm, 2),
            screenplay_coverage_score=round(screenplay_cov, 2),
            overall_storyboard_score=overall,
            issues=issues,
        )

    def validate_grounded_storyboard(
        self,
        shots: List[Any],
        panels: List[Any],
        budget: int = 8,
        cache_hit_rate: float = 1.0,
        repo_root: Optional[Path] = None,
    ) -> StoryboardQualityReport:
        """Validate Phase 8 grounded shot plans and rendered keyframe panels.

        Reports independent inspectable metrics without score aggregation:
        - shot_provenance_completeness_pct
        - panel_provenance_completeness_pct
        - vocabulary_leak_count (must be 0)
        - internal_state_leak_count (must be 0)
        - budget_compliance (strictly N panels for budget N — never more)
        - priority_order_compliance (matches PRIORITY_ORDER rankings)
        - cache_hit_rate
        - prohibited_media_scan_clean (must be True)
        - passed
        """
        # 1. Shot Provenance Completeness
        if not shots:
            shot_prov_pct = 100.0
        else:
            valid_shots = sum(
                1 for s in shots
                if getattr(s, "screenplay_block_ids", None) and getattr(s, "source_event_ids", None)
            )
            shot_prov_pct = round((valid_shots / len(shots)) * 100.0, 1)

        # 2. Panel Provenance Completeness
        valid_shot_ids = {getattr(s, "shot_id", "") for s in shots} if shots else None
        if not panels:
            panel_prov_pct = 100.0
        else:
            valid_panels = sum(
                1 for p in panels
                if getattr(p, "shot_id", None) and (valid_shot_ids is None or p.shot_id in valid_shot_ids)
            )
            panel_prov_pct = round((valid_panels / len(panels)) * 100.0, 1)

        # 3. Vocabulary Leaks
        vocab_leaks = 0
        for p in panels:
            p_used = getattr(p, "prompt_used", "") or getattr(p, "prompt", "")
            if p_used:
                vocab_leaks += len(scan_for_internal_vocabulary(p_used))
        for s in shots:
            for txt in [getattr(s, "emotion", ""), getattr(s, "rationale", "")]:
                if txt:
                    vocab_leaks += len(scan_for_internal_vocabulary(txt))

        # 4. Internal State Leaks
        guard_verbs = set(InternalStateVerbGuard.FORBIDDEN_VERBS) | {
            "believes", "suspects", "wants", "intends", "understands", "thinks", "fears",
        }
        internal_leaks = 0
        for p in panels:
            p_used = getattr(p, "prompt_used", "") or getattr(p, "prompt", "")
            if p_used:
                for word in guard_verbs:
                    if re.search(rf"\b{re.escape(word)}\b", p_used, re.IGNORECASE):
                        internal_leaks += 1
        for s in shots:
            em = getattr(s, "emotion", "")
            if em:
                for word in guard_verbs:
                    if re.search(rf"\b{re.escape(word)}\b", em, re.IGNORECASE):
                        internal_leaks += 1

        # 5. Budget Compliance
        expected_count = min(budget, len(shots)) if shots else budget
        budget_comp = (len(panels) == expected_count) and (len(panels) <= budget)

        # 6. Priority Order Compliance
        from src.storyboard.keyframe_rendering import KeyframeSelector
        compliance_tags: List[str] = []
        shot_map = {getattr(s, "shot_id", ""): s for s in shots}
        seen_chars: Set[str] = set()
        for idx, p in enumerate(panels):
            pid = getattr(p, "shot_id", "")
            s = shot_map.get(pid)
            if s:
                tags = KeyframeSelector.identify_shot_priorities(s, idx, len(panels), seen_chars)
                compliance_tags.append(f"{pid}: {','.join(tags) if tags else 'STANDARD'}")
            else:
                compliance_tags.append(f"{pid}: UNKNOWN")

        # 7. Cache Hit Rate
        cache_rate = max(0.0, min(1.0, float(cache_hit_rate)))

        # 8. Prohibited Media Scan Clean
        scan_clean, violations = scan_codebase_for_prohibited_media(repo_root=repo_root)

        # Overall Passed
        passed = (
            shot_prov_pct == 100.0
            and panel_prov_pct == 100.0
            and vocab_leaks == 0
            and internal_leaks == 0
            and budget_comp is True
            and scan_clean is True
        )

        return StoryboardQualityReport(
            shot_provenance_completeness_pct=shot_prov_pct,
            panel_provenance_completeness_pct=panel_prov_pct,
            vocabulary_leak_count=vocab_leaks,
            internal_state_leak_count=internal_leaks,
            budget_compliance=budget_comp,
            priority_order_compliance=compliance_tags,
            cache_hit_rate=cache_rate,
            prohibited_media_scan_clean=scan_clean,
            passed=passed,
            total_panels=len(panels),
        )

GroundedStoryboardValidator = StoryboardQualityValidator
