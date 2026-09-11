# D3 Story Lab

> **Emergent Narrative Simulation Platform**

D3 Story Lab is an emergent storytelling sandbox where narrative emerges organically from autonomous character interactions, bounded perception, evolving emotional states, and deterministic physics — converting verified simulation history into professional Fountain screenplays and storyboard shot plans.

It is **NOT** an animation studio, 3D application, video generator, or audio synthesizer. It does not use Three.js, Blender, or virtual cameras.

---

## 🏗️ Core Narrative Pipeline

```
Input Premise / Seed
   │
   ▼
World Initialization (Provenance Tagging & Blueprinting)
   │
   ▼
Canonical WorldState (Locations, Objects, Actors, Private Secrets & Beliefs)
   │
   ▼
Autonomous Simulation Loop
   ├── Perception Boundaries (KnowledgeFilter)
   ├── Memory Retrieval & Compression
   ├── Actor Cognitive Reasoning (Proposals)
   ├── Deterministic Action Validation & Execution
   ├── Director Pacing Interventions (External Pressure)
   └── Belief & Emotion Evolution
   │
   ▼
Immutable Event Log (Canonical Source of Truth)
   │
   ▼
Observer Agent (Significance Scoring & Beat Clustering with Provenance)
   │
   ▼
Scribe Agent (Screenplay Composition with Zero Invented Facts)
   │
   ▼
Fountain Screenplay Export (.fountain)
   │
   ▼
Storyboard Preparation (Cinematic Shot Plans & Framing)
```

---

## 📐 Architectural Rules

1. **Canonical WorldState is the source of truth**: No rogue state outside the registry.
2. **AI agents propose, never mutate**: Actions must be proposed via `ActionProposal` and executed only by the deterministic engine.
3. **Deterministic Action Validation**: Every action passes invariant physics checks (connectivity, inventory, portable flags).
4. **Strict Knowledge & Perception Isolation**: Characters perceive only co-located entities and events. Private beliefs, secrets, and episodic memories are strictly inaccessible to other actors.
5. **Separation of Objective Truth and Subjective Belief**: Objective facts are immutable; character beliefs evolve dynamically based on observations and trust.
6. **Immutable Events**: Simulation history is strictly immutable (`frozen=True`).
7. **Observer Filters, Never Alters**: The Observer clusters and highlights dramatic beats without altering underlying events.
8. **Scribe Never Hallucinates**: Screenplay action lines and dialogue map with 100% provenance back to `source_event_ids`.
9. **Zero External API Requirement**: Runs 100% locally and deterministically in Mock LLM mode. Supports Google Gemini via `GEMINI_API_KEY`.
10. **Decoupled Architecture**: Python (FastAPI / Pydantic v2) backend cleanly decoupled from React / TypeScript frontend.

---

## 🚀 Quickstart

### Prerequisites
- **Python**: 3.10+ (tested on Python 3.14)
- **Node.js**: 18+ (tested on Node v24)
- **npm**: 9+

### 1. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run all automated tests (156 tests, 0 warnings)
pytest
```

#### Run Backend API Server
```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

The API will be live at `http://localhost:8000`. Interactive OpenAPI documentation is accessible at `http://localhost:8000/docs`.

### 2. Frontend Workstation Setup

```bash
cd frontend

# Install dependencies
npm install

# Run type check and production build
npm run build

# Start development server
npm run dev
```

The creative workstation UI will be accessible at `http://localhost:5173`.

---

## 🔑 Configuration & LLM Providers

D3 Story Lab operates deterministically out of the box with zero API keys required.

To enable live Google Gemini inference:
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Populate `GEMINI_API_KEY`:
   ```bash
   GEMINI_API_KEY="your-gemini-api-key-here"
   ```
3. Restart the FastAPI server. If no key is detected, the system smoothly falls back to the deterministic `MockLLMProvider`.

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health and active LLM provider (`mock` or `gemini`) |
| `GET` | `/api/projects` | List all saved simulation projects |
| `POST` | `/api/projects` | Initialize a new simulation world from raw seed text |
| `GET` | `/api/projects/{id}` | Retrieve complete project data snapshot |
| `DELETE` | `/api/projects/{id}` | Delete a saved project |
| `GET` | `/api/projects/{id}/world` | Inspect current canonical `WorldState` |
| `GET` | `/api/projects/{id}/events` | Fetch full chronological immutable event stream |
| `POST` | `/api/projects/{id}/step` | Advance simulation by $N$ ticks |
| `POST` | `/api/projects/{id}/run` | Run autonomous multi-tick simulation loop |
| `POST` | `/api/projects/{id}/generate-screenplay` | Run Observer & Scribe to synthesize Fountain screenplay |
| `GET` | `/api/projects/{id}/screenplay` | Retrieve screenplay structure and Fountain text |
| `GET` | `/api/projects/{id}/screenplay/download` | Download `.fountain` screenplay file |
| `GET` | `/api/projects/{id}/storyboard` | Generate cinematic ShotPlan and rendered panels |

---

## 🧪 Testing Suite

Run the complete test suite across all 12 test modules:

```bash
cd backend
pytest
```

**Test Coverage Summary:**
- `test_world_state.py`: Registries, ID resolution, dangling reference validation.
- `test_event.py`: Immutable event creation, serialization, frozen constraints.
- `test_simulation_engine.py`: Deterministic action validator, executor, engine ticks.
- `test_perception.py`: KnowledgeFilter boundaries, private secret/belief isolation.
- `test_memory_system.py`: Memory scoring formula, retrieval, compression.
- `test_evolution.py`: Belief, trust, affinity, and emotional state updates.
- `test_providers.py`: MockLLMProvider schema generation and Gemini error handling.
- `test_initializer.py`: World initialization plan, fact tagging (`SOURCE_FACT`, `DERIVED_PREMISE`, `SIMULATION_INVENTION`).
- `test_actor_agent.py`: Actor cognitive loop, perception, action proposal.
- `test_director.py`: Pacing monitoring, tension tracking, environmental interventions.
- `test_orchestrator.py`: Multi-agent cyclic simulation, pause/resume, loop detection.
- `test_reflection.py`: Episodic memory synthesis into beliefs without event alteration.
- `test_observer.py`: Significance scoring, noise filtering, beat clustering, provenance.
- `test_scribe.py`: Fountain screenplay formatting, uppercase cues, dialogue blocks.
- `test_project_store.py`: Filesystem persistence, round-trip serialization.
- `test_api.py`: FastAPI end-to-end endpoints, simulation stepping, screenplay download.
- `test_hotel_intrigue_demo.py`: Flagship Hotel Intrigue end-to-end verification.
- `test_evaluation.py`: Narrative coherence, action diversity, autonomy metrics, multi-seed experiments.
- `test_storyboard.py`: Shot plan generation, framing, mock SVG panel rendering.

**Result**: 156 passed, 0 failures, 0 warnings.
