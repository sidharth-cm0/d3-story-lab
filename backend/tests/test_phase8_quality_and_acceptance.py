"""Tests for Phase 8.3: Quality Validator, Legacy Resolution, and Phase 8 Acceptance.

Covers:
1. StoryboardQualityValidator produces StoryboardQualityReport with all 8 inspectable fields correct:
   - shot_provenance_completeness_pct == 100.0
   - panel_provenance_completeness_pct == 100.0
   - vocabulary_leak_count == 0
   - internal_state_leak_count == 0
   - budget_compliance == True
   - priority_order_compliance matches PRIORITY_ORDER
   - cache_hit_rate is a valid float
   - prohibited_media_scan_clean == True
   - passed == True
2. Leak Detection:
   - Vocabulary blocklist violations increment vocabulary_leak_count and fail report.
   - Cognitive verb violations increment internal_state_leak_count and fail report.
3. Prohibited Media Scan:
   - Prohibited library scanner passes cleanly on current repository.
   - Prohibited library scanner flags mock violations correctly.
4. Part 3.B.4 Budget-Violation Regression Test:
   - Old behavior (24 unbudgeted panels for 3 scenes) is structurally impossible.
   - Panel count for any project always respects configured budget (capped at 12, default 8).
5. Provider-disabled fallback:
   - All rendered panels report provider_used == "DETERMINISTIC_SVG_FALLBACK".
6. End-to-end Missing Dossier acceptance run on world_init_4bef81 with zero AI calls.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.storage.project_store import ProjectStore
from src.narrative.scene_builder import SceneBuilder
from src.narrative.scene_projection import ObservableSceneProjector
from src.narrative.scribe import Scribe
from src.storyboard.shot_planner import (
    ShotPlan,
    ShotType,
    CameraAngle,
    CompositionPlan,
    ShotPlanner,
)
from src.storyboard.keyframe_rendering import (
    StoryboardPanel,
    KeyframeSelector,
    GroundedStoryboardRenderer,
    PRIORITY_ORDER,
)
from src.storyboard.storyboard_validator import (
    StoryboardQualityReport,
    StoryboardQualityValidator,
    GroundedStoryboardValidator,
    scan_codebase_for_prohibited_media,
)
from src.providers.budget import ContentHashCache, BudgetGovernor


@pytest.fixture
def missing_dossier_pipeline():
    """Load The Missing Dossier and execute Scribe through ShotPlanner."""
    store = ProjectStore()
    project = store.load_project("world_init_4bef81")
    assert project is not None

    builder = SceneBuilder()
    enriched = builder.enrich_scenes_with_phase6(project.scenes, project.world)
    projector = ObservableSceneProjector()
    projections = projector.project_all_scenes(enriched, project.world)
    scribe = Scribe(provider=None)
    doc = scribe.compose_from_projections(projections, title="THE MISSING DOSSIER")
    planner = ShotPlanner()
    full_shot_list = planner.plan_shots_for_screenplay(doc, projections, project.world)

    return project, projections, doc, full_shot_list


# =============================================================================
# 1. QUALITY REPORT METRICS & FIELD COMPLETENESS
# =============================================================================

def test_quality_validator_clean_report_passes_all_checks(missing_dossier_pipeline):
    """Verify clean full pipeline produces a 100% compliant report with zero leaks."""
    project, projections, doc, full_shot_list = missing_dossier_pipeline
    renderer = GroundedStoryboardRenderer()
    budget = 8
    panels, bible = renderer.render_budgeted_storyboard(
        shots=full_shot_list,
        world=project.world,
        budget=budget,
        project_id="world_init_4bef81",
    )

    validator = GroundedStoryboardValidator()
    report = validator.validate_grounded_storyboard(
        shots=full_shot_list,
        panels=panels,
        budget=budget,
        cache_hit_rate=1.0,
    )

    assert isinstance(report, StoryboardQualityReport)
    assert report.shot_provenance_completeness_pct == 100.0
    assert report.panel_provenance_completeness_pct == 100.0
    assert report.vocabulary_leak_count == 0
    assert report.internal_state_leak_count == 0
    assert report.budget_compliance is True
    assert len(report.priority_order_compliance) == budget
    assert report.cache_hit_rate == 1.0
    assert report.prohibited_media_scan_clean is True
    assert report.passed is True


# =============================================================================
# 2. VOCABULARY & INTERNAL STATE LEAK CHECKS
# =============================================================================

def test_quality_validator_detects_vocabulary_leak(missing_dossier_pipeline):
    """Verify that architecture vocabulary in a panel prompt fails validation."""
    project, projections, doc, full_shot_list = missing_dossier_pipeline
    renderer = GroundedStoryboardRenderer()
    panels, bible = renderer.render_budgeted_storyboard(
        shots=full_shot_list,
        world=project.world,
        budget=4,
    )

    # Poison panel 0 with internal vocabulary
    poisoned_panel = panels[0].model_copy(
        update={"prompt_used": panels[0].prompt_used + " The second sovereign actor enters with BeatPressure."}
    )
    poisoned_panels = [poisoned_panel] + panels[1:]

    validator = GroundedStoryboardValidator()
    report = validator.validate_grounded_storyboard(
        shots=full_shot_list,
        panels=poisoned_panels,
        budget=4,
    )

    assert report.vocabulary_leak_count > 0
    assert report.passed is False


def test_quality_validator_detects_internal_state_verb_leak(missing_dossier_pipeline):
    """Verify that forbidden cognitive verbs in prompt or emotion fail validation."""
    project, projections, doc, full_shot_list = missing_dossier_pipeline
    renderer = GroundedStoryboardRenderer()
    panels, bible = renderer.render_budgeted_storyboard(
        shots=full_shot_list,
        world=project.world,
        budget=4,
    )

    # Poison panel 0 with internal cognitive state verb
    poisoned_panel = panels[0].model_copy(
        update={"prompt_used": panels[0].prompt_used + " He believes the courier suspects betrayal."}
    )
    poisoned_panels = [poisoned_panel] + panels[1:]

    validator = GroundedStoryboardValidator()
    report = validator.validate_grounded_storyboard(
        shots=full_shot_list,
        panels=poisoned_panels,
        budget=4,
    )

    assert report.internal_state_leak_count > 0
    assert report.passed is False


# =============================================================================
# 3. PROHIBITED MEDIA SCAN TESTS
# =============================================================================

def test_scan_codebase_for_prohibited_media_is_clean():
    """Verify repository has zero video/animation/3D dependencies or imports."""
    clean, violations = scan_codebase_for_prohibited_media()
    assert clean is True
    assert violations == []


def test_scan_codebase_detects_mock_violations(tmp_path):
    """Verify scanner detects prohibited dependencies in mock repository."""
    # Mock frontend package.json with three.js
    fe = tmp_path / "frontend"
    fe.mkdir()
    (fe / "package.json").write_text('{"dependencies": {"three": "^0.160.0"}}')

    # Mock backend requirements with moviepy
    be = tmp_path / "backend"
    be.mkdir()
    (be / "requirements.txt").write_text("moviepy==1.0.3\npytest==8.0.0\n")

    clean, violations = scan_codebase_for_prohibited_media(repo_root=tmp_path)
    assert clean is False
    assert any("three" in v for v in violations)
    assert any("moviepy" in v for v in violations)


# =============================================================================
# 4. PART 3.B.4 BUDGET REGRESSION TEST
# =============================================================================

def test_regression_old_24_panel_unbudgeted_behavior_is_structurally_impossible(missing_dossier_pipeline):
    """Regression Test (§B.4 / Invariant #27):
    Old behavior — 24 panels for 3 scenes with no budget applied — is structurally impossible.
    Assert panel count always respects configured budget (bounded at max 12, default 8).
    """
    project, projections, doc, full_shot_list = missing_dossier_pipeline
    assert len(full_shot_list) == 23  # Unbudgeted shot candidates across 3 scenes

    renderer = GroundedStoryboardRenderer()

    # 1. No budget specified (None) -> Defaults to 8, never 24
    panels_default, _ = renderer.render_budgeted_storyboard(
        shots=full_shot_list,
        world=project.world,
        budget=None,
    )
    assert len(panels_default) == 8
    assert len(panels_default) != 23
    assert len(panels_default) != 24

    # 2. Oversize budget request (e.g. 24 or 100) -> Clamped to max 12
    panels_24, _ = renderer.render_budgeted_storyboard(
        shots=full_shot_list,
        world=project.world,
        budget=24,
    )
    assert len(panels_24) == 12  # Structurally clamped to 12 max

    panels_100, _ = renderer.render_budgeted_storyboard(
        shots=full_shot_list,
        world=project.world,
        budget=100,
    )
    assert len(panels_100) == 12

    # 3. Direct KeyframeSelector call with None or oversize budget
    sel_none = KeyframeSelector.select_keyframes(full_shot_list, budget=None)
    assert len(sel_none) == 8

    sel_24 = KeyframeSelector.select_keyframes(full_shot_list, budget=24)
    assert len(sel_24) == 12

    # 4. Valid explicit budgets (4, 8, 12)
    for b in (4, 8, 12):
        panels_b, _ = renderer.render_budgeted_storyboard(
            shots=full_shot_list,
            world=project.world,
            budget=b,
        )
        assert len(panels_b) == b


# =============================================================================
# 5. PROVIDER DISABLED FALLBACK (INVARIANT #28)
# =============================================================================

def test_offline_fallback_provider_used_is_explicit(missing_dossier_pipeline):
    """Verify all fallback rendered panels are explicitly DETERMINISTIC_SVG_FALLBACK."""
    project, projections, doc, full_shot_list = missing_dossier_pipeline
    renderer = GroundedStoryboardRenderer()
    panels, bible = renderer.render_budgeted_storyboard(
        shots=full_shot_list,
        world=project.world,
        budget=8,
    )

    for p in panels:
        assert p.provider_used == "DETERMINISTIC_SVG_FALLBACK"
        assert p.image_path.endswith(".svg")
        assert p.generation_status == "GENERATED"
        assert p.prompt_content_hash != ""


# =============================================================================
# 6. END-TO-END MISSING DOSSIER ACCEPTANCE AT BUDGETS 4, 8, 12
# =============================================================================

@pytest.mark.parametrize("budget", [4, 8, 12])
def test_missing_dossier_full_acceptance_by_budget(missing_dossier_pipeline, budget):
    """Verify end-to-end Missing Dossier acceptance across standard budgets."""
    project, projections, doc, full_shot_list = missing_dossier_pipeline
    renderer = GroundedStoryboardRenderer()
    panels, bible = renderer.render_budgeted_storyboard(
        shots=full_shot_list,
        world=project.world,
        budget=budget,
    )

    assert len(panels) == budget

    validator = GroundedStoryboardValidator()
    report = validator.validate_grounded_storyboard(
        shots=full_shot_list,
        panels=panels,
        budget=budget,
    )

    assert report.shot_provenance_completeness_pct == 100.0
    assert report.panel_provenance_completeness_pct == 100.0
    assert report.vocabulary_leak_count == 0
    assert report.internal_state_leak_count == 0
    assert report.budget_compliance is True
    assert len(report.priority_order_compliance) == budget
    assert report.prohibited_media_scan_clean is True
    assert report.passed is True
