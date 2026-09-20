# D3 Story Lab — Implementation Progress

| Phase | Name | Status | Session | Notes |
|-------|------|--------|---------|-------|
| 0 | Audit | COMPLETE | 1 | Comprehensive read-only architecture audit completed. |
| 1 | Foundations | COMPLETE | 2 | Seeding/replay, typed propositions/knowledge, bidirectional provenance, unified persistence + migration, and budget governor with hash cache. |
| 2 | Deterministic decision policy | COMPLETE | 3 | Omniscience firewall (CharacterWorldView), mandatory Motivation, 4 validator gates, RuleDecisionPolicy with repetition penalty, causal Event.caused_by wiring, and zero-AI simulation verified. |
| 3 | Story structure engine | COMPLETE | 4 | Data-driven YAML structures, unified DramaticFunction, flat PredicateSpec, pure rubric score, Kishōtenketsu sensitivity, and compatibility matrix. |
| 4 | Blueprint / beats / director / gate | COMPLETE | 4 | Role bindings, StateSnapshotDiffer, CanonGate enforcement, Director intervention validation, and NarrativeSufficiencyGate. |
| 5 | Observer / scene builder / causality | COMPLETE | 8 | Phase 5A (Observer, SceneBuilder, SceneObjective) & Phase 5B (CausalContinuityAnalyzer, SceneLink taxonomy, Provenance traversal) complete. |
| 6 | Arcs / subtext / performance cues | COMPLETE | 9 | CharacterArcTracker (5 arc types, persistent vs transient shifts), SubtextAnalyzer (10 intents, subjective belief preservation), PerformanceCueGenerator (8 types), InternalStateVerbGuard ("Show, Don't Tell"), and SceneBuilder Phase 6 enrichment. |
| 7.1 | Scribe contract & scene projection | COMPLETE | 11 | Omniscience firewall, ObservableSceneProjection, blocklist scanner, exact event matching, and zero-internal-leak verification. |
| 7.2 | Scribe screenplay generation | COMPLETE | 12 | Deterministic screenplay generation behind firewall, DialogueTemplateLibrary, InternalStateVerbGuard enforcement, sparse parentheticals, and Missing Dossier acceptance. |
| 7.3 | Quality validator & legacy migration | COMPLETE | 13 | ScreenplayQualityValidator (inspectable rules), legacy completion/synopsis migration, vocabulary cleanup, and full Phase 7 acceptance gate. |
| 8.1 | Shot planner & psychological camera | COMPLETE | 14 | Domain models (ShotPlan, CompositionPlan), inspectable rules table (11 rows), Show-Don't-Tell emotion from PerformanceCue, and unbudgeted shot planning. |
| 8.2 | Visual bible / keyframe budget / rendering | COMPLETE | 15 | VisualBibleBuilder with cached entity reuse and scoped props, KeyframeSelector (budgets 4/8/12 scored against PRIORITY_ORDER), StoryboardPromptBuilder with fixed style profile and leak checks, and GroundedStoryboardRenderer wiring deterministic SVG fallback previs. |
| 8.3 | Storyboard QA & acceptance gate | COMPLETE | 16 | StoryboardQualityValidator (8 inspectable metrics, zero aggregate scoring), prohibited media static scanner, legacy cut-over of renderer.py, budget-violation regression prevention, and Missing Dossier acceptance. |
| **8** | **Overall Storyboard Phase** | **COMPLETE** | **16** | **Phase 8 (8.1, 8.2, 8.3) complete. Phase 9 (Frontend) is next.** |
| 9 | Frontend | NOT_STARTED | | |
| 10 | Export / demo / metrics / cleanup | NOT_STARTED | | |

## Session log
- Session 1: Phase 0 audit complete. Recorded inventory of 311 backend tests (14.7s) and 49 frontend tests (14.7s), mapped 98 capabilities, verified all 12 architectural invariants, audited AI call sites, and identified demo blockers.
- Session 2: Phase 1 Foundations complete. Implemented:
  - 1.1 Deterministic RNG seeding & replay across SimulationOrchestrator, SimulationEngine, EventRecorder, ActorAgent, and policies. Added EventLog domain model. Verified byte-identical replay over 10 ticks.
  - 1.2 Typed Proposition & KnowledgeItem models adhering to Rules 4 & 5. WorldState proposition registry + character.knows() view. Verified false beliefs/deception and inter-character knowledge sharing.
  - 1.3 ProvenanceService providing bidirectional traversal across panels, screenplay blocks, and world events.
  - 1.4 Project persistence enhancements: schema_version=2, media/ directory layout, and lossless migration of legacy unversioned project files.
  - 1.5 BudgetGovernor with token/panel/cost hard limits and ContentHashCache for duplicate prompt caching.
  - Added 9 unit tests in test_phase1_foundations.py. Verification suite passing: 320 backend tests, 49 frontend tests.
- Session 3: Phase 2 Deterministic Decision Policy complete. Implemented:
  - 2.1 Carry-over verification: Hardened replay over 100 ticks with AI providers disabled, byte-identical history & final state, seed sensitivity confirmed. Verified round-trip persistence and audited existing scoring/decision components.
  - 2.2 Omniscience Firewall: Pure projection `project_view(world, character) -> CharacterWorldView` exposing only character's subjective `KnowledgeItem`s, co-located visible entities, and reachable zones. Canonical proposition registry, foreign knowledge, and unheld secrets strictly excluded.
  - 2.3 ActionProposal with mandatory `motivation: Motivation` (no default value) carrying causal context (`PURSUE_GOAL`, `REACT_TO_EVENT`, `ACT_ON_KNOWLEDGE`, `AVOID_THREAT`).
  - 2.4 Causal Event wiring: `Event.caused_by: List[str]` and `Event.motivation: Optional[Dict[str, Any]]` populated deterministically by `ActionExecutor` from proposal motivation and `KnowledgeItem.acquired_at_event`.
  - 2.5 Four validator gates (`KnowledgeGate`, `SpatialGate`, `CanonGate` stub, `AffordanceGate`) with `ActionRejection` logged outside immutable event history.
  - 2.6 `@runtime_checkable` `DecisionPolicy` protocol with formal `RuleDecisionPolicy` (zero AI calls, repetition penalty anti-stall, scoring tie-breaks) and swappable `LLMDecisionPolicy`.
  - Added 17 unit tests in test_phase2_decision_policy.py. Verification suite passing: 346 backend tests, 49 frontend tests. Zero regressions.
