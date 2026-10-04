"""Tests for CharacterReferenceProfile, Normalizer, and Enricher integration.

Phase G1, G2, G3 verification:
- CharacterReferenceProfile model and 13 stable visual fields.
- sync_from_dynamics single-authority mapping.
- to_actor_visual_profile / from_actor_visual_profile bidirectional legacy adapters.
- CharacterProfileDraft lock/unlock/authority routing for reference fields.
- Natural language and structured normalization of reference profile fields.
- Deterministic enrichment respecting USER_LOCKED and USER_PREFERRED.
- CharacterCompleteness calculation against reference_profile.
"""

import pytest
from src.domain.character_reference import (
    CharacterReferenceProfile,
    FieldAuthority,
    FieldProvenance,
    REFERENCE_FIELD_NAMES,
)
from src.domain.character_creation import CharacterProfileDraft, CharacterInput
from src.domain.character_dynamics import CharacterDynamicsProfile
from src.domain.character_completeness import calculate_character_completeness
from src.generator.character_normalizer import CharacterProfileNormalizer
from src.generator.character_enricher import CharacterEnrichmentService


def test_character_reference_profile_defaults():
    """Verify default instantiation of CharacterReferenceProfile."""
    ref = CharacterReferenceProfile()
    assert ref.apparent_age_range == ""
    assert ref.build == ""
    assert ref.distinguishing_features == ""
    assert ref.wardrobe_palette == []
    assert ref.signature_objects == []
    assert ref.usual_environments == []
    assert len(REFERENCE_FIELD_NAMES) == 13


def test_character_reference_profile_sync_from_dynamics():
    """Verify single-authority mapping where dynamics hydrates reference profile fields."""
    dynamics = CharacterDynamicsProfile(
        mannerisms=["bites lip", "crosses arms defensively"],
        lifestyle="underground bunker inhabitant",
    )
    ref = CharacterReferenceProfile()
    ref.sync_from_dynamics(dynamics)

    assert ref.body_language == "bites lip; crosses arms defensively"
    assert "underground bunker inhabitant" in ref.usual_environments
    assert ref.provenance["body_language"].authority == FieldAuthority.SYSTEM_INFERRED
    assert ref.provenance["body_language"].inference_rule == "derived_from:dynamics.mannerisms"


def test_character_reference_profile_legacy_adapters():
    """Verify bidirectional legacy adapter with ActorVisualProfile."""
    ref = CharacterReferenceProfile(
        apparent_age_range="mid 40s",
        build="lean, wiry",
        face_description="sharp jawline, tired eyes",
        hair="receding gray hair",
        baseline_wardrobe="tattered charcoal suit",
        signature_objects=["silver pocket watch", "brass key"],
    )
    legacy = ref.to_actor_visual_profile("char_elena")
    assert legacy.character_id == "char_elena"
    assert legacy.age == "mid 40s"
    assert legacy.build == "lean, wiry"
    assert legacy.face_traits == "sharp jawline, tired eyes"
    assert legacy.hairstyle == "receding gray hair"
    assert legacy.clothing == "tattered charcoal suit"
    assert "silver pocket watch" in legacy.signature_items

    # Convert back
    roundtrip = CharacterReferenceProfile.from_actor_visual_profile(legacy)
    assert roundtrip.apparent_age_range == "mid 40s"
    assert roundtrip.build == "lean, wiry"
    assert roundtrip.baseline_wardrobe == "tattered charcoal suit"
    assert "silver pocket watch" in roundtrip.signature_objects


def test_draft_reference_field_authority_and_locking():
    """Verify CharacterProfileDraft routes reference profile locks and updates."""
    draft = CharacterProfileDraft(name="Marcus", role="Investigator")
    assert draft.reference_profile is not None

    # Update reference field
    updated = draft.set_field(
        "baseline_wardrobe",
        "oilskin trench coat",
        authority=FieldAuthority.USER_PREFERRED,
        source_snippet="user prompt",
    )
    assert updated is True
    assert draft.reference_profile.baseline_wardrobe == "oilskin trench coat"
    assert draft.get_authority("baseline_wardrobe") == FieldAuthority.USER_PREFERRED

    # Lock field
    assert draft.is_locked("baseline_wardrobe") is False
    draft.lock_field("baseline_wardrobe")
    assert draft.is_locked("baseline_wardrobe") is True
    assert draft.get_authority("baseline_wardrobe") == FieldAuthority.USER_LOCKED

    # Unlock field
    draft.unlock_field("baseline_wardrobe")
    assert draft.is_locked("baseline_wardrobe") is False
    assert draft.get_authority("baseline_wardrobe") == FieldAuthority.USER_PREFERRED


