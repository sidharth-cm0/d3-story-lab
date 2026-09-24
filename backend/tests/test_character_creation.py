"""Comprehensive unit and integration tests for Phase A Character Creation with Field Authority."""

import pytest
from fastapi.testclient import TestClient
from src.api.app import app
from src.domain.character_creation import (
    FieldAuthority,
    FieldProvenance,
    CharacterInput,
    CharacterProfileDraft,
)
from src.domain.character_completeness import (
    CompletenessReport,
    calculate_character_completeness,
)
from src.domain.character import Character
from src.domain.world import WorldState, Location
from src.domain.continuity import ActorVisualProfile
from src.generator.character_normalizer import CharacterProfileNormalizer
from src.generator.character_enricher import CharacterEnrichmentService
from src.storage.project_store import ProjectStore, ProjectData, ProjectMetadata


# ============================================================================
# 1. Normalizer Tests
# ============================================================================

def test_normalizer_free_text_nl_extraction():
    """Verify natural-language description normalizes into structured draft with USER_PREFERRED authority."""
    normalizer = CharacterProfileNormalizer()
    raw_text = (
        "Detective Marcus Vance, a cynical 42-year-old homicide investigator with a sharp jawline and dark trench coat. "
        "He wants to solve the waterfront murder case. "
        "Secretly, he was at the docks the night of the crime. "
        "He believes his partner is hiding evidence. "
        "Cautious, observant, and distrusting."
    )

    char_input, draft = normalizer.normalize(raw_text=raw_text)

    # 1. Immutable CharacterInput record
    assert char_input.id.startswith("cinp_")
    assert char_input.raw_text == raw_text
    assert char_input.linked_character_id == draft.id

    # 2. Extracted fields
    assert "Marcus Vance" in draft.name
    assert "Investigator" in draft.role or "Detective" in draft.role
    assert len(draft.goals) >= 1
    assert any("waterfront murder" in g.lower() for g in draft.goals)
    assert len(draft.secrets) >= 1
    assert any("docks" in s.lower() for s in draft.secrets)
    assert len(draft.beliefs) >= 1
    assert any("partner" in b.lower() for b in draft.beliefs)
    assert len(draft.personality_traits) >= 2
    assert "cautious" in draft.personality_traits or "observant" in draft.personality_traits

    # 3. Field Authority & Provenance
    assert draft.get_authority("name") == FieldAuthority.USER_PREFERRED
    assert draft.provenance["name"].source_snippet is not None
    assert draft.get_authority("role") == FieldAuthority.USER_PREFERRED
    assert draft.get_authority("goals") == FieldAuthority.USER_PREFERRED
    assert draft.get_authority("secrets") == FieldAuthority.USER_PREFERRED
    assert draft.get_authority("beliefs") == FieldAuthority.USER_PREFERRED


def test_normalizer_structured_form_input():
    """Verify structured form data normalizes with appropriate USER_PREFERRED / USER_LOCKED tags."""
    normalizer = CharacterProfileNormalizer()
    payload = {
        "name": "Elena Rostova",
        "role": "Security Specialist",
        "description": "High-threat asset protection courier",
        "goals": ["Extract the informant before dawn"],
        "secrets": ["Carrying a forged clearance keycard"],
        "beliefs": ["The safehouse has already been breached"],
        "personality_traits": {"alert": 0.9, "stoic": 0.8},
        "locked_fields": ["name", "role", "secrets"],
    }

    char_input, draft = normalizer.normalize(structured_payload=payload)

    assert draft.name == "Elena Rostova"
    assert draft.role == "Security Specialist"
    assert draft.goals == ["Extract the informant before dawn"]
    assert draft.secrets == ["Carrying a forged clearance keycard"]
    assert draft.personality_traits == {"alert": 0.9, "stoic": 0.8}

    # Locked fields should have USER_LOCKED authority
    assert draft.get_authority("name") == FieldAuthority.USER_LOCKED
    assert draft.is_locked("name")
    assert draft.get_authority("role") == FieldAuthority.USER_LOCKED
    assert draft.is_locked("role")
    assert draft.get_authority("secrets") == FieldAuthority.USER_LOCKED
    assert draft.is_locked("secrets")

    # Unlocked user fields should have USER_PREFERRED authority
    assert draft.get_authority("goals") == FieldAuthority.USER_PREFERRED
    assert not draft.is_locked("goals")
    assert draft.get_authority("beliefs") == FieldAuthority.USER_PREFERRED