- Session 4: Phases 3 & 4 (Story Structure Engine + Blueprint / Director / Sufficiency Gate) complete:
  - Phase 3 Story Structure Engine:
    - 3.1 Three orthogonal axes separated: MACRO (three_act, kishotenketsu, freytag, story_circle, heros_journey), BEAT (save_the_cat, freytag_beats, story_circle_stations, virgins_promise), and FRAMING (chronological, in_medias_res, flashback, intercut, parallel_action, reveal_delay). in_medias_res strictly excluded from MACRO candidates. virgins_promise set to manual_only.
    - 3.2 Unified 13-member `DramaticFunction` enum defined once and aligned with `ScenePurposeType` for Phase 5 reuse.
    - 3.3 Zero-code-change YAML data structures in `src/story/structures/*.yaml` with startup validation failing loudly on malformed syntax/schemas.
    - 3.4 Flat `PredicateSpec` / `PredicateClause` schema validating `any_of` xor `all_of` without nested composition.
    - 3.5 External `src/story/compatibility.yaml` matrix with reason strings rejecting `freytag + save_the_cat` and `kishotenketsu + conflict beats`.
    - 3.6 `StoryFeatures` extraction (Site #1) with pure keyword/heuristic fallback sensitive to twist/juxtaposition, allowing Kishōtenketsu to score competitively on non-conflict material.
    - 3.7 Pure `score()` rubric function with transparent criterion contributions (0.0-1.0 fit scores) and `select_structure()` preserving user overrides.
    - Added 10 unit tests in test_phase3_story_structure.py. Verification suite passing: 356 backend tests, 49 frontend tests. Zero regressions.
  - Phase 4 Blueprint, Director, and Narrative Sufficiency Gate:
    - 4.1 `Proposition.enforced: bool = False` added. Replaced `CanonGate` stub with mechanical check rejecting actions contradicting `enforced=True` propositions (possession, locations, locked states). Non-enforced propositions remain un-policed for character deception.
    - 4.2 `StoryRoleBindings` resolves protagonist, focal object, central proposition, antagonist, and mentor from input analysis. Unresolvable symbolic references degrade gracefully by dropping the clause or marking beat `unevaluable=True` without crashing.
    - 4.3 `StateSnapshotDiffer` caches world state snapshots across ticks to evaluate predicates over replay (`GOAL_ADOPTED`, `BELIEF_FLIP`, `POSSESSION_CHANGE`, `RELATIONSHIP_THRESHOLD_CROSSED`, `SECRET_LEARNED`). Genuine threshold crossing correctly distinguished from already-above conditions. Phase 6 arc reuse comment included.
    - 4.4 `compile_blueprint()` generates `StoryBlueprint` with `BeatPressure`s bound to concrete world entities and normalized `target_window`s. Unmet beats whose windows expire transition cleanly to `UNSATISFIED` with `deviation_note` without stalling simulation.
    - 4.5 `DirectorAgent` constrained strictly to `DirectorIntervention` enum. Interventions routed through `ActionValidator` and rejected identically to character proposals if violating gates. Puppetry prevented: external interventions produce `actor_ids = []` and `source = "DIRECTOR"`. Asymmetric escalation ladders populated for obstacles and empty for setup/revelation/resolution.
    - 4.6 `NarrativeSufficiencyGate` evaluates beat satisfaction, climax detection, and arc emergence, producing all 4 recommendation values (`PROCEED`, `CONTINUE`, `ADJUST_PRESSURE_AND_CONTINUE`, `HALT_INSUFFICIENT`).
    - 4.7 `SimulationOrchestrator` integrates differ, beat predicate evaluations, Director pacing/beat escalation, and dynamically extends tick budget on `ADJUST_PRESSURE_AND_CONTINUE` with pending beat window recomputations up to `hard_cap`, halting cleanly on `HALT_INSUFFICIENT` without exceptions.
    - Full pipeline verified end-to-end with zero AI calls.
    - Added 19 unit tests in test_phase4_blueprint_director.py. Verification suite passing: 375 backend tests, 49 frontend tests. Zero regressions.
- Session 5: Phase 3 (Phase 3A + Phase 3B: Story Structure Definitions, Taxonomy, Compatibility, Features, Rubric Scoring, and Selection) complete:
  - Phase 3A: Formalized 3 orthogonal narrative axes (`MACRO`, `BEAT`, `FRAMING`), single shared 13-member `DramaticFunction` vocabulary (`ScenePurposeType = DramaticFunction`), YAML data definitions across all 9 canonical structures, `PredicateClause`/`PredicateSpec`, and external `compatibility.yaml` with typed verdicts (`ALLOW`, `WARN`, `REJECT`) and human-readable reasons.
  - Phase 3B: Extended `StoryFeatures` with explicit `material_driver` (`CONFLICT_ESCALATION` vs `TWIST_JUXTAPOSITION`) allowing Kishōtenketsu to score fairly. Implemented dual extraction (AI call site #1 + deterministic rule fallback with providers disabled). Implemented pure explainable rubric scoring `score(features, definitions)` with 0.0-1.0 FIT SCORE, mandatory `criterion_contributions`, and zero I/O. Hardened `select_structure()` to preserve manual overrides across rescoring, filter invalid compatibility pairings, and restrict `in_medias_res` to framing only.
  - Verified on real premises A (The Missing Dossier), B (Low-conflict juxtaposition/twist), and C (Transformation/journey).
- Session 6: Phase 4 (Blueprint, Canon, Beat Pressure, Director, and Sufficiency Gate) complete:
  - 4.1 Canon extends Proposition: `Proposition.enforced: bool = False` verified. `CanonFact` metadata links `proposition_id`, `source_span`, and `role_tag`. `CanonGate` mechanically enforces possession, location, and lock invariants for `enforced=True` propositions while allowing unenforced propositions to mutate freely.
  - 4.2 Symbolic Role Bindings: `StoryRoleBindings` resolves protagonist, focal object, and central proposition from prompt analysis. Unresolvable symbolic references degrade gracefully by dropping clauses or setting `unevaluable=True` without raising exceptions.
  - 4.3 StateSnapshotDiffer: Deterministic replay state-diffing implemented for `GOAL_ADOPTED`, `BELIEF_FLIP`, `POSSESSION_CHANGE`, `RELATIONSHIP_THRESHOLD_CROSSED` (with true-crossing vs already-above boundary semantics), and `SECRET_LEARNED`. Marked with reuse comment for Phase 6 `CharacterArcTracker`.
  - 4.4 Director Guardrails: Director interventions strictly constrained to 7 non-dialogue environmental types (`INTRODUCE_OBSTACLE`, `CHANGE_DOOR_STATE`, `MOVE_NPC`, `REVEAL_CLUE`, `ANNOUNCE_DEADLINE`, `ENVIRONMENTAL_EVENT`, `INCREASE_TIME_PRESSURE`). Interventions convert to `ActionProposal(actor_id="DIRECTOR")` and route through identical `ActionValidator` gates (`KnowledgeGate`, `SpatialGate`, `CanonGate`, `AffordanceGate`). Direct dialogue forcing strictly forbidden by `AffordanceGate`. Configurable `max_interventions_total` and `min_ticks_between_interventions` cooldown enforced.
  - 4.5 Beat Pressure & Pacing: Asymmetric escalation ladders populated for obstacles and empty for setup/revelation/resolution. Normalized beat windows trigger escalation at >=60% progress if unsatisfied; closed unsatisfied windows set `status = "UNSATISFIED"` with `deviation_note` without stalling simulation.
  - 4.6 Narrative Sufficiency Gate: Explicit `SufficiencyReport` evaluated across 4 recommendations (`CONTINUE`, `ADJUST_PRESSURE_AND_CONTINUE`, `PROCEED`, `HALT_INSUFFICIENT`). `SimulationOrchestrator` dynamically extends running tick budget on `ADJUST_PRESSURE_AND_CONTINUE` bounded by `hard_cap`, halting cleanly on `HALT_INSUFFICIENT` without throwing exceptions.
  - 4.7 The Missing Dossier Scenario Integration: End-to-end zero-AI verification on detective/courier premise confirming structure selection (`three_act`), role bindings, canonical truth, omniscience firewall protection (0 knowledge leaks), lack of puppetry violations (0 character events sourced to Director), immutable event history (0 event rewrites), and byte-identical deterministic replay.
  - Full verification suite passing: 402 backend tests (34 in `test_phase4_blueprint_director.py`), 49 frontend tests (`npm test -- --run`), `npm run build` succeeds, `npx tsc --noEmit` succeeds, `git diff --check` clean. Phase 4 COMPLETE.
- Session 7: Pre-Phase-5 Carry-Over Stabilization complete:
  - 7.1 Early-Beat Satisfaction Diagnostic & Fix:
    - Analyzed `setup` and `inciting_incident` in The Missing Dossier scenario.
    - Classified `setup` as **B. BASELINE SEMANTIC BUG**: `StateSnapshotDiffer.evaluate_goal_adopted` checked delta from tick 0 against tick 0 where initial seeded goals were already established, preventing pre-seeded goals from satisfying opening beats starting at tick 0.
    - Classified `inciting_incident` (window `[0.08, 0.20]`) as **A. CORRECT EMERGENT UNSATISFIED**: characters legitimately explored rather than discovering secrets or adopting new goals during ticks 1-4; beat expired cleanly with a logged deviation note without halting simulation.
    - Applied the smallest generic correction in `StateSnapshotDiffer.evaluate_goal_adopted`: when `start_tick == 0`, initial seeded goals are recognized as adopted for opening beats, while for later windows (`start_tick > 0`), genuine adoption transitions within `[start_tick, end_tick]` remain strictly required.
    - Added `satisfaction_tick: Optional[int] = None` to `BeatPressure` and populated it upon satisfaction in `SimulationOrchestrator`. Fixed tick boundary rounding to `int(round(...))` across `SimulationOrchestrator` and `DirectorAgent`.
    - Added 3 regression tests in `tests/test_pre_phase5_stabilization.py`.
  - 7.2 Legacy Knowledge & Subtext Audit and Migration:
    - Audited all reads of `Character.known_facts` and `Character.beliefs` across `backend/src/`.
    - Enumerated and classified occurrences across 7 architectural categories (`MIGRATION_ONLY`, `BACKWARD_COMPATIBILITY_ONLY`, `DISPLAY_DEBUG_ONLY`, `ACTIVE_DECISION_INPUT`, `ACTIVE_VALIDATION_INPUT`, `ACTIVE_SUBTEXT_INPUT`, `ACTIVE_WORLD_TRUTH_INPUT`).
    - Migrated `SubtextAnalyzer` (`src/narrative/subtext.py`) to read typed `Character.knowledge` (`KnowledgeItem`) with subjective perspective-relative truth vs canonical objective truth comparison, preserving backward-compatibility fallback when `character.knowledge` is empty.
    - Added 7 regression tests in `tests/test_pre_phase5_stabilization.py` verifying typed driving, false belief perspective retention, unheld secret firewall, isolation between characters, isolation from legacy fields, and legacy project backward compatibility.
  - 7.3 Scenario Re-run & Invariants:
    - Re-ran The Missing Dossier: `setup` SATISFIED at tick 0, `save_the_cat_opening_image` SATISFIED at tick 0, `save_the_cat_midpoint` SATISFIED at tick 5, `climax` SATISFIED at tick 22.
    - Re-verified all 6 architectural invariants: zero AI calls in CI/offline verification (`provider.call_count == 0`), canonical truth inviolate, zero knowledge leaks, zero puppetry violations, zero event rewrites, and byte-identical replay over 204 events.
  - Full verification suite passing: 412 backend tests (`pytest -q`), 49 frontend tests (`npm test -- --run`), `npm run build` succeeds, `npx tsc --noEmit` succeeds, `git diff --check` clean. Working tree is NOT committed and NOT pushed.
- Session 8: Phase 5 (Phase 5A: Observer + Scene Builder + Scene Objective, and Phase 5B: Scene Causal Continuity + Phase 5 Acceptance) complete:
  - Phase 5A:
    - 5A.1 Shared Dramatic Vocabulary: Ensured `DramaticFunction` (13 members) is the canonical shared enum definition for `BeatPressure.dramatic_function`, `ScenePurpose`, and `ScenePurposeType`. Exported from `domain.story_structure` and `domain`.
    - 5A.2 Observer Salience Scoring: Implemented deterministic `EventSalience` with non-empty `signals` dict (`state_delta_magnitude`, `knowledge_change_magnitude`, `relationship_change_magnitude`, `goal_progress_delta`, `beat_binding_bonus`, `dramatic_intensity`). Calibrated scoring (idle < 0.25, confrontation >= 0.80, director urgency >= 0.60). Guaranteed zero AI calls and byte-identical immutability on `EventHistory`.
    - 5A.3 Scene & SceneObjective Models: Created/extended `Scene` (`presentation_position == chronological_position`) and observational `SceneObjective` (`pov_character_id`, `wants`, `emotional_want`, `obstacle`, `tactics`, `outcome`, `state_delta`) with zero invented goals/tactics.
    - 5A.4 Sufficiency Gate Gating: Implemented `SufficiencyGateExecutionError`; Scene Builder runs only after terminal recommendation (`PROCEED`, `HALT_INSUFFICIENT`) and rejects non-terminal recommendation (`CONTINUE`, `ADJUST_PRESSURE_AND_CONTINUE`).
    - 5A.5 Deterministic Scene Grouping & Static Scene Flagging: Grouped events on location changes, time gaps (>2 ticks), and participant changes. Detected static scenes (`is_static = True`) based on zero entry-to-exit state delta.
    - 5A.6 Deterministic Turning Point & Provenance: Selected salience-backed turning point event or None. Registered Event -> Scene bidirectional provenance via `ProvenanceService`.
    - 5A.7 Verification: Added 19 comprehensive unit tests in `tests/test_phase5a_observer_scene_builder.py`.
  - Phase 5B:
    - 5B.1 SceneLink Model: Defined `SceneLinkType` (`THEREFORE`, `BUT`, `AND_THEN`, `MEANWHILE`) and `SceneLink` backed by mandatory evidence event IDs.
    - 5B.2 THEREFORE: Deterministic causal ancestry traversal using BFS along `Event.caused_by` back to initiating events.
    - 5B.3 BUT: Goal-progress reversal evaluation using `SceneObjective`, `StateSnapshotDiffer`, and goal status/possession loss. Explicitly verified that an obstacle without reversal is NOT automatically BUT.
    - 5B.4 AND_THEN & MEANWHILE: Evaluated uncaused transitions as diagnostic defects (`AND_THEN`) and demonstrably concurrent cross-location scenes as `MEANWHILE`.
    - 5B.5 CausalContinuityAnalyzer: Computed total scene links, therefore/but/and_then/meanwhile counts, `and_then_ratio`, and detected consecutive AND_THEN runs (`consecutive_and_then_runs`).
    - 5B.6 Provenance Integration: Extended `ProvenanceService` with bidirectional `Event <-> Scene <-> SceneLink` traversal.
    - 5B.7 The Missing Dossier Scenario Diagnostic: 205 events, 21 scenes, 20 links (18 THEREFORE, 1 MEANWHILE, 1 AND_THEN, 0 BUT, `and_then_ratio = 0.05`, 0 consecutive runs).
    - 5B.8 Verification: Added 16 unit/integration tests in `tests/test_phase5b_causal_continuity.py`. Total backend tests expanded to 447 passing tests. Frontend tests: 49 passing. Production build and typecheck passing. Phase 5 COMPLETE.
- Session 9: Phase 6 (Character Arcs + Subtext + Performance Cues) complete:
  - 6.1 Character Arc Tracker:
    - Extended domain models: `ArcClassification` (`POSITIVE_CHANGE`, `FALL`, `FLAT_TESTING`, `DISILLUSIONMENT`, `NO_ARC_DETECTED`), `TurningPoint` (`event_id`, `delta_magnitude`, `description`, `tick`, `state_change_type`), and `CharacterArc` with starting/ending state dictionaries, turning points, evidence event IDs, and `reason_if_none`.
    - Integrated `CharacterArcTracker` using `StateSnapshotDiffer` (`snap_start` vs `snap_end`). Grounded turning points on belief flips (`0.40`), goal status transitions (`0.35`), relationship shifts (`0.30`), and persistent emotional changes (`0.30`).
    - Differentiated persistent emotional transformations from transient spikes (spikes reverting within 2 subsequent ticks or ending at baseline are excluded).
    - Hardened trajectory classification with word boundary detection to prevent false substring matches (e.g. "allies" vs "lies"). Verified Arjun's trajectory in The Missing Dossier classifies deterministically as `DISILLUSIONMENT`.
  - 6.2 Subtext Analyzer:
    - Fully migrated to typed `Character.knowledge` (`dict[str, KnowledgeItem]`) without authoritative reads of legacy unversioned fields.
    - Supported 10 spoken intent classifications: `TRUTHFUL`, `EVASIVE`, `CONCEALING`, `HALF_TRUTH`, `MISDIRECTING`, `LYING`, `MANIPULATIVE`, `THREATENING`, `DEFLECTING`, `VULNERABLE`.
    - Preserved subjective false belief separation: when character subjectively believes P=False, stating "P is false" is classified as `TRUTHFUL`, not `LYING`.
    - Deception detection: Maya's denial of the classified dossier in The Missing Dossier classifies as `LYING` with private truth referencing `prop_dossier_in_desk` (`"dossier is_in desk_drawer"`). Arjun's knowledge is completely unpolluted.
  - 6.3 Performance Cue Generator:
    - Mapped internal subtext and emotion into observable physical behavior across 8 canonical types: `EYE_MOVEMENT`, `PHYSICAL_DISTANCE`, `GESTURE_TICK`, `BREATHING`, `MICRO_EXPRESSION`, `OBJECT_DISPLACEMENT`, `VOICE_CRACK`, `POSTURE_SHIFT`.
    - Implemented `InternalStateVerbGuard` enforcing "Show, Don't Tell" by strictly rejecting unobservable internal verbs (`knows`, `realizes`, `feels`, `remembers`, `is afraid`, `decides`). Verified that 100% of generated performance cues pass this guard.
  - 6.4 Scene Model & Downstream Scribe Support:
    - Extended `Scene` with `character_arcs: Dict[str, Any]`, `subtext_analyses: List[Any]`, and `performance_cues: List[Any]`.
    - Added `SceneBuilder.enrich_scenes_with_phase6(...)` to automatically attach character arcs, dialogue subtext analyses, and physical performance cues to scenes for Phase 7 Scribe consumption.
  - 6.5 Zero AI Calls:
    - Ensured 100% deterministic rule-based execution across arc tracking, subtext analysis, cue generation, and verb guarding.
  - 6.6 Verification & Diagnostics:
    - Added 23 unit/integration tests in `tests/test_phase6_arcs_subtext_cues.py` covering all required specifications.
    - Executed full Missing Dossier Phase 6 pipeline: Arjun arc (`DISILLUSIONMENT`, 2 turning points), Maya arc (`DISILLUSIONMENT`, 1 turning point), Maya denial subtext (`LYING`, private truth referenced), all cues passed `InternalStateVerbGuard`, 0 AI calls.
    - Full verification suite passing: 470 backend tests (`pytest -q` in 12.03s), 49 frontend tests (`npm test -- --run` in 14.49s), production build and TypeScript check clean (`npm run build && npx tsc --noEmit`). Phase 6 COMPLETE.
- Session 10: Pre-Phase-7 Live UI Integration Verification complete:
  - 10.1 Blank-Screen Root Cause: In `StructureAndArcsViewer.tsx`, character arc relationship deltas were formatted using `delta.toFixed(2)`. Backend Phase 6 `CharacterArcTracker` (`src/narrative/arc_tracker.py`) generates `relationship_deltas: Dict[str, str]` with values formatted like `"Affinity: +0.4, Trust: +0.5"`. Invoking `.toFixed(2)` on string values threw an unhandled `TypeError: delta.toFixed is not a function`. In the absence of an Error Boundary, React 18 unmounted the component tree, producing a blank black screen. In addition, blueprint fit metadata nested under `blueprint.metadata` lacked safe fallback accessors, and the component lacked explicit state modeling for `LOADING`, `READY`, `NO_DATA`, and `ERROR`.
  - 10.2 Integration Fix:
    - Updated `CharacterArcReport`, `BeatDefinition`, `StoryBlueprint`, and `CausalTransitionReport` in `frontend/src/types/index.ts` to accommodate both string and numeric deltas, optional beat statuses, and enriched transition types.
    - Re-implemented `StructureAndArcsViewer.tsx` to support a 4-state lifecycle (`LOADING`, `READY`, `NO_DATA`, `ERROR`).
    - Added an internal `StructureErrorBoundary` catching uncaught rendering errors and presenting a dark-themed error card with a retry affordance rather than failing silently to a blank screen.
    - Implemented safe delta formatting (`formatDelta`, `isPositive`) supporting string deltas, numeric floats, and missing entries.
    - Added status badges (`[SATISFIED]`, `[PENDING]`, `[UNSATISFIED]`, `[PARTIAL]`) to target beats in the story blueprint outline.
    - Added a scenes breakdown section under Causal Continuity displaying POV objectives, subtext analyses (`[intent] dialogue / private truth`), and physical performance cues (`[cue_type] action`).
    - Updated `App.tsx` so `StructureAndArcsViewer` receives `project={projectData}` directly and manages its own empty/loading container state.
    - Appended styling in `frontend/src/styles.css` for error cards, loading containers, beat status badges, and scene subtext/cue chips.
  - 10.3 Project Identity Verification: Verified project `world_init_4bef81` represents "The Missing Dossier" (T10, current_tick: 10, 20 events, 3 scenes, 24 storyboard panels). Characters are preserved as Vincent Cross (`char_alpha`, Infiltrator) and Evelyn Vance (`char_beta`, Clandestine Custodian). Confirmed that Home, World, Actors, Arcs, Simulation, Script, Storyboard, and Export all bind to this exact project ID. No character renaming was performed.
  - 10.4 Script/Synopsis Legacy-Path Diagnostic: Investigated ungrounded terms ("Director interventions", "second sovereign actor") appearing in Script/Synopsis. Traced root cause to hardcoded fallback outline templates in `backend/src/narrative/completion.py` (`StoryCompletionEngine._fallback_outline`, line 138) and fallback synopsis synthesis in `backend/src/narrative/synopsis.py` (`SynopsisGenerator.generate_synopsis`, line 58). This is not a stale project ID bug; the legacy generator templates predate Phase 5-6 narrative grounding and will be cleanly superseded in Phase 7 Scribe without ad-hoc edits.
  - 10.5 Live Tab Acceptance: Verified all 8 creative workstation tabs (`HOME`, `WORLD`, `ACTORS`, `ARCS & STRUCTURE`, `SIMULATION`, `SCRIPT`, `STORYBOARD`, `EXPORT`) render without blank screens using live production data.
  - 10.6 Regression & Verification Suites: Added 5 regression tests in `frontend/src/__tests__/StructureAndArcsViewer.test.tsx` and 9 acceptance tests in `frontend/src/__tests__/LiveTabAcceptance.test.tsx`. Total frontend tests expanded from 49 to 63 passing tests.
  - Verification suite passing: 470 backend tests (`pytest -q` in 11.65s), 63 frontend tests (`npm test -- --run` in 16.27s), production build clean (`npm run build`), TypeScript check clean (`npx tsc --noEmit`), `git diff --check` clean. Working tree is NOT committed and NOT pushed.
- Session 11: Phase 7.1 Scribe Input Contract + Observable Scene Projection complete:
  - 11.1 Omniscience Firewall Models: Implemented `ObservableBeat`, `ObservableObjective`, `ObservableDialogueLine`, and `ObservableSceneProjection` in `src/narrative/scene_projection.py`. Scribe receives only this projection; never raw `WorldState` or shadow knowledge.
  - 11.2 Invariant & Exclusion Enforcement: Enforced strict 1:1 event correspondence (`projection.source_event_ids == scene.source_event_ids`). Filtered `in_play_knowledge` exclusively to present characters and propositions actively referenced in the scene's events. Strictly isolated from legacy `known_facts` and `beliefs` (reads only `character.knowledge`). Unrelated secrets held by present characters are completely excluded.
  - 11.3 Dialogue & Subtext Grounding: `ObservableDialogueLine` carries typed `communicative_intent` alongside literal `text`. In `to_reader_prose()`, `communicative_intent` is never rendered as prose or parentheticals.
  - 11.4 Vocabulary Scanner: Defined `INTERNAL_VOCABULARY_BLOCKLIST` covering 27 internal engine types. Implemented `scan_for_internal_vocabulary()` detecting any planted internal terms with word boundaries.
  - 11.5 Missing Dossier Acceptance: Projected all 3 scenes of `world_init_4bef81`. Confirmed 0 blocklist violations, exact event ID correspondence (4, 4, 12 beats), 0 knowledge leaks.
  - 11.6 Verification Suite: Added 8 comprehensive unit tests in `tests/test_phase7_scene_projection.py`. Total backend tests expanded from 470 to 478 passing tests (`pytest -q` in 12.95s). Frontend tests: 63 passing (`npm test -- --run` in 16.99s). Production build and typecheck clean (`npm run build && npx tsc --noEmit`). Clean `git diff --check`. Working tree is NOT committed and NOT pushed. Phase 7.1 COMPLETE. Prompt 2 is next.
- Session 12: Phase 7.2 Scribe Screenplay Generation + Formatting complete:
  - 12.1 ScreenplayBlock Contract & Compatibility: Extended `ScreenplayBlock` in `src/narrative/fountain.py` with `block_id`, `scene_id`, `element_type` (`SLUGLINE`, `ACTION`, `CHARACTER_CUE`, `DIALOGUE`, `PARENTHETICAL`, `TRANSITION`), `content`, and `presentation_position`, maintaining bidirectional compatibility with legacy fields (`id`, `text`, `block_type`, `chronological_position`).
  - 12.2 Dialogue Template Library & Name Resolution: Built `DialogueTemplateLibrary` in `src/narrative/scribe.py` covering all 10 communicative intents across speech acts. Implemented `resolve_display_name` mapping internal IDs to display names (e.g. `char_alpha` -> `VINCENT CROSS`), ensuring internal IDs never appear in character cues.
  - 12.3 Scene Block Composition & Invariant Enforcement: Implemented `compose_scene_blocks` and `compose_from_projections` operating purely behind `ObservableSceneProjection` with zero raw `WorldState` access:
    - `SLUGLINE`: `INT./EXT. LOCATION - TIME`, uppercase.
    - `ACTION`: Present-tense observable action passing Phase 6's `InternalStateVerbGuard.check_and_raise` directly.
    - `CHARACTER_CUE`: Uppercase display name.
    - `DIALOGUE`: Grounded line from simulation or slot-filled from `DialogueTemplateLibrary`. Repetitions suppressed into physical reaction beats.
    - `PARENTHETICAL`: Sparse physical vocal quality only (`(lowers voice)`, `(rapidly)`, `(quietly)`), max 1 per 3 lines of dialogue; never psychological emotions.
    - `TRANSITION`: Omitted by default.
    - Strict Invariants: Every block's `source_event_ids` is a subset of the projection's `source_event_ids`; `presentation_position == chronological_position` for all blocks; 0 AI calls in deterministic path.
  - 12.4 Missing Dossier Live Acceptance on `world_init_4bef81`: Generated complete screenplay (3 scenes, 33 blocks: 3 SLUGLINE, 13 ACTION, 7 CHARACTER_CUE, 3 PARENTHETICAL, 7 DIALOGUE, 0 TRANSITION). Confirmed 0 internal vocabulary blocklist hits and 0 `InternalStateVerbGuard` violations.
  - 12.5 Verification Suite: Added 10 comprehensive unit/integration tests in `tests/test_phase7_screenplay_generation.py`. Total backend tests expanded from 478 to 488 passing tests (`pytest -q` in 12.87s). Frontend tests: 63 passing (`npm test -- --run` in 16.58s). Production build and typecheck clean (`npm run build && npx tsc --noEmit`). Clean `git diff --check`. Working tree is NOT committed and NOT pushed. Phase 7.2 COMPLETE. Prompt 3 is next.
- Session 13: Phase 7.3 Screenplay Quality Validator + Legacy Migration + Phase 7 Acceptance complete:
  - 13.1 Objective ScreenplayQualityReport: Implemented deterministic `ScreenplayQualityReport` and `ScreenplayQualityValidator` in `src/narrative/screenplay_validator.py`. Reports inspectable individual metrics without opaque score aggregation: `format_conformance` (7 rules), `internal_state_leak_count` (via `InternalStateVerbGuard`), `architecture_vocabulary_leak_count` (via `INTERNAL_VOCABULARY_BLOCKLIST`), `provenance_completeness_pct`, `scene_coverage_pct`, `dialogue_subtext_consistency_issues`, `unsupported_event_invention_count`, and `missing_source_reference_count`.
  - 13.2 Legacy Completion & Synopsis Migration:
    - Cleansed hardcoded internal engine templates in `src/narrative/completion.py` ("second sovereign actor", "The Director triggers..."). Marked module as legacy/deprecated.
    - Upgraded `src/narrative/synopsis.py` (`SynopsisGenerator`) to derive grounded three-tier synopsis directly from Phase 5/6/7 scenes and screenplay blocks. Added `sanitize_narrative_text` purging all 10 legacy architecture terms ("Director injects...", "second sovereign actor", "BeatPressure", "Sufficiency Gate", etc.).
    - Cleaned frontend fallback text in `ScreenplayViewer.tsx` (purged "sovereign actors").
    - Updated `ProjectStore.normalize_project_dict` to automatically sanitize legacy synopses in-memory on project load.
    - Updated API `/api/projects/{project_id}/scribe/run`, `/synopsis`, and `/export/synopsis` to route through Phase 7 scene projections and store validated `screenplay_quality`.
  - 13.3 Full Pipeline Acceptance on The Missing Dossier (`world_init_4bef81`):
    - Generated complete screenplay (3 scenes, 33 blocks).
    - `format_conformance`: 0 violations across all 7 categories (slugline, action, character cue, dialogue, parenthetical, transition).
    - `internal_state_leak_count`: 0 (100% compliant with "Show, Don't Tell").
    - `architecture_vocabulary_leak_count`: 0.
    - `provenance_completeness_pct`: 100.0%.
    - `scene_coverage_pct`: 100.0%.
    - `unsupported_event_invention_count`: 0.
    - `missing_source_reference_count`: 0.
    - `passed`: True.
    - Provider call count: 0 (deterministic offline verification).
    - EventHistory: byte-identical before and after Scribe + validation.
  - 13.4 Verification Suite: Added 15 targeted tests in `tests/test_phase7_quality_validator.py`. Total backend tests expanded from 488 to 503 passing tests (`pytest -q` in 13.10s). Frontend tests: 63 passing (`npm test -- --run` in 16.37s). Production build clean (`npm run build`). TypeScript check clean (`npx tsc --noEmit`). `git diff --check` clean. Working tree is NOT committed and NOT pushed.
  - **Phase 7 (7.1, 7.2, 7.3) is COMPLETE overall.** Phase 8 is unlocked for human confirmation.
- Session 14: Phase 8.1 Shot Planner & Psychological Camera complete:
  - 14.1 Domain Models: Defined typed `ShotType` (10 uppercase members), `CameraAngle` (4 uppercase members), `ShotContextSignals` (9 fields), `CompositionPlan` (framing rect, subject positions, gaze vectors, depth layers, focal point), and `ShotPlan` (19 fields including non-empty provenance, PerformanceCue emotion, explainable rationale, and contributing signals dictionary) in `src/storyboard/shot_planner.py`.
  - 14.2 Inspectable Psychological Camera Rules Table: Implemented `PSYCHOLOGICAL_CAMERA_RULES` data table covering all 11 rows from §5. Evaluates power differential, revelation/reaction beats, goal progress delta (low/high angles), two-character info advantage (over-the-shoulder), intimate emotional intensity (extreme close-up), scene opening (establishing), ensemble (wide), physical action (tracking), and reversal/destabilization (dutch angle). Verbatim neutral default rationale ("no strong psychological signal, neutral default") enforced when no psychological signal dominates.
  - 14.3 Show-Don't-Tell Downstream Enforcement: `ShotPlan.emotion` populated strictly from `PerformanceCue.observable_behaviour` and verified with `InternalStateVerbGuard.check_and_raise`. Zero raw emotion vector values or internal cognitive state verbs leak downstream.
  - 14.4 Granularity & Provenance Discipline: Generates 1 establishing shot per scene plus 1 shot candidate per `ObservableBeat`. Both `screenplay_block_ids` and `source_event_ids` are strictly non-empty across all shots. Shot list is completely unbudgeted (no truncation to 4/8/12).
  - 14.5 Missing Dossier Acceptance on `world_init_4bef81`: Generated 23 complete shots across all 3 scenes (Scene 1: 5 shots, Scene 2: 5 shots, Scene 3: 13 shots). Shot distribution: 3 ESTABLISHING, 10 MEDIUM_CLOSE_UP, 4 TRACKING, 6 OVER_THE_SHOULDER. Camera angles: 13 EYE_LEVEL, 10 HIGH_ANGLE. 100% compliant with Show-Don't-Tell and non-empty provenance. Zero AI calls.
  - 14.6 Verification Suite: Added 15 comprehensive unit and acceptance tests in `tests/test_phase8_shot_planner.py`. Total backend tests expanded from 503 to 518 passing tests (`pytest -q` in 13.47s). Frontend tests: 63 passing (`npm test -- --run` in 16.39s). Production build clean (`npm run build`). TypeScript check clean (`npx tsc --noEmit`). Clean `git diff --check`. Working tree is NOT committed and NOT pushed. Phase 8.1 COMPLETE. Prompt 2 is next.
- Session 15: Phase 8.2 Visual Bible, Keyframe Budgeting, and Deterministic Previs Rendering complete:
  - 15.1 Continuity & Visual Bible Models: Defined `CharacterVisualRef`, `LocationVisualRef`, `PropVisualRef`, `VisualBible`, `ContinuityPack`, and `StoryboardPanel` in `src/storyboard/keyframe_rendering.py`.
  - 15.2 Cached Visual Bible & Scoped Props: Implemented `VisualBibleBuilder` with lazy generation and cached entity reuse so each unique entity is generated once across panels. Strictly scoped `PropVisualRef` to props present in `ShotPlan.important_props` on at least one shot candidate, avoiding scene-wide prop fabrication.
  - 15.3 Keyframe Selector: Implemented `KeyframeSelector` scoring unbudgeted shots against `PRIORITY_ORDER` (`SCENE_OPENING`, `CHARACTER_INTRODUCTION`, `CLUE_DISCOVERY`, `REACTION`, `MIDPOINT_REVERSAL`, `CONFRONTATION`, `CLIMAX`, `RESOLUTION`). Enforces exact panel budget counts (`min(budget, len(shots))`) and validates limits with Phase 1 `BudgetGovernor`.
  - 15.4 Grounded Prompt Assembly & Leak Prevention: Implemented `StoryboardPromptBuilder` with fixed style profile (pencil/charcoal/rough cross-hatching production sketch; negative tags forbidding photorealism/CGI/dialogue). Prompts are verified with `scan_for_internal_vocabulary` and `InternalStateVerbGuard` before hashing with `ContentHashCache`.
  - 15.5 Deterministic Previs Fallback: Implemented `GroundedStoryboardRenderer` wiring deterministic SVG fallback generation via `HandDrawnStoryboardProvider`/`renderer.py` without requiring AI providers (`provider_used = "DETERMINISTIC_SVG_FALLBACK"`). Reuses Phase 1 `ContentHashCache` to prevent redundant panel rendering.
  - 15.6 Missing Dossier Acceptance on `world_init_4bef81`: Planned 23 unbudgeted shots. Keyframe selector selected exactly 4 shots for budget 4, 8 shots for budget 8, and 12 shots for budget 12. Rendered 8 SVG panels for budget 8 with 0 internal leaks. Visual Bible produced 2 characters (`char_alpha`, `char_beta`), 2 locations (`Abandoned Industrial Bay`, `Subterranean Archive Vault`), and exactly 1 scoped prop (`obj_dossier`).
  - 15.7 Verification Suite: Added 8 comprehensive tests in `tests/test_phase8_keyframe_rendering.py`. Total backend tests expanded from 518 to 526 passing tests (`pytest -q` in 12.32s). Frontend tests: 63 passing (`npm test -- --run` in 16.04s). Production build clean (`npm run build`). TypeScript check clean (`npx tsc --noEmit`). Clean `git diff --check`. Working tree is NOT committed and NOT pushed. Phase 8.2 COMPLETE. Prompt 3 is next.
- Session 16: Phase 8.3 Quality Validator, Legacy Resolution, and Phase 8 Acceptance complete:
  - 16.1 Grounded StoryboardQualityReport: Implemented `StoryboardQualityReport` and `StoryboardQualityValidator` in `src/storyboard/storyboard_validator.py`. Evaluates 8 independent, inspectable metrics with zero aggregate scoring: `shot_provenance_completeness_pct` (100.0%), `panel_provenance_completeness_pct` (100.0%), `vocabulary_leak_count` (0), `internal_state_leak_count` (0), `budget_compliance` (True), `priority_order_compliance` (matches PRIORITY_ORDER rankings), `cache_hit_rate` (1.0), `prohibited_media_scan_clean` (True), and `passed` (True). Maintained backwards compatibility for legacy visual QA suite.
  - 16.2 Prohibited Media Static Scanner: Implemented `scan_codebase_for_prohibited_media` inspecting `package.json`, `requirements.txt`, and AST/regex source imports across `backend/src` and `frontend/src` for forbidden libraries (Three.js, moviepy, ffmpeg, pygame, opencv, webgl, remotion, babylon, etc.). Verified current codebase is 100% clean.
  - 16.3 Legacy Cut-Over of `renderer.py`: Added `render_from_composition_plan` directly to `HandDrawnStoryboardProvider` in `src/storyboard/sketch/renderer.py` and delegated `GroundedStoryboardRenderer.render_shot_to_svg` to it, confirming `renderer.py` is the single source of truth for deterministic SVG previs rendering.
  - 16.4 Invariant #27 Structural Budget Enforcement: Hardened `KeyframeSelector.select_keyframes` and `GroundedStoryboardRenderer.render_budgeted_storyboard` to clamp budgets strictly to `[1, 12]` (defaulting to 8 if unspecified or non-positive). Proved structurally that the legacy unbudgeted behavior (e.g. 24 panels for 3 scenes) is impossible.
  - 16.5 Missing Dossier Full Acceptance on `world_init_4bef81`: Planned 23 unbudgeted shots, selected keyframes across budgets 4, 8, 12, and rendered budget 8. Verified:
    - 0 AI calls required in offline path (`provider_calls == 0`).
    - Event history byte-identical before and after rendering (immutability preserved).
    - Exact panel count = 8.
    - All 4 invariants verified (#25 no fabricated facts, #26 prompt leak checks, #27 budget enforcement, #28 fallback distinction `provider_used = "DETERMINISTIC_SVG_FALLBACK"`).
  - 16.6 Verification Suite: Added 10 comprehensive tests in `tests/test_phase8_quality_and_acceptance.py`. Total backend tests expanded from 526 to 536 passing tests (`pytest -q` in 13.34s). Frontend tests: 63 passing (`npm test -- --run` in 16.05s). Production build clean (`npm run build`). TypeScript check clean (`npx tsc --noEmit`). Clean `git diff --check`. Working tree is NOT committed and NOT pushed.
  - **Phase 8 (8.1, 8.2, 8.3) is COMPLETE overall.** Phase 9 (Frontend) is unlocked.

## Open decisions awaiting human input
1. **Knowledge & Proposition Modeling Migration Strategy**:
   - Currently, character beliefs, secrets, facts, and memories use free-text statements (`statement: str`, `summary: str`).
   - Introducing a typed `PropositionRegistry` and `KnowledgeItem` requires deciding whether to keep existing models (`Belief`, `Secret`, `DiscoveredFact`) as backward-compatible facade wrappers or perform a clean breaking consolidation in Phase 1.
2. **AI Call Site Scope Alignment**:
   - The brief targets exactly 4 call sites: (1) Feature extraction, (2) Decision policy, (3) Scribe, (4) Image provider.
   - The existing codebase uses an LLM in `WorldInitializerService` (`WorldInitializationPlan`) to generate world layouts, characters, and initial props, as well as an LLM in `ReflectionAgent` (`ReflectionResult`).
   - Decision: Should world initialization from raw text remain an allowed LLM call site (making 5 total), or should world initialization be driven purely by feature extraction into a deterministic compiler?
3. **Storyboard Provider Consolidation**:
   - Currently, the codebase contains duplicate provider architectures (`StoryboardImageProvider` in `image_provider.py` vs `StoryboardRenderProvider` in `provider_base.py`) and multiple image engines (Google Imagen, HuggingFace, ComfyUI, Diffusers, Comic SVG, and Hand-Drawn Sketch SVG).
   - Decision: Should external cloud/local runtime providers (HuggingFace, ComfyUI, Diffusers) be pruned/demoted to focus strictly on Google Imagen + deterministic offline Hand-Drawn Sketch SVG previs?
4. **Director Privilege & Mutation Channel**:
   - Currently, the Director bypasses `ActionValidator` and directly invokes `recorder.record_event(...)`. In addition, `SimulationOrchestrator` applies emotional and belief mutations directly outside of `ActionExecutor`.
   - Decision: Should Director interventions be modeled as world-level `ActionProposal`s executed strictly via `ActionValidator` and `ActionExecutor`?
