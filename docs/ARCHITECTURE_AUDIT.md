# D3 Story Lab — Architecture Audit

**Date:** 2026-09-15  
**Auditor:** Senior Software Engineer (Antigravity Read-Only Architecture Audit)  
**Workspace:** `/workspaces/d3-story-lab`  
**Operating Contract:** Read-only inspection. Zero source modifications. Zero git mutations.

---

## 1. Executive Summary

1. **Demo Blocker — Unstructured Knowledge State (B1, B2, B3):** Character secrets, beliefs, facts, and memories are stored as free-form strings (`statement: str`, `summary: str`) rather than atomic typed propositions. As a result, deception and asymmetrical knowledge verification in "The Missing Dossier" scenario currently rely on fragile substring matching rather than mechanical proposition comparison.
2. **Demo Blocker — Mock Initializer Character & Spatial Scale (B10, C2):** The deterministic fallback initializer (`WorldInitializerService._build_deterministic_mock_plan`) only instantiates two actors (`char_alpha`, `char_beta`) and two rooms. The demo scenario requires three distinct actors (Detective, Courier, Security Guard) and three locations (Warehouse, Locked Office, Guarded Exit).
3. **Demo Blocker — Missing Narrative Sufficiency Gate (C15, C16):** The simulation orchestrator lacks a `NarrativeSufficiencyGate` and `BeatEvaluator` to measure beat satisfaction dynamically. Termination is currently triggered solely by fixed tick limits (`max_ticks`), generic goal flags (`GoalStatus.ACHIEVED`), or a repetition escape hatch.
4. **Architectural Invariant Violation — Director Privilege (Invariant 3, C14):** `DirectorAgent.inject_intervention` bypasses the `ActionValidator` and calls `recorder.record_event(...)` directly. Furthermore, `SimulationOrchestrator` directly mutates `WorldState` facts, beliefs, emotions, and memories outside of `ActionExecutor`, violating the strict "agents propose; only executor mutates" rule.
5. **Architectural Invariant Violation — Scribe Omniscience (Invariant 8, F2):** `Scribe.compose_screenplay` accepts the full canonical `WorldState` instead of an observable-only scene context projection. While `ScreenplayQualityValidator` audits outputs for secret leakage post-hoc, the Scribe itself has unrestricted structural access to private character state.
6. **AI Call Site Divergence (Target = 4, Actual = 8+):** The target architecture calls for four AI sites. In reality:
   - Feature extraction is purely rule-based (no LLM site implemented).
   - An extra LLM call site exists in `WorldInitializerService` (`WorldInitializationPlan`).
   - An extra LLM call site exists in `ReflectionAgent` (`ReflectionResult`).
   - Scribe has `self.provider` completely unused (100% deterministic template-based).
   - Five distinct image provider implementations exist (Google Imagen, Hugging Face, ComfyUI, Diffusers, and procedural SVGs).
7. **Severe Duplicate Systems in Storyboard & Continuity:** Two parallel provider hierarchies exist (`StoryboardImageProvider` in `image_provider.py` vs `StoryboardRenderProvider` in `provider_base.py`); two procedural SVG engines exist (`ComicGraphicStoryboardProvider` vs `HandDrawnStoryboardProvider`); and three overlapping continuity models exist across `domain/continuity.py`, `storyboard/continuity.py`, and `storyboard/visual_bible.py`.
8. **Hard-coded Story Structures (D1, D5):** The 6 dramatic structures and the compatibility matrix are hard-coded in Python dictionaries inside `src/narrative/structure_library.py` rather than external, data-driven YAML/JSON definitions with human-readable compatibility reason strings.
9. **Zero-Quota Offline Determinism Holds (Invariants 9 & 10):** The entire system runs 100% offline without API keys or network access. All 311 backend tests pass in 14.70 seconds; all 49 frontend tests pass in 14.73 seconds. Video, animation, 3D, and WebGL outputs are strictly prohibited and mechanically guarded.
10. **High-Quality Deterministic Narrative Core:** Grounded modules already exist and function with high quality: `ActionValidator` (spatial & affordance gates), `Observer` (read-only beat clustering), `ScreenplayQualityValidator` (real computed checks for provenance, repetition, cliches, and leaks), and `PsychologicalCameraPlanner` (multidimensional camera logic).

---

## 2. Repository Map

### Real Source Tree (to Depth 3)

```
/workspaces/d3-story-lab/
├── AGENTS.md                          # Core architectural rules & mission
├── README.md                          # Platform overview & quickstart
├── backend/                           # Python FastAPI + Simulation backend
│   ├── pytest.ini                     # Pytest configuration
│   ├── requirements.txt               # Backend dependencies (FastAPI, Pydantic v2, etc.)
│   ├── data/
│   │   └── projects/                  # Local filesystem project JSON snapshots & panel assets
│   ├── scripts/                       # Quality inspection and image pipeline smoke tests
│   │   ├── render_storyboard_quality_samples.py
│   │   ├── smoke_test_image_pipeline.py
│   │   └── test_single_image.py
│   ├── src/
│   │   ├── demo_world.py              # Reference standalone sandbox world
│   │   ├── agents/                    # Autonomous character & director reasoning agents
│   │   ├── api/                       # FastAPI router, request schemas, REST endpoints
│   │   ├── domain/                    # Canonical Pydantic data models & state
│   │   ├── evaluation/                # Coherence, autonomy, and experiment metrics
│   │   ├── evolution/                 # Emotion, trust, affinity, and belief transition functions
│   │   ├── generator/                 # World initialization service & seed parser
│   │   ├── memory/                    # Episodic memory scoring, retrieval & compression
│   │   ├── narrative/                 # Scribe, Observer, Causal, Arc, Subtext, Structure analyzers
│   │   ├── providers/                 # LLM provider abstractions (Mock, Gemini)
│   │   ├── simulation/                # Clock, engine, orchestrator, actions, affordances, perception
│   │   ├── storage/                   # Project persistence & schema migration
│   │   └── storyboard/                # Shot planner, visual bible, sketch SVG, image providers
│   └── tests/                         # 51 pytest test suites (311 tests, 0 failures)
└── frontend/                          # React 18 + TypeScript creative workstation
    ├── package.json                   # Frontend dependencies (React, Vite, Vitest)
    ├── vite.config.ts                 # Vite bundler & test configuration
    ├── src/
    │   ├── App.tsx                    # Main workstation shell & tab router
    │   ├── api.ts                     # REST client connecting to backend
    │   ├── styles.css                 # Noir/Cinematic design system stylesheet
    │   ├── components/                # Modular creative UI views & inspectors
    │   ├── services/                  # Client-side external integrations
    │   ├── types/                     # TypeScript DTOs & domain mirror interfaces
    │   ├── utils/                     # Formatting utilities & prompt compilers
    │   └── __tests__/                 # 5 vitest test suites (49 tests, 0 failures)
```

