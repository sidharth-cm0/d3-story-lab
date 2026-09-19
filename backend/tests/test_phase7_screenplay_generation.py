"""Tests for Phase 7 Prompt 2: Screenplay Generation and Formatting.

Validates that Scribe operates purely behind the ObservableSceneProjection firewall:
- Slugline formatting: INT./EXT. LOCATION - TIME, uppercase
- Action lines: Show-don't-tell passing InternalStateVerbGuard directly
- Character cues: Uppercase display names (never internal IDs)
- Dialogue: Grounded lines and slot-filling via DialogueTemplateLibrary
- Parentheticals: Sparse, physically observable vocal quality only
- Transitions: Omitted by default
- Event provenance: Every block's source_event_ids is a subset of the projection's source_event_ids
- Presentation order: presentation_position == chronological_position for all blocks
- Zero AI calls in deterministic path
- Blocklist clean: scan_for_internal_vocabulary returns zero violations
- Live Missing Dossier acceptance on world_init_4bef81
"""

import pytest
from typing import List, Dict

from src.storage.project_store import ProjectStore
from src.narrative.scene_builder import SceneBuilder
from src.domain.story_structure import DramaticFunction
from src.narrative.scene_projection import (
    ObservableSceneProjector,
    ObservableSceneProjection,
    ObservableBeat,
    ObservableObjective,
    ObservableDialogueLine,
    scan_for_internal_vocabulary,
    INTERNAL_VOCABULARY_BLOCKLIST,
)
from src.narrative.performance_cues import (
    PerformanceCue,
    PerformanceCueType,
    InternalStateVerbGuard,
)
from src.narrative.fountain import (
    ScreenplayBlock,
    ScreenplayBlockType,
    ScreenplayScene,
    ScreenplayDocument,
)
from src.narrative.scribe import (
    Scribe,
    DialogueTemplateLibrary,
    resolve_display_name,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_projection() -> ObservableSceneProjection:
    """Create a synthetic ObservableSceneProjection with beats, cues, and dialogue."""
    return ObservableSceneProjection(
        scene_id="scene_synth_01",
        scene_number=1,
        source_event_ids=["evt_001", "evt_002", "evt_003", "evt_004"],
        location_label="Interrogation Room",
        time_label="DAY",
        characters_present=["char_alpha", "char_beta"],
        purpose=DramaticFunction.INVESTIGATION,
        objective=ObservableObjective(
            pov_character_id="char_alpha",
            wants="Recover the manifest",
            obstacle="Evelyn denies knowledge",
            outcome="PARTIAL",
        ),
        beats=[
            ObservableBeat(
                event_id="evt_001",
                tick=10,
                description="Vincent Cross examined the metal briefcase.",
                characters_involved=["char_alpha"],
            ),
            ObservableBeat(
                event_id="evt_002",
                tick=11,
                description="Evelyn Vance leaned forward against the table.",
                characters_involved=["char_beta"],
            ),
            ObservableBeat(
                event_id="evt_003",
                tick=12,
                description="Vincent Cross asked Evelyn Vance about the manifest.",
                characters_involved=["char_alpha", "char_beta"],
            ),
            ObservableBeat(
                event_id="evt_004",
                tick=13,
                description="Evelyn Vance spoke to Vincent Cross.",
                characters_involved=["char_beta", "char_alpha"],
            ),
        ],
        dialogue=[
            ObservableDialogueLine(
                speaker_id="char_alpha",
                listener_id="char_beta",
                communicative_intent="TRUTHFUL",
                source_event_id="evt_003",
                text="Where was the transit dossier logged?",
                dialogue="Where was the transit dossier logged?",
            ),
            ObservableDialogueLine(
                speaker_id="char_beta",
                listener_id="char_alpha",
                communicative_intent="LYING",
                source_event_id="evt_004",
                text="",  # Empty to trigger DialogueTemplateLibrary slot-filling
                dialogue="",
            ),
        ],
        performance_cues=[
            PerformanceCue(
                type=PerformanceCueType.LOWERS_VOICE,
                character_id="char_alpha",
                target_character_id="char_beta",
                event_id="evt_003",
                observable_behaviour="Vincent Cross lowers his voice.",
                action_text="Vincent Cross lowers his voice.",
            ),
        ],
    )


# =============================================================================
# UNIT TESTS
# =============================================================================

def test_1_subset_source_events(mock_projection):
    """Test 1: Every block's source_event_ids is a subset of its scene's projection."""
    scribe = Scribe(provider=None)
    blocks = scribe.compose_scene_blocks(mock_projection)

    proj_event_ids = set(mock_projection.source_event_ids)
    assert len(blocks) > 0

    for block in blocks:
        assert isinstance(block.source_event_ids, list)
        block_event_ids = set(block.source_event_ids)
        assert block_event_ids.issubset(proj_event_ids), (
            f"Block {block.block_id} contains events {block_event_ids} not in {proj_event_ids}"
        )


def test_2_slugline_formatting(mock_projection):
    """Test 2: Slugline formatting matches INT./EXT. LOCATION - TIME, uppercase."""
    scribe = Scribe(provider=None)
    blocks = scribe.compose_scene_blocks(mock_projection)

    slugline_blocks = [b for b in blocks if b.element_type == "SLUGLINE"]
    assert len(slugline_blocks) == 1
    slugline = slugline_blocks[0]

    assert slugline.content == "INT. INTERROGATION ROOM - DAY"
    assert slugline.content == slugline.content.upper()
    assert slugline.content.startswith("INT. ") or slugline.content.startswith("EXT. ")
    assert " - " in slugline.content


def test_3_action_line_internal_state_verb_guard():
    """Test 3: Action-line InternalStateVerbGuard raises ValueError on forbidden verbs."""
    # Forbidden internal state verb "realizes"
    forbidden_text = "Vincent realizes the briefcase has been tampered with."
    with pytest.raises(ValueError) as excinfo:
        InternalStateVerbGuard.check_and_raise(forbidden_text)
    assert "internal-state verb" in str(excinfo.value).lower() or "realize" in str(excinfo.value).lower()

    # Valid observable action passes
    valid_text = "Vincent slides the briefcase across the steel surface."
    # Should not raise
    InternalStateVerbGuard.check_and_raise(valid_text)


def test_4_dialogue_composition_slot_filling():
    """Test 4: Dialogue composition test for a crafted communicative act slot-filling display names."""
    scribe = Scribe(provider=None)

    # Test lying denial template slot-filling
    line = scribe.compose_dialogue(
        intent="LYING",
        action_type="deny",
        topic="the sealed dossier",
        speaker="Evelyn Vance",
    )
    assert "the sealed dossier" in line
    assert scan_for_internal_vocabulary(line) == []

    # Test truthful warn template slot-filling
    line_warn = scribe.compose_dialogue(
        intent="TRUTHFUL",
        action_type="warn",
        speaker="Vincent Cross",
    )
    assert len(line_warn) > 0
    assert scan_for_internal_vocabulary(line_warn) == []


def test_5_full_screenplay_zero_ai_calls(mock_projection):
    """Test 5: Full screenplay generated with zero AI calls (deterministic path)."""
    # Scribe instantiated with no provider (provider=None)
    scribe = Scribe(provider=None)
    doc = scribe.compose_from_projections([mock_projection])

    assert isinstance(doc, ScreenplayDocument)
    assert len(doc.scenes) == 1
    assert doc.scenes[0].heading == "INT. INTERROGATION ROOM - DAY"

    # Confirm Fountain string generation works cleanly
    fountain_output = doc.to_fountain()
    assert "Title: EMERGENT NARRATIVE" in fountain_output
    assert "INT. INTERROGATION ROOM - DAY" in fountain_output
    assert "VINCENT CROSS" in fountain_output
    assert "EVELYN VANCE" in fountain_output


def test_6_vocabulary_blocklist_scan_zero_hits(mock_projection):
    """Test 6: Vocabulary blocklist scan on generated screenplay blocks with zero hits."""
    scribe = Scribe(provider=None)
    doc = scribe.compose_from_projections([mock_projection])

    for scene in doc.scenes:
        for block in scene.blocks:
            hits = scan_for_internal_vocabulary(block.content)
            assert hits == [], (
                f"Block {block.block_id} ({block.element_type}) contains forbidden terms {hits}: '{block.content}'"
            )


def test_7_scope_exclusion_presentation_position(mock_projection):
    """Test 7: Scope exclusion assertion: presentation_position == chronological_position for all blocks."""
    scribe = Scribe(provider=None)
    doc = scribe.compose_from_projections([mock_projection])

    for scene in doc.scenes:
        for block in scene.blocks:
            assert block.presentation_position == block.chronological_position
            assert block.presentation_position > 0


def test_8_character_names_never_leak_internal_ids(mock_projection):
    """Test that character cues never contain internal IDs like 'char_alpha'."""
    scribe = Scribe(provider=None)
    blocks = scribe.compose_scene_blocks(mock_projection)

    character_cues = [b for b in blocks if b.element_type == "CHARACTER_CUE"]
    assert len(character_cues) >= 2

    for cue in character_cues:
        assert not cue.content.startswith("CHAR_")
        assert not cue.content.startswith("char_")
        assert cue.content in ("VINCENT CROSS", "EVELYN VANCE")


def test_9_sparse_parentheticals_physically_observable(mock_projection):
    """Test parentheticals are sparse and strictly physical vocal cues."""
    scribe = Scribe(provider=None)
    blocks = scribe.compose_scene_blocks(mock_projection)

    parentheticals = [b for b in blocks if b.element_type == "PARENTHETICAL"]
    assert len(parentheticals) <= 1
    for p in parentheticals:
        assert p.content in ("(lowers voice)", "(rapidly)", "(quietly)")


# =============================================================================
# LIVE MISSING DOSSIER ACCEPTANCE TEST
# =============================================================================

def test_missing_dossier_live_screenplay_acceptance():
    """Test 8: Missing Dossier Acceptance on world_init_4bef81."""
    store = ProjectStore()
    project = store.load_project("world_init_4bef81")
    assert project is not None, "world_init_4bef81 project must exist"

    # Enrich scenes with Phase 6
    builder = SceneBuilder()
    enriched_scenes = builder.enrich_scenes_with_phase6(project.scenes, project.world)

    # Project scenes behind firewall
    projector = ObservableSceneProjector()
    projections = projector.project_all_scenes(enriched_scenes, project.world)
    assert len(projections) == 3

    # Compose screenplay behind firewall
    scribe = Scribe(provider=None)
    doc = scribe.compose_from_projections(projections, title="THE MISSING DOSSIER")

    assert len(doc.scenes) == 3
    assert doc.title == "THE MISSING DOSSIER"

    total_blocks_by_type: Dict[str, int] = {}
    all_blocks: List[ScreenplayBlock] = []

    for scene in doc.scenes:
        for block in scene.blocks:
            total_blocks_by_type[block.element_type] = total_blocks_by_type.get(block.element_type, 0) + 1
            all_blocks.append(block)

            # Invariant: Subset source event IDs
            scene_event_ids = set(scene.source_event_ids)
            assert set(block.source_event_ids).issubset(scene_event_ids)

            # Invariant: Presentation position == Chronological position
            assert block.presentation_position == block.chronological_position

            # Invariant: Action blocks pass InternalStateVerbGuard
            if block.element_type == "ACTION":
                InternalStateVerbGuard.check_and_raise(block.content)

            # Invariant: Zero internal vocabulary blocklist hits
            hits = scan_for_internal_vocabulary(block.content)
            assert hits == [], f"Vocabulary violation in scene {scene.scene_number}: {hits} in '{block.content}'"

            # Invariant: No internal ID in CHARACTER_CUE
            if block.element_type == "CHARACTER_CUE":
                assert not block.content.startswith("CHAR_")
                assert not block.content.startswith("char_")

    # Verify block counts
    assert total_blocks_by_type["SLUGLINE"] == 3
    assert total_blocks_by_type["ACTION"] >= 5
    assert total_blocks_by_type["CHARACTER_CUE"] >= 3
    assert total_blocks_by_type["DIALOGUE"] >= 3

    # Verify Fountain text generation
    fountain_text = doc.to_fountain()
    assert "Title: THE MISSING DOSSIER" in fountain_text
    assert "INT. ABANDONED INDUSTRIAL BAY - CONTINUOUS" in fountain_text
    assert "INT. SUBTERRANEAN ARCHIVE VAULT - CONTINUOUS" in fountain_text
    assert "VINCENT CROSS" in fountain_text
    assert "EVELYN VANCE" in fountain_text
