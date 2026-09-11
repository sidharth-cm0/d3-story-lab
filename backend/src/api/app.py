"""FastAPI application for D3 Story Lab."""

from __future__ import annotations
import os
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.domain.world import WorldState
from src.generator.initializer import WorldInitializerService
from src.simulation.orchestrator import SimulationOrchestrator
from src.agents.actor import ActorAgent
from src.agents.director import DirectorAgent
from src.narrative.observer import Observer, NarrativeEventSelection
from src.narrative.scribe import Scribe
from src.narrative.fountain import ScreenplayDocument
from src.storage.project_store import ProjectStore, ProjectData, ProjectMetadata
from src.storyboard.planner import StoryboardPlanner
from src.storyboard.provider import MockStoryboardProvider
from src.providers.mock import MockLLMProvider
from src.providers.gemini import GeminiProvider
from src.providers.base import LLMProvider


class CreateProjectRequest(BaseModel):
    seed_prompt: str = Field(..., min_length=3)
    title: Optional[str] = None


class StepRequest(BaseModel):
    ticks: int = Field(default=1, ge=1, le=50)


class RunRequest(BaseModel):
    num_ticks: int = Field(default=5, ge=1, le=100)


def get_llm_provider() -> LLMProvider:
    """Instantiate configured LLM provider (defaults to deterministic Mock)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            return GeminiProvider(api_key=api_key)
        except Exception:
            return MockLLMProvider()
    return MockLLMProvider()


def create_app(store_dir: Optional[str] = None) -> FastAPI:
    """Application factory for D3 Story Lab."""
    app = FastAPI(
        title="D3 Story Lab API",
        description="Emergent Narrative Simulation Engine & Fountain Screenplay Generator",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = ProjectStore(base_dir=store_dir)
    orchestrator_cache: Dict[str, SimulationOrchestrator] = {}

    def get_or_create_orchestrator(project: ProjectData) -> SimulationOrchestrator:
        pid = project.metadata.id
        if pid in orchestrator_cache:
            return orchestrator_cache[pid]

        provider = get_llm_provider()
        orch = SimulationOrchestrator(
            world=project.world,
            provider=provider,
        )
        orchestrator_cache[pid] = orch
        return orch

    # --- Routes ---

    @app.get("/api/health")
    def health():
        provider = get_llm_provider()
        provider_name = "gemini" if isinstance(provider, GeminiProvider) else "mock"
        return {
            "status": "healthy",
            "provider": provider_name,
            "version": "0.1.0",
        }

    @app.get("/api/projects", response_model=List[ProjectMetadata])
    def list_projects():
        return store.list_projects()

    @app.post("/api/projects", response_model=ProjectMetadata)
    def create_project(req: CreateProjectRequest):
        provider = get_llm_provider()
        init_service = WorldInitializerService(provider=provider)
        plan = init_service.generate_plan(req.seed_prompt)
        world = init_service.instantiate_world(plan)
        if req.title:
            world.name = req.title

        title = req.title or world.name or "Untitled Simulation"
        metadata = ProjectMetadata(
            id=world.id,
            title=title,
            seed_prompt=req.seed_prompt,
            current_tick=world.current_tick,
            total_events=len(world.events),
            total_scenes=0,
        )

        project = ProjectData(
            metadata=metadata,
            plan=plan,
            world=world,
        )
        store.save_project(project)
        get_or_create_orchestrator(project)
        return project.metadata

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        return proj.model_dump(mode="json")

    @app.delete("/api/projects/{project_id}")
    def delete_project(project_id: str):
        success = store.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        if project_id in orchestrator_cache:
            del orchestrator_cache[project_id]
        return {"deleted": True, "project_id": project_id}

    @app.get("/api/projects/{project_id}/world")
    def get_world(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        return proj.world.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/events")
    def get_events(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        events = sorted(proj.world.events.values(), key=lambda e: (e.tick, e.id))
        return [e.model_dump(mode="json") for e in events]

    @app.post("/api/projects/{project_id}/step")
    def step_simulation(project_id: str, req: StepRequest = StepRequest()):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        orch = get_or_create_orchestrator(proj)
        executed_events = []
        for _ in range(req.ticks):
            tick_events = orch.step()
            executed_events.extend(tick_events)

        proj.world = orch.world
        store.save_project(proj)

        return {
            "project_id": project_id,
            "current_tick": orch.world.current_tick,
            "new_events_count": len(executed_events),
            "new_events": [e.model_dump(mode="json") for e in executed_events],
        }

    @app.post("/api/projects/{project_id}/run")
    def run_simulation(project_id: str, req: RunRequest = RunRequest()):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        orch = get_or_create_orchestrator(proj)
        results = orch.run(max_ticks=req.num_ticks)

        proj.world = orch.world
        store.save_project(proj)

        return {
            "project_id": project_id,
            "current_tick": orch.world.current_tick,
            "total_new_events": len(results),
            "total_events": len(orch.world.events),
        }

    @app.post("/api/projects/{project_id}/generate-screenplay")
    def generate_screenplay(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        provider = get_llm_provider()
        events = sorted(proj.world.events.values(), key=lambda e: (e.tick, e.id))

        observer = Observer(provider=provider)
        selection = observer.observe_events(events, proj.world)

        scribe = Scribe(provider=provider)
        doc = scribe.compose_screenplay(selection, proj.world, title=proj.metadata.title)
        fountain_text = doc.to_fountain()

        proj.selection = selection
        proj.screenplay = doc
        proj.fountain_text = fountain_text
        store.save_project(proj)

        return {
            "project_id": project_id,
            "total_beats": len(selection.filtered_beats),
            "total_scenes": len(doc.scenes),
            "fountain_text": fountain_text,
            "screenplay": doc.model_dump(mode="json"),
        }

    @app.get("/api/projects/{project_id}/screenplay")
    def get_screenplay(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        return {
            "screenplay": proj.screenplay.model_dump(mode="json") if proj.screenplay else None,
            "fountain_text": proj.fountain_text,
            "selection": proj.selection.model_dump(mode="json") if proj.selection else None,
        }

    @app.get("/api/projects/{project_id}/screenplay/download")
    def download_screenplay(project_id: str):
        proj = store.load_project(project_id)
        if not proj or not proj.fountain_text:
            raise HTTPException(status_code=404, detail="Screenplay not yet generated")

        filename = f"{proj.metadata.title.replace(' ', '_').lower()}.fountain"
        return Response(
            content=proj.fountain_text,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


    @app.get("/api/projects/{project_id}/storyboard")
    def get_storyboard(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if not proj.screenplay:
            raise HTTPException(status_code=400, detail="Screenplay must be generated first")

        planner = StoryboardPlanner()
        shot_plan = planner.plan_shots(proj.screenplay, proj.world)
        provider = MockStoryboardProvider()
        rendered_panels = [provider.render_panel(p) for p in shot_plan.panels]

        return {
            "shot_plan": shot_plan.model_dump(mode="json"),
            "rendered_panels": rendered_panels,
        }

    return app


app = create_app()
