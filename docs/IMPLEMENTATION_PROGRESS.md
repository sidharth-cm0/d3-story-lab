# D3 Story Lab — Implementation Progress

| Phase | Name | Status | Session | Notes |
|-------|------|--------|---------|-------|
| 0 | Audit | COMPLETE | 1 | Comprehensive read-only architecture audit completed. |
| 1 | Foundations | COMPLETE | 2 | Seeding/replay, typed propositions/knowledge, bidirectional provenance, unified persistence + migration, and budget governor with hash cache. |
| 2 | Deterministic decision policy | COMPLETE | 3 | Omniscience firewall (CharacterWorldView), mandatory Motivation, 4 validator gates, RuleDecisionPolicy with repetition penalty, causal Event.caused_by wiring, and zero-AI simulation verified. |
| 3 | Story structure engine | COMPLETE | 4 | Data-driven YAML structures, unified DramaticFunction, flat PredicateSpec, pure rubric score, Kishōtenketsu sensitivity, and compatibility matrix. |
| 4 | Blueprint / beats / director / gate | COMPLETE | 4 | Role bindings, StateSnapshotDiffer, CanonGate enforcement, Director intervention validation, and NarrativeSufficiencyGate. |
| 5 | Observer / scene builder / causality | NOT_STARTED | | |
| 6 | Arcs / subtext / performance cues | NOT_STARTED | | |
| 7 | Scribe / formatting / quality | NOT_STARTED | | |
| 8 | Shot planner / visual bible / storyboard | NOT_STARTED | | |
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