def test_normalizer_empty_fallback():
    """Verify empty input falls back gracefully to system defaults without crashing."""
    normalizer = CharacterProfileNormalizer()
    char_input, draft = normalizer.normalize(raw_text="")

    assert draft.name == "Unnamed Character"
    assert draft.role == "Protagonist"
    assert draft.get_authority("name") == FieldAuthority.SYSTEM_GENERATED
    assert draft.get_authority("role") == FieldAuthority.SYSTEM_GENERATED


# ============================================================================
# 2. Completeness Scoring Tests
# ============================================================================

def test_completeness_scoring_empty_and_full():
    """Verify completeness score calculations, field weights, and missing field reporting."""
    # 1. Empty draft
    empty_draft = CharacterProfileDraft(name="", role="")
    rep_empty = calculate_character_completeness(empty_draft)
    assert rep_empty.score == 0.0
    assert not rep_empty.is_complete
    assert "name" in rep_empty.missing_fields
    assert "role" in rep_empty.missing_fields
    assert "goals" in rep_empty.missing_fields
    assert "secrets" in rep_empty.missing_fields
    assert "visual_profile" in rep_empty.missing_fields

    # 2. Partial draft: Name + Role only
    partial_draft = CharacterProfileDraft(name="Marcus", role="Detective")
    rep_partial = calculate_character_completeness(partial_draft)
    assert rep_partial.score == 30.0  # 15 for name + 15 for role
    assert not rep_partial.is_complete
    assert "name" in rep_partial.present_fields
    assert "role" in rep_partial.present_fields
    assert "goals" in rep_partial.missing_fields

    # 3. Full draft
    full_draft = CharacterProfileDraft(
        name="Marcus",
        role="Detective",
        goals=["Solve the case"],
        secrets=["Was at the docks"],
        beliefs=["Partner is suspicious"],
        personality_traits={"cautious": 0.8},
        visual_profile=ActorVisualProfile(
            character_id="char_1",
            name="Marcus",
            clothing="Trench coat",
            face_traits="Tired gaze",
        ),
    )
    rep_full = calculate_character_completeness(full_draft)
    assert rep_full.score == 100.0
    assert rep_full.is_complete
    assert len(rep_full.missing_fields) == 0


def test_completeness_scorer_determinism():
    """Verify that completeness scoring is pure and deterministic."""
    draft = CharacterProfileDraft(name="Arjun", role="Investigator", goals=["Find truth"])
    rep1 = calculate_character_completeness(draft)
    rep2 = calculate_character_completeness(draft)
    assert rep1.score == rep2.score
    assert rep1.missing_fields == rep2.missing_fields
    assert rep1.present_fields == rep2.present_fields


# ============================================================================
# 3. Enrichment and Field Authority Invariant Tests
# ============================================================================

def test_enrichment_never_overwrites_user_locked_fields():
    """CRITICAL: USER_LOCKED fields must NEVER be overwritten by enrichment."""
    enricher = CharacterEnrichmentService()
    draft = CharacterProfileDraft(
        name="User Custom Name",
        role="Custom Role",
        goals=["User Locked Goal"],
    )
    draft.lock_field("name")
    draft.lock_field("goals")

    assert draft.is_locked("name")
    assert draft.is_locked("goals")

    enriched = enricher.enrich(draft, premise="A corporate conspiracy in downtown Tokyo")

    # Verify locked fields were NOT overwritten
    assert enriched.name == "User Custom Name"
    assert enriched.goals == ["User Locked Goal"]
    assert enriched.get_authority("name") == FieldAuthority.USER_LOCKED
    assert enriched.get_authority("goals") == FieldAuthority.USER_LOCKED


