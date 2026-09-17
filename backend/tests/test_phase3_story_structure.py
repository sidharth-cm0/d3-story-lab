"""Verification tests for Phase 3A & 3B: Story Structure Definitions, Taxonomy, Compatibility, Features, Rubric Scoring, and Selection.

Covers targeted tests:
Phase 3A:
1. new structure can be added via data file only
2. malformed structure file fails clearly
3. in_medias_res cannot load as MACRO
4. compatibility matrix returns expected ALLOW/WARN/REJECT
5. freytag + save_the_cat rejected with reason
6. kishotenketsu + conflict beat framework rejected with reason
7. PredicateSpec accepts any_of
8. PredicateSpec accepts all_of
9. PredicateSpec rejects both
10. PredicateSpec rejects neither if one is required

Phase 3B:
1. feature extraction works with providers disabled
2. same features -> same ranking
3. no I/O in score path
4. conflict-forward premise ranks kishotenketsu below conflict structures
5. juxtaposition premise lets kishotenketsu score competitively
6. manual override persists after rescoring
7. invalid compatibility cannot be selected
8. in_medias_res remains framing only
9. sanity test with real premises A, B, C printing all diagnostic fields
"""
import pytest
from pathlib import Path
from pydantic import ValidationError

from src.domain.story_structure import (
    CompatibilityVerdict,
    DramaticFunction,
    DRAMATIC_FUNCTIONS,
    NarrativeAxis,
    MacroStructure,
    BeatFramework,
    FramingStrategy,
    MACRO_STRUCTURES,
    BEAT_FRAMEWORKS,
    FRAMING_STRATEGIES,
    normalize_beat_framework,
    normalize_structure_id,
)
from src.story.models import (
    PredicateClause,
    PredicateSpec,
    StoryFeatures,
    StoryStructureDefinition,
    StructureCandidate,
    StructureSelection,
)
from src.story.loader import (
    load_structure_from_yaml,
    load_all_structures,
    get_structure_registry,
    StructureLoadError,
)
from src.story.compatibility import CompatibilityEvaluator, DEFAULT_COMPATIBILITY_EVALUATOR
from src.story.features import (
    extract_story_input_rule_based,
    analyze_story_input,
    StoryInputAnalysisResult,
)
from src.story.scorer import score, select_structure


