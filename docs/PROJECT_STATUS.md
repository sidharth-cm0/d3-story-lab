# D3 Story Lab — Project Status & Implementation Inventory

**Date:** 2026-10-24<br/>
**Auditor / Engineer:** Senior AI Systems Architect (Antigravity)<br/>
**Workspace:** `/workspaces/d3-story-lab`<br/>
**Governing Principle:** Structure Without Puppetry<br/>
*(The simulation determines what happened. The event history records it. Narrative Intelligence interprets it. RAG supplies relevant knowledge. Character graphs reveal supported changes. The Scribe communicates the story.)*

---

## 1. Repository Inspection & Environment Baseline (Phase 0.1)

### 1.1 Git Topology & Working Tree
- **Repository Root:** `/workspaces/d3-story-lab`
- **Active Branch:** `main` (tracking `origin/main` at commit `4f8096a`)
- **Recent Commit History:**
  - `4f8096a` — *feat: add Narrative Genome v0.1 and narrative intelligence*
  - `cdd118e` — *Complete D3 Story Lab final integration*
  - `e51c4f0` — *Implement analytics workstation UX with dimension history sparklines and Three.js throttling (Phase I-Lite)*
  - `0fea256` — *Add shot continuity, 180 axis tracking, and reference asset upload validation (Phase H)*
  - `4ca3795` — *Add character reference profiles and event-derived continuity (Phase G)*
- **Status Summary (`git status --short --branch`):**
  - **Modified Tracked Files:**
    - `backend/src/agents/director.py` — Director narrative recommendation consideration and bounds checking.
    - `backend/src/api/app.py` — Narrative RAG, graph endpoints, recommendation application routes.
    - `backend/src/domain/character.py` — Optional emotional state typing preventing fabricated zero-defaults.
    - `backend/src/simulation/differ.py` — Belief rollback for discrete historical snapshot reconstruction.
    - `backend/src/storage/project_store.py` — Narrative intelligence fields in `ProjectData`.
    - `backend/tests/test_narrative_genome.py` — Director recommendation persistence test updates.
    - `frontend/src/__tests__/StructureAndArcsViewer.test.tsx` — Test harness updates.
    - `frontend/src/api.ts` — Recommendation POST method fix and AbortSignal support.
    - `frontend/src/components/StructureAndArcsViewer.tsx` — Recommendation button feedback lifecycle state.
    - `frontend/src/types/index.ts` — TypeScript types for RAG and temporal character graph.
  - **Untracked Additions (Audited & Verified):**
    - `backend/src/narrative/rag/` — Grounded RAG engine, models, retrieval, ingestion, embeddings, grounding validator.
    - `backend/src/narrative/temporal_graph/` — Temporal graph projector, discrete tick models, diff engine.
    - `backend/tests/test_narrative_rag.py` — 10 unit/integration tests for RAG engine and firewall.
    - `backend/tests/test_temporal_graph.py` — 11 tests for graph projection, determinism, and caching.
    - `backend/tests/test_retrieval_benchmark.py` — 4 benchmark tests comparing BM25, local hashing, and hybrid ranking.
    - `backend/tests/test_full_narrative_integration.py` — 2 end-to-end integration tests.
    - `frontend/src/components/temporal_graph/` — Interactive temporal character graph viewer component.
    - `frontend/src/__tests__/TemporalCharacterGraph.test.tsx` — 5 Vitest tests for graph UI.