def test_enrichment_never_overwrites_user_preferred_fields():
    """CRITICAL: USER_PREFERRED fields must NOT be silently replaced by enrichment."""
    enricher = CharacterEnrichmentService()
    draft = CharacterProfileDraft(
        name="Alice Walker",
        role="Undercover Courier",
        goals=["Deliver package to sector 7"],
        secrets=["Package contains antidote"],
    )
    # Tag as USER_PREFERRED
    draft.set_field("name", "Alice Walker", FieldAuthority.USER_PREFERRED)
    draft.set_field("role", "Undercover Courier", FieldAuthority.USER_PREFERRED)
    draft.set_field("goals", ["Deliver package to sector 7"], FieldAuthority.USER_PREFERRED)
    draft.set_field("secrets", ["Package contains antidote"], FieldAuthority.USER_PREFERRED)

    enriched = enricher.enrich(draft, premise="High-stakes heist")

    # User fields remain completely intact
    assert enriched.name == "Alice Walker"
    assert enriched.role == "Undercover Courier"
    assert enriched.goals == ["Deliver package to sector 7"]
    assert enriched.secrets == ["Package contains antidote"]
    assert enriched.get_authority("goals") == FieldAuthority.USER_PREFERRED
    assert enriched.get_authority("secrets") == FieldAuthority.USER_PREFERRED

    # But missing fields (like personality_traits and visual_profile) are enriched!
    assert len(enriched.personality_traits) > 0
    assert enriched.get_authority("personality_traits") == FieldAuthority.SYSTEM_INFERRED
    assert enriched.visual_profile is not None
    assert enriched.get_authority("visual_profile") == FieldAuthority.SYSTEM_INFERRED


def test_enrichment_populates_missing_fields_with_system_inferred():
    """Enrichment fills only missing fields with SYSTEM_INFERRED tags and records rule names."""
    enricher = CharacterEnrichmentService()
    draft = CharacterProfileDraft(
        name="Dr. Thorne",
        role="Neurosurgeon",
    )
    draft.set_field("name", "Dr. Thorne", FieldAuthority.USER_PREFERRED)
    draft.set_field("role", "Neurosurgeon", FieldAuthority.USER_PREFERRED)

    enriched = enricher.enrich(draft)

    assert len(enriched.goals) > 0
    assert enriched.get_authority("goals") == FieldAuthority.SYSTEM_INFERRED
    assert enriched.provenance["goals"].inference_rule is not None
    assert "role_inference" in enriched.provenance["goals"].inference_rule

    assert len(enriched.secrets) > 0
    assert enriched.get_authority("secrets") == FieldAuthority.SYSTEM_INFERRED

    assert "analytical" in enriched.personality_traits or "meticulous" in enriched.personality_traits


# ============================================================================
# 4. Lock / Unlock State Transition Tests
# ============================================================================

def test_lock_and_unlock_lifecycle():
    """Verify lock and unlock state transitions and lock timestamps."""
    draft = CharacterProfileDraft(name="Marcus", role="Detective")
    draft.set_field("role", "Detective", FieldAuthority.USER_PREFERRED, source_snippet="Role: Detective")

    assert draft.get_authority("role") == FieldAuthority.USER_PREFERRED
    assert not draft.is_locked("role")

    # Lock field
    draft.lock_field("role")
    assert draft.is_locked("role")
    assert draft.get_authority("role") == FieldAuthority.USER_LOCKED
    assert draft.provenance["role"].locked_at is not None

    # Unlock field
    draft.unlock_field("role")
    assert not draft.is_locked("role")
    assert draft.get_authority("role") == FieldAuthority.USER_PREFERRED
    assert draft.provenance["role"].locked_at is None


def test_unlock_allows_subsequent_enrichment():
    """Unlocking a field allows subsequent enrichment to update it."""
    draft = CharacterProfileDraft(name="Marcus", role="Detective", goals=["Old Locked Goal"])
    draft.lock_field("goals")

    enricher = CharacterEnrichmentService()
    enriched1 = enricher.enrich(draft)
    assert enriched1.goals == ["Old Locked Goal"]  # Untouched while locked

    # Now user unlocks it and changes authority to SYSTEM_GENERATED to request regeneration
    draft.set_field("goals", ["Temporary Goal"], FieldAuthority.SYSTEM_GENERATED, force=True)
    assert not draft.is_locked("goals")

    enriched2 = enricher.enrich(draft)
    assert enriched2.goals != ["Old Locked Goal"]
    assert enriched2.get_authority("goals") == FieldAuthority.SYSTEM_INFERRED


# ============================================================================
# 5. Full Intake -> Enrich -> Lock -> Accept API Integration Flow
# ============================================================================