class TestPhase3AStoryStructureEngine:
    """Targeted tests covering Phase 3A requirements."""

    # 1. new structure can be added via data file only
    def test_new_structure_can_be_added_via_data_file_only(self, tmp_path):
        """Dropping a valid YAML file dynamically registers a new structure without code modification."""
        custom_yaml = tmp_path / "custom_mythic.yaml"
        custom_yaml.write_text(
            """id: custom_mythic
axis: MACRO
display_name: "Custom Mythic Structure"
description: "A dynamically added mythic structure"
acts:
  - { id: act_a, name: "Phase 1", position: [0.0, 0.5] }
  - { id: act_b, name: "Phase 2", position: [0.5, 1.0] }
beats:
  - id: beat_1
    dramatic_function: INCITING_INCIDENT
    window: [0.1, 0.3]
    required: true
    satisfaction:
      any_of:
        - { type: GOAL_ADOPTED }
compatible_beat_frameworks: []
affinity:
  conflict_axis.external: 0.7
disqualifiers: []
manual_only: false
""",
            encoding="utf-8",
        )

        defn = load_structure_from_yaml(custom_yaml)
        assert defn.id == "custom_mythic"
        assert defn.axis == "MACRO"
        assert defn.display_name == "Custom Mythic Structure"
        assert len(defn.beats) == 1
        assert defn.beats[0].dramatic_function == "INCITING_INCIDENT"

        # Load all from the directory containing this new file
        registry = load_all_structures(tmp_path)
        assert "custom_mythic" in registry
        assert registry["custom_mythic"].display_name == "Custom Mythic Structure"

    # 2. malformed structure file fails clearly
    def test_malformed_structure_file_fails_clearly(self, tmp_path):
        """Malformed YAML syntax or schema violation raises StructureLoadError with diagnostic message."""
        # 2a: Syntax error
        syntax_err_file = tmp_path / "broken_syntax.yaml"
        syntax_err_file.write_text("id: broken\nacts: [unclosed list", encoding="utf-8")
        with pytest.raises(StructureLoadError) as exc_syntax:
            load_structure_from_yaml(syntax_err_file)
        assert "Malformed YAML" in str(exc_syntax.value)

        # 2b: Schema violation (missing required axis, display_name)
        schema_err_file = tmp_path / "invalid_schema.yaml"
        schema_err_file.write_text("id: incomplete_data\n", encoding="utf-8")
        with pytest.raises(StructureLoadError) as exc_schema:
            load_structure_from_yaml(schema_err_file)
        assert "Schema validation failed" in str(exc_schema.value)

    # 3. in_medias_res cannot load as MACRO
    def test_in_medias_res_cannot_load_as_macro(self, tmp_path):
        """in_medias_res is FRAMING, never MACRO, and fails validation if loaded as MACRO."""
        bad_yaml = tmp_path / "in_medias_res.yaml"
        bad_yaml.write_text(
            """id: in_medias_res
axis: MACRO
display_name: "In Medias Res"
description: "Erroneously declared as macro structure"
""",
            encoding="utf-8",
        )

        with pytest.raises(StructureLoadError) as exc_info:
            load_structure_from_yaml(bad_yaml)
        assert "in_medias_res is FRAMING, never MACRO" in str(exc_info.value)

        # Direct model instantiation also fails
        with pytest.raises(ValidationError) as val_exc:
            StoryStructureDefinition(
                id="in_medias_res",
                axis="MACRO",
                display_name="In Medias Res",
            )
        assert "in_medias_res is FRAMING, never MACRO" in str(val_exc.value)

        # But valid loading as FRAMING succeeds
        valid_framing = StoryStructureDefinition(
            id="in_medias_res",
            axis="FRAMING",
            display_name="In Medias Res Framing",
        )
        assert valid_framing.axis == "FRAMING"

    # 4. compatibility matrix returns expected ALLOW/WARN/REJECT
    def test_compatibility_matrix_returns_expected_allow_warn_reject(self):
        """Compatibility matrix returns expected typed ALLOW, WARN, and REJECT verdicts."""
        evaluator = DEFAULT_COMPATIBILITY_EVALUATOR

        # ALLOW cases
        v_3act_stc, _ = evaluator.check_macro_beat_verdict("three_act", "save_the_cat")
        assert v_3act_stc == CompatibilityVerdict.ALLOW
        assert v_3act_stc == "ALLOW"

        v_3act_sc, _ = evaluator.check_macro_beat_verdict("three_act", "story_circle_stations")
        assert v_3act_sc == CompatibilityVerdict.ALLOW

        # WARN case
        v_hero_stc, _ = evaluator.check_macro_beat_verdict("heros_journey", "save_the_cat")
        assert v_hero_stc == CompatibilityVerdict.WARN
        assert v_hero_stc == "WARN"

        # REJECT cases
        v_frey_stc, _ = evaluator.check_macro_beat_verdict("freytag", "save_the_cat")
        assert v_frey_stc == CompatibilityVerdict.REJECT
        assert v_frey_stc == "REJECT"

        v_kisho_stc, _ = evaluator.check_macro_beat_verdict("kishotenketsu", "save_the_cat")
        assert v_kisho_stc == CompatibilityVerdict.REJECT

        # Any MACRO + any FRAMING = ALLOW
        for macro in ["three_act", "kishotenketsu", "freytag", "story_circle", "heros_journey"]:
            for framing in ["chronological", "in_medias_res", "flashback", "intercut", "parallel_action", "reveal_delay"]:
                v_framing, _ = evaluator.check_macro_framing_verdict(macro, framing)
                assert v_framing == CompatibilityVerdict.ALLOW

    # 5. freytag + save_the_cat rejected with reason
    def test_freytag_plus_save_the_cat_rejected_with_reason(self):
        """freytag + save_the_cat must be rejected with an explicit human-readable reason."""
        evaluator = DEFAULT_COMPATIBILITY_EVALUATOR
        verdict, reason = evaluator.check_macro_beat_verdict("freytag", "save_the_cat")
        assert verdict == CompatibilityVerdict.REJECT
        assert len(reason) > 0
        assert "positions conflict" in reason.lower() or "five-part" in reason.lower() or "freytag" in reason.lower()

        compat, warn, reason_compat = evaluator.check_macro_beat_compatibility("freytag", "save_the_cat")
        assert compat is False
        assert warn is False
        assert len(reason_compat) > 0

    # 6. kishotenketsu + conflict beat framework rejected with reason
    def test_kishotenketsu_plus_conflict_beat_framework_rejected_with_reason(self):
        """kishotenketsu + conflict-oriented beat layers must be rejected with an explicit reason."""
        evaluator = DEFAULT_COMPATIBILITY_EVALUATOR
        conflict_beats = ["save_the_cat", "freytag_beats", "story_circle_stations"]

        for beat in conflict_beats:
            verdict, reason = evaluator.check_macro_beat_verdict("kishotenketsu", beat)
            assert verdict == CompatibilityVerdict.REJECT
            assert "juxtaposition" in reason.lower() or "escalation" in reason.lower()

    # 7. PredicateSpec accepts any_of
    def test_predicate_spec_accepts_any_of(self):
        """PredicateSpec cleanly accepts any_of with valid PredicateClause items."""
        clause1 = PredicateClause(type="GOAL_ADOPTED", character="protagonist")
        clause2 = PredicateClause(type="SECRET_LEARNED", subject="central_proposition")
        spec = PredicateSpec(any_of=[clause1, clause2])
        assert spec.any_of is not None
        assert len(spec.any_of) == 2
        assert spec.all_of is None

    # 8. PredicateSpec accepts all_of
    def test_predicate_spec_accepts_all_of(self):
        """PredicateSpec cleanly accepts all_of with valid PredicateClause items."""
        clause1 = PredicateClause(type="GOAL_ADOPTED", character="protagonist")
        clause2 = PredicateClause(type="SECRET_LEARNED", subject="central_proposition")
        spec = PredicateSpec(all_of=[clause1, clause2])
        assert spec.all_of is not None
        assert len(spec.all_of) == 2
        assert spec.any_of is None

    # 9. PredicateSpec rejects both
    def test_predicate_spec_rejects_both(self):
        """PredicateSpec raises validation error when both any_of and all_of are provided."""
        clause1 = PredicateClause(type="GOAL_ADOPTED")
        clause2 = PredicateClause(type="SECRET_LEARNED")
        with pytest.raises(ValidationError) as exc_info:
            PredicateSpec(any_of=[clause1], all_of=[clause2])
        assert "not both" in str(exc_info.value) or "exactly one" in str(exc_info.value)

    # 10. PredicateSpec rejects neither if one is required
    def test_predicate_spec_rejects_neither_if_one_is_required(self):
        """PredicateSpec raises validation error when neither any_of nor all_of is provided."""
        with pytest.raises(ValidationError) as exc_info:
            PredicateSpec()
        assert "at least one" in str(exc_info.value) or "exactly one" in str(exc_info.value)

        with pytest.raises(ValidationError):
            PredicateSpec(any_of=None, all_of=None)

    # Additional Phase 3A normalization checks
    def test_fifteen_beat_collapses_to_save_the_cat(self):
        """fifteen_beat collapses into save_the_cat across normalization and compatibility."""
        assert normalize_beat_framework("fifteen_beat") == "save_the_cat"
        assert normalize_structure_id("fifteen_beat") == "save_the_cat"

        evaluator = DEFAULT_COMPATIBILITY_EVALUATOR
        verdict, _ = evaluator.check_macro_beat_verdict("three_act", "fifteen_beat")
        assert verdict == CompatibilityVerdict.ALLOW

        defn = StoryStructureDefinition(
            id="fifteen_beat",
            axis="BEAT",
            display_name="15 Beats",
        )
        assert defn.id == "save_the_cat"

    def test_virgins_promise_is_manual_only(self):
        """virgins_promise is strictly manual_only."""
        defn = StoryStructureDefinition(
            id="virgins_promise",
            axis="BEAT",
            display_name="Virgin's Promise",
            manual_only=False,  # Validator forces to True
        )
        assert defn.manual_only is True

    def test_shared_dramatic_function_vocabulary(self):
        """Verifies exactly the 13 defined dramatic functions in shared vocabulary."""
        expected = (
            "SETUP",
            "INCITING_INCIDENT",
            "INVESTIGATION",
            "DISCOVERY",
            "ESCALATION",
            "NEGOTIATION",
            "REVERSAL",
            "CONFRONTATION",
            "CRISIS",
            "CHASE",
            "REVELATION",
            "CLIMAX",
            "RESOLUTION",
        )
        assert len(DramaticFunction) == 13
        assert tuple(f.value for f in DramaticFunction) == expected
        assert DRAMATIC_FUNCTIONS == expected


