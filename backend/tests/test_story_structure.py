"""Tests for Story Structure Library, Compatibility Matrix, and Structure Selection Engine."""

import pytest
from src.domain.story_structure import (
    StoryStructureType,
    StructureSelectionMode,
    StructureSelectionResult,
)
from src.narrative.structure_library import (
    STRUCTURE_DEFINITIONS,
    get_compatible_secondary_structures,
    is_structure_pair_compatible,
)
from src.narrative.structure_selector import StructureSelector


def test_structure_definitions_complete():
    """Verify that all 6 primary dramatic structures are defined with valid beats."""
    assert len(STRUCTURE_DEFINITIONS) == 6

    for st_type, defn in STRUCTURE_DEFINITIONS.items():
        assert defn.structure_type == st_type
        assert len(defn.beats) >= 4, f"{st_type} must have at least 4 beats"
        # Verify beat positions are monotonically increasing or within 0.0 - 1.0
        for b in defn.beats:
            assert 0.0 <= b.target_position_pct <= 1.0
            assert b.expected_dramatic_function
            assert b.pressure_signal


def test_compatibility_matrix_rules():
    """Verify strict adherence to the dramatic structure compatibility matrix."""
    # THREE_ACT allows SAVE_THE_CAT and STORY_CIRCLE
    three_act_compat = get_compatible_secondary_structures(StoryStructureType.THREE_ACT)
    assert StoryStructureType.SAVE_THE_CAT in three_act_compat
    assert StoryStructureType.STORY_CIRCLE in three_act_compat
    assert is_structure_pair_compatible(StoryStructureType.THREE_ACT, StoryStructureType.SAVE_THE_CAT)

    # HERO_JOURNEY allows THREE_ACT
    assert is_structure_pair_compatible(StoryStructureType.HERO_JOURNEY, StoryStructureType.THREE_ACT)

    # FREYTAG allows THREE_ACT
    assert is_structure_pair_compatible(StoryStructureType.FREYTAG, StoryStructureType.THREE_ACT)

    # KISHOTENKETSU explicitly forbids conflict-centric overlay by default
    kisho_compat = get_compatible_secondary_structures(StoryStructureType.KISHOTENKETSU)
    assert len(kisho_compat) == 0
    assert not is_structure_pair_compatible(StoryStructureType.KISHOTENKETSU, StoryStructureType.THREE_ACT)
    assert not is_structure_pair_compatible(StoryStructureType.KISHOTENKETSU, StoryStructureType.SAVE_THE_CAT)

    # Self-pairing is forbidden
    assert not is_structure_pair_compatible(StoryStructureType.THREE_ACT, StoryStructureType.THREE_ACT)


def test_auto_structure_selection_undercover_warehouse():
    """Verify AUTO selection for the Undercover Warehouse Dossier premise."""
    prompt = (
        "An undercover detective enters an abandoned warehouse at midnight to recover a stolen classified dossier. "
        "Inside, the detective meets a nervous courier who claims not to know anything about the dossier."
    )
    selector = StructureSelector()
    res = selector.select_structure(prompt, input_type="beginning", mode=StructureSelectionMode.AUTO)

    assert isinstance(res, StructureSelectionResult)
    # High-tension investigative premise should select THREE_ACT or SAVE_THE_CAT
    assert res.primary_structure in (StoryStructureType.THREE_ACT, StoryStructureType.SAVE_THE_CAT)
    # Heuristic fit score must be between 10.0 and 98.0
    assert 65.0 <= res.fit_score <= 98.0
    # Secondary structure, if present, must be strictly compatible
    if res.secondary_structure:
        assert is_structure_pair_compatible(res.primary_structure, res.secondary_structure)
    # Rationale must not claim calibrated statistical probability
    assert "% confidence" not in res.fit_rationale
    assert "heuristic" in res.fit_rationale.lower()


def test_auto_structure_selection_contemplative_quiet():
    """Verify AUTO selection for a non-adversarial, contemplative routine."""
    prompt = "A student is sitting quietly by the open classroom window, staring at the rain on a sleepy afternoon."
    selector = StructureSelector()
    res = selector.select_structure(prompt, input_type="full_concept", mode=StructureSelectionMode.AUTO)

    assert res.primary_structure == StoryStructureType.KISHOTENKETSU
    assert res.fit_score >= 60.0
    # No conflict-centric secondary structure for Kishōtenketsu
    assert res.secondary_structure is None


def test_manual_structure_selection_with_valid_and_invalid_secondaries():
    """Verify MANUAL mode respects user choice and validates secondary compatibility."""
    selector = StructureSelector()
    prompt = "An operative infiltrates a vault."

    # Valid manual pairing: THREE_ACT + SAVE_THE_CAT
    res_valid = selector.select_structure(
        prompt,
        mode=StructureSelectionMode.MANUAL,
        manual_primary=StoryStructureType.THREE_ACT,
        manual_secondary=StoryStructureType.SAVE_THE_CAT,
    )
    assert res_valid.primary_structure == StoryStructureType.THREE_ACT
    assert res_valid.secondary_structure == StoryStructureType.SAVE_THE_CAT
    assert res_valid.selection_mode == StructureSelectionMode.MANUAL

    # Invalid manual pairing: KISHOTENKETSU + THREE_ACT (incompatible)
    res_invalid = selector.select_structure(
        prompt,
        mode=StructureSelectionMode.MANUAL,
        manual_primary=StoryStructureType.KISHOTENKETSU,
        manual_secondary=StoryStructureType.THREE_ACT,
    )
    assert res_invalid.primary_structure == StoryStructureType.KISHOTENKETSU
    # Incompatible secondary should be dropped
    assert res_invalid.secondary_structure is None
    assert "incompatible" in res_invalid.fit_rationale