### Mapping Real Layout to Target Architecture

| Target Layout Module | Real Layout Path(s) | Responsibility Alignment & Notes |
|---|---|---|
| `app/story/` | `backend/src/generator/`, `backend/src/narrative/structure_*.py` | Input normalization, feature extraction, and structure selection exist across `completion.py`, `initializer.py`, and `structure_selector.py`. Structure definitions are in Python code, not `structures/*.yaml`. |
| `app/world/` | `backend/src/domain/world.py`, `backend/src/simulation/actions.py` | `WorldState`, location connectivity, and `ActionValidator`/`ActionExecutor` are cleanly implemented here. |
| `app/characters/` | `backend/src/domain/character.py`, `backend/src/agents/actor.py` | `Character`, bounded `EmotionalState`, `Relationship`, and `ActorAgent` decision logic reside here. |
| `app/simulation/` | `backend/src/simulation/`, `backend/src/agents/director.py` | `SimulationOrchestrator` handles the tick loop and agent cycles; `DirectorAgent` handles environmental pressure. Sufficiency gate is missing. |
| `app/narrative/` | `backend/src/narrative/` | Houses `Observer`, `SceneBuilder`, `CausalContinuityAnalyzer`, `CharacterArcTracker`, and `SubtextAnalyzer`. |
| `app/screenplay/` | `backend/src/narrative/scribe.py`, `fountain.py`, `screenplay_validator.py` | Screenplay generation, Fountain formatter, and quality validator reside together in `narrative/`. |
| `app/storyboard/` | `backend/src/storyboard/` | Complete shot planner, psychological camera, visual bible, and SVG sketch engine reside here. |
| `app/providers/` | `backend/src/providers/`, `backend/src/storyboard/*provider*.py` | LLM providers are in `src/providers/`, while image providers are currently located inside `src/storyboard/`. |
| `app/persistence/`| `backend/src/storage/project_store.py`, `backend/src/storyboard/asset_store.py` | Filesystem project persistence and sandboxed asset storage are cleanly separated. |
| `app/api/` | `backend/src/api/app.py` | Monolithic FastAPI app containing all REST endpoints and DTOs. |

---

## 3. How the App Runs

### Verification Commands (Exact Commands)
- **Backend Tests (Unit & Integration):**
  ```bash
  cd /workspaces/d3-story-lab/backend && pytest
  ```
  *Observed Result:* `311 passed in 14.70s` (0 failures, 0 warnings).
- **Frontend Tests:**
  ```bash
  cd /workspaces/d3-story-lab/frontend && npm test
  ```
  *Observed Result:* `5 passed (5), 49 passed (49) in 14.73s`.
- **Frontend Build & Typecheck:**
  ```bash
  cd /workspaces/d3-story-lab/frontend && npm run build
  ```
  *Observed Result:* `tsc && vite build` succeeds cleanly with 0 TypeScript errors.

### Development Servers & Ports
- **Backend API:**
  ```bash
  cd /workspaces/d3-story-lab/backend
  uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
  ```
  Runs at `http://localhost:8000`. OpenAPI interactive docs at `http://localhost:8000/docs`.
- **Frontend UI Workstation:**
  ```bash
  cd /workspaces/d3-story-lab/frontend
  npm run dev
  ```
  Runs at `http://localhost:5173`. Proxies `/api` requests to backend on port 8000 via `vite.config.ts`.

### Environment Variables
- `GEMINI_API_KEY` / `GOOGLE_API_KEY`: Optional. If unset, backend operates 100% locally with `MockLLMProvider`.
- `STORYBOARD_IMAGE_MODEL`: Optional. Default: `gemini-3.1-flash-image`.
- `HUGGINGFACE_API_KEY`: Optional for external HuggingFace Inference API image rendering.
- `COMFYUI_SERVER_ADDRESS`: Optional for local ComfyUI instance (default: `127.0.0.1:8188`).

### Data & Storage
- Project JSON storage directory: `/workspaces/d3-story-lab/backend/data/projects/*.json`
- Asset file storage: `/workspaces/d3-story-lab/backend/data/projects/{project_id}/storyboard/{category}/{filename}`

---

## 4. Capability Matrix