def test_character_creation_api_end_to_end():
    """End-to-end API test: project creation, character intake, lock, enrich, and accept."""
    client = TestClient(app)

    # 1. Create a project
    create_res = client.post("/api/projects", json={
        "seed_prompt": "An undercover detective investigates classified corporate files.",
        "title": "Corporate Files",
    })
    assert create_res.status_code == 200
    project_id = create_res.json()["id"]

    # 2. Intake character from free text
    intake_res = client.post(f"/api/projects/{project_id}/characters/intake", json={
        "raw_text": "Detective Sarah Cross, a sharp 35-year-old forensic investigator. Wants to decode the ledger. Cautious and observant.",
        "auto_enrich": False,
    })
    assert intake_res.status_code == 200
    intake_data = intake_res.json()
    draft = intake_data["draft"]
    draft_id = draft["id"]
    char_input = intake_data["input"]

    assert char_input["linked_character_id"] == draft_id
    assert "Sarah Cross" in draft["name"]
    assert draft["provenance"]["name"]["authority"] == "USER_PREFERRED"

    # 3. Lock name and role
    lock_res = client.post(f"/api/projects/{project_id}/characters/drafts/{draft_id}/lock", json={
        "field_name": "name"
    })
    assert lock_res.status_code == 200
    assert lock_res.json()["authority"] == "USER_LOCKED"

    # 4. Enrich remaining missing fields
    enrich_res = client.post(f"/api/projects/{project_id}/characters/drafts/{draft_id}/enrich")
    assert enrich_res.status_code == 200
    enriched_data = enrich_res.json()
    enriched_draft = enriched_data["draft"]

    # Name remained locked and untouched
    assert "Sarah Cross" in enriched_draft["name"]
    assert enriched_draft["provenance"]["name"]["authority"] == "USER_LOCKED"

    # Secrets and visual profile were enriched
    assert len(enriched_draft["secrets"]) > 0
    assert enriched_draft["provenance"]["secrets"]["authority"] == "SYSTEM_INFERRED"
    assert enriched_data["completeness"]["score"] >= 80.0

    # 5. Check completeness endpoint
    comp_res = client.get(f"/api/projects/{project_id}/characters/drafts/{draft_id}/completeness")
    assert comp_res.status_code == 200
    assert comp_res.json()["is_complete"] is True

    # 6. Accept draft into the canonical simulation world state
    accept_res = client.post(f"/api/projects/{project_id}/characters/drafts/{draft_id}/accept")
    assert accept_res.status_code == 200
    char_result = accept_res.json()["character"]
    char_id = accept_res.json()["character_id"]

    assert char_result["name"] == enriched_draft["name"]
    assert char_result["input_id"] == char_input["id"]
    assert "name" in char_result["field_provenance"]
    assert char_result["field_provenance"]["name"]["authority"] == "USER_LOCKED"

    # 7. Verify character exists in WorldState and has real Goals and Secrets
    world_res = client.get(f"/api/projects/{project_id}/world")
    assert world_res.status_code == 200
    world_data = world_res.json()
    assert char_id in world_data["characters"]
    saved_char = world_data["characters"][char_id]
    assert len(saved_char["goals"]) > 0
    assert len(saved_char["secrets"]) > 0
    for gid in saved_char["goals"]:
        assert gid in world_data["goals"]

    # 8. Verify simulation step works properly with the new character
    step_res = client.post(f"/api/projects/{project_id}/step", json={"ticks": 1})
    assert step_res.status_code == 200
    assert step_res.json()["current_tick"] == 1


# ============================================================================
# 6. Backward Compatibility & Simulation Invariance
# ============================================================================

def test_pre_existing_characters_simulate_unaffected():
    """Verify that existing characters without intake/provenance fields continue to work seamlessly."""
    world = WorldState(
        id="world_test",
        name="Legacy Test",
        locations={"loc_1": Location(id="loc_1", name="Office")},
        characters={
            "char_legacy": Character(
                id="char_legacy",
                name="Legacy Agent",
                role="Operative",
                current_location_id="loc_1",
            )
        },
    )

    # Legacy character serializes and deserializes cleanly
    dumped = world.model_dump(mode="json")
    reloaded = WorldState.model_validate(dumped)

    char = reloaded.characters["char_legacy"]
    assert char.name == "Legacy Agent"
    assert char.input_id is None
    assert char.field_provenance == {}