class TestPhase3BStoryFeaturesAndSelection:
    """Targeted tests covering Phase 3B requirements."""

    # 1. feature extraction works with providers disabled
    def test_feature_extraction_works_with_providers_disabled(self):
        """Rule-based extractor produces a valid, complete StoryFeatures object with zero AI inference."""
        prompt = "Detective Arjun searches the warehouse at midnight for the secret classified dossier while security guards patrol."
        result = analyze_story_input(prompt, input_position="BEGINNING", provider=None)

        assert isinstance(result, StoryInputAnalysisResult)
        assert isinstance(result.features, StoryFeatures)
        assert result.features.conflict_axis == "EXTERNAL"
        assert result.features.material_driver == "CONFLICT_ESCALATION"
        assert result.features.withheld_information_present is True
        assert "thriller" in result.features.genre_signals or "noir" in result.features.genre_signals
        assert result.features.scope in ["LOCAL", "INTIMATE", "EPIC"]
        assert result.features.timespan in ["HOURS", "DAYS", "YEARS", "SINGLE_SCENE"]
        assert -1.0 <= result.features.moral_polarity <= 1.0

    # 2. same features -> same ranking
    def test_same_features_produce_same_ranking(self):
        """score() is pure and deterministic: identical inputs yield byte-for-byte identical candidate rankings."""
        defs = get_structure_registry()
        features = StoryFeatures(
            input_position="BEGINNING",
            genre_signals=["thriller", "noir"],
            protagonist_count=1,
            conflict_axis="EXTERNAL",
            transformation_expected=True,
            withheld_information_present=True,
            return_to_origin=False,
            ensemble=False,
            tone="noir",
            scope="LOCAL",
            timespan="HOURS",
            ending_known=False,
            moral_polarity=-0.5,
            twist_or_juxtaposition_driven=False,
        )

        res1 = score(features, defs)
        res2 = score(features, defs)

        assert len(res1) == len(res2)
        for c1, c2 in zip(res1, res2):
            assert c1.structure_id == c2.structure_id
            assert c1.fit_score == c2.fit_score
            assert c1.criterion_contributions == c2.criterion_contributions
            assert c1.disqualified == c2.disqualified
            assert c1.disqualifier_reasons == c2.disqualifier_reasons

    # 3. no I/O in score path
    def test_no_io_in_score_path(self, monkeypatch):
        """score() must perform zero file, network, or external I/O during execution."""
        defs = get_structure_registry()
        features = StoryFeatures(conflict_axis="EXTERNAL")

        def forbidden_io(*args, **kwargs):
            raise AssertionError("I/O attempted inside score()!")

        monkeypatch.setattr("builtins.open", forbidden_io)
        monkeypatch.setattr("pathlib.Path.open", forbidden_io)
        monkeypatch.setattr("pathlib.Path.read_text", forbidden_io)
        monkeypatch.setattr("pathlib.Path.read_bytes", forbidden_io)

        candidates = score(features, defs)
        assert len(candidates) > 0
        for c in candidates:
            assert 0.0 <= c.fit_score <= 1.0
            assert len(c.criterion_contributions) > 0

    # 4. conflict-forward premise ranks kishotenketsu below conflict structures
    def test_conflict_forward_premise_ranks_kishotenketsu_below_conflict_structures(self):
        """Under external conflict, Kishōtenketsu ranks below Three-Act and Hero's Journey."""
        prompt = (
            "An undercover detective enters an abandoned warehouse at midnight to recover a stolen classified dossier. "
            "Inside, the detective meets a nervous courier who claims not to know anything about the dossier."
        )
        analysis = extract_story_input_rule_based(prompt)
        assert analysis.features.conflict_axis == "EXTERNAL"
        assert analysis.features.twist_or_juxtaposition_driven is False

        defs = get_structure_registry()
        candidates = score(analysis.features, defs)
        scores_by_id = {c.structure_id: c.fit_score for c in candidates}

        assert scores_by_id["kishotenketsu"] < scores_by_id["three_act"]
        assert scores_by_id["kishotenketsu"] < scores_by_id["heros_journey"]
        assert candidates[0].structure_id in ["three_act", "heros_journey", "save_the_cat"]

    # 5. juxtaposition premise lets kishotenketsu score competitively
    def test_juxtaposition_premise_lets_kishotenketsu_score_competitively(self):
        """Under juxtaposition/twist, Kishōtenketsu scores competitively (>= 0.65, not near zero)."""
        prompt = (
            "A student sits in a peaceful quiet classroom watching the rain outside the window, "
            "reflecting on memories of tea with a grandfather, when an unexpected parallel juxtaposition "
            "reveals an ironic contrast in the quiet afternoon."
        )
        analysis = extract_story_input_rule_based(prompt)
        assert analysis.features.twist_or_juxtaposition_driven is True
        assert analysis.features.material_driver == "TWIST_JUXTAPOSITION"

        defs = get_structure_registry()
        candidates = score(analysis.features, defs)
        scores_by_id = {c.structure_id: c.fit_score for c in candidates}

        kisho_score = scores_by_id["kishotenketsu"]
        assert kisho_score >= 0.65
        assert candidates[0].structure_id == "kishotenketsu" or kisho_score >= scores_by_id["three_act"]

    # 6. manual override persists after rescoring
    def test_manual_override_persists_after_rescoring(self):
        """A manual structure override sets overridden_by_user=True and survives subsequent re-scoring."""
        features = StoryFeatures(conflict_axis="EXTERNAL", tone="dramatic")
        defs = get_structure_registry()

        manual_selection = select_structure(
            features=features,
            definitions=defs,
            mode="MANUAL",
            manual_macro="kishotenketsu",
            manual_beat=None,
            framing="in_medias_res",
        )
        assert manual_selection.primary_macro == "kishotenketsu"
        assert manual_selection.selection_mode == "MANUAL"
        assert manual_selection.overridden_by_user is True

        # Re-score with new conflict-heavy features
        new_features = StoryFeatures(
            conflict_axis="EXTERNAL",
            genre_signals=["thriller", "heist"],
        )
        re_selected = select_structure(
            features=new_features,
            definitions=defs,
            mode="AUTO",
            previous_selection=manual_selection,
        )

        assert re_selected.primary_macro == "kishotenketsu"
        assert re_selected.selection_mode == "MANUAL"
        assert re_selected.overridden_by_user is True

    # 7. invalid compatibility cannot be selected
    def test_invalid_compatibility_cannot_be_selected(self):
        """Invalid structure pairing cannot be selected in AUTO or MANUAL mode."""
        defs = get_structure_registry()
        features = StoryFeatures(conflict_axis="EXTERNAL")

        # In AUTO mode, beat_layer is never an incompatible pair
        for c in score(features, defs):
            sel = select_structure(features, defs, mode="AUTO")
            if sel.beat_layer:
                verdict, _ = DEFAULT_COMPATIBILITY_EVALUATOR.check_macro_beat_verdict(sel.primary_macro, sel.beat_layer)
                assert verdict.value != "REJECT"

        # In MANUAL mode, incompatible pairing is rejected and omitted
        manual_sel = select_structure(
            features,
            defs,
            mode="MANUAL",
            manual_macro="freytag",
            manual_beat="save_the_cat",
        )
        assert manual_sel.beat_layer is None

        # If raise_on_invalid=True, it raises ValueError
        with pytest.raises(ValueError) as exc:
            select_structure(
                features,
                defs,
                mode="MANUAL",
                manual_macro="freytag",
                manual_beat="save_the_cat",
                raise_on_invalid=True,
            )
        assert "Invalid structure compatibility" in str(exc.value)

    # 8. in_medias_res remains framing only
    def test_in_medias_res_remains_framing_only(self):
        """in_medias_res is strictly FRAMING and cannot be selected as MACRO."""
        defs = get_structure_registry()
        features = StoryFeatures(conflict_axis="EXTERNAL")

        candidates = score(features, defs)
        candidate_ids = [c.structure_id for c in candidates]
        assert "in_medias_res" not in candidate_ids

        with pytest.raises(ValueError) as exc:
            select_structure(features, defs, mode="MANUAL", manual_macro="in_medias_res")
        assert "in_medias_res is FRAMING, never MACRO" in str(exc.value)

        selection = select_structure(features, defs, mode="AUTO", framing="in_medias_res")
        assert selection.framing == "in_medias_res"

    # Task 5 Sanity Test with Real Premises A, B, C
    def test_sanity_real_premises_a_b_c(self):
        """Sanity tests with real premises A (Missing Dossier), B (Juxtaposition/Twist), and C (Transformation/Journey)."""
        defs = get_structure_registry()

        # A. The Missing Dossier
        premise_a = (
            "An undercover detective enters an abandoned warehouse at midnight to recover a stolen classified dossier. "
            "Inside, the detective meets a nervous courier who claims not to know anything about the dossier."
        )
        res_a = extract_story_input_rule_based(premise_a)
        sel_a = select_structure(res_a.features, defs)
        print("\n=== PREMISE A: THE MISSING DOSSIER ===")
        print("StoryFeatures:", res_a.features.model_dump())
        print(f"Selected Macro: {sel_a.primary_macro}, Beat Layer: {sel_a.beat_layer}, Framing: {sel_a.framing}")
        print("Ranked Candidates:")
        for c in sel_a.candidates:
            print(f"  {c.structure_id}: fit_score={c.fit_score}, criterion_contributions={c.criterion_contributions}")

        assert sel_a.primary_macro in ["three_act", "heros_journey", "save_the_cat"]
        score_3act = next(c.fit_score for c in sel_a.candidates if c.structure_id == "three_act")
        score_kisho = next(c.fit_score for c in sel_a.candidates if c.structure_id == "kishotenketsu")
        assert score_3act > score_kisho

        # B. Low-conflict juxtaposition/twist premise
        premise_b = (
            "A student sits in a peaceful quiet classroom watching the rain outside the window, "
            "reflecting on memories of tea with a grandfather, when an unexpected parallel juxtaposition "
            "reveals an ironic contrast in the quiet afternoon."
        )
        res_b = extract_story_input_rule_based(premise_b)
        sel_b = select_structure(res_b.features, defs)
        print("\n=== PREMISE B: LOW-CONFLICT JUXTAPOSITION / TWIST ===")
        print("StoryFeatures:", res_b.features.model_dump())
        print(f"Selected Macro: {sel_b.primary_macro}, Beat Layer: {sel_b.beat_layer}, Framing: {sel_b.framing}")
        print("Ranked Candidates:")
        for c in sel_b.candidates:
            print(f"  {c.structure_id}: fit_score={c.fit_score}, criterion_contributions={c.criterion_contributions}")

        score_b_kisho = next(c.fit_score for c in sel_b.candidates if c.structure_id == "kishotenketsu")
        assert score_b_kisho >= 0.65
        assert sel_b.primary_macro == "kishotenketsu"

        # C. Transformation/journey premise
        premise_c = (
            "A young villager is called on a dangerous quest across the perilous threshold to retrieve a sacred relic from the mountain depths, "
            "enduring great ordeals before making the circular journey back home transformed."
        )
        res_c = extract_story_input_rule_based(premise_c)
        sel_c = select_structure(res_c.features, defs)
        print("\n=== PREMISE C: TRANSFORMATION / JOURNEY ===")
        print("StoryFeatures:", res_c.features.model_dump())
        print(f"Selected Macro: {sel_c.primary_macro}, Beat Layer: {sel_c.beat_layer}, Framing: {sel_c.framing}")
        print("Ranked Candidates:")
        for c in sel_c.candidates:
            print(f"  {c.structure_id}: fit_score={c.fit_score}, criterion_contributions={c.criterion_contributions}")

        score_c_sc = next(c.fit_score for c in sel_c.candidates if c.structure_id == "story_circle")
        score_c_hero = next(c.fit_score for c in sel_c.candidates if c.structure_id == "heros_journey")
        assert score_c_sc >= 0.70 or score_c_hero >= 0.70
        assert sel_c.primary_macro in ["story_circle", "heros_journey"]
