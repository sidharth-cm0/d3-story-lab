# D3 Story Lab — Implementation Progress

| Phase | Name | Status | Session | Notes |
|-------|------|--------|---------|-------|
| 0 | Audit | COMPLETE | 1 | Comprehensive read-only architecture audit completed. |
| 1 | Foundations | COMPLETE | 2 | Seeding/replay, typed propositions/knowledge, bidirectional provenance, unified persistence + migration, and budget governor with hash cache. |
| 2 | Deterministic decision policy | COMPLETE | 3 | Omniscience firewall (CharacterWorldView), mandatory Motivation, 4 validator gates, RuleDecisionPolicy with repetition penalty, causal Event.caused_by wiring, and zero-AI simulation verified. |
| 3 | Story structure engine | NOT_STARTED | | |
| 4 | Blueprint / beats / director / gate | NOT_STARTED | | |
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
