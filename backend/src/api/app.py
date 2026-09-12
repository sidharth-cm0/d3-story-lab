"""FastAPI application for D3 Story Lab."""

from __future__ import annotations
import os
import csv
import io
from typing import Dict, Any, Optional, List

def _load_env_file() -> None:
    candidate_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"),
        "/workspaces/d3-story-lab/backend/.env",
        "/workspaces/d3-story-lab/.env",
        ".env",
    ]
    for p in candidate_paths:
        p_abs = os.path.abspath(p)
        if os.path.exists(p_abs):
            try:
                with open(p_abs, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

_load_env_file()
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
from src.narrative.completion import StoryCompletionEngine, StoryOutline, StoryInputType
from src.narrative.synopsis import SynopsisGenerator, StorySynopsis
from src.storage.project_store import ProjectStore, ProjectData, ProjectMetadata
from src.storyboard.models import ShotPlan, StoryboardPanel, StoryboardImageVersion, StoryboardImageStatus
from src.storyboard.planner import StoryboardPlanner
from src.storyboard.visual_bible import VisualBible, StoryboardStyleProfile
from src.storyboard.compiler import StoryboardPromptCompiler, ContinuityValidator
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.image_provider import (
    StoryboardImageProvider,
    StoryboardImageResult,
    FallbackComicSvgProvider,
    CloudImagenStoryboardProvider,
    MockStoryboardImageProvider,
)
from src.storyboard.provider import (
    StoryboardProvider,
    ComicGraphicStoryboardProvider,
    GeminiImageStoryboardProvider,
    MockStoryboardProvider,
)
from src.providers.mock import MockLLMProvider
from src.providers.gemini import GeminiProvider
from src.providers.base import LLMProvider


class CreateProjectRequest(BaseModel):
    seed_prompt: str = Field(..., min_length=3)
    title: Optional[str] = None
    input_type: Optional[str] = "beginning"
    target_duration_minutes: int = Field(default=20, ge=5, le=120)


class StepRequest(BaseModel):
    ticks: int = Field(default=1, ge=1, le=50)


class RunRequest(BaseModel):
    num_ticks: int = Field(default=5, ge=1, le=100)


class PlanStoryboardRequest(BaseModel):
    density_mode: str = Field(default="standard")  # "quick" | "standard" | "detailed"
    panels_per_page: int = Field(default=4, ge=1, le=8)


class GenerateStoryboardRequest(BaseModel):
    provider: Optional[str] = None  # "cloud" | "fallback" | "mock"


class SelectVersionRequest(BaseModel):
    version: int = Field(..., ge=1)


class RegeneratePanelRequest(BaseModel):
    panel_id: str
    provider: Optional[str] = None


class RegeneratePageRequest(BaseModel):
    page_number: int = Field(default=1, ge=1)
    provider: Optional[str] = None


def get_llm_provider() -> LLMProvider:
    """Instantiate configured LLM provider (defaults to deterministic Mock)."""
    if os.environ.get("USE_MOCK_LLM", "0") == "1":
        return MockLLMProvider()
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            return GeminiProvider(api_key=api_key)
        except Exception:
            return MockLLMProvider()
    return MockLLMProvider()


def get_storyboard_provider() -> StoryboardProvider:
    """Instantiate storyboard rendering engine (ComicGraphic or Gemini Image adapter)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return GeminiImageStoryboardProvider(api_key=api_key)
    return ComicGraphicStoryboardProvider()


def get_image_provider(
    provider_type: Optional[str] = None,
    asset_store: Optional[StoryboardAssetStore] = None,
) -> StoryboardImageProvider:
    """Instantiate storyboard renderer. Defaults to offline HandDrawnStoryboardProvider."""
    asset_store = asset_store or StoryboardAssetStore()
    provider_type = provider_type or os.environ.get("STORYBOARD_PROVIDER", "hand_drawn")

    if provider_type in ("hand_drawn", "hand_drawn_storyboard", "sketch"):
        from src.storyboard.sketch.renderer import HandDrawnStoryboardProvider
        return HandDrawnStoryboardProvider(asset_store=asset_store)
    if provider_type == "mock":
        return MockStoryboardImageProvider(asset_store=asset_store)
    if provider_type == "mock_ai":
        return MockStoryboardImageProvider(asset_store=asset_store, simulate_ai_mode=True)
    if provider_type == "fallback":
        return FallbackComicSvgProvider(asset_store=asset_store)

    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("IMAGEN_API_KEY")
    )
    model_name = os.environ.get("STORYBOARD_IMAGE_MODEL") or "gemini-3.1-flash-image"
    return CloudImagenStoryboardProvider(api_key=api_key, asset_store=asset_store, model_name=model_name)


def create_app(store_dir: Optional[str] = None) -> FastAPI:
    """Application factory for D3 Story Lab."""
    app = FastAPI(
        title="D3 Story Lab API",
        description="Emergent Narrative Simulation Engine & Fountain Screenplay Generator",
        version="0.2.0",
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
            "version": "0.2.0",
        }

    @app.get("/api/projects", response_model=List[ProjectMetadata])
    def list_projects():
        return store.list_projects()

    @app.post("/api/projects", response_model=ProjectMetadata)
    def create_project(req: CreateProjectRequest):
        provider = get_llm_provider()
        init_service = WorldInitializerService(provider=provider)

        # Generate world initialization plan with story outline
        plan = init_service.generate_plan(
            req.seed_prompt,
            declared_type=req.input_type,
            target_duration_minutes=req.target_duration_minutes,
        )
        world = init_service.instantiate_world(plan)

        outline = plan.story_outline or init_service.completion_engine.complete_story(
            req.seed_prompt,
            declared_type=req.input_type,
            target_duration_minutes=req.target_duration_minutes,
        )

        title = req.title or outline.episode_title or world.name or "Untitled Simulation"
        world.name = title

        # Generate initial three-tier synopsis
        synopsis_gen = SynopsisGenerator()
        synopsis = synopsis_gen.generate_synopsis(outline=outline, world=world)

        metadata = ProjectMetadata(
            id=world.id,
            title=title,
            seed_prompt=req.seed_prompt,
            input_type=req.input_type or outline.input_type.value,
            target_duration_minutes=req.target_duration_minutes,
            current_tick=world.current_tick,
            total_events=len(world.events),
            total_scenes=0,
            total_panels=0,
        )

        project = ProjectData(
            metadata=metadata,
            plan=plan,
            world=world,
            story_outline=outline,
            synopsis=synopsis,
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

    @app.get("/api/projects/{project_id}/outline")
    def get_outline(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if not proj.story_outline:
            comp = StoryCompletionEngine(provider=get_llm_provider())
            proj.story_outline = comp.complete_story(proj.metadata.seed_prompt)
            store.save_project(proj)
        return proj.story_outline.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/synopsis")
    def get_synopsis(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if not proj.synopsis:
            if not proj.story_outline:
                comp = StoryCompletionEngine(provider=get_llm_provider())
                proj.story_outline = comp.complete_story(proj.metadata.seed_prompt)
            syn_gen = SynopsisGenerator()
            proj.synopsis = syn_gen.generate_synopsis(
                outline=proj.story_outline,
                world=proj.world,
                selection=proj.selection,
            )
            store.save_project(proj)
        return proj.synopsis.model_dump(mode="json")

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

        # Update synopsis grounded in verified simulation beats
        if proj.story_outline:
            syn_gen = SynopsisGenerator()
            proj.synopsis = syn_gen.generate_synopsis(
                outline=proj.story_outline,
                world=proj.world,
                selection=selection,
            )

        # Automatically plan cinematic shots and render comic illustrations with Visual Bible
        asset_store = StoryboardAssetStore(store.base_dir)
        bible = proj.visual_bible or asset_store.load_visual_bible(project_id)
        if not bible:
            bible = VisualBible.from_world(proj.world)
            proj.visual_bible = bible
            asset_store.save_visual_bible(project_id, bible)

        planner = StoryboardPlanner(panels_per_page=4)
        shot_plan = planner.plan_shots(doc, proj.world, bible=bible, project_id=project_id)
        storyboard_engine = get_image_provider(asset_store=asset_store)
        rendered_panels = []
        for p in shot_plan.panels:
            res = storyboard_engine.generate_panel(p, bible=bible, version=1)
            p.image_url = res.image_url
            p.rendered_image_url = res.image_url
            p.rendered_svg = res.svg_content
            p.image_status = res.status
            p.provider = res.provider
            p.fallback_reason = res.fallback_reason
            p.continuity_mode = res.continuity_mode
            ver = StoryboardImageVersion(
                version=1,
                image_url=res.image_url,
                prompt_used=res.compiled_prompt,
                negative_prompt=res.negative_prompt,
                provider=res.provider,
                mode=res.mode,
                fallback_reason=res.fallback_reason,
                mime_type=res.mime_type,
                continuity_mode=res.continuity_mode,
                is_selected=True,
                render_metadata=res.render_metadata,
            )
            p.versions = [ver]
            p.selected_version = 1
            rendered_panels.append(storyboard_engine.render_panel(p, bible=bible, version=1))

        proj.shot_plan = shot_plan
        proj.rendered_panels = rendered_panels
        store.save_project(proj)

        return {
            "project_id": project_id,
            "total_beats": len(selection.filtered_beats),
            "total_scenes": len(doc.scenes),
            "total_panels": len(shot_plan.panels),
            "fountain_text": fountain_text,
            "screenplay": doc.model_dump(mode="json"),
            "synopsis": proj.synopsis.model_dump(mode="json") if proj.synopsis else None,
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
            "synopsis": proj.synopsis.model_dump(mode="json") if proj.synopsis else None,
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

    @app.get("/api/projects/{project_id}/visual-bible")
    def get_visual_bible(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        asset_store = StoryboardAssetStore(store.base_dir)
        bible = proj.visual_bible or asset_store.load_visual_bible(project_id)
        if not bible:
            bible = VisualBible.from_world(proj.world)
            proj.visual_bible = bible
            store.save_project(proj)
            asset_store.save_visual_bible(project_id, bible)

        return bible.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/storyboard/plan")
    def plan_storyboard(project_id: str, req: Optional[PlanStoryboardRequest] = None):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if not proj.screenplay:
            raise HTTPException(status_code=400, detail="Screenplay must be generated first")

        density = req.density_mode if req else "standard"
        ppp = req.panels_per_page if req else 4

        asset_store = StoryboardAssetStore(store.base_dir)
        bible = proj.visual_bible or asset_store.load_visual_bible(project_id)
        if not bible:
            bible = VisualBible.from_world(proj.world)
            proj.visual_bible = bible
            asset_store.save_visual_bible(project_id, bible)

        planner = StoryboardPlanner(panels_per_page=ppp, density_mode=density)
        shot_plan = planner.plan_shots(proj.screenplay, proj.world, bible=bible, project_id=project_id)

        continuity_report = ContinuityValidator.validate_shot_plan(shot_plan.panels, bible)

        engine = get_image_provider(asset_store=asset_store)
        rendered_panels = []
        for p in shot_plan.panels:
            res = engine.generate_panel(p, bible=bible, version=1)
            p.image_url = res.image_url
            p.rendered_image_url = res.image_url
            p.rendered_svg = res.svg_content
            p.image_status = res.status
            p.provider = res.provider
            p.fallback_reason = res.fallback_reason
            p.continuity_mode = res.continuity_mode
            ver = StoryboardImageVersion(
                version=1,
                image_url=res.image_url,
                prompt_used=res.compiled_prompt,
                negative_prompt=res.negative_prompt,
                provider=res.provider,
                mode=res.mode,
                fallback_reason=res.fallback_reason,
                mime_type=res.mime_type,
                continuity_mode=res.continuity_mode,
                is_selected=True,
                render_metadata=res.render_metadata,
            )
            p.versions = [ver]
            p.selected_version = 1
            rendered_panels.append(engine.render_panel(p, bible=bible, version=1))

        proj.shot_plan = shot_plan
        proj.rendered_panels = rendered_panels
        store.save_project(proj)

        return {
            "shot_plan": shot_plan.model_dump(mode="json"),
            "continuity_report": continuity_report.model_dump(mode="json"),
            "rendered_panels": rendered_panels,
        }

    @app.post("/api/projects/{project_id}/storyboard/generate")
    def generate_storyboard(project_id: str, req: Optional[GenerateStoryboardRequest] = None):
        proj = store.load_project(project_id)
        if not proj or not proj.shot_plan:
            raise HTTPException(status_code=404, detail="Project or shot plan not found")

        asset_store = StoryboardAssetStore(store.base_dir)
        bible = proj.visual_bible or asset_store.load_visual_bible(project_id)
        if not bible:
            bible = VisualBible.from_world(proj.world)
            proj.visual_bible = bible
            asset_store.save_visual_bible(project_id, bible)

        provider_type = req.provider if req else None
        engine = get_image_provider(provider_type=provider_type, asset_store=asset_store)

        rendered_panels = []
        for p in proj.shot_plan.panels:
            target_version = len(p.versions) + 1 if p.versions else 1
            res = engine.generate_panel(p, bible=bible, version=target_version)
            p.image_url = res.image_url
            p.rendered_image_url = res.image_url
            p.rendered_svg = res.svg_content
            p.image_status = res.status
            p.provider = res.provider
            p.fallback_reason = res.fallback_reason
            p.continuity_mode = res.continuity_mode
            p.generation_version = target_version
            p.selected_version = target_version

            for v in p.versions:
                v.is_selected = False

            new_ver = StoryboardImageVersion(
                version=target_version,
                image_url=res.image_url,
                prompt_used=res.compiled_prompt,
                negative_prompt=res.negative_prompt,
                provider=res.provider,
                mode=res.mode,
                fallback_reason=res.fallback_reason,
                mime_type=res.mime_type,
                continuity_mode=res.continuity_mode,
                is_selected=True,
                render_metadata=res.render_metadata,
            )
            p.versions.append(new_ver)
            rendered_panels.append(engine.render_panel(p, bible=bible, version=target_version))

        proj.rendered_panels = rendered_panels
        store.save_project(proj)

        return {
            "shot_plan": proj.shot_plan.model_dump(mode="json"),
            "rendered_panels": rendered_panels,
        }

    @app.get("/api/projects/{project_id}/storyboard")
    def get_storyboard(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if not proj.screenplay:
            raise HTTPException(status_code=400, detail="Screenplay must be generated first")

        # Reuse precomputed shot plan and rendered panels if present
        if proj.shot_plan and proj.rendered_panels:
            return {
                "shot_plan": proj.shot_plan.model_dump(mode="json"),
                "rendered_panels": proj.rendered_panels,
            }

        asset_store = StoryboardAssetStore(store.base_dir)
        bible = proj.visual_bible or asset_store.load_visual_bible(project_id)
        if not bible:
            bible = VisualBible.from_world(proj.world)
            proj.visual_bible = bible
            asset_store.save_visual_bible(project_id, bible)

        planner = StoryboardPlanner(panels_per_page=4)
        shot_plan = planner.plan_shots(proj.screenplay, proj.world, bible=bible, project_id=project_id)
        engine = get_image_provider(asset_store=asset_store)
        rendered_panels = []
        for p in shot_plan.panels:
            res = engine.generate_panel(p, bible=bible, version=1)
            p.image_url = res.image_url
            p.rendered_image_url = res.image_url
            p.rendered_svg = res.svg_content
            p.image_status = res.status
            p.provider = res.provider
            p.fallback_reason = res.fallback_reason
            p.continuity_mode = res.continuity_mode
            ver = StoryboardImageVersion(
                version=1,
                image_url=res.image_url,
                prompt_used=res.compiled_prompt,
                negative_prompt=res.negative_prompt,
                provider=res.provider,
                mode=res.mode,
                fallback_reason=res.fallback_reason,
                mime_type=res.mime_type,
                continuity_mode=res.continuity_mode,
                is_selected=True,
                render_metadata=res.render_metadata,
            )
            p.versions = [ver]
            p.selected_version = 1
            rendered_panels.append(engine.render_panel(p, bible=bible, version=1))

        proj.shot_plan = shot_plan
        proj.rendered_panels = rendered_panels
        store.save_project(proj)

        return {
            "shot_plan": shot_plan.model_dump(mode="json"),
            "rendered_panels": rendered_panels,
        }

    @app.get("/api/projects/{project_id}/storyboard/pages/{page_number}")
    def get_storyboard_page(project_id: str, page_number: int):
        proj = store.load_project(project_id)
        if not proj or not proj.shot_plan:
            raise HTTPException(status_code=404, detail="Project or shot plan not found")

        matching_pages = [page for page in proj.shot_plan.pages if page.page_number == page_number]
        if not matching_pages:
            raise HTTPException(status_code=404, detail=f"Page {page_number} not found")

        page = matching_pages[0]
        return {
            "page": page.model_dump(mode="json"),
            "total_pages": proj.shot_plan.total_pages,
            "project_title": proj.shot_plan.project_title,
        }

    @app.post("/api/projects/{project_id}/storyboard/panels/{panel_id}/regenerate")
    def regenerate_panel_version(project_id: str, panel_id: str, req: Optional[GenerateStoryboardRequest] = None):
        proj = store.load_project(project_id)
        if not proj or not proj.shot_plan:
            raise HTTPException(status_code=404, detail="Project or shot plan not found")

        target_panel = None
        target_idx = -1
        for idx, p in enumerate(proj.shot_plan.panels):
            if p.id == panel_id or p.panel_id == panel_id:
                target_panel = p
                target_idx = idx
                break

        if not target_panel:
            raise HTTPException(status_code=404, detail=f"Panel '{panel_id}' not found")

        asset_store = StoryboardAssetStore(store.base_dir)
        bible = proj.visual_bible or asset_store.load_visual_bible(project_id)
        if not bible:
            bible = VisualBible.from_world(proj.world)
            proj.visual_bible = bible

        next_ver = len(target_panel.versions) + 1
        provider_type = req.provider if req else None
        engine = get_image_provider(provider_type=provider_type, asset_store=asset_store)

        res = engine.generate_panel(target_panel, bible=bible, version=next_ver)
        target_panel.image_url = res.image_url
        target_panel.rendered_image_url = res.image_url
        target_panel.rendered_svg = res.svg_content
        target_panel.image_status = res.status
        target_panel.provider = res.provider
        target_panel.fallback_reason = res.fallback_reason
        target_panel.continuity_mode = res.continuity_mode
        target_panel.generation_version = next_ver
        target_panel.selected_version = next_ver

        for v in target_panel.versions:
            v.is_selected = False

        new_version = StoryboardImageVersion(
            version=next_ver,
            image_url=res.image_url,
            prompt_used=res.compiled_prompt,
            negative_prompt=res.negative_prompt,
            provider=res.provider,
            mode=res.mode,
            fallback_reason=res.fallback_reason,
            mime_type=res.mime_type,
            continuity_mode=res.continuity_mode,
            is_selected=True,
            render_metadata=res.render_metadata,
        )
        target_panel.versions.append(new_version)

        rendered_dict = engine.render_panel(target_panel, bible=bible, version=next_ver)
        if proj.rendered_panels and 0 <= target_idx < len(proj.rendered_panels):
            proj.rendered_panels[target_idx] = rendered_dict

        store.save_project(proj)

        return {
            "panel_id": panel_id,
            "panel_index": target_idx,
            "version": next_ver,
            "panel": target_panel.model_dump(mode="json"),
            "rendered_panel": rendered_dict,
        }

    @app.post("/api/projects/{project_id}/storyboard/panels/{panel_id}/select-version")
    def select_panel_version(project_id: str, panel_id: str, req: SelectVersionRequest):
        proj = store.load_project(project_id)
        if not proj or not proj.shot_plan:
            raise HTTPException(status_code=404, detail="Project or shot plan not found")

        target_panel = None
        target_idx = -1
        for idx, p in enumerate(proj.shot_plan.panels):
            if p.id == panel_id or p.panel_id == panel_id:
                target_panel = p
                target_idx = idx
                break

        if not target_panel:
            raise HTTPException(status_code=404, detail=f"Panel '{panel_id}' not found")

        matching_versions = [v for v in target_panel.versions if v.version == req.version]
        if not matching_versions:
            raise HTTPException(status_code=404, detail=f"Version {req.version} not found for panel '{panel_id}'")

        target_ver = matching_versions[0]
        for v in target_panel.versions:
            v.is_selected = (v.version == req.version)

        target_panel.selected_version = req.version
        target_panel.image_url = target_ver.image_url
        target_panel.rendered_image_url = target_ver.image_url
        target_panel.provider = target_ver.provider

        if proj.rendered_panels and 0 <= target_idx < len(proj.rendered_panels):
            p_dict = proj.rendered_panels[target_idx]
            p_dict["image_url"] = target_ver.image_url
            p_dict["version"] = req.version
            p_dict["provider"] = target_ver.provider
            p_dict["mode"] = target_ver.mode
            p_dict["prompt_used"] = target_ver.prompt_used
            p_dict["metadata"] = target_ver.render_metadata

        store.save_project(proj)

        return {
            "panel_id": panel_id,
            "selected_version": req.version,
            "panel": target_panel.model_dump(mode="json"),
        }

    @app.post("/api/projects/{project_id}/storyboard/regenerate-panel")
    def regenerate_panel(project_id: str, req: RegeneratePanelRequest):
        """Legacy-compatible single panel regeneration endpoint."""
        gen_req = GenerateStoryboardRequest(provider=req.provider)
        res = regenerate_panel_version(project_id=project_id, panel_id=req.panel_id, req=gen_req)
        return {
            "panel_id": req.panel_id,
            "panel_index": res["panel_index"],
            "rendered_panel": res["rendered_panel"],
        }

    @app.post("/api/projects/{project_id}/storyboard/regenerate-page")
    def regenerate_page(project_id: str, req: RegeneratePageRequest):
        proj = store.load_project(project_id)
        if not proj or not proj.shot_plan:
            raise HTTPException(status_code=404, detail="Project or shot plan not found")

        asset_store = StoryboardAssetStore(store.base_dir)
        bible = proj.visual_bible or asset_store.load_visual_bible(project_id)
        engine = get_image_provider(provider_type=req.provider, asset_store=asset_store)
        updated_renders = list(proj.rendered_panels or [])

        for idx, p in enumerate(proj.shot_plan.panels):
            if p.page_number == req.page_number:
                res = engine.generate_panel(p, bible=bible, version=len(p.versions) + 1)
                p.image_url = res.image_url
                p.rendered_image_url = res.image_url
                p.rendered_svg = res.svg_content
                p.image_status = res.status
                p.provider = res.provider
                rendered = engine.render_panel(p, bible=bible, version=p.selected_version)
                if idx < len(updated_renders):
                    updated_renders[idx] = rendered
                else:
                    updated_renders.append(rendered)

        proj.rendered_panels = updated_renders
        store.save_project(proj)

        return {
            "page_number": req.page_number,
            "panels_count": len([p for p in proj.shot_plan.panels if p.page_number == req.page_number]),
            "rendered_panels": updated_renders,
        }

    @app.get("/api/storyboard/provider-status")
    def get_storyboard_provider_status():
        """Expose image provider availability and diagnostic status without exposing secrets."""
        provider = get_image_provider()
        return provider.get_status()

    @app.get("/api/storyboard/capabilities")
    def get_storyboard_capabilities():
        """Expose image provider capability report without exposing secrets."""
        provider = get_image_provider()
        if hasattr(provider, "get_capabilities"):
            return provider.get_capabilities()
        return provider.get_status()

    @app.get("/api/projects/{project_id}/storyboard/status")
    def get_project_storyboard_status(project_id: str):
        """Expose project-level storyboard generation diagnostics."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        provider = get_image_provider()
        status = provider.get_status()
        status["project_id"] = project_id
        status["total_panels"] = len(proj.shot_plan.panels) if proj.shot_plan else 0
        return status

    @app.get("/api/projects/{project_id}/storyboard/assets/{category}/{filename}")
    def serve_storyboard_asset(project_id: str, category: str, filename: str):
        """Secure asset serving endpoint with strict path containment protection."""
        asset_store = StoryboardAssetStore(store.base_dir)
        try:
            content, mime_type = asset_store.load_asset(project_id, category, filename)
            return Response(
                content=content,
                media_type=mime_type,
                headers={"Cache-Control": "public, max-age=3600"},
            )
        except (ValueError, PermissionError) as e:
            raise HTTPException(status_code=403, detail=f"Access denied: {str(e)}")
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=f"Asset not found: {str(e)}")

    @app.get("/api/projects/{project_id}/export/{export_format}")
    def export_data(project_id: str, export_format: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        title_slug = proj.metadata.title.replace(" ", "_").lower()

        if export_format in ("screenplay", "fountain"):
            content = proj.fountain_text or (proj.screenplay.to_fountain() if proj.screenplay else "")
            if not content:
                raise HTTPException(status_code=400, detail="Screenplay not yet generated")
            return Response(
                content=content,
                media_type="text/plain; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{title_slug}.fountain"'},
            )

        elif export_format == "synopsis":
            syn = proj.synopsis
            if not syn:
                if proj.story_outline:
                    syn = SynopsisGenerator().generate_synopsis(proj.story_outline, proj.world, proj.selection)
                else:
                    raise HTTPException(status_code=400, detail="Synopsis not yet generated")
            md_text = (
                f"# {syn.title}\n\n"
                f"**LOGLINE**:\n{syn.logline}\n\n"
                f"**SUMMARY**:\n{syn.paragraph_summary}\n\n"
                f"**DRAMATIC QUESTION**:\n{syn.dramatic_question}\n\n"
                f"**FULL SYNOPSIS**:\n{syn.full_synopsis}\n"
            )
            return Response(
                content=md_text,
                media_type="text/markdown; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{title_slug}_synopsis.md"'},
            )

        elif export_format == "shots_csv":
            if not proj.shot_plan:
                raise HTTPException(status_code=400, detail="Shot plan not yet prepared")
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Scene", "Shot", "Page", "Shot Type", "Camera Angle",
                "Location", "Actors", "Objects", "Action / Caption", "Dialogue"
            ])
            for p in proj.shot_plan.panels:
                writer.writerow([
                    p.scene_number,
                    p.shot_number,
                    p.page_number,
                    p.shot_type.value,
                    p.camera_angle.value,
                    p.location_name,
                    ", ".join(p.character_names),
                    ", ".join(p.objects_in_frame),
                    p.action_description,
                    p.dialogue_excerpt or "",
                ])
            return Response(
                content=output.getvalue(),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{title_slug}_shotlist.csv"'},
            )

        elif export_format == "shots_json":
            if not proj.shot_plan:
                raise HTTPException(status_code=400, detail="Shot plan not yet prepared")
            return proj.shot_plan.model_dump(mode="json")

        elif export_format == "bundle":
            return proj.model_dump(mode="json")

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported export format: {export_format}")

    return app


app = create_app()