def test_character_normalizer_natural_language_extraction():
    """Verify normalizer extracts reference profile features from free text."""
    normalizer = CharacterProfileNormalizer()
    text = (
        "Elena is a weary 40-year-old archivist with a wiry build and scarred chin. "
        "She wears a dark wool coat and carries an embossed leather notebook."
    )
    _, draft = normalizer.normalize(raw_text=text)

    assert draft.reference_profile is not None
    assert "40" in draft.reference_profile.apparent_age_range
    assert draft.reference_profile.build.lower() == "wiry"
    assert any("scar" in f for f in draft.reference_profile.distinguishing_features) or "scar" in draft.reference_profile.distinguishing_features
    assert draft.reference_profile.baseline_wardrobe != ""
    assert "wool coat" in draft.reference_profile.baseline_wardrobe
    assert any("notebook" in obj for obj in draft.reference_profile.signature_objects)
    # Legacy sync check
    assert draft.visual_profile is not None
    assert draft.visual_profile.clothing == draft.reference_profile.baseline_wardrobe


def test_character_normalizer_structured_payload():
    """Verify normalizer parses structured reference profile data with locks."""
    normalizer = CharacterProfileNormalizer()
    payload = {
        "name": "Kaelen",
        "role": "Courier",
        "apparent_age_range": "late 20s",
        "build": "athletic, compact",
        "baseline_wardrobe": "reinforced flight jacket",
        "locked_fields": ["baseline_wardrobe"],
    }
    _, draft = normalizer.normalize(structured_payload=payload)

    assert draft.reference_profile.apparent_age_range == "late 20s"
    assert draft.reference_profile.build == "athletic, compact"
    assert draft.reference_profile.baseline_wardrobe == "reinforced flight jacket"
    assert draft.get_authority("baseline_wardrobe") == FieldAuthority.USER_LOCKED
    assert draft.get_authority("build") == FieldAuthority.USER_PREFERRED


def test_character_enricher_respects_user_locked_reference_fields():
    """Verify enricher populates empty reference fields without touching USER_LOCKED ones."""
    draft = CharacterProfileDraft(
        name="Vance",
        role="Investigator",
        reference_profile=CharacterReferenceProfile(
            baseline_wardrobe="custom velvet tuxedo",
            provenance={
                "baseline_wardrobe": FieldProvenance(
                    field_name="baseline_wardrobe",
                    authority=FieldAuthority.USER_LOCKED,
                    source_snippet="user explicitly locked this",
                )
            },
        ),
    )

    enricher = CharacterEnrichmentService()
    enriched = enricher.enrich(draft, premise="A gritty industrial espionage thriller")

    # Locked wardrobe must remain untouched
    assert enriched.reference_profile.baseline_wardrobe == "custom velvet tuxedo"
    assert enriched.get_authority("baseline_wardrobe") == FieldAuthority.USER_LOCKED

    # Unspecified fields must be enriched with SYSTEM_INFERRED
    assert enriched.reference_profile.apparent_age_range != ""
    assert enriched.reference_profile.face_description != ""
    assert enriched.get_authority("face_description") == FieldAuthority.SYSTEM_INFERRED
    assert enriched.reference_profile.build != ""


def test_completeness_calculation_with_reference_profile():
    """Verify calculate_character_completeness assesses reference_profile fields."""
    draft = CharacterProfileDraft(name="Soren", role="Analyst")
    rep_initial = calculate_character_completeness(draft)
    assert "visual_profile" in rep_initial.missing_fields

    draft.reference_profile.baseline_wardrobe = "pressed dark grey suit"
    # Sync legacy visual profile so completeness score reflects it
    draft.visual_profile = draft.reference_profile.to_actor_visual_profile("char_soren")
    rep_with_wardrobe = calculate_character_completeness(draft)
    assert rep_with_wardrobe.score > rep_initial.score