### 1.2 Runtime & Dependency Versions
- **Python:** `3.14.2`
- **Node.js:** `v24.20.0`
- **npm:** `11.19.0`
- **Backend Manifest:** [`backend/requirements.txt`](file:///workspaces/d3-story-lab/backend/requirements.txt)
  - `pydantic>=2.0` (active: 2.13.0)
  - `pytest>=7.0` (active: 9.1.1)
  - `fastapi>=0.100.0`
  - `uvicorn>=0.20.0`
  - `httpx>=0.25.0`
  - `python-dotenv>=1.0.0`
- **Frontend Manifest:** [`frontend/package.json`](file:///workspaces/d3-story-lab/frontend/package.json)
  - `react`: `^18.3.1`, `react-dom`: `^18.3.1`
  - `vite`: `^5.4.10`, `vitest`: `^2.1.9`
  - `tailwindcss`: `^3.4.19`, `framer-motion`: `^13.4.0`, `three`: `^0.186.0`
  - `@testing-library/react`: `^16.3.3`, `typescript`: `~5.6.2`

### 1.3 Security & Secret Hygiene
- Root `.env` and `backend/.env` are strictly excluded via [`.gitignore`](file:///workspaces/d3-story-lab/.gitignore).
- No API keys, credentials, or production tokens are committed to tracked git history.
- Local storage directories `backend/data/projects/*` are git-ignored with `.gitkeep` preservation.

---

## 2. Implementation Inventory (Phase 0.2)

### 2.1 World Initialization & Story Blueprinting
- **Location:** `backend/src/generator/` ([`world_initializer.py`](file:///workspaces/d3-story-lab/backend/src/generator/world_initializer.py)), `backend/src/story/` ([`blueprint_compiler.py`](file:///workspaces/d3-story-lab/backend/src/story/blueprint_compiler.py), [`structure_selector.py`](file:///workspaces/d3-story-lab/backend/src/story/structure_selector.py), [`structures/*.yaml`](file:///workspaces/d3-story-lab/backend/src/story/structures/))
- **Public Interface:**
  - `WorldInitializerService.generate_plan(seed_prompt, declared_type, target_duration_minutes) -> WorldInitializationPlan`
  - `WorldInitializerService.instantiate_world(plan) -> WorldState`
  - `StructureSelector.select_structure(seed_prompt, declared_type) -> StructureSelectionResult`
  - `compile_blueprint(structure, roles, duration) -> StoryBlueprint`
- **Data Inputs / Outputs:** Inputs: string prompts, input types (`ARTICLE`, `SCENARIO`, `PREMISE`), durations. Outputs: validated `WorldState`, `StoryBlueprint` with target beat windows and `BeatPressure`s.
- **Persistence:** Saved in `project.json` under `story_blueprint` and initial `world`.
- **Test Coverage:** `test_blueprint_and_analyzer.py`, `test_story_structure.py`, `test_phase3_story_structure.py`, `test_phase4_blueprint.py`.
- **Dependencies:** `domain/world.py`, `domain/story_structure.py`, `providers/llm.py` (MockLLMProvider fallback).

### 2.2 Character Models & Intake
- **Location:** `backend/src/domain/character.py`, `backend/src/domain/character_creation.py`, `backend/src/domain/character_dynamics.py`
- **Public Interface:**
  - `Character(id, name, role, personality_traits, emotional_state, goals, beliefs, secrets, knowledge, current_location_id, inventory)`
  - `CharacterInput`, `CharacterProfileDraft`
  - `CharacterEnrichmentService.enrich(draft) -> CharacterProfileDraft`
- **Data Inputs / Outputs:** Character archetypes, traits, dynamic psychological profiles $\to$ validated runtime `Character` entities.
- **Persistence:** Nested in `WorldState.characters` and `ProjectData.character_inputs`.
- **Test Coverage:** `test_character.py`, `test_character_enrichment.py`, `test_character_workstation.py`.
- **Dependencies:** `domain/continuity.py`, `domain/proposition.py`.

### 2.3 WorldState & WorldView
- **Location:** `backend/src/domain/world.py`, `backend/src/simulation/perception.py` ([`CharacterWorldView`](file:///workspaces/d3-story-lab/backend/src/simulation/perception.py))
- **Public Interface:**
  - `WorldState(id, name, current_tick, locations, characters, objects, propositions, secrets, relationships, events)`
  - `project_view(world: WorldState, character: Character) -> CharacterWorldView`
- **Data Inputs / Outputs:** Inputs: canonical `WorldState` and target `Character`. Outputs: strictly bounded `CharacterWorldView` exposing only co-located entities, reachable adjacent zones, and private subjective knowledge.
- **Firewall Invariant:** Canonical proposition registry, foreign character knowledge, and unheld secrets are mechanically excluded from `CharacterWorldView`.
- **Persistence:** Authoritative source of truth serialized into `project.json`.
- **Test Coverage:** `test_world_state.py`, `test_phase2_decision_policy.py`, `test_narrative_coherence.py`.

### 2.4 Decision Policies & Action Validation
- **Location:** `backend/src/simulation/actions.py`, `backend/src/simulation/decision_policy.py`, `backend/src/simulation/affordances.py`
- **Public Interface:**
  - `DecisionPolicy.propose_action(world_view: CharacterWorldView, character: Character, tick: int) -> ActionProposal`
  - `RuleDecisionPolicy`, `LLMDecisionPolicy`
  - `ActionValidator.validate_action(world: WorldState, proposal: ActionProposal) -> Tuple[bool, str]`
- **Validation Gates:**
  1. `KnowledgeGate`: Rejects actions referencing unobserved objects or unheld propositions.
  2. `SpatialGate`: Enforces graph adjacency for movement and co-location for speech/transfers.
  3. `AffordanceGate`: Enforces portability, lock states, and physical capacity.
  4. `CanonGate`: Rejects actions contradicting `enforced=True` propositions.
- **Persistence:** Rejections logged to ephemeral rejection audit; approved actions executed into `EventLog`.
- **Test Coverage:** `test_action.py`, `test_action_validator.py`, `test_phase2_decision_policy.py`.

### 2.5 Simulation Clock & Execution Loop
- **Location:** `backend/src/simulation/engine.py`, `backend/src/simulation/orchestrator.py`
- **Public Interface:**
  - `SimulationEngine.step(world: WorldState, ticks: int = 1) -> List[Event]`
  - `SimulationOrchestrator.run(num_ticks: int = 1) -> OrchestrationResult`
- **Data Flow:** Discrete tick increments $\to$ perception filtering $\to$ agent action proposals $\to$ validation gate check $\to$ state execution $\to$ event recording $\to$ relationship/emotion evolution.
- **Test Coverage:** `test_engine.py`, `test_orchestrator.py`, `test_simulation.py`.

### 2.6 EventLog & Causal References
- **Location:** `backend/src/domain/event.py`, `backend/src/simulation/recorder.py`
- **Public Interface:**
  - `Event(id, tick, event_type, actor_ids, location_id, description, caused_by: List[str], motivation: Optional[Dict], metadata)`
  - `EventRecorder.record_event(...) -> Event`
  - `EventLog(events: List[Event])`
- **Causal Guarantee:** Every executed event carries deterministic `caused_by` parent event IDs derived from the proposing character's motivation and knowledge provenance.
- **Persistence:** Immutable ordered list stored in `project.json`.
- **Test Coverage:** `test_event.py`, `test_causal_and_arc.py`, `test_phase1_foundations.py`.

### 2.7 State Snapshots & Historical Reconstruction
- **Location:** `backend/src/simulation/differ.py` ([`StateSnapshotDiffer`](file:///workspaces/d3-story-lab/backend/src/simulation/differ.py))
- **Public Interface:**
  - `StateSnapshotDiffer.get_or_create_snapshot(tick, world) -> WorldSnapshot`
  - Historical rollback: reverses object pickups/drops, spatial moves, relationship dimensions, emotions, and character beliefs acquired after `tick`.
  - Evaluators: `evaluate_goal_adopted`, `evaluate_belief_flip`, `evaluate_possession_change`.
- **Test Coverage:** `test_differ.py`, `test_phase4_blueprint.py`, `test_temporal_graph.py`.

### 2.8 Director Agent & Intervention Budgets
- **Location:** `backend/src/agents/director.py` ([`DirectorAgent`](file:///workspaces/d3-story-lab/backend/src/agents/director.py))
- **Public Interface:**
  - `DirectorAgent.consider_intervention(world, blueprint, current_tick) -> Optional[DirectorIntervention]`
  - `DirectorAgent.consider_narrative_recommendation(world, rec) -> Optional[DirectorIntervention]`
  - `DirectorAgent.inject_intervention(world, recorder, intervention, validator=ActionValidator()) -> Optional[Event]`
- **Budget Governor:** Enforces global intervention budget, cooldown intervals (min 3 ticks between interventions), and quiet interval respect.
- **Anti-Puppetry Boundary:** Director actions execute with `actor_ids = []` and `source = "DIRECTOR"`. Characters retain complete autonomy to ignore environmental conditions.
- **Test Coverage:** `test_director.py`, `test_narrative_genome.py`, `test_full_narrative_integration.py`.

### 2.9 Conflict & Dramatic Signal Analysis
- **Location:** `backend/src/narrative/conflict_engine.py`, `backend/src/domain/conflict.py`
- **Public Interface:**
  - `ConflictEngine.derive_conflict_graph(world: WorldState, project_id: str) -> ConflictGraph`
  - `ConflictEdge(source_character_id, target_character_id, dimensions, aggregate_intensity)`
  - Dimensions: Goal Opposition, Resource Contention, Information Asymmetry, Relationship Friction, Ideological Clash.
- **Test Coverage:** `test_conflict_engine.py`, `test_conflict_engine_api.py`.

### 2.10 Narrative Genome & Advisory System
- **Location:** `backend/src/narrative/genome/`, `backend/data/narrative_genome/core_patterns.json`
- **Public Interface:**
  - `NarrativeAnalyzer.analyze(world, events, blueprint, conflict_graph) -> NarrativeAnalysisResult`
  - `NarrativeAdvisor.advise(analysis, blueprint) -> List[NarrativeRecommendation]`
  - `core_patterns.json`: 14 curated abstract patterns (`NG-001` through `NG-014`).
- **Test Coverage:** `test_narrative_genome.py`, `test_narrative_genome_api.py`.

### 2.11 Project Persistence & REST API
- **Location:** `backend/src/storage/project_store.py`, `backend/src/api/app.py`
- **Public Interface:**
  - `ProjectStore(base_dir)` with per-file mutex locks (`_locks_guard`), schema versioning (`schema_version=2`), and atomic writes.
  - Endpoints: `/api/projects`, `/step`, `/run`, `/synopsis`, `/screenplay`, `/storyboard`, `/conflicts`, `/narrative-genome/*`, `/graph/*`, `/narrative-rag/*`.
- **Test Coverage:** `test_api.py`, `test_migration_compatibility.py`, `test_full_narrative_integration.py`.

### 2.12 Screenplay Generation & Grounding (Scribe)
- **Location:** `backend/src/narrative/scribe.py`, `backend/src/narrative/screenplay_quality.py`, `backend/src/narrative/fountain.py`
- **Public Interface:**
  - `Scribe.compose_screenplay(projection: ObservableSceneProjection) -> ScreenplayDocument`
  - `ScreenplayQualityValidator.validate(document, projection) -> ScreenplayQualityReport`
- **Grounding Rule:** Scribe is restricted to observable scene projections and verified events. Internal private states are policed by `InternalStateVerbGuard` ("Show, Don't Tell").
- **Test Coverage:** `test_scribe.py`, `test_screenplay_quality.py`, `test_subtext_performance.py`.

### 2.13 Visual Production, Continuity & Storyboard
- **Location:** `backend/src/storyboard/` ([`shot_planner.py`](file:///workspaces/d3-story-lab/backend/src/storyboard/shot_planner.py), [`visual_bible.py`](file:///workspaces/d3-story-lab/backend/src/storyboard/visual_bible.py), [`continuity_validator.py`](file:///workspaces/d3-story-lab/backend/src/storyboard/continuity_validator.py), [`sketch/`](file:///workspaces/d3-story-lab/backend/src/storyboard/sketch/))
- **Public Interface:**
  - `ShotPlanner.plan_shots(scene: SceneData) -> ShotPlan` (Psychological camera & 180° axis tracking).
  - `VisualBibleBuilder.build(world, scenes) -> VisualBible`.
  - `ContinuityValidator.validate(plan, bible) -> ContinuityReport`.
  - Deterministic vector preview renderer (procedural SVG crosshatching, graphite grain).
- **Prohibited Media Enforcement:** Zero animation, video, audio, or 3D dependencies in production path.
- **Test Coverage:** `test_storyboard.py`, `test_storyboard_pipeline.py`, `test_sketch_storyboard.py`.

### 2.14 Frontend Workstation & Viewers
- **Location:** `frontend/src/` ([`App.tsx`](file:///workspaces/d3-story-lab/frontend/src/App.tsx), [`components/`](file:///workspaces/d3-story-lab/frontend/src/components/), [`api.ts`](file:///workspaces/d3-story-lab/frontend/src/api.ts))
- **Workstations:**
  1. Overview & Setup Modal (`NewProjectModal.tsx`)
  2. World & Spatial Map (`WorldCanvas.tsx`)
  3. Character Workstation (`CharacterWorkstation.tsx`)
  4. Arcs & Structure Intelligence (`StructureAndArcsViewer.tsx`)
  5. Simulation Controls & Event History (`SimulationControls.tsx`)
  6. Temporal Character Graph (`TemporalCharacterGraph.tsx`)
  7. Screenplay Viewer (`ScreenplayViewer.tsx`)
  8. Storyboard Studio (`StoryboardStudio.tsx`)
  9. Visual QA Inspector (`VisualQaView.tsx`)
- **Test Coverage:** 14 Vitest suites, 182 tests passed.

---

## 3. Reproducible Baseline Execution (Phase 0.3)

### 3.1 Test Execution Results
All test commands executed natively in the workspace environment:

```bash
# 1. Full Backend Test Suite
pytest backend/tests
# Result: 684 passed in 20.52s (100% pass rate)

# 2. Frontend Vitest Test Suite
npm --prefix frontend test -- --run
# Result: 182 passed across 14 test files in 39.77s (100% pass rate)

# 3. Frontend Production Build
npm --prefix frontend run build
# Result: tsc && vite build built in 6.54s (Clean bundle output)
```

### 3.2 Known-Good Scenario Fixture: "The Missing Dossier"
To verify deterministic continuity without third-party LLMs or non-deterministic drift, the reference test scenario in [`test_undercover_warehouse_demo.py`](file:///workspaces/d3-story-lab/backend/tests/test_undercover_warehouse_demo.py) was verified:

- **Cast:**
  - Detective Evelyn Cross (`char_cross`) — Goal: Secure the stolen syndicate manifest.
  - Smuggler Vincent Vane (`char_vane`) — Goal: Deliver cargo to buyer at the docks.
  - Security Guard Marcus Reyes (`char_reyes`) — Goal: Patrol sector and log unauthorized entry.
- **Spatial Topology:**
  - `loc_warehouse` $\leftrightarrow$ `loc_dock`
  - `loc_warehouse` $\leftrightarrow$ `loc_office`
- **Initial Propositions & Asymmetrical Secrets:**
  - `prop_dossier_location`: Objective truth = inside locked safe in `loc_office`.
  - Secret: Cross knows Vane's true contact frequency; Vane believes the dossier is already moved to the docks.
- **Deterministic Replay Verification:**
  - Replaying 100 ticks with AI providers disabled yields byte-identical event logs, character knowledge sets, and final world states across multiple runs (`test_hardened_replay_100_ticks_providers_off_identical_history_and_final_state`).
  - Seed sensitivity confirmed: altering RNG seed produces branching behavior within physical affordance bounds.

---

## 4. Phase 0 Completion Gate

Phase 0 requirements are satisfied:
1. **Repository state understood and baseline recorded** (684 backend tests, 182 frontend tests passing).
2. **All existing uncommitted work protected and cataloged.**
3. **Canonical invariants verified** (canonical `WorldState` and `EventLog` non-mutation sovereignty).
4. **Implementation inventory completed** across all 14 subsystem domains.

---

## 5. Phase 1 — Stabilize the Simulation Engine (Completed)

### 5.1 Objectives & Architectural Guarantees
- **Canonical State Protection:** `WorldState` is the sole source of truth for the active simulation. Analytics, Narrative Genome, RAG, Graph visualizers, and Scribe can never mutate canonical state directly.
- **AST Sovereignty Enforcement:** AST inspection in `backend/tests/test_simulation_sovereignty.py` ensures no simulation module imports `rag`, `genome`, `temporal_graph`, or `scribe`.
- **Character Autonomy & WorldView Boundaries:** Characters act strictly upon subjective `CharacterWorldView`, isolated from ground truth propositions and other characters' private beliefs/secrets.
- **Transaction Rollback on Action Failure:** If an action proposal is rejected by any gate (CanonGate, SpatialGate, AffordanceGate, KnowledgeGate), world state remains untouched (0 mutation).
- **Causal Integrity:** Events in `EventLog` reference valid prior causal parent IDs (`caused_by`). A causal parent cannot originate from a future tick (`evt.tick <= world.current_tick`).
- **Deterministic Replay:** Re-simulating from the same initial state and seed reproduces the exact sequence of events, world properties, and character inventories.

### 5.2 Implementation Deliverables
- [`backend/src/domain/world_view.py`](file:///workspaces/d3-story-lab/backend/src/domain/world_view.py): Added safe string handling to `ObservableObject` and `project_view` to prevent validation errors on un-described objects.
- [`backend/src/simulation/affordances.py`](file:///workspaces/d3-story-lab/backend/src/simulation/affordances.py): Added null-safe `.lower()` handling for object descriptions.
- [`backend/src/simulation/orchestrator.py`](file:///workspaces/d3-story-lab/backend/src/simulation/orchestrator.py): Null-safe description slicing in cognitive effect processing.
- [`backend/src/simulation/actions.py`](file:///workspaces/d3-story-lab/backend/src/simulation/actions.py): Validated causal parents in `caused_by` to enforce `pevt.tick <= world.current_tick`.
- [`backend/tests/test_phase1_engine_stabilization.py`](file:///workspaces/d3-story-lab/backend/tests/test_phase1_engine_stabilization.py): 6 dedicated tests covering canonical immutability, worldview isolation, director anti-puppetry, transaction rollback, causal validation, and multi-tick deterministic replay.

---

## 6. Phase 2 — Narrative Genome to Director Integration (Completed)

### 6.1 Objectives & Architectural Guarantees
- **Advisory Non-Privilege:** Recommendations produced by Narrative Genome advise the Director Agent but cannot directly mutate `WorldState` or puppet character actions.
- **Deterministic Lifecycle Evaluation:** The Director evaluates recommendations through `evaluate_recommendation_lifecycle` with explicit typed states:
  - `EXECUTED`: Successfully validated environmental event injected into simulation and persisted.
  - `BLOCKED_COOLDOWN`: Interventions requested within the minimum cooldown period (3 ticks) are blocked.
  - `BLOCKED_BUDGET`: Interventions exceeding `max_interventions_total` are blocked.
  - `BLOCKED_QUIET_PERIOD`: Interventions during scene establishment (ticks 0-1) are blocked.
  - `REJECTED_VALIDATION`: Environmental actions that fail physical or canonical validation are rejected with zero mutation.
  - `REJECTED_DUPLICATE`: Re-applying an already-executed recommendation is rejected with zero mutation.
- **ActionValidator Sovereignty:** Director interventions must pass through the exact same `ActionValidator` gates (SpatialGate, AffordanceGate, CanonGate). Directors cannot force character dialogue (`SPEAK` is rejected) or violate canon facts.
- **EventLog Traceability:** Injected director events are tagged with `recommendation_id` in metadata and atomically appended to canonical `EventLog`.
- **UI Responsiveness:** The frontend `StructureAndArcsViewer` awaits POST response, disables buttons during flight, and reflects status badges ("Applied", "Queued", "Blocked").

### 6.2 Implementation Deliverables
- [`backend/src/domain/narrative_genome.py`](file:///workspaces/d3-story-lab/backend/src/domain/narrative_genome.py): Added `RecommendationLifecycleStatus` enum and typed model attributes.
- [`backend/src/agents/director.py`](file:///workspaces/d3-story-lab/backend/src/agents/director.py): Implemented `evaluate_recommendation_lifecycle`, `create_action_proposal` mapping, and default description handling.
- [`backend/src/api/app.py`](file:///workspaces/d3-story-lab/backend/src/api/app.py): Added `logger` integration, POST endpoint `/projects/{project_id}/director/apply-narrative-recommendation` returning full typed lifecycle response.
- [`frontend/src/api.ts`](file:///workspaces/d3-story-lab/frontend/src/api.ts): Corrected HTTP POST method, added request abort handling.
- [`frontend/src/components/StructureAndArcsViewer.tsx`](file:///workspaces/d3-story-lab/frontend/src/components/StructureAndArcsViewer.tsx): Integrated recommendation lifecycle UI state.
- [`backend/tests/test_phase2_director_integration.py`](file:///workspaces/d3-story-lab/backend/tests/test_phase2_director_integration.py): 6 comprehensive integration tests covering end-to-end execution, disk persistence, duplicate rejection, cooldowns, budgets, quiet periods, and ActionValidator rejections.

### 6.3 Test & Verification Summary
- **Backend Tests:** 696 passed in 20.14s (100% pass rate).
- **Frontend Tests:** 182 passed in 41.08s (100% pass rate).
- **Frontend Production Build:** `tsc && vite build` built cleanly in 6.85s.

---

## 7. Phase 3 — Define the Narrative Intelligence Contract & Evaluation Baseline (Completed)

### 7.1 Objectives & Architectural Guarantees
- **System Boundary Formalization:** Documented and enforced distinct roles across the entire engine:
  - `SIMULATION`: Sole component with execution authority to mutate `WorldState`.
  - `WORLD_STATE`: Canonical source of truth for physical entities.
  - `EVENT_LOG`: Immutable chronological history with causal parent links.
  - `NARRATIVE_GENOME`: Observational dramatic pattern and tension detection.
  - `RAG`: Grounded narrative retrieval citing verifiable project entity IDs.
  - `ADVISOR`: Generates optional recommendations for pacing/tension.
  - `DIRECTOR`: Injects bounded environmental pressures through ActionValidator.
  - `CHARACTER_GRAPH`: Reconstructs historical states/beliefs without foresight leakage.
  - `SCRIBE`: Converts canonical events into Fountain screenplay format.
- **Standardized Evidence Citations:** All analytical claims must cite standardized evidence records containing `id`, `category`, `entity_type`, `entity_id`, `tick`, `character_id`, `relationship_key`, and `analyzer_version`.
- **Category Firewall & Unsupported Claim Labeling:**
  - Citing an abstract pattern or unexecuted recommendation as an executed canonical fact is flagged as `CATEGORY_MISMATCH`.
  - Claims without explicit evidence IDs are strictly labeled `INFERRED`.
  - Claims citing nonexistent entities or events are labeled `UNSUPPORTED`.
- **Versioned Evaluation Corpus:** Introduced versioned scenarios (`scenario_missing_dossier_v1`, `scenario_hotel_intrigue_v1`) specifying:
  - Exact initial world topologies and enforced propositions.
  - Asymmetric private secrets and strict character knowledge boundaries.
  - Known no-answer questions to test refusal/insufficient evidence handling.
  - Expected dramatic signals, pattern IDs, and intervention outcomes.
- **Quantitative Baseline Metrics Suite:** Implemented `BaselineMetricsCalculator` measuring all 11 required dimensions:
  1. `deterministic_replay_consistency`
  2. `action_validation_correctness`
  3. `causal_reference_validity`
  4. `narrative_pattern_detection_accuracy`
  5. `evidence_citation_validity`
  6. `unsupported_claim_rate`
  7. `correct_no_answer_rate`
  8. `character_knowledge_violation_rate`
  9. `director_execution_audit`
  10. `graph_reconstruction_consistency`
  11. `screenplay_factual_grounding`

### 7.2 Implementation Deliverables
- [`backend/src/narrative/intelligence_contract.py`](file:///workspaces/d3-story-lab/backend/src/narrative/intelligence_contract.py): Formal system boundary specifications, `StandardizedEvidence`, `EvidenceAuditResult`, `NarrativeBaselineMetrics`, `NarrativeContractVerifier`, and `BaselineMetricsCalculator`.
- [`backend/src/narrative/evaluation_corpus.py`](file:///workspaces/d3-story-lab/backend/src/narrative/evaluation_corpus.py): Versioned test scenarios (`SCENARIO_MISSING_DOSSIER_V1`, `SCENARIO_HOTEL_INTRIGUE_V1`) and world factories.
- [`backend/tests/test_phase3_narrative_intelligence_contract.py`](file:///workspaces/d3-story-lab/backend/tests/test_phase3_narrative_intelligence_contract.py): 8 comprehensive tests verifying boundaries, firewall mismatch detection, claim labeling, corpus initialization, baseline metrics computation, and correct no-answer behavior.

### 7.3 Test & Verification Summary
- **Backend Tests:** 704 passed in 21.63s (100% pass rate).
- **Frontend Tests:** 182 passed in 41.08s (100% pass rate).
- **Frontend Production Build:** Clean build in 6.85s.

---

## 8. Phase 4 — Finish Narrative Genome v0.1 (Completed)

### 8.1 Objectives & Architectural Guarantees
- **Domain Schema Stabilization:** Stabilized `NarrativeRecommendation` with explicit explainability fields:
  - `observed_issue`: Exact diagnostic finding that motivated the advisory pressure.
  - `relevance_score`: Heuristic relevance to the immediate pacing need (distinct from epistemic confidence).
  - `counter_conditions`: Specific operational or dramatic conditions where the recommendation should NOT be applied.
  - `limitations`: Structural and spatial constraints (e.g. clue reachability, Director budgets).
  - `status`: Typed lifecycle status tracking (`PENDING`, `ACCEPTED`, `BLOCKED_*`, `REJECTED_*`, `EXECUTED`).
- **Deterministic Analyzer Hardening:**
  - Robust handling of 0-event and 1-event stories without zero-division or NaN crashes.
  - Deduplicated information discovery tracking so repeated event IDs do not double-count discoveries.
  - Explicit detection of belief contradictions (`EventType.BELIEF_FORMED` with inverted confidence or contradicted facts $\to$ `InformationPattern.CONTRADICTION`).
  - Explicit detection of secret revelations (`InformationPattern.REVELATION`).
  - Detection of stalled relationships in `_identify_unresolved_threads`.
  - Pacing assessment accurately categorizes `healthy`, `stalled`, `idle`, and `overheated` states.
- **Advisor Deduplication & Director Awareness:**
  - Prevents recommending interventions whose target pressure or recommendation ID has already been executed in recent history.
  - Director cooldowns and budget exhaustion are surfaced directly in recommendation `counter_conditions` and `limitations`.
- **UI Diagnostics, Dismissal & Feedback:**
  - Updated `StructureAndArcsViewer.tsx` to display `observed_issue`, supporting event IDs, relevance percentage, and counter-condition tags.
  - Added user dismissal capability (`Dismiss` button with `dismissedRecIds` state).
  - Clean empty state when all recommendations are dismissed or pacing is balanced.

### 8.2 Implementation Deliverables
- [`backend/src/domain/narrative_genome.py`](file:///workspaces/d3-story-lab/backend/src/domain/narrative_genome.py): Added `observed_issue`, `relevance_score`, `counter_conditions`, `limitations`, and `status` to `NarrativeRecommendation`.
- [`backend/src/narrative/narrative_analyzer.py`](file:///workspaces/d3-story-lab/backend/src/narrative/narrative_analyzer.py): Event deduplication, belief flip detection, secret revelation classification, and stalled relationship thread extraction.
- [`backend/src/narrative/narrative_advisor.py`](file:///workspaces/d3-story-lab/backend/src/narrative/narrative_advisor.py): Director awareness, past execution filtering, and explainability attribute population.
- [`frontend/src/types/index.ts`](file:///workspaces/d3-story-lab/frontend/src/types/index.ts): Synchronized TypeScript `NarrativeRecommendation` interface.
- [`frontend/src/components/StructureAndArcsViewer.tsx`](file:///workspaces/d3-story-lab/frontend/src/components/StructureAndArcsViewer.tsx): Rendered observed issues, supporting event citations, dismiss controls, and counter-condition alerts.
- [`backend/tests/test_phase4_narrative_genome_hardening.py`](file:///workspaces/d3-story-lab/backend/tests/test_phase4_narrative_genome_hardening.py): 8 comprehensive tests covering schema, short stories, event deduplication, belief flips, pacing states, advisor deduplication, director constraints, and repeated analysis consistency.

### 8.3 Test & Verification Summary
- **Backend Tests:** 712 passed in 22.05s (100% pass rate).
- **Frontend Tests:** 182 passed in 44.51s (100% pass rate).
- **Frontend Production Build:** Clean build in 7.42s (`tsc && vite build`).

---

## 9. Phase 5 — Harden Narrative RAG v1 (Completed)

### 9.1 Objectives & Architectural Guarantees
- **100% Offline Local Determinism:** RAG retrieval operates purely locally without paid vector databases, external network calls, or third-party embeddings. Combines BM25 lexical token matching with deterministic local feature hashing.
- **Categorical Source Separation & Firewalls:**
  - `CANONICAL_FACT`: Authoritative physical state and events from `WorldState` and `EventLog`.
  - `CHARACTER_KNOWLEDGE`: Asymmetric beliefs, memories, and held secrets strictly partitioned per character.
  - `ABSTRACT_PATTERN`: Narrative Genome patterns (`NG-001` through `NG-014`).
  - `DIRECTOR_POLICY`: Advisory constraints, intervention rules, and pacing budgets.
  - Asserting an abstract principle or unexecuted recommendation as an executed fact triggers a `CATEGORY_MISMATCH` rejection.
- **Evidence Verification (`EvidenceValidator`):**
  - Audits every `GroundedClaim` against ground truth before output.
  - Labels claims as `VERIFIED`, `INFERRED`, `CONTRADICTORY`, or `UNSUPPORTED`.
  - Rejects fabricated or nonexistent event/character citations (`evt_nonexistent_999`).
  - Detects WorldView firewall violations (e.g., claiming a character knows a secret they were never told).
- **Prompt Injection & Adversarial Immunity:**
  - Injected instructions attempting to mutate `WorldState` or execute simulation actions are intercepted safely.
  - RAG engine responses are strictly advisory and purely observational.
- **Safe Out-of-Domain & No-Answer Handling:**
  - Low-confidence or ungrounded queries return `status = "insufficient_evidence"` with empty claims and explicit refusal.

### 9.2 Implementation Deliverables
- [`backend/src/narrative/rag/models.py`](file:///workspaces/d3-story-lab/backend/src/narrative/rag/models.py): Typed schemas for `RAGKnowledgeRecord`, `GroundedClaim`, `EvidenceReference`, `RAGQueryResponse`, `ClaimVerificationStatus`, and `EvidenceCategory`.
- [`backend/src/narrative/rag/embeddings.py`](file:///workspaces/d3-story-lab/backend/src/narrative/rag/embeddings.py): Deterministic `LocalHashedEmbedder` with TF-IDF weighting and zero external dependencies.
- [`backend/src/narrative/rag/retrieval.py`](file:///workspaces/d3-story-lab/backend/src/narrative/rag/retrieval.py): `NarrativeRetriever` providing hybrid BM25 + dense hashed similarity with configurable score thresholds.
- [`backend/src/narrative/rag/ingestion.py`](file:///workspaces/d3-story-lab/backend/src/narrative/rag/ingestion.py): Ingestion pipelines converting `WorldState`, `EventLog`, `ConflictGraph`, and `core_patterns.json` into typed knowledge records.
- [`backend/src/narrative/rag/grounding.py`](file:///workspaces/d3-story-lab/backend/src/narrative/rag/grounding.py): `EvidenceValidator` and `GroundedNarrativeEngine` enforcing categorical evidence verification.
- [`backend/src/narrative/rag/service.py`](file:///workspaces/d3-story-lab/backend/src/narrative/rag/service.py): Facade service providing project-level inquiry and pattern recommendation search.
- [`backend/tests/test_narrative_rag.py`](file:///workspaces/d3-story-lab/backend/tests/test_narrative_rag.py): 10 unit and integration tests.
- [`backend/tests/test_retrieval_benchmark.py`](file:///workspaces/d3-story-lab/backend/tests/test_retrieval_benchmark.py): 4 benchmark tests validating BM25, hashing, and hybrid retrieval.
- [`backend/tests/test_phase5_rag_safety.py`](file:///workspaces/d3-story-lab/backend/tests/test_phase5_rag_safety.py): 6 adversarial and safety tests.

---

## 10. Phase 6 — Temporal Character Graph (Completed)

### 10.1 Objectives & Architectural Guarantees
- **Strict Observational Sovereignty:** The temporal character graph is a derived projection of canonical `WorldState` and `EventLog`. It never mutates canonical story state.
- **Deterministic Historical Snapshot Reconstruction:**
  - Projecting at discrete tick $T$ deterministically reconstructs character locations, emotions, active goals, and held secrets strictly based on events elapsed at or prior to tick $T$ ($t \le T$).
  - Future events ($t > T$) are strictly excluded.
- **Multidimensional Relationship Edge Modeling:**
  - Replaces scalar affinity with 9 explicit dramatic dimensions: `affinity`, `trust`, `affection`, `fear`, `dependency`, `respect`, `resentment`, `suspicion`, and `power_imbalance`.
  - Every edge and dimension shift carries verifiable event IDs linking back to the `EventLog` (`evidence_event_ids`, `recent_event_id`).
  - Aggregate intensity is calculated deterministically on a $[0.0, 1.0]$ scale.
- **Deterministic Delta & Diff Calculation (`TemporalGraphDiff`):**
  - Computes exact node and edge shifts between any `from_tick` and `to_tick`.
  - Captures intervening causal events occurring strictly within the interval.
- **State Digest Caching & Invalidation:**
  - Computes SHA256 digest over project ID, tick, event tokens, character positions, and relationship metrics.
  - Automatically invalidates cache when canonical state or history changes.
- **Interactive Frontend Visualization:**
  - React/TypeScript component [`TemporalCharacterGraph.tsx`](file:///workspaces/d3-story-lab/frontend/src/components/temporal_graph/TemporalCharacterGraph.tsx) with SVG-based node rendering, timeline scrubber, character inspector drawer, and side-by-side snapshot comparison diff mode.

### 10.2 Implementation Deliverables
- [`backend/src/narrative/temporal_graph/models.py`](file:///workspaces/d3-story-lab/backend/src/narrative/temporal_graph/models.py): `TemporalGraphNode`, `TemporalGraphEdge`, `TemporalGraphSnapshot`, `TemporalGraphDiff`.
- [`backend/src/narrative/temporal_graph/projector.py`](file:///workspaces/d3-story-lab/backend/src/narrative/temporal_graph/projector.py): `TemporalGraphProjector` with state-digest caching and discrete snapshot rollback.
- [`backend/src/api/app.py`](file:///workspaces/d3-story-lab/backend/src/api/app.py): REST endpoints `/api/projects/{project_id}/graph` and `/api/projects/{project_id}/graph/diff`.
- [`frontend/src/components/temporal_graph/TemporalCharacterGraph.tsx`](file:///workspaces/d3-story-lab/frontend/src/components/temporal_graph/TemporalCharacterGraph.tsx): Interactive graph workstation and inspector.
- [`backend/tests/test_temporal_graph.py`](file:///workspaces/d3-story-lab/backend/tests/test_temporal_graph.py): 11 tests verifying replay continuity, snapshot boundaries, edge provenance, and diff calculations.
- [`frontend/src/__tests__/TemporalCharacterGraph.test.tsx`](file:///workspaces/d3-story-lab/frontend/src/__tests__/TemporalCharacterGraph.test.tsx): 5 Vitest tests.

---

## 11. Phase 7 — Cross-System Integration: RAG, Genome, Graphs, and Simulation (Completed)

### 11.1 Objectives & Architectural Guarantees
- **Unified Cross-System Invariants:**
  - Advisory outputs (Narrative Genome, RAG answers, Graph projections) cannot mutate canonical story state.
  - The Director Agent acts as the sole, strictly gated bridge between advisory recommendations and physical simulation.
- **ActionValidator Gate Sovereignty:**
  - Director recommendations are translated into concrete `DirectorIntervention` actions.
  - All interventions pass through `ActionValidator` (SpatialGate, AffordanceGate, CanonGate).
  - Validation failures produce zero state changes, zero event log modifications, and preserve disk integrity.
- **Atomic Persistence & Lifecycle Audit:**
  - Validated interventions append to the `EventLog`, mutate `WorldState`, and atomically commit to `ProjectStore`.
  - Re-projecting the temporal graph immediately reflects the executed intervention in subsequent ticks.
- **Screenplay Grounding Protection:**
  - Scribe generates scenes solely from verified historical events in the `EventLog`.
  - Unexecuted recommendations or rejected actions are never emitted into screenplays.

### 11.2 Implementation Deliverables
- [`backend/tests/test_full_narrative_integration.py`](file:///workspaces/d3-story-lab/backend/tests/test_full_narrative_integration.py): End-to-end integration tests verifying project creation, stepping, graph queries at discrete ticks, diff inspection, grounded RAG queries, out-of-domain refusals, and director intervention lifecycle.

---

## 12. Phase 8 — Stabilize Scribe & Screenplay Pipeline (Completed)

### 12.1 Objectives & Architectural Guarantees
- **Fountain Screenplay Compliance:**
  - Produces valid Fountain screenplay syntax: scene headings (sluglines), action blocks, character cues, dialogue, and sparse parentheticals.
- **100% Observable Grounding ("Show, Don't Tell"):**
  - All action lines and dialogue beats originate strictly from verified `EventLog` events via `ObservableSceneProjection`.
  - Enforces `InternalStateVerbGuard`: prohibits internal vocabulary leaks ("she felt afraid", "he wondered") in action lines.
- **Subtext, Deception & Performance Cues:**
  - `SubtextAnalyzer` compares outward dialogue against private character beliefs to identify lying, concealment, and subtextual deflection.
  - `PerformanceCueGenerator` emits physical, observable blocking cues rather than emotional exposition.
- **Screenplay Quality Validation (`ScreenplayQualityValidator`):**
  - Audits generated screenplays against observable facts, format conformance, internal vocabulary leaks, and character knowledge consistency.

### 12.2 Implementation Deliverables & Test Verification
- [`backend/src/narrative/scribe.py`](file:///workspaces/d3-story-lab/backend/src/narrative/scribe.py), [`backend/src/narrative/screenplay_validator.py`](file:///workspaces/d3-story-lab/backend/src/narrative/screenplay_validator.py), [`backend/src/narrative/fountain.py`](file:///workspaces/d3-story-lab/backend/src/narrative/fountain.py).
- Verified with 100% pass across: `test_scribe.py`, `test_screenplay_validation_hardened.py`, `test_phase7_screenplay_generation.py`, `test_phase7_quality_validator.py`, `test_subtext_performance.py`.

---

## 13. Phase 9 — Complete Visual Production & Export (Completed)

### 13.1 Objectives & Architectural Guarantees
- **Visual Bible & Continuity Tracking:**
  - Defines immutable visual reference profiles for characters (wardrobe, physical traits), locations (architectural style, lighting keys), and props.
  - `ContinuityProjector` verifies visual state consistency across sequential scenes.
- **180-Degree Camera Axis & Spatial Blocking:**
  - `ShotPlanner` and `PsychologicalCamera` track character eyelines and camera positioning.
  - Enforces 180-degree axis continuity across cut transitions to prevent disorienting reverse-angle violations.
- **Local SVG Storyboard Rendering:**
  - Procedural vector sketch engine (`backend/src/storyboard/sketch/`) generates clean architectural sketches, character poses, and lighting crosshatching with zero external GPU/cloud dependencies.
  - Fallback support for local/mock on-demand image providers.
- **Deterministic Project Export & Import:**
  - Clean serialization of visual bibles, shot plans, and storyboard manifests into project bundles.

### 13.2 Implementation Deliverables & Test Verification
- [`backend/src/storyboard/shot_planner.py`](file:///workspaces/d3-story-lab/backend/src/storyboard/shot_planner.py), [`backend/src/storyboard/visual_bible.py`](file:///workspaces/d3-story-lab/backend/src/storyboard/visual_bible.py), [`backend/src/storyboard/continuity.py`](file:///workspaces/d3-story-lab/backend/src/storyboard/continuity.py), [`backend/src/storyboard/sketch/`](file:///workspaces/d3-story-lab/backend/src/storyboard/sketch/).
- Verified with 100% pass across: `test_storyboard.py`, `test_storyboard_pipeline.py`, `test_sketch_storyboard.py`, `test_phase8_shot_planner.py`, `test_phase_h_shot_continuity.py`.

---

## 14. Phase 10 — Product-Level Quality Assurance & Scenario Benchmarks (Completed)

### 14.1 Comprehensive Test Suite Execution
- **Backend Test Suite:** **718 tests passing** in 18.69s (100% pass rate).
- **Frontend Vitest Suite:** **182 tests passing** across 14 test files in 40.07s (100% pass rate).
- **Frontend Production Build:** **Clean production bundle** built in 6.62s (`tsc && vite build`).

### 14.2 Canonical Scenario Benchmarks
Executed end-to-end across full narrative simulation pipelines:
1. **The Missing Dossier (`test_missing_dossier_scenario.py`):**
   - Verified multi-character goal contention, locked container affordance, asymmetric secret protection, and deterministic event progression.
2. **Hotel Intrigue (`test_hotel_intrigue_demo.py`):**
   - Verified multi-room spatial graph traversal, clandestine conversation observation, and conflict escalation.
3. **Undercover Warehouse (`test_undercover_warehouse_demo.py`):**
   - Verified complete 100-tick replay stability, byte-identical event logs, and zero non-deterministic drift.

---

## 15. Phase 11 — Packaging, Documentation, and Local Run Guide (Completed)

### 15.1 System Architecture Invariants (Summary)
1. **Canonical WorldState is the source of truth.** Analytics, RAG, Graph visualizers, and Scribes cannot directly mutate it.
2. **AI agents propose actions; deterministic ActionValidator executes them.**
3. **Character WorldViews are strictly bounded.** Characters cannot access foreign knowledge or unobserved entities.
4. **Events in EventLog are immutable historical facts.**
5. **Retrieval and claims are evidence-grounded.** Citations without evidence are rejected; unverified inferences are explicitly labeled.
6. **Temporal character graphs reconstruct history at tick $T$ without future leakage.**
7. **Screenplays are grounded in observable simulation events.** Internal states are never told in action lines.
8. **Storyboards preserve 180-degree camera axis and visual continuity.**
9. **The system is 100% offline runnable with zero paid external API dependencies.**

### 15.2 Local Execution Quick Start
```bash
# 1. Run all backend tests
pytest backend/tests/ -q

# 2. Run all frontend tests
npm --prefix frontend test -- --run

# 3. Build frontend production assets
npm --prefix frontend run build

# 4. Start backend server
cd backend && uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

# 5. Start frontend development server
cd frontend && npm run dev
```

---

## 16. Phase 12 — Research Roadmap & Future Directions

The following long-term research directions build upon the stabilized D3 Story Lab platform:
1. **Long-Term Memory Consolidation & Semantic Drift:** Modeling decay curves, emotional distortion, and rumor propagation over hundreds of simulation ticks.
2. **Multi-Agent Coalition & Dynamic Faction Formation:** Algorithmic detection of emerging alliances, betrayal thresholds, and conspiratorial coordination among autonomous agents.
3. **Cinematic Blocking & Real-Time Psychological Camera:** Dynamic real-time adaptation of camera focal length, Dutch angles, and lighting schemes directly responding to temporal relationship tension spikes.
4. **Interactive Audience Interventions:** Multi-user collaborative director stations with budget-weighted voting on environmental pressures.