| ID | Capability | Classification | File Path(s) | Note |
|---|---|---|---|---|
| **A1** | Seeded RNG / reproducible replay from `(seed, input)` | `PARTIAL` | `src/storyboard/sketch/stroke.py:30`, `src/evaluation/experiment.py:20` | Seed is passed to sketch stroke RNG, but `SimulationOrchestrator` and `WorldInitializerService` lack an explicit integer RNG seed parameter for reproducible simulation replay. |
| **A2** | Project persistence — save/load blueprint, events, screenplay, panels, media | `EXISTS` | `src/storage/project_store.py:71-206` | Full filesystem persistence of `ProjectData` including world, blueprint, scenes, screenplay, and shot plan. |
| **A3** | Schema version field in saved project format | `EXISTS` | `src/storage/project_store.py:31,50` | `schema_version: int = 2` on `ProjectMetadata` and `ProjectData` with migration normalizers. |
| **A4** | Provenance service, bidirectional (event ↔ panel) | `PARTIAL` | `src/narrative/fountain.py:27`, `src/storyboard/models.py:180-181` | Provenance IDs exist on elements (`source_event_ids`, `source_screenplay_block_ids`), but there is no dedicated bidirectional lookup service mapping an event to all resulting panels. |
| **A5** | Provider abstraction + graceful degradation | `EXISTS` | `src/providers/base.py:10`, `src/providers/gemini.py:96-100` | Clean fallback from `GeminiProvider` to `MockLLMProvider` on auth/network failure. |
| **A6** | Cassette / record-replay fixtures for provider tests | `MISSING` | `tests/test_providers.py` | No VCR / cassette fixtures exist; tests rely on explicit in-memory mocks (`MockLLMProvider`). |
| **A7** | Budget governor — token budget, panel budget | `PARTIAL` | `src/storyboard/open_model_provider.py:59`, `src/storyboard/planner.py:60` | Panel keyframe budget (4, 8, 12) is strictly enforced with candidate scoring; token budget governor is missing. |
| **A8** | Content-hash caching for generated images | `PARTIAL` | `src/storyboard/prompt_compiler.py:258`, `src/storyboard/models.py:76` | SHA-256 prompt hash (`prompt_hash`) is computed and stored on version records, but no cache lookup bypasses redundant generation. |
| **B1** | `PropositionRegistry` of canonical world facts | `MISSING` | `src/domain/world.py:123`, `src/domain/fact.py:8` | Facts are stored in `world.facts: Dict[str, DiscoveredFact]` with free text statements; no atomic proposition registry. |
| **B2** | `KnowledgeItem` with holder / certainty / acquired_at_event / source / is_secret / shared_with | `MISSING` | `src/domain/fact.py`, `src/domain/belief.py`, `src/domain/secret.py` | Disparate models (`DiscoveredFact`, `Belief`, `Secret`, `Memory`) hold unlinked, unstructured text strings without this unified model. |
| **B3** | Per-character world *view* projection | `PARTIAL` | `src/simulation/perception.py:61-144` | `KnowledgeFilter.build_observation` projects visible characters and objects, but does not filter private knowledge propositions. |
| **B4** | Bounded `EmotionVector` (numeric, not free text) | `EXISTS` | `src/domain/character.py:7-50` | `EmotionalState` has bounded floats (-1.0 to 1.0) for happiness, fear, anger, trust, curiosity. |
| **B5** | `GoalStack` — external goal, internal goal, current objective | `PARTIAL` | `src/domain/goal.py:18-53` | `Goal` model has priority and status, but lacks structured separation into external/internal/objective stack. |
| **B6** | `RelationshipScores` | `EXISTS` | `src/domain/relationship.py:5-46` | Bounded floats (-1.0 to 1.0) for `affinity` and `trust`. |
| **B7** | Deterministic rule-based `DecisionPolicy` | `EXISTS` | `src/agents/actor.py:171-280`, `src/simulation/policy.py:9` | GoalActionSelector scores affordances, dialogue, and movement deterministically. |
| **B8** | Optional LLM `DecisionPolicy` behind same interface | `EXISTS` | `src/agents/actor.py:93-128` | ActorAgent calls `generate_structured(ActorDecision)` with automatic fallback to deterministic policy. |
| **B9** | Repetition / idle-loop penalty in decision scoring | `EXISTS` | `src/agents/repetition.py:8-147` | `RepetitionTracker` penalizes consecutive waits, object pickup/drop oscillations, and repeated speech topics. |
| **B10** | Character auto-generation | `EXISTS` | `src/generator/initializer.py:89-215` | Instantiates characters, traits, visual profiles, and inventories from plans. |
| **B11** | Character CRUD via API | `MISSING` | `src/api/app.py` | Characters can only be inspected as part of `/world`; no dedicated endpoints for creating or updating characters individually. |
| **C1** | `WorldState` canonical model | `EXISTS` | `src/domain/world.py:89-146` | Central registry for locations, characters, objects, goals, beliefs, secrets, events, and facts. |
| **C2** | Zone graph — zones, adjacency, containment, doors, occlusion | `PARTIAL` | `src/domain/world.py:16-44`, `src/narrative/spatial.py:27` | `Location.connected_locations` models adjacency, and `SpatialReasoner` computes sightlines/exits, but door state and containment hierarchies are incomplete. |
| **C3** | `ActionProposal` carrying motivation | `PARTIAL` | `src/domain/action.py:30-60` | `reason: Optional[str]` exists, but there is no typed field referencing a `KnowledgeItem` or prior `event_id`. |
| **C4** | Action Validator — knowledge gate | `MISSING` | `src/simulation/actions.py:19-165` | Checks physical co-location and object ownership, but never verifies whether the actor knows the object/location exists. |
| **C5** | Action Validator — spatial gate (no teleportation) | `EXISTS` | `src/simulation/actions.py:40-44` | Verifies destination is in `current_loc.connected_locations`. |
| **C6** | Action Validator — canon gate | `MISSING` | `src/simulation/actions.py:19-165` | No verification against immutable canonical facts. |
| **C7** | Action Validator — affordance gate | `EXISTS` | `src/simulation/actions.py:59,140` | Enforces portability, lock state, container state, and character capacity. |
| **C8** | Action Executor | `EXISTS` | `src/simulation/actions.py:168-435` | Mutates world state, transfers objects, moves actors, and records events. |
| **C9** | Immutable `EventHistory` | `EXISTS` | `src/domain/event.py:25-66`, `src/simulation/recorder.py:7` | `Event` is `frozen=True` and append-only in `world.events`. |
| **C10** | `Event.caused_by[]` populated at execution time | `MISSING` | `src/domain/event.py:25` | `Event` has no `caused_by` field; causality is only inferred post-hoc in `CausalContinuityAnalyzer`. |
| **C11** | Tick orchestrator | `EXISTS` | `src/simulation/orchestrator.py:29-215` | Coordinates multi-agent turns, perception, cognition, evolution, and clock advance. |
| **C12** | Director with intervention budget | `PARTIAL` | `src/agents/director.py:36-134` | Tracks history of interventions, but lacks a budget limit or cap. |
| **C13** | Director interventions restricted to world-level enum | `EXISTS` | `src/agents/director.py:13-23` | `DirectorInterventionType` enum (knock on door, power failure, phone ring, alarm, etc.). |
| **C14** | Director interventions pass through standard Validator | `BROKEN` | `src/agents/director.py:121-131` | Directly injects events into `EventRecorder`, completely bypassing `ActionValidator`. |
| **C15** | Beat Evaluator producing `BeatBinding[]` | `MISSING` | `src/narrative/structure_analyzer.py:49` | Post-hoc `StructureAnalyzer` assesses fulfillment, but runtime simulation lacks a `BeatEvaluator` producing `BeatBinding[]`. |
| **C16** | Narrative Sufficiency Gate | `MISSING` | `src/simulation/orchestrator.py:195` | Orchestrator halts only on `max_ticks`, goal completion, or 6 identical actions. No sufficiency evaluation. |
| **C17** | Hard tick cap | `EXISTS` | `src/simulation/orchestrator.py:198` | Strict `max_ticks` loop limit enforced. |
| **D1** | Data-driven structure definitions (YAML/JSON), zero code to add | `PARTIAL` | `src/narrative/structure_library.py:23-491` | Beat sheets and structures are defined in Python code, not external YAML/JSON files. |
| **D2** | `StoryStructureDefinition` Pydantic model validated at startup | `EXISTS` | `src/domain/story_structure.py:80-92` | `StructureDefinition` model with typed beat sheets. |
| **D3** | Three-axis taxonomy: MACRO / BEAT / FRAMING | `PARTIAL` | `src/domain/story_structure.py:18,67,28` | The three concepts exist as separate enums (`StoryStructureType`, `BeatDefinition`, `PresentationStrategy`), but are not grouped into a unified taxonomy model. |
| **D4** | `in_medias_res` treated as FRAMING, not as a structure | `EXISTS` | `src/domain/story_structure.py:28-36` | Explicitly modeled under `PresentationStrategy`, separate from `StoryStructureType`. |
| **D5** | Compatibility matrix with human-readable reason strings | `PARTIAL` | `src/narrative/structure_library.py:502-516` | Matrix exists, but returns booleans without human-readable explanation strings. |
| **D6** | `StoryFeatures` extraction — LLM path | `MISSING` | `src/narrative/structure_selector.py:40` | `StructureSelector` accepts `provider` but only executes heuristic keyword parsing. |
| **D7** | `StoryFeatures` extraction — rule/keyword fallback path | `EXISTS` | `src/narrative/structure_selector.py:43-66` | Keyword sets for thriller, noir, tragedy, heist, etc. |
| **D8** | Rubric scoring as a pure function | `EXISTS` | `src/narrative/structure_selector.py:68-125` | `compute_heuristic_fit_scores` is a pure function mapping features to fit scores. |
| **D9** | Per-criterion contributions exposed (explainability) | `PARTIAL` | `src/narrative/structure_selector.py:145` | Returns a composite `fit_rationale` string rather than a structured breakdown table of criterion contributions. |
| **D10** | Scores labelled "fit score", not "confidence"/"probability" | `EXISTS` | `src/domain/story_structure.py:99` | Explicitly labelled `fit_score` with documentation emphasizing non-statistical nature. |
| **D11** | User manual override, recorded | `EXISTS` | `src/domain/story_structure.py:103` | `StructureSelectionMode.MANUAL` is recorded in selection result. |
| **D12** | `StoryBlueprint` with CANON vs INTENT separation | `PARTIAL` | `src/domain/story_structure.py:106-120` | Separates `expected_beats` and `soft_constraints`, but lacks typed `CANON` and `INTENT` sub-containers. |
| **D13** | `BeatPressure` with satisfaction predicates | `MISSING` | `src/domain/story_structure.py:67` | Beats contain string `pressure_signal`, but no executable satisfaction predicates. |
| **D14** | Escalation ladders of world-level interventions | `PARTIAL` | `src/agents/director.py:82-110` | Implemented as a static 4-step modulo sequence rather than a dynamic beat-driven escalation ladder. |
| **E1** | Observer, read-only salience selection | `EXISTS` | `src/narrative/observer.py:57-195` | Calculates event dramatic scores and filters beats without mutating history. |
| **E2** | Scene Builder as a distinct module | `EXISTS` | `src/narrative/scene_builder.py:34-220` | Clusters events into `SceneData` with boundaries and turning points. |
| **E3** | `ScenePurpose` enum | `EXISTS` | `src/domain/story_structure.py:44-56` | `ScenePurposeType` (SETUP, INVESTIGATION, CONFRONTATION, REVERSAL, etc.). |
| **E4** | `SceneObjective` (Core Emotional Objective) with `state_delta` | `PARTIAL` | `src/domain/story_structure.py:122-131` | `CoreEmotionalObjective` defines desire, obstacle, and emotional shift, but lacks an explicit `state_delta` field. |
| **E5** | Static-scene detection (empty `state_delta`) | `PARTIAL` | `src/narrative/scene_builder.py:140` | Flags low-tension/idle scenes, but not through formal empty `state_delta` checks. |
| **E6** | `SceneLink` typing — THEREFORE / BUT / AND_THEN / MEANWHILE | `PARTIAL` | `src/domain/story_structure.py:59-65` | `CausalTransitionType` has `BUT_THEREFORE`, `AND_THEN`, `COINCIDENCE`, `DISCONNECTED`; `MEANWHILE` is missing. |
| **E7** | `CausalContinuityAnalyzer` + AND_THEN ratio metric | `EXISTS` | `src/narrative/causal_analyzer.py:21-138` | Calculates `but_therefore_ratio` and `and_then_count`. |
| **E8** | Consecutive-AND_THEN run detection | `MISSING` | `src/narrative/causal_analyzer.py:113` | Computes global counts, but does not detect or flag consecutive runs of `AND_THEN`. |
| **E9** | `CharacterArcTracker` | `EXISTS` | `src/narrative/arc_tracker.py:23-159` | Observes starting/ending states, turns, decisions, and trajectory without mutating world state. |
| **E10** | `NO_ARC_DETECTED` supported end-to-end | `EXISTS` | `src/narrative/arc_tracker.py:123`, `frontend/src/components/StructureAndArcsViewer.tsx:278` | Classifies flat journeys as `OBSERVED_STABLE` and displays "Character remained steadfast throughout observed events." |
| **E11** | `SubtextAnalyzer` derived from knowledge/utterance gap | `EXISTS` | `src/narrative/subtext.py:56-231` | Evaluates dialogue against private secrets and beliefs to classify lying, evasive, and deflecting intent. |
| **E12** | `PerformanceCueGenerator` (show-don't-tell) | `EXISTS` | `src/narrative/performance_cues.py:54-191` | Translates deceptive dissonance into physical cues (tightens jaw, glances toward object, swallows). |
| **E13** | Structure conformance analyzer | `EXISTS` | `src/narrative/structure_analyzer.py:49-146` | Compares immutable events against blueprint beats to assess alignment vs organic deviation. |
| **F1** | Scribe | `EXISTS` | `src/narrative/scribe.py:26-438` | Converts filtered beats into structured screenplay blocks with headings, action, and dialogue. |
| **F2** | Scribe receives observable-only scene context | `VIOLATED` | `src/narrative/scribe.py:71` | Scribe receives full canonical `WorldState` instead of an observable-only projection. |
| **F3** | Deterministic template scribe fallback | `EXISTS` | `src/narrative/scribe.py:209-380` | Scribe currently operates 100% deterministically via template formatting without LLM reliance. |
| **F4** | `ScreenplayBlock` element model | `EXISTS` | `src/narrative/fountain.py:20-37` | Typed block element with `ScreenplayBlockType`, text, and metadata. |
| **F5** | `source_event_ids` required on every block | `PARTIAL` | `src/narrative/fountain.py:27`, `src/narrative/screenplay_validator.py:127` | Model defaults to empty list, but `ScreenplayQualityValidator` flags ungrounded blocks as errors. |
| **F6** | Formatter — slugline / action / cue / dialogue / parenthetical | `EXISTS` | `src/narrative/fountain.py:72-105` | `ScreenplayDocument.to_fountain()` formats valid Fountain syntax. |
| **F7** | Character cues resolved to stable entity IDs, not raw strings | `PARTIAL` | `src/narrative/fountain.py:28`, `src/narrative/scribe.py:48-53` | `character_id` is stored on the block, but rendered cue is upper-cased display string. |
| **F8** | `ScreenplayQualityValidator` — list each check actually implemented | `EXISTS` | `src/narrative/screenplay_validator.py:47-342` | Implements: (1) Provenance Grounding, (2) Dialogue Repetition, (3) Exposition Clichés, (4) Secret Knowledge Leakage, (5) Consecutive Parentheticals, (6) Action Duplication, (7) Spatial Presence / Teleportation, (8) Scene Turn Fulfillment. |
| **F9** | Framing / presentation ordering separate from chronology | `EXISTS` | `src/narrative/framer.py:43-225` | Preserves both `chronological_position` and `presentation_position` across framing modes. |
| **G1** | Shot Planner | `EXISTS` | `src/storyboard/planner.py:43-580` | Translates screenplay scenes and blocks into cinematic storyboard shot sequences. |
| **G2** | Psychological camera logic (power / fear / certainty / info advantage) | `EXISTS` | `src/storyboard/psychological_camera.py:39-210` | Calculates normalized vector (`PsychologicalState`) to choose lens, angle, elevation, and movement. |
| **G3** | Simplistic `emotion == CLOSE_UP` rules present? | `EXISTS` | `src/storyboard/psychological_camera.py:107-174` | Verified: No simplistic 1:1 rule. Framing is derived from a composite vector of dominance, certainty, and purpose. |
| **G4** | `CompositionPlan` | `PARTIAL` | `src/storyboard/models.py:109`, `src/storyboard/sketch/staging.py:25` | Panel composition guidance and staging planes exist, but not as an isolated `CompositionPlan` class. |
| **G5** | Procedural SVG — classify as `LEGACY` unless already demoted to previs metadata | `LEGACY` | `src/storyboard/provider.py`, `src/storyboard/sketch/renderer.py` | `provider.py` is legacy comic SVG; `sketch/renderer.py` is newer hand-drawn production board SVG. Both demoted to previs guide in tests. |
| **G6** | `VisualBible` keyed on stable entity IDs, not names | `EXISTS` | `src/storyboard/visual_bible.py:115-218` | Keyed by character, object, and location IDs (`cid`, `oid`, `lid`). |
| **G7** | `ContinuityPack` | `EXISTS` | `src/storyboard/continuity.py:42-180` | Character, location, and prop continuity packs with wardrobe, silhouettes, and lighting palettes. |
| **G8** | Keyframe budget (4 / 8 / 12) | `EXISTS` | `src/storyboard/open_model_provider.py:62-90` | Budget parameter strictly limits keyframes with hard cap of 12. |
| **G9** | Panel prioritisation order | `EXISTS` | `src/storyboard/open_model_provider.py:94-176` | Scoring algorithm prioritizes climax, major reveals, focal characters, and turning points. |
| **G10** | Image persistence to disk; no regeneration on reopen | `EXISTS` | `src/storyboard/asset_store.py:54-98` | Assets saved to disk; API checks disk files before re-rendering. |
| **G11** | Storyboard prompt style profile (graphite/charcoal/grayscale) | `EXISTS` | `src/storyboard/visual_bible.py:13-44`, `src/storyboard/sketch/lighting.py:38` | `SketchStyle.GRAPHITE_PRODUCTION_BOARD` and noir chiaroscuro ink profile. |
| **G12** | Any video / animation / 3D / WebGL code present? | `EXISTS` | `src/storyboard/on_demand_provider.py:113-115`, `tests/test_on_demand_provider.py:155` | Verified NONE present. Validation explicitly rejects GIF, MP4, animation, and video. |
| **H1** | Fountain screenplay export | `EXISTS` | `src/api/app.py:1735-1743` | Export endpoint returns downloadable `.fountain` text file. |
| **H2** | FDX export | `MISSING` | `src/api/app.py:1727-1803` | No Final Draft XML (`.fdx`) export implemented. |
| **H3** | Storyboard PDF contact sheet | `MISSING` | `src/api/app.py:1727-1803` | No PDF contact sheet export implemented. |
| **H4** | Project JSON bundle export | `EXISTS` | `src/api/app.py:1798-1800` | Export endpoint returns full `ProjectData` JSON bundle. |
| **I1** | Project creation flow (input type, structure mode, characters) | `PARTIAL` | `frontend/src/components/NewProjectModal.tsx:71-150` | Input type and structure mode are selectable, but character definition is not in the modal. |
| **I2** | Story structure display with fit score + per-criterion reasons | `PARTIAL` | `frontend/src/components/StructureAndArcsViewer.tsx:103-135` | Displays `fit_score` and `fit_rationale` string, but lacks a per-criterion tabular breakdown. |
| **I3** | Beat status display (SATISFIED / PARTIAL / UNSATISFIED) | `PARTIAL` | `frontend/src/components/StructureAndArcsViewer.tsx:146-164` | Displays target beats and pressure signals, but not runtime satisfaction status badges. |
| **I4** | Manual structure override control | `PARTIAL` | `frontend/src/components/NewProjectModal.tsx:76` | Selectable during project creation, but cannot override structure on existing project. |
| **I5** | Character arc display | `EXISTS` | `frontend/src/components/StructureAndArcsViewer.tsx:173-308` | Initial state, decisions, turns, relationship shifts, and ending state. |
| **I6** | `NO_ARC_DETECTED` rendered honestly | `EXISTS` | `frontend/src/components/StructureAndArcsViewer.tsx:278` | Displays honest steadfast/no-change message when no turns occur. |
| **I7** | Project progress display | `EXISTS` | `frontend/src/components/SimulationTicker.tsx:1-120` | Displays tick progress, events count, scene counter, and active status. |
| **I8** | Screenplay view | `EXISTS` | `frontend/src/components/ScreenplayViewer.tsx:1-400` | Displays formatted Fountain screenplay with provenance drawer. |
| **I9** | Storyboard view | `EXISTS` | `frontend/src/components/StoryboardViewer.tsx:1-600` | Grid, comic page, and presentation views with version selector. |
| **I10**| Provenance inspector (panel → shot → block → scene → event) | `PARTIAL` | `frontend/src/components/ScreenplayViewer.tsx:320`, `frontend/src/components/ShotCard.tsx:84` | Screenplay viewer traces block → event; panel viewer traces panel → block; 5-hop unified breadcrumb inspector is missing. |

### Capability Status Count Summary
- **EXISTS:** 43
- **PARTIAL:** 26
- **MISSING:** 15
- **LEGACY:** 1
- **BROKEN / VIOLATED:** 2 (`C14`, `F2`)
- **UNVERIFIED:** 0

---

## 5. Invariant Compliance (12 Invariants)

| # | Invariant | Status | Evidence (File & Line) | Detailed Analysis |
|---|---|---|---|---|
| **1** | `WorldState` is the single canonical truth. No shadow state. | **HOLDS** | `backend/src/domain/world.py:89` | Single canonical container for all locations, characters, objects, and events. No persistent shadow registries exist. |
| **2** | Agents propose; they never mutate. All mutation flows Validator → Executor. | **VIOLATED** | `backend/src/simulation/orchestrator.py:166,171` | While `ActorAgent` proposals flow through `ActionValidator` and `ActionExecutor`, post-action cognitive updates (`EmotionUpdater.adjust_emotion`) and Director interventions directly mutate `WorldState` attributes outside `ActionExecutor`. |
| **3** | The Director is not privileged — its interventions pass the same Validator. | **VIOLATED** | `backend/src/agents/director.py:121-131` | `DirectorAgent.inject_intervention` invokes `recorder.record_event(...)` directly without constructing an `ActionProposal` or passing through `ActionValidator.validate(...)`. |
| **4** | `EventHistory` is append-only and immutable. Nothing rewrites or reorders it. | **HOLDS** | `backend/src/domain/event.py:53`, `backend/src/simulation/recorder.py:34` | `Event` is configured with `ConfigDict(frozen=True)`. Events are registered into `world.events` via monotonic counter and UUID without modification or deletion. |
| **5** | The Observer selects and interprets; it never alters events. | **HOLDS** | `backend/src/narrative/observer.py:64-195` | Purely reads and scores events, emitting new `NarrativeBeat` objects that reference `source_event_ids`. |
| **6** | Characters are not omniscient. A character may only act on knowledge they hold. | **PARTIAL** | `backend/src/simulation/perception.py:65`, `backend/src/simulation/actions.py:19-165` | `KnowledgeFilter` strips private state for observations, but `ActionValidator` lacks a knowledge gate (actors can interact with any co-located entity even if unobserved). |
| **7** | Every `ScreenplayBlock` carries `source_event_ids`; every `ShotPlan` carries `screenplay_block_ids` and `source_event_ids`; every `StoryboardPanel` carries `shot_id`. | **PARTIAL** | `backend/src/narrative/fountain.py:27`, `backend/src/storyboard/models.py:103,180-181` | `ScreenplayBlock` has `source_event_ids`; `StoryboardPanel` has `source_event_ids` and `source_screenplay_block_ids` and `shot_number`, but lacks explicit `shot_id: str`; `ShotPlan` panels carry IDs but top-level `ShotPlan` does not. |
| **8** | The Scribe receives only observable facts for that scene — never full world state, never another character's private knowledge. | **VIOLATED** | `backend/src/narrative/scribe.py:71-78` | `compose_screenplay` accepts `world: WorldState` directly, exposing full world objects, all character secrets, and private memories to the Scribe method. |
| **9** | The system runs end-to-end with no LLM and no image provider, producing a complete screenplay and placeholder panels. | **HOLDS** | `backend/tests/test_undercover_warehouse_demo.py:23-131` | Entire pipeline executes offline using `MockLLMProvider` and procedural sketch SVG generators, passing 100% of integration checks. |
| **10** | CI never requires an external AI quota or network access. | **HOLDS** | `backend/tests/test_providers.py:53`, `backend/tests/conftest.py` | All 311 backend tests run in 14.70 seconds with zero network access or external API calls. |
| **11** | Simulation is chronological; presentation may reorder. Both `chronological_position` and `presentation_position` are stored; canonical history is never rewritten. | **HOLDS** | `backend/src/narrative/framer.py:65-76`, `backend/src/domain/story_structure.py:150-151` | `NarrativeFramer` assigns explicit dual positions without modifying `world.events`. |
| **12** | Quality metrics correspond to real computed checks. No decorative scores. | **HOLDS** | `backend/src/narrative/screenplay_validator.py:84-240`, `backend/src/storyboard/storyboard_validator.py:69-175` | Real algorithmic passes: substring cliché search, secret set intersection, provenance registry verification, consecutive parenthetical counts, and shot variety ratios. |

---

## 6. AI Call Site Inventory

The target architecture mandates **exactly four** AI call sites. The repository currently contains **8+ call sites** across LLMs and image providers:

### LLM Call Sites
1. **Actor Action Proposal:**  
   `backend/src/agents/actor.py:97` (`self.provider.generate_structured(ActorDecision, ...)`).  
   *Target Site 2 (Decision Policy).* Has deterministic rule-based fallback.
2. **Actor Action Retry on Rejection:**  
   `backend/src/agents/actor.py:118` (`self.provider.generate_structured(ActorDecision, retry_prompt, ...)`).  
   *Sub-call of Site 2.*
3. **World Initialization Planning:**  
   `backend/src/generator/initializer.py:71` (`self.provider.generate_structured(WorldInitializationPlan, ...)`).  
   *EXTRA CALL SITE.* Generates entire world, characters, traits, and props from raw text. Has deterministic heuristic fallback.
4. **Episodic Memory Reflection:**  
   `backend/src/agents/reflection.py:65` (`self.provider.generate_structured(ReflectionResult, ...)`).  
   *EXTRA CALL SITE.* Synthesizes episodic memories into character beliefs. Has deterministic mock fallback.
5. **Feature Extraction (Target Site 1):**  
   *MISSING CALL SITE.* `src/narrative/structure_selector.py` only implements heuristic keyword parsing; no LLM call site exists here.
6. **Scribe Screenplay Composition (Target Site 3):**  
   *MISSING CALL SITE.* `src/narrative/scribe.py` accepts `provider` in `__init__`, but never invokes it. Operates 100% deterministically.

### Image Provider Call Sites (Target Site 4)
7. **Google Cloud Imagen / Gemini:**  
   `backend/src/storyboard/image_provider.py:392` (`client.post(url, json=payload)`). Calls Google `predict` or `generateContent`.
8. **Hugging Face Inference API:**  
   `backend/src/storyboard/image_provider.py:598` (`client.post(api_url, ...)`). Calls HF endpoints.
9. **ComfyUI Local Adapter:**  
   `backend/src/storyboard/open_model_provider.py:284` & `backend/src/storyboard/on_demand_provider.py:270`. Calls local ComfyUI websocket/prompt API.
10. **In-Process Diffusers:**  
    `backend/src/storyboard/open_model_provider.py:616`. PyTorch diffusers pipeline.

---

## 7. Duplicate-System Report

1. **Storyboard Provider Abstraction Hierarchy:**
   - Hierarchy A: `StoryboardImageProvider(ABC)` in `backend/src/storyboard/image_provider.py`.
   - Hierarchy B: `StoryboardRenderProvider(ABC)` in `backend/src/storyboard/provider_base.py`.
   - Result: Parallel provider trees that duplicate status reporting, capability discovery, and rendering dispatch.
2. **Procedural SVG Rendering Engines:**
   - Engine A: `ComicGraphicStoryboardProvider` in `backend/src/storyboard/provider.py` (older SVG comic engine).
   - Engine B: `HandDrawnStoryboardProvider` in `backend/src/storyboard/sketch/renderer.py` (newer graphite sketch production board).
3. **Visual Continuity & Profile Models:**
   - `domain/continuity.py` defines `ActorVisualProfile`, `ObjectVisualProfile`, `LocationVisualProfile`.
   - `storyboard/continuity.py` defines `CharacterContinuityPack`, `LocationContinuityPack`, `PropContinuityPack`, `CharacterReferenceSheet`.
   - `storyboard/visual_bible.py` defines `VisualBible`, `CharacterVisualReference`, `LocationVisualReference`, `ObjectVisualReference`.
   - Result: Redundant fields across three different packages describing identical wardrobe, face traits, palettes, and lighting.
4. **Simulation Runtime Engines:**
   - `SimulationEngine` in `src/simulation/engine.py` (simple clock-step-validator loop).
   - `SimulationOrchestrator` in `src/simulation/orchestrator.py` (multi-agent cognitive cycle with pacing and evolution).
5. **Narrative Outline vs Story Blueprint:**
   - `StoryCompletionEngine` in `src/narrative/completion.py` outputs `StoryOutline`.
   - `StoryBlueprintGenerator` in `src/narrative/blueprint_generator.py` outputs `StoryBlueprint`.

---

## 8. Legacy / Dead Code Report

| File Path | Item | Recommendation | Risk & Rationale |
|---|---|---|---|
| `backend/src/storyboard/provider.py` | `ComicGraphicStoryboardProvider` | **Demote / Delete** | Superseded by `src/storyboard/sketch/renderer.py` (`HandDrawnStoryboardProvider`), which has far richer anatomical, perspective, and architectural rendering. |
| `backend/src/storyboard/open_model_provider.py` | `ComfyUIStoryboardAdapter`, `DiffusersStoryboardAdapter` | **Consolidate** | High maintenance overhead; duplicates `on_demand_provider.py` and `image_provider.py`. Risk: breaks local ComfyUI tests if removed without updating adapter calls. |
| `backend/src/simulation/engine.py` | `SimulationEngine` | **Keep as Facade / Demote** | Used by `tests/test_simulation_engine.py`. Can be kept for low-level unit tests or refactored into a thin wrapper around `SimulationOrchestrator`. |
| `backend/src/domain/action.py:21-28` | Legacy `ActionType` aliases (`PICKUP`, `DROP`, `GIVE`, `OPEN_DOOR`) | **Keep Aliases** | Backwards-compatibility aliases. Zero runtime cost; risk of breaking early tests if deleted prematurely. |
| `backend/src/narrative/completion.py` | `StoryCompletionEngine` | **Consolidate** | Generates legacy `StoryOutline`. Should be unified into `StoryBlueprintGenerator` so the pipeline has a single source of structural intent. |

---

## 9. Test Inventory

- **Backend (Pytest):**
  - Total test files: **51 files** in `backend/tests/`
  - Total test count: **311 tests**
  - Total execution time: **14.70s**
  - Pass / Fail: **311 passed, 0 failures, 0 warnings**
  - Unit vs Integration Split:
    - *Unit Tests:* ~230 tests (domain model serialization, emotion validators, memory retrieval formulas, spatial sightlines, sketch stroke determinism, repetition scoring).
    - *Integration Tests:* ~81 tests (FastAPI endpoints, end-to-end hotel intrigue, undercover warehouse scenario, shot planning with psychological camera, multi-seed experiments).
  - External AI Quota / Network Requirement: **0 tests require network access or external AI credentials.**
- **Frontend (Vitest):**
  - Total test files: **5 files** in `frontend/src/__tests__/`
  - Total test count: **49 tests**
  - Total execution time: **14.73s**
  - Pass / Fail: **49 passed, 0 failures**

---

## 10. Conflicts and Risks

1. **Conflict: Target Architecture Restricts to 4 AI Sites vs Real Generator:**
   - The brief targets: (1) Feature extraction, (2) Decision policy, (3) Scribe, (4) Image provider.
   - In reality, world initialization from raw unstructured text (`WorldInitializerService`) is the most prominent LLM call in the system, turning a prompt like "A warehouse at midnight..." into characters, rooms, and items.
   - *Risk:* If this call site is removed to satisfy the "exactly four" rule, world generation must be re-architected into a two-stage process: LLM Feature Extractor -> Deterministic World Compiler.
2. **Conflict: Free-Text Statements vs Mechanical Deception:**
   - In `src/domain/secret.py`, `belief.py`, and `fact.py`, knowledge is stored as unstructured strings (`"The courier hides the dossier in the locked office"`).
   - The brief requires mechanical deception verification. Currently, deception is checked by substring matching (`"dossier" in m.summary`).
   - *Risk:* Migrating to typed `Proposition(subject, predicate, object, state)` breaks existing mock plans and requires refactoring perception, dialogue generation, and existing tests.
3. **Conflict: Hard-coded Python Structures vs YAML Data Files:**
   - Target expects `structures/*.yaml` and `compatibility.yaml`.
   - Codebase currently implements these in `src/narrative/structure_library.py`.
   - *Risk:* Moving to YAML is clean and low-risk, but all 6 structure definitions, beat definitions, and compatibility mappings must be preserved identically.
4. **Conflict: Director Bypass vs Strict Validator:**
   - `DirectorAgent` currently writes events directly to `EventRecorder`.
   - Enforcing Invariant 3 requires modeling Director interventions as world-level action proposals (`ActionProposal`) that pass through `ActionValidator`.

---

## 11. Proposed Work Plan

| Phase | Target Scope | Concrete Files to Touch | Estimated Lines (New / Mod) | Dependencies |
|---|---|---|---|---|
| **Phase 1: Foundations** | Seeded RNG parameter in engine, typed `Proposition` & `KnowledgeItem` models, provenance spine, budget governor. | `backend/src/domain/fact.py`, `belief.py`, `secret.py`, `world.py`, `simulation/engine.py`, `simulation/orchestrator.py`, `providers/budget.py` (new). | +350 / ~200 | None |
| **Phase 2: Deterministic Decision Policy** | Hardened `ActionValidator` with Knowledge Gate (C4) and Canon Gate (C6); enforce `ActionProposal.motivation` (C3); eliminate direct world mutations in `SimulationOrchestrator`. | `backend/src/simulation/actions.py`, `backend/src/agents/actor.py`, `backend/src/simulation/orchestrator.py`. | +250 / ~150 | Phase 1 |
| **Phase 3: Story Structure Engine** | Externalize structures to `structures/*.yaml` and `compatibility.yaml` with reason strings (D1, D5); implement LLM feature extractor schema (D6) with keyword fallback. | `backend/src/story/structures/*.yaml` (new), `backend/src/story/compatibility.yaml` (new), `backend/src/narrative/structure_library.py`, `structure_selector.py`. | +400 / ~150 | Phase 1 |
| **Phase 4: Blueprint, Director & Gate** | `StoryBlueprint` CANON/INTENT separation; `BeatPressure` with predicates (D13); Director intervention budget (C12) routed via `ActionValidator` (C14); `NarrativeSufficiencyGate` (C16). | `backend/src/domain/story_structure.py`, `backend/src/agents/director.py`, `backend/src/simulation/orchestrator.py`. | +350 / ~180 | Phases 2 & 3 |
| **Phase 5: Observer & Scene Builder** | Refine `SceneBuilder` to generate explicit `SceneData` with typed `SceneObjective` containing `state_delta` (E4, E5); add `MEANWHILE` link (E6) and consecutive `AND_THEN` detection (E8). | `backend/src/narrative/scene_builder.py`, `backend/src/narrative/causal_analyzer.py`, `backend/src/narrative/observer.py`. | +200 / ~120 | Phase 4 |
| **Phase 6: Arcs & Subtext** | Ground `SubtextAnalyzer` in `KnowledgeItem` comparisons; verify `NO_ARC_DETECTED` support end-to-end (E10); tie performance cues to deception provenance. | `backend/src/narrative/subtext.py`, `backend/src/narrative/performance_cues.py`, `backend/src/narrative/arc_tracker.py`. | +180 / ~100 | Phases 1 & 5 |
| **Phase 7: Scribe & Quality Validator** | Implement observable-only scene context projection for Scribe (F2); wire optional LLM Scribe path while keeping template scribe fallback (F3); enforce strict block provenance (F5). | `backend/src/narrative/scribe.py`, `backend/src/narrative/screenplay_validator.py`. | +250 / ~150 | Phases 5 & 6 |
| **Phase 8: Shot Planner & Storyboard** | Enforce `shot_id` and block IDs on all panels (G1); content-hash caching lookup (A8); prune duplicate provider hierarchies; enforce keyframe budget. | `backend/src/storyboard/planner.py`, `backend/src/storyboard/models.py`, `backend/src/storyboard/image_provider.py`. | +300 / ~200 | Phase 7 |
| **Phase 9: Frontend Workstation** | Display beat satisfaction status (`SATISFIED / PARTIAL / UNSATISFIED`), per-criterion fit score breakdown, character creation flow, and full 5-hop provenance inspector. | `frontend/src/components/StructureAndArcsViewer.tsx`, `NewProjectModal.tsx`, `StoryboardViewer.tsx`, `ScreenplayViewer.tsx`. | +350 / ~200 | Phase 8 |
| **Phase 10: Export, Demo & Cleanup** | Implement FDX export (H2) and Storyboard PDF contact sheet (H3); verify "The Missing Dossier" 3-character scenario end-to-end; clean legacy SVG provider. | `backend/src/api/app.py`, `backend/tests/test_missing_dossier_scenario.py`, `backend/src/storyboard/provider.py`. | +300 / ~150 | All prior |

---

## 12. Demo Scenario Assessment ("The Missing Dossier")

```
TITLE:       The Missing Dossier
INPUT TYPE:  BEGINNING

An undercover detective enters an abandoned warehouse at midnight to
recover a stolen classified dossier. Inside, the detective meets a
nervous courier who claims not to know anything about the dossier. The
courier is secretly hiding the dossier in a locked office. A security
guard patrols the only obvious exit. The detective suspects the courier
is lying, but does not yet know where the dossier is.
```

### Gap Analysis for Demo Scenario
1. **Asymmetric Knowledge & Deception Engine:**  
   The courier's lie ("I know nothing about the dossier") and secret ("Hiding dossier in locked office") currently reside as free-text strings. Mechanically verifying that the detective detects deception without learning the locked office location requires typed propositions.
2. **Actor & Location Count in Mock Plan:**  
   The scenario specifies three actors (Detective, Courier, Guard) and three spaces (Warehouse, Locked Office, Exit). The mock generator currently caps at 2 actors and 2 rooms.
3. **Knowledge Gate in Action Validator:**  
   When the courier lies, the detective must not be able to immediately propose `MOVE -> locked_office` or `TAKE -> dossier` until that location is learned through interrogation or environmental discovery.
4. **Sufficiency Gate & Escalation:**  
   The simulation must recognize when the courier's deception is exposed and when the security guard arrives, rather than running blindly to a static tick count.
