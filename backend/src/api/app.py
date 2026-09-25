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
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict

from src.domain.world import WorldState
from src.domain.character import Character
from src.domain.goal import Goal, GoalStatus
from src.domain.secret import Secret
from src.domain.belief import Belief
from src.domain.character_creation import (
    FieldAuthority,
    FieldProvenance,
    CharacterInput,
    CharacterProfileDraft,
)
from src.domain.character_completeness import (
    CompletenessReport,
    calculate_character_completeness,
)
from src.domain.character_dynamics import (
    CharacterDynamicsProfile,
    DYNAMICS_FIELD_NAMES,
)
from src.domain.archetype import (
    ArchetypeType,
    ArchetypeShiftPoint,
    ArchetypeTrajectory,
)
from src.domain.conflict import (
    ConflictDimension,
    ConflictEvidence,
    ConflictEdge,
    ConflictGraph,
)
from src.narrative.conflict_engine import ConflictEngine
from src.narrative.state_history import (
    CharacterStateHistoryReconstructor,
    RELATIONSHIP_METRIC_NAMES,
    CHARACTER_METRIC_NAMES,
)
from src.generator.initializer import WorldInitializerService
from src.generator.character_normalizer import CharacterProfileNormalizer
from src.generator.character_enricher import CharacterEnrichmentService
from src.generator.archetype_inference import ArchetypeInferenceEngine
from src.narrative.archetype_analyzer import ArchetypeTrajectoryAnalyzer
from src.simulation.orchestrator import SimulationOrchestrator
from src.agents.actor import ActorAgent
from src.agents.director import DirectorAgent
from src.narrative.observer import Observer, NarrativeEventSelection
from src.narrative.scribe import Scribe
from src.narrative.fountain import ScreenplayDocument
from src.narrative.framer import FramingMode
from src.narrative.screenplay_validator import ScreenplayQualityValidator
from src.narrative.completion import StoryCompletionEngine, StoryOutline, StoryInputType
from src.narrative.synopsis import SynopsisGenerator, StorySynopsis
from src.domain.story_structure import (
    StoryStructureType,
    PresentationStrategy,
    StructureSelectionMode,
    ScenePurposeType,
)
from src.narrative.structure_library import STRUCTURE_LIBRARY, COMPATIBILITY_MATRIX
from src.narrative.structure_selector import StructureSelector
from src.narrative.blueprint_generator import StoryBlueprintGenerator
from src.narrative.scene_builder import SceneBuilder
from src.narrative.scene_projection import ObservableSceneProjector
from src.narrative.causal_analyzer import CausalContinuityAnalyzer
from src.narrative.arc_tracker import CharacterArcTracker
from src.storage.project_store import (
    ProjectStore,
    ProjectData,
    ProjectMetadata,
    ProjectStorageError,
    ProjectCorruptedError,
)
from src.storyboard.models import ShotPlan, StoryboardPanel, StoryboardImageVersion, StoryboardImageStatus
from src.storyboard.planner import StoryboardPlanner
from src.storyboard.storyboard_validator import StoryboardQualityValidator
from src.storyboard.visual_bible import VisualBible, StoryboardStyleProfile
from src.storyboard.compiler import StoryboardPromptCompiler, ContinuityValidator
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.continuity import (
    CharacterContinuityPack,
    LocationContinuityPack,
    PropContinuityPack,
    StoryboardSequenceContext,
)
from src.storyboard.control import StoryboardControlBundle, PrevisControlRenderer
from src.storyboard.open_model_provider import (
    OpenModelStoryboardProvider,
    ComfyUIStoryboardAdapter,
    DiffusersStoryboardAdapter,
    MockOpenModelStoryboardAdapter,
    select_keyframe_indices,
    RenderMode,
)
from src.storyboard.image_provider import (
    StoryboardImageProvider,
    StoryboardImageResult,
    ExternalStoryboardImageProvider,
    HuggingFaceStoryboardProvider,
    FallbackComicSvgProvider,
    CloudImagenStoryboardProvider,
    MockStoryboardImageProvider,
    OpenModelImageProviderAdapter,
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
    structure_mode: Optional[str] = "AUTO"
    structure_type: Optional[str] = None
    secondary_structure: Optional[str] = None
    presentation_strategy: Optional[str] = "CHRONOLOGICAL"


class StepRequest(BaseModel):
    ticks: int = Field(default=1, ge=1, le=50)


class RunRequest(BaseModel):
    num_ticks: int = Field(default=5, ge=1, le=100)


class CharacterIntakeRequest(BaseModel):
    raw_text: Optional[str] = None
    structured_payload: Optional[Dict[str, Any]] = None
    auto_enrich: Optional[bool] = False


class LockFieldRequest(BaseModel):
    field_name: str


class UnlockFieldRequest(BaseModel):
    field_name: str


class UpdateFieldRequest(BaseModel):
    field_name: str
    value: Any
    authority: Optional[FieldAuthority] = FieldAuthority.USER_LOCKED


class UpdateDynamicsRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    core_value: Optional[str] = None
    shadow_value: Optional[str] = None
    conscious_want: Optional[str] = None
    dramatic_need: Optional[str] = None
    fear: Optional[str] = None
    contradiction: Optional[str] = None
    moral_boundary: Optional[str] = None
    habits: Optional[List[str]] = None
    mannerisms: Optional[List[str]] = None
    lifestyle: Optional[str] = None
    speech_style: Optional[str] = None
    conflict_strategy: Optional[str] = None
    primary_archetype: Optional[str] = None
    secondary_archetype: Optional[str] = None
    locked_fields: Optional[List[str]] = None
    force: Optional[bool] = False


class UpdateArchetypeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    primary_archetype: Optional[str] = None
    secondary_archetype: Optional[str] = None
    locked_fields: Optional[List[str]] = None
    force: Optional[bool] = False


class GenerateScreenplayRequest(BaseModel):
    framing_mode: Optional[str] = "chronological"


class PlanStoryboardRequest(BaseModel):
    density_mode: str = Field(default="standard")  # "quick" | "standard" | "detailed"
    panels_per_page: int = Field(default=4, ge=1, le=8)
    render_mode: str = Field(default="KEYFRAMES")  # "KEYFRAMES" | "FULL_BOARD"
    keyframe_budget: Optional[int] = Field(default=8, ge=1, le=12)


class GenerateStoryboardRequest(BaseModel):
    provider: Optional[str] = None  # "on_demand" | "comfyui" | "diffusers" | "cloud" | "mock"
    render_mode: Optional[str] = "KEYFRAMES"  # "KEYFRAMES" | "FULL_BOARD"
    model: Optional[str] = None
    keyframe_budget: Optional[int] = 8  # 4 | 8 | 12 (hard cap: 12)


class ConfigureRendererRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    provider: str = "on_demand"  # "on_demand" | "comfyui"
    runtime_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None



class SelectVersionRequest(BaseModel):
    version: int = Field(..., ge=1)


class RegeneratePanelRequest(BaseModel):
    panel_id: str
    provider: Optional[str] = None


class RegeneratePageRequest(BaseModel):
    page_number: int = Field(default=1, ge=1)
    provider: Optional[str] = None


class ExternalRenderRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    provider: str = "huggingface"
    model: Optional[str] = None


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
    """Instantiate storyboard renderer. Defaults strictly to OpenModelImageProviderAdapter."""
    asset_store = asset_store or StoryboardAssetStore()
    provider_type = (provider_type or os.environ.get("STORYBOARD_PROVIDER", "open_model")).lower()

    if provider_type in ("on_demand", "ondemand", "on-demand"):
        return OpenModelImageProviderAdapter(asset_store=asset_store, adapter_type="on_demand")
    if provider_type in ("open_model", "open_model_storyboard", "ai_storyboard", "open"):
        return OpenModelImageProviderAdapter(asset_store=asset_store)
    if provider_type in ("comfyui", "comfy"):
        return OpenModelImageProviderAdapter(asset_store=asset_store, adapter_type="comfyui")

    if provider_type in ("diffusers",):
        return OpenModelImageProviderAdapter(asset_store=asset_store, adapter_type="diffusers")
    if provider_type in ("mock_ai", "mock_connected"):
        return OpenModelImageProviderAdapter(asset_store=asset_store, adapter_type="mock_ai")
    if provider_type in ("mock", "mock_unavailable"):
        return OpenModelImageProviderAdapter(asset_store=asset_store, adapter_type="mock_unavailable")
    if provider_type in ("hand_drawn", "hand_drawn_storyboard", "sketch", "local", "previs"):
        from src.storyboard.sketch.renderer import HandDrawnStoryboardProvider
        return HandDrawnStoryboardProvider(asset_store=asset_store)
    if provider_type in ("huggingface", "hf", "experimental_ai"):
        return HuggingFaceStoryboardProvider(asset_store=asset_store)
    if provider_type == "fallback":
        return FallbackComicSvgProvider(asset_store=asset_store)

    if provider_type in ("google_imagen", "imagen", "gemini"):
        api_key = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("IMAGEN_API_KEY")
        )
        model_name = os.environ.get("STORYBOARD_IMAGE_MODEL") or "gemini-3.1-flash-image"
        return CloudImagenStoryboardProvider(api_key=api_key, asset_store=asset_store, model_name=model_name)

    return OpenModelImageProviderAdapter(asset_store=asset_store)


def _format_rendered_panel_dict(panel, res, version: int = 1) -> dict:
    """Format rendered panel dictionary from generation result without repeating generation."""
    return {
        "panel_id": res.panel_id,
        "scene_number": panel.scene_number,
        "shot_number": panel.shot_number,
        "page_number": panel.page_number,
        "shot_type": panel.shot_type.value if hasattr(panel.shot_type, "value") else str(panel.shot_type),
        "camera_angle": panel.camera_angle.value if hasattr(panel.camera_angle, "value") else str(panel.camera_angle),
        "image_url": res.image_url,
        "rendered_svg": None,
        "render_type": "ai_image" if res.image_url else "previs_guide",
        "provider": res.provider,
        "mode": res.mode,
        "status": res.status.value if hasattr(res.status, "value") else str(res.status),
        "fallback_reason": res.fallback_reason,
        "provider_status": res.provider_status,
        "continuity_mode": res.continuity_mode,
        "mime_type": res.mime_type,
        "version": version,
        "prompt_used": res.compiled_prompt,
        "negative_prompt": res.negative_prompt,
        "caption": panel.caption,
        "psychological_rationale": getattr(panel, "psychological_rationale", None) or (panel.metadata.get("psychological_rationale") if panel.metadata else None),
        "metadata": res.render_metadata,
    }


def _build_continuity_context(world, bible):
    """Build Character, Location, and Prop continuity packs from world state or visual bible."""
    char_packs = {}
    if world and world.characters:
        for cid, char in world.characters.items():
            char_packs[cid] = CharacterContinuityPack.from_character(char)
    elif bible and bible.characters:
        for cid, cref in bible.characters.items():
            char_packs[cid] = CharacterContinuityPack.from_visual_reference(cref)

    loc_packs = {}
    if world and world.locations:
        for lid, loc in world.locations.items():
            loc_packs[lid] = LocationContinuityPack.from_location(loc)
    elif bible and bible.locations:
        for lid, lref in bible.locations.items():
            loc_packs[lid] = LocationContinuityPack.from_visual_reference(lref)

    prop_packs = {}
    if world and world.objects:
        for oid, obj in world.objects.items():
            prop_packs[oid] = PropContinuityPack.from_object(obj)
    elif bible and bible.objects:
        for oid, oref in bible.objects.items():
            prop_packs[oid] = PropContinuityPack.from_visual_reference(oref)

    return char_packs, loc_packs, prop_packs


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

    @app.exception_handler(ProjectCorruptedError)
    def handle_project_corrupted(request, exc: ProjectCorruptedError):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "error": "ProjectCorruptedError"},
        )

    @app.exception_handler(ProjectStorageError)
    def handle_project_storage_error(request, exc: ProjectStorageError):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "error": "ProjectStorageError"},
        )

    store = ProjectStore(base_dir=store_dir)
    orchestrator_cache: Dict[str, SimulationOrchestrator] = {}

    def get_or_create_orchestrator(project: ProjectData) -> SimulationOrchestrator:
        pid = project.metadata.id
        if pid in orchestrator_cache:
            cached = orchestrator_cache[pid]
            if set(cached.world.characters.keys()) == set(project.world.characters.keys()):
                return cached
            orchestrator_cache.pop(pid, None)

        provider = get_llm_provider()
        orch = SimulationOrchestrator(
            world=project.world,
            provider=provider,
            story_blueprint=getattr(project, "story_blueprint", None),
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

        try:
            # Generate world initialization plan with story outline
            plan = init_service.generate_plan(
                req.seed_prompt,
                declared_type=req.input_type,
                target_duration_minutes=req.target_duration_minutes,
            )
        except Exception:
            fallback_init = WorldInitializerService(provider=MockLLMProvider())
            plan = fallback_init.generate_plan(
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

        # Select narrative structure & synthesize soft-pressure blueprint
        selector = StructureSelector()
        mode_val = StructureSelectionMode.AUTO
        if req.structure_mode and req.structure_mode.upper() in StructureSelectionMode._value2member_map_:
            mode_val = StructureSelectionMode(req.structure_mode.upper())
        elif req.structure_type:
            mode_val = StructureSelectionMode.MANUAL

        primary_val = None
        if req.structure_type and req.structure_type.upper() in StoryStructureType._value2member_map_:
            primary_val = StoryStructureType(req.structure_type.upper())

        sec_val = None
        if req.secondary_structure and req.secondary_structure.upper() in StoryStructureType._value2member_map_:
            sec_val = StoryStructureType(req.secondary_structure.upper())

        pres_val = PresentationStrategy.CHRONOLOGICAL
        if req.presentation_strategy and req.presentation_strategy.upper() in PresentationStrategy._value2member_map_:
            pres_val = PresentationStrategy(req.presentation_strategy.upper())

        sel_result = selector.select_structure(
            prompt=req.seed_prompt,
            input_type=req.input_type or "beginning",
            mode=mode_val,
            manual_primary=primary_val,
            manual_secondary=sec_val,
        )

        bp_gen = StoryBlueprintGenerator()
        blueprint = bp_gen.generate_blueprint(
            prompt=req.seed_prompt,
            selection=sel_result,
            title=title,
            presentation_strategy=pres_val,
        )

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
            story_structure=sel_result.primary_structure.value,
            story_blueprint=blueprint,
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
                scenes=proj.scenes,
                screenplay=proj.screenplay,
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
    def generate_screenplay(project_id: str, req: Optional[GenerateScreenplayRequest] = None):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        framing_mode = FramingMode.CHRONOLOGICAL
        if req and req.framing_mode:
            try:
                framing_mode = FramingMode(req.framing_mode.lower())
            except Exception:
                framing_mode = FramingMode.CHRONOLOGICAL

        provider = get_llm_provider()
        events = sorted(proj.world.events.values(), key=lambda e: (e.tick, e.id))

        observer = Observer(provider=provider)
        selection = observer.observe_events(events, proj.world)

        # Route through Phase 7 ObservableSceneProjection pipeline if scenes exist
        projections = None
        if proj.scenes:
            builder = SceneBuilder()
            enriched_scenes = builder.enrich_scenes_with_phase6(proj.scenes, proj.world)
            projector = ObservableSceneProjector()
            projections = projector.project_all_scenes(enriched_scenes, proj.world)
            scribe = Scribe(provider=provider)
            doc = scribe.compose_from_projections(projections, title=proj.metadata.title)
        else:
            scribe = Scribe(provider=provider)
            doc = scribe.compose_screenplay(selection, proj.world, title=proj.metadata.title, framing_mode=framing_mode)

        fountain_text = doc.to_fountain()

        proj.selection = selection
        proj.screenplay = doc
        proj.fountain_text = fountain_text

        # Update synopsis grounded in verified simulation beats & scenes
        syn_gen = SynopsisGenerator()
        proj.synopsis = syn_gen.generate_synopsis(
            outline=proj.story_outline,
            world=proj.world,
            selection=selection,
            scenes=proj.scenes,
            screenplay=doc,
            projections=projections,
        )

        # Execute deterministic ScreenplayQualityReport validation
        val = ScreenplayQualityValidator()
        report = val.validate(doc, proj.world, scenes=proj.scenes, projections=projections)
        proj.screenplay_quality = report.to_dict()

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
        caps = storyboard_engine.get_capabilities() if hasattr(storyboard_engine, "get_capabilities") else storyboard_engine.get_status()
        shot_plan.runtime_status = caps
        rendered_panels = []
        for p in shot_plan.panels:
            # In default KEYFRAMES mode, only render keyframe dramatic beats
            if not p.is_keyframe:
                previs_renderer = PrevisControlRenderer(asset_store=asset_store)
                bundle = previs_renderer.generate_control_bundle(p, bible=bible, version=1)
                p.control_bundle = bundle.to_dict()
                p.previs_svg = bundle.previs_svg
                p.image_url = None
                p.rendered_image_url = None
                p.rendered_svg = None
                p.image_status = StoryboardImageStatus.PLANNED
                p.provider = caps.get("provider", "open_model_storyboard")
                ver = StoryboardImageVersion(
                    version=1,
                    image_url="",
                    prompt_used=p.visual_prompt,
                    negative_prompt="",
                    provider=p.provider,
                    mode="previs_guide",
                    previs_available=True,
                    control_bundle=p.control_bundle,
                    continuity_mode="Open-Model Continuity Pack",
                    is_selected=True,
                    render_metadata={"previs_available": True, "label": "PREVIS GUIDE", "keyframe_deferred": True},
                )
                p.versions = [ver]
                p.selected_version = 1
                rendered_panels.append({
                    "panel_id": p.panel_id or p.id,
                    "scene_number": p.scene_number,
                    "shot_number": p.shot_number,
                    "page_number": p.page_number,
                    "shot_type": p.shot_type.value if hasattr(p.shot_type, "value") else str(p.shot_type),
                    "camera_angle": p.camera_angle.value if hasattr(p.camera_angle, "value") else str(p.camera_angle),
                    "image_url": None,
                    "rendered_svg": None,
                    "render_type": "previs_guide",
                    "provider": p.provider,
                    "mode": "previs_guide",
                    "status": "PLANNED",
                    "fallback_reason": None,
                    "provider_status": "AVAILABLE",
                    "continuity_mode": "Open-Model Continuity Pack",
                    "mime_type": "image/png",
                    "version": 1,
                    "prompt_used": p.visual_prompt,
                    "negative_prompt": "",
                    "caption": p.caption,
                    "metadata": {"previs_available": True, "label": "PREVIS GUIDE", "keyframe_deferred": True},
                })
            else:
                res = storyboard_engine.generate_panel(p, bible=bible, version=1)
                p.image_url = res.image_url if res.status == StoryboardImageStatus.READY else None
                p.rendered_image_url = p.image_url
                p.rendered_svg = None  # Never show procedural SVG as final artwork
                p.image_status = res.status
                p.provider = res.provider
                p.fallback_reason = res.fallback_reason
                p.continuity_mode = res.continuity_mode
                ctrl_dict = res.render_metadata.get("control_bundle") or p.control_bundle
                p.control_bundle = ctrl_dict
                ver = StoryboardImageVersion(
                    version=1,
                    image_url=res.image_url or "",
                    prompt_used=res.compiled_prompt,
                    negative_prompt=res.negative_prompt,
                    provider=res.provider,
                    mode=res.mode,
                    fallback_reason=res.fallback_reason,
                    mime_type=res.mime_type,
                    continuity_mode=res.continuity_mode,
                    is_selected=True,
                    control_bundle=ctrl_dict,
                    previs_available=True,
                    render_metadata=res.render_metadata,
                )
                p.versions = [ver]
                p.selected_version = 1
                rendered_panels.append(_format_rendered_panel_dict(p, res, version=1))

        proj.shot_plan = shot_plan
        proj.rendered_panels = rendered_panels

        # Build scenes with SceneBuilder and CoreEmotionalObjective
        scene_builder = SceneBuilder()
        scenes = scene_builder.build_scenes(selection, proj.world)
        proj.scenes = scenes

        # Analyze causal continuity ('Therefore / But' vs 'And Then')
        causal_analyzer = CausalContinuityAnalyzer()
        proj.causal_summary = causal_analyzer.analyze_causal_continuity(events, scenes)

        # Track observational character arcs
        arc_tracker = CharacterArcTracker()
        proj.character_arcs = arc_tracker.track_character_arcs(proj.world, events)

        # Validate screenplay and storyboard quality
        screenplay_validator = ScreenplayQualityValidator()
        screenplay_report = screenplay_validator.validate_screenplay(doc, proj.world)
        proj.screenplay_quality = screenplay_report.to_dict()

        storyboard_validator = StoryboardQualityValidator()
        storyboard_report = storyboard_validator.validate_storyboard(shot_plan, proj.world)
        proj.storyboard_quality = storyboard_report.to_dict()

        store.save_project(proj)

        return {
            "project_id": project_id,
            "total_beats": len(selection.filtered_beats),
            "total_scenes": len(doc.scenes),
            "total_panels": len(shot_plan.panels),
            "fountain_text": fountain_text,
            "screenplay": doc.model_dump(mode="json"),
            "synopsis": proj.synopsis.model_dump(mode="json") if proj.synopsis else None,
            "screenplay_quality": proj.screenplay_quality,
            "storyboard_quality": proj.storyboard_quality,
            "causal_summary": proj.causal_summary.model_dump(mode="json") if proj.causal_summary else None,
            "character_arcs": {cid: r.model_dump(mode="json") for cid, r in proj.character_arcs.items()} if proj.character_arcs else {},
            "scenes": [s.model_dump(mode="json") for s in proj.scenes] if proj.scenes else [],
        }

    @app.get("/api/structures")
    def list_structures():
        return {
            "structures": [
                {
                    "structure_type": s.structure_type.value,
                    "name": s.name,
                    "description": s.description,
                    "pacing_curve": s.pacing_curve,
                    "ideal_for": s.ideal_for,
                    "beats": [b.model_dump(mode="json") for b in s.beats],
                }
                for s in STRUCTURE_LIBRARY.values()
            ],
            "compatibility": {
                f"{k[0].value}:{k[1].value}": v
                for k, v in COMPATIBILITY_MATRIX.items()
            },
        }

    @app.get("/api/projects/{project_id}/blueprint")
    def get_blueprint(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if not proj.story_blueprint:
            selector = StructureSelector()
            sel_result = selector.select_structure(
                prompt=proj.metadata.seed_prompt,
                mode=StructureSelectionMode.AUTO,
            )
            bp_gen = StoryBlueprintGenerator()
            proj.story_blueprint = bp_gen.generate_blueprint(
                prompt=proj.metadata.seed_prompt,
                selection=sel_result,
                title=proj.metadata.title,
            )
            store.save_project(proj)
        return proj.story_blueprint.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/character-arcs")
    def get_character_arcs(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if proj.character_arcs:
            return {cid: rep.model_dump(mode="json") for cid, rep in proj.character_arcs.items()}
        events = sorted(proj.world.events.values(), key=lambda e: (e.tick, e.id))
        tracker = CharacterArcTracker()
        reports = tracker.track_character_arcs(proj.world, events)
        proj.character_arcs = reports
        store.save_project(proj)
        return {cid: rep.model_dump(mode="json") for cid, rep in reports.items()}

    # --- Phase A: Character Creation & Field Authority Endpoints ---

    @app.post("/api/projects/{project_id}/characters/intake")
    def intake_character_for_project(project_id: str, req: CharacterIntakeRequest):
        """Intake character from free text or structured fields with field-level authority."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        normalizer = CharacterProfileNormalizer()
        char_input, draft = normalizer.normalize(
            raw_text=req.raw_text,
            structured_payload=req.structured_payload,
            project_id=project_id,
        )

        if req.auto_enrich:
            enricher = CharacterEnrichmentService()
            draft = enricher.enrich(draft, premise=proj.metadata.seed_prompt)

        completeness = calculate_character_completeness(draft)

        if proj.character_inputs is None:
            proj.character_inputs = {}
        if proj.character_drafts is None:
            proj.character_drafts = {}

        proj.character_inputs[char_input.id] = char_input
        proj.character_drafts[draft.id] = draft
        store.save_project(proj)

        return {
            "input": char_input.model_dump(mode="json"),
            "draft": draft.model_dump(mode="json"),
            "completeness": completeness.model_dump(mode="json"),
        }

    @app.get("/api/projects/{project_id}/characters/drafts")
    def list_character_drafts(project_id: str):
        """List all character profile drafts for a project."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        drafts = list((proj.character_drafts or {}).values())
        return [
            {
                "draft": d.model_dump(mode="json"),
                "completeness": calculate_character_completeness(d).model_dump(mode="json"),
            }
            for d in drafts
        ]

    @app.get("/api/projects/{project_id}/characters/drafts/{draft_id}")
    def get_character_draft(project_id: str, draft_id: str):
        """Retrieve a character draft with its per-field authority and completeness."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        draft = (proj.character_drafts or {}).get(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Character draft not found")
        return {
            "draft": draft.model_dump(mode="json"),
            "completeness": calculate_character_completeness(draft).model_dump(mode="json"),
        }

    @app.get("/api/projects/{project_id}/characters/drafts/{draft_id}/completeness")
    def get_character_draft_completeness(project_id: str, draft_id: str):
        """Get pure completeness report for a character draft."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        draft = (proj.character_drafts or {}).get(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Character draft not found")
        return calculate_character_completeness(draft).model_dump(mode="json")

    @app.post("/api/projects/{project_id}/characters/drafts/{draft_id}/enrich")
    def enrich_character_draft(project_id: str, draft_id: str):
        """Enrich missing and unlocked fields deterministically, respecting USER_LOCKED fields."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        draft = (proj.character_drafts or {}).get(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Character draft not found")

        enricher = CharacterEnrichmentService()
        draft = enricher.enrich(draft, premise=proj.metadata.seed_prompt)
        completeness = calculate_character_completeness(draft)

        proj.character_drafts[draft_id] = draft
        store.save_project(proj)

        return {
            "draft": draft.model_dump(mode="json"),
            "completeness": completeness.model_dump(mode="json"),
        }

    @app.post("/api/projects/{project_id}/characters/drafts/{draft_id}/lock")
    def lock_character_field(project_id: str, draft_id: str, req: LockFieldRequest):
        """Lock a field on a character profile draft so enrichment will never modify it."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        draft = (proj.character_drafts or {}).get(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Character draft not found")

        draft.lock_field(req.field_name)
        proj.character_drafts[draft_id] = draft
        store.save_project(proj)

        return {
            "draft": draft.model_dump(mode="json"),
            "field_name": req.field_name,
            "authority": draft.get_authority(req.field_name),
        }

    @app.post("/api/projects/{project_id}/characters/drafts/{draft_id}/unlock")
    def unlock_character_field(project_id: str, draft_id: str, req: UnlockFieldRequest):
        """Unlock a previously locked field on a character profile draft."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        draft = (proj.character_drafts or {}).get(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Character draft not found")

        draft.unlock_field(req.field_name)
        proj.character_drafts[draft_id] = draft
        store.save_project(proj)

        return {
            "draft": draft.model_dump(mode="json"),
            "field_name": req.field_name,
            "authority": draft.get_authority(req.field_name),
        }

    @app.post("/api/projects/{project_id}/characters/drafts/{draft_id}/update-field")
    def update_character_field(project_id: str, draft_id: str, req: UpdateFieldRequest):
        """Explicitly update a field on a draft with user authority."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        draft = (proj.character_drafts or {}).get(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Character draft not found")

        auth = req.authority or FieldAuthority.USER_LOCKED
        success = draft.set_field(
            field_name=req.field_name,
            value=req.value,
            authority=auth,
            source_snippet="manual_edit",
            force=True,
        )
        if not success:
            raise HTTPException(status_code=400, detail=f"Cannot update field '{req.field_name}'")

        completeness = calculate_character_completeness(draft)
        proj.character_drafts[draft_id] = draft
        store.save_project(proj)

        return {
            "draft": draft.model_dump(mode="json"),
            "completeness": completeness.model_dump(mode="json"),
        }

    @app.post("/api/projects/{project_id}/characters/drafts/{draft_id}/accept")
    def accept_character_draft(project_id: str, draft_id: str):
        """Accept a character profile draft and instantiate it into the canonical world state."""
        import re as re_mod
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        draft = (proj.character_drafts or {}).get(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Character draft not found")

        # Generate character ID
        clean_name = re_mod.sub(r"[^a-zA-Z0-9_]", "", (draft.name or "actor").lower().replace(" ", "_"))
        char_id = f"char_{clean_name}"
        if char_id in proj.world.characters:
            char_id = f"char_{clean_name}_{draft.id[-4:]}"

        # Resolve location
        loc_id = draft.current_location_id
        if not loc_id or loc_id not in proj.world.locations:
            loc_id = next(iter(proj.world.locations.keys()), None)

        # Create Goals
        char_goals: List[str] = []
        for g_idx, g_desc in enumerate(draft.goals):
            gid = f"goal_{char_id}_{g_idx + 1}"
            goal = Goal(
                id=gid,
                character_id=char_id,
                description=g_desc,
                priority=0.8,
                status=GoalStatus.ACTIVE,
                reason="User-defined objective",
            )
            proj.world.goals[gid] = goal
            char_goals.append(gid)

        # Safe projection of conscious_want -> Goal (if not already represented)
        if draft.dynamics and draft.dynamics.conscious_want and draft.dynamics.conscious_want.strip():
            want_desc = draft.dynamics.conscious_want.strip()
            if not any(g_desc.strip().lower() == want_desc.lower() for g_desc in draft.goals):
                want_gid = f"goal_{char_id}_want"
                want_goal = Goal(
                    id=want_gid,
                    character_id=char_id,
                    description=want_desc,
                    priority=0.9,
                    status=GoalStatus.ACTIVE,
                    reason="Conscious want projected from dynamics profile",
                )
                proj.world.goals[want_gid] = want_goal
                char_goals.insert(0, want_gid)

        # Create Secrets
        char_secrets: List[str] = []
        for s_idx, s_desc in enumerate(draft.secrets):
            sid = f"sec_{char_id}_{s_idx + 1}"
            sec = Secret(
                id=sid,
                character_id=char_id,
                statement=s_desc,
                importance=1.0,
            )
            proj.world.secrets[sid] = sec
            char_secrets.append(sid)

        # Create Beliefs
        char_beliefs: List[str] = []
        for b_idx, b_desc in enumerate(draft.beliefs):
            bid = f"bel_{char_id}_{b_idx + 1}"
            bel = Belief(
                id=bid,
                character_id=char_id,
                statement=b_desc,
                confidence=0.85,
                source="initial_belief",
            )
            proj.world.beliefs[bid] = bel
            char_beliefs.append(bid)

        # Create Character
        char = Character(
            id=char_id,
            name=draft.name,
            role=draft.role,
            description=draft.description,
            personality_traits=dict(draft.personality_traits),
            goals=char_goals,
            secrets=char_secrets,
            beliefs=char_beliefs,
            visual_profile=draft.visual_profile,
            current_location_id=loc_id,
            input_id=draft.input_id,
            field_provenance=dict(draft.provenance),
            dynamics=draft.dynamics.model_copy(deep=True) if draft.dynamics else None,
        )

        proj.world.characters[char_id] = char

        # Link input
        if draft.input_id and proj.character_inputs and draft.input_id in proj.character_inputs:
            proj.character_inputs[draft.input_id].linked_character_id = char_id

        store.save_project(proj)
        orchestrator_cache.pop(project_id, None)

        return {
            "character": char.model_dump(mode="json"),
            "character_id": char_id,
            "draft_id": draft_id,
        }

    # --- Phase B: Character Dynamics & Safe Projection Endpoints ---

    @app.get("/api/projects/{project_id}/characters/{character_id}/dynamics")
    def get_character_dynamics(project_id: str, character_id: str):
        """Get CharacterDynamicsProfile design metadata for a character."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        char = proj.world.characters.get(character_id)
        if not char:
            raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")
        dyn = char.dynamics or CharacterDynamicsProfile()
        return dyn.model_dump(mode="json")

    @app.put("/api/projects/{project_id}/characters/{character_id}/dynamics")
    def update_character_dynamics(project_id: str, character_id: str, req: UpdateDynamicsRequest):
        """Update CharacterDynamicsProfile design metadata respecting FieldAuthority locks."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        char = proj.world.characters.get(character_id)
        if not char:
            raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")
        if char.dynamics is None:
            char.dynamics = CharacterDynamicsProfile()

        locked_set = set(req.locked_fields or [])

        # Update each field if provided
        for field_name in (
            "core_value", "shadow_value", "conscious_want", "dramatic_need",
            "fear", "contradiction", "moral_boundary", "lifestyle",
            "speech_style", "conflict_strategy", "primary_archetype", "secondary_archetype"
        ):
            val = getattr(req, field_name)
            if val is not None:
                if field_name in ("primary_archetype", "secondary_archetype"):
                    val = ArchetypeType.from_str(str(val)) if not isinstance(val, ArchetypeType) else val
                auth = FieldAuthority.USER_LOCKED if field_name in locked_set else FieldAuthority.USER_PREFERRED
                success = char.dynamics.set_field(
                    field_name=field_name,
                    value=val,
                    authority=auth,
                    source_snippet=f"api_update:{field_name}",
                    force=bool(req.force),
                )
                if not success and not req.force:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field '{field_name}' is USER_LOCKED and cannot be overwritten without force=True",
                    )
                if field_name in char.dynamics.provenance:
                    char.field_provenance[field_name] = char.dynamics.provenance[field_name]

        for list_field in ("habits", "mannerisms"):
            val = getattr(req, list_field)
            if val is not None:
                auth = FieldAuthority.USER_LOCKED if list_field in locked_set else FieldAuthority.USER_PREFERRED
                success = char.dynamics.set_field(
                    field_name=list_field,
                    value=val,
                    authority=auth,
                    source_snippet=f"api_update:{list_field}",
                    force=bool(req.force),
                )
                if not success and not req.force:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field '{list_field}' is USER_LOCKED and cannot be overwritten without force=True",
                    )
                if list_field in char.dynamics.provenance:
                    char.field_provenance[list_field] = char.dynamics.provenance[list_field]

        proj.world.characters[character_id] = char
        store.save_project(proj)
        return char.dynamics.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/characters/{character_id}/dynamics/enrich")
    def enrich_character_dynamics(project_id: str, character_id: str):
        """Enrich missing and unlocked dynamics fields on an existing character."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        char = proj.world.characters.get(character_id)
        if not char:
            raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")

        temp_draft = CharacterProfileDraft(
            id=f"enrich_{char.id}",
            name=char.name,
            role=char.role,
            description=char.description,
            personality_traits=dict(char.personality_traits),
            dynamics=char.dynamics.model_copy(deep=True) if char.dynamics else CharacterDynamicsProfile(),
            provenance=dict(char.field_provenance),
        )
        if char.dynamics and char.dynamics.provenance:
            temp_draft.dynamics.provenance.update(char.dynamics.provenance)
            temp_draft.provenance.update(char.dynamics.provenance)

        enricher = CharacterEnrichmentService()
        enriched_draft = enricher.enrich(temp_draft, premise=proj.metadata.seed_prompt)

        char.dynamics = enriched_draft.dynamics
        char.field_provenance.update(enriched_draft.dynamics.provenance)
        proj.world.characters[character_id] = char
        store.save_project(proj)

        return char.dynamics.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/characters/{character_id}/project-want")
    def project_character_conscious_want_to_goal(project_id: str, character_id: str):
        """Safely project character's conscious_want into the canonical Goal model.

        CRITICAL INVARIANT:
        dramatic_need remains analytical only and must NEVER be projected to Goal.
        Does not overwrite a USER_LOCKED Goal.
        """
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        char = proj.world.characters.get(character_id)
        if not char:
            raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")
        if not char.dynamics or not char.dynamics.conscious_want or not char.dynamics.conscious_want.strip():
            raise HTTPException(status_code=400, detail="Character has no conscious_want defined")

        want_text = char.dynamics.conscious_want.strip()
        want_gid = f"goal_{char.id}_want"

        # Check existing goal and locks
        prov = char.field_provenance.get("goals")
        if prov and prov.authority == FieldAuthority.USER_LOCKED and want_gid in char.goals:
            raise HTTPException(status_code=400, detail="Character goals are USER_LOCKED")

        want_goal = Goal(
            id=want_gid,
            character_id=char.id,
            description=want_text,
            priority=0.9,
            status=GoalStatus.ACTIVE,
            reason="Conscious want projected from dynamics profile",
        )
        proj.world.goals[want_gid] = want_goal
        if want_gid not in char.goals:
            char.goals.insert(0, want_gid)

        proj.world.characters[character_id] = char
        store.save_project(proj)

        return {
            "character_id": character_id,
            "goal": want_goal.model_dump(mode="json"),
            "conscious_want": want_text,
            "dramatic_need": char.dynamics.dramatic_need,
            "is_need_projected": False,
        }

    @app.post("/api/projects/{project_id}/characters/drafts/{draft_id}/project-want")
    def project_draft_conscious_want_to_goal(project_id: str, draft_id: str):
        """Safely project draft's conscious_want into draft.goals."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        draft = (proj.character_drafts or {}).get(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Character draft not found")
        if not draft.dynamics or not draft.dynamics.conscious_want or not draft.dynamics.conscious_want.strip():
            raise HTTPException(status_code=400, detail="Draft has no conscious_want defined")

        want_text = draft.dynamics.conscious_want.strip()
        if draft.is_locked("goals"):
            raise HTTPException(status_code=400, detail="Draft goals are USER_LOCKED")

        if not any(g.strip().lower() == want_text.lower() for g in draft.goals):
            draft.goals.insert(0, want_text)
            draft.set_field("goals", draft.goals, FieldAuthority.USER_PREFERRED, source_snippet=f"project_want:{want_text}", force=True)

        completeness = calculate_character_completeness(draft)
        proj.character_drafts[draft_id] = draft
        store.save_project(proj)

        return {
            "draft": draft.model_dump(mode="json"),
            "completeness": completeness.model_dump(mode="json"),
            "conscious_want": want_text,
            "is_need_projected": False,
        }

    # --- Phase C: Narrative Archetype & Observational Trajectory Endpoints ---

    @app.get("/api/projects/{project_id}/characters/{character_id}/archetype")
    def get_character_archetype(project_id: str, character_id: str):
        """Get primary and secondary archetype metadata and provenance for a character."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        char = proj.world.characters.get(character_id)
        if not char:
            raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")
        dyn = char.dynamics or CharacterDynamicsProfile()
        return {
            "character_id": character_id,
            "primary_archetype": dyn.primary_archetype.value if dyn.primary_archetype else None,
            "secondary_archetype": dyn.secondary_archetype.value if dyn.secondary_archetype else None,
            "primary_authority": dyn.get_authority("primary_archetype"),
            "secondary_authority": dyn.get_authority("secondary_archetype"),
            "provenance": {
                k: v.model_dump(mode="json")
                for k, v in dyn.provenance.items()
                if k in ("primary_archetype", "secondary_archetype")
            },
        }

    @app.put("/api/projects/{project_id}/characters/{character_id}/archetype")
    def update_character_archetype(project_id: str, character_id: str, req: UpdateArchetypeRequest):
        """Update archetype metadata on an existing character respecting FieldAuthority locks."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        char = proj.world.characters.get(character_id)
        if not char:
            raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")
        if char.dynamics is None:
            char.dynamics = CharacterDynamicsProfile()

        locked_set = set(req.locked_fields or [])

        if req.primary_archetype is not None:
            parsed_primary = ArchetypeType.from_str(req.primary_archetype)
            auth = FieldAuthority.USER_LOCKED if "primary_archetype" in locked_set else FieldAuthority.USER_PREFERRED
            success = char.dynamics.set_field(
                field_name="primary_archetype",
                value=parsed_primary,
                authority=auth,
                source_snippet="api_update:primary_archetype",
                force=bool(req.force),
            )
            if not success and not req.force:
                raise HTTPException(status_code=400, detail="Field 'primary_archetype' is USER_LOCKED")
            if "primary_archetype" in char.dynamics.provenance:
                char.field_provenance["primary_archetype"] = char.dynamics.provenance["primary_archetype"]

        if req.secondary_archetype is not None:
            parsed_sec = ArchetypeType.from_str(req.secondary_archetype)
            auth = FieldAuthority.USER_LOCKED if "secondary_archetype" in locked_set else FieldAuthority.USER_PREFERRED
            success = char.dynamics.set_field(
                field_name="secondary_archetype",
                value=parsed_sec,
                authority=auth,
                source_snippet="api_update:secondary_archetype",
                force=bool(req.force),
            )
            if not success and not req.force:
                raise HTTPException(status_code=400, detail="Field 'secondary_archetype' is USER_LOCKED")
            if "secondary_archetype" in char.dynamics.provenance:
                char.field_provenance["secondary_archetype"] = char.dynamics.provenance["secondary_archetype"]

        proj.world.characters[character_id] = char
        store.save_project(proj)
        return {
            "character_id": character_id,
            "primary_archetype": char.dynamics.primary_archetype.value if char.dynamics.primary_archetype else None,
            "secondary_archetype": char.dynamics.secondary_archetype.value if char.dynamics.secondary_archetype else None,
            "primary_authority": char.dynamics.get_authority("primary_archetype"),
            "secondary_authority": char.dynamics.get_authority("secondary_archetype"),
            "provenance": {
                k: v.model_dump(mode="json")
                for k, v in char.dynamics.provenance.items()
                if k in ("primary_archetype", "secondary_archetype")
            },
        }

    @app.post("/api/projects/{project_id}/characters/{character_id}/archetype/infer")
    def infer_character_archetypes_endpoint(project_id: str, character_id: str):
        """Deterministically infer primary and secondary archetypes for an existing character."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        char = proj.world.characters.get(character_id)
        if not char:
            raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")
        if char.dynamics is None:
            char.dynamics = CharacterDynamicsProfile()

        ArchetypeInferenceEngine.enrich_dynamics_archetypes(
            dynamics=char.dynamics,
            role=char.role or "",
            personality_traits=char.personality_traits,
        )
        if "primary_archetype" in char.dynamics.provenance:
            char.field_provenance["primary_archetype"] = char.dynamics.provenance["primary_archetype"]
        if "secondary_archetype" in char.dynamics.provenance:
            char.field_provenance["secondary_archetype"] = char.dynamics.provenance["secondary_archetype"]

        proj.world.characters[character_id] = char
        store.save_project(proj)
        return {
            "character_id": character_id,
            "primary_archetype": char.dynamics.primary_archetype.value if char.dynamics.primary_archetype else None,
            "secondary_archetype": char.dynamics.secondary_archetype.value if char.dynamics.secondary_archetype else None,
            "primary_authority": char.dynamics.get_authority("primary_archetype"),
            "secondary_authority": char.dynamics.get_authority("secondary_archetype"),
            "provenance": {
                k: v.model_dump(mode="json")
                for k, v in char.dynamics.provenance.items()
                if k in ("primary_archetype", "secondary_archetype")
            },
        }

    @app.post("/api/projects/{project_id}/characters/drafts/{draft_id}/archetype/infer")
    def infer_draft_archetypes_endpoint(project_id: str, draft_id: str):
        """Deterministically infer primary and secondary archetypes for a draft."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        draft = (proj.character_drafts or {}).get(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Character draft not found")
        if draft.dynamics is None:
            draft.dynamics = CharacterDynamicsProfile()

        ArchetypeInferenceEngine.enrich_dynamics_archetypes(
            dynamics=draft.dynamics,
            role=draft.role or "",
            personality_traits=draft.personality_traits,
        )
        if "primary_archetype" in draft.dynamics.provenance:
            draft.provenance["primary_archetype"] = draft.dynamics.provenance["primary_archetype"]
        if "secondary_archetype" in draft.dynamics.provenance:
            draft.provenance["secondary_archetype"] = draft.dynamics.provenance["secondary_archetype"]

        completeness = calculate_character_completeness(draft)
        proj.character_drafts[draft_id] = draft
        store.save_project(proj)

        return {
            "draft": draft.model_dump(mode="json"),
            "completeness": completeness.model_dump(mode="json"),
        }

    @app.get("/api/projects/{project_id}/characters/{character_id}/archetype-trajectory")
    def get_character_archetype_trajectory(project_id: str, character_id: str):
        """Observational analysis of a character's archetype alignment drift over time.

        CRITICAL INVARIANT:
        Strictly read-only post-hoc analyzer. ZERO mutation of world state.
        """
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        char = proj.world.characters.get(character_id)
        if not char:
            raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")

        events = sorted(proj.world.events.values(), key=lambda e: (e.tick, e.id))
        trajectory = ArchetypeTrajectoryAnalyzer.analyze_trajectory(
            character_id=character_id,
            world=proj.world,
            events=events,
        )
        return trajectory.model_dump(mode="json")

    # Standalone character endpoints (in-memory, no project ID required)
    @app.post("/api/characters/intake")
    def standalone_character_intake(req: CharacterIntakeRequest):
        """Intake character from free text or form payload without binding to a saved project."""
        normalizer = CharacterProfileNormalizer()
        char_input, draft = normalizer.normalize(
            raw_text=req.raw_text,
            structured_payload=req.structured_payload,
        )
        if req.auto_enrich:
            enricher = CharacterEnrichmentService()
            draft = enricher.enrich(draft)
        completeness = calculate_character_completeness(draft)
        return {
            "input": char_input.model_dump(mode="json"),
            "draft": draft.model_dump(mode="json"),
            "completeness": completeness.model_dump(mode="json"),
        }

    @app.post("/api/characters/enrich")
    def standalone_character_enrich(draft_data: Dict[str, Any] = Body(...)):
        """Enrich a character draft payload in-memory respecting authority tags."""
        draft = CharacterProfileDraft.model_validate(draft_data)
        enricher = CharacterEnrichmentService()
        enriched = enricher.enrich(draft)
        completeness = calculate_character_completeness(enriched)
        return {
            "draft": enriched.model_dump(mode="json"),
            "completeness": completeness.model_dump(mode="json"),
        }

    # Conflict and Relationship Endpoints (Phase D)
    @app.get("/api/projects/{project_id}/conflicts")
    def get_project_conflicts(project_id: str):
        """Retrieve ConflictGraph for the project cast (derives on the fly if not yet stored)."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if proj.conflict_graph:
            return proj.conflict_graph.model_dump(mode="json")
        graph = ConflictEngine.derive_conflict_graph(proj.world, project_id)
        return graph.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/conflicts/derive")
    def derive_project_conflicts(project_id: str):
        """Derive and persist a fresh ConflictGraph for the project, respecting locked edges."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        graph = ConflictEngine.derive_conflict_graph(
            proj.world, project_id, existing_graph=proj.conflict_graph
        )
        proj.conflict_graph = graph
        store.save_project(proj)
        return graph.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/conflicts/{char_a_id}/{char_b_id}")
    def get_pairwise_conflict(project_id: str, char_a_id: str, char_b_id: str):
        """Get or derive pairwise ConflictEdge between two characters."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if char_a_id not in proj.world.characters or char_b_id not in proj.world.characters:
            raise HTTPException(status_code=404, detail="One or both characters not found")
        if proj.conflict_graph:
            edge = proj.conflict_graph.get_edge(char_a_id, char_b_id)
            if edge:
                return edge.model_dump(mode="json")
        edge = ConflictEngine.derive_pairwise_conflict(proj.world, char_a_id, char_b_id)
        return edge.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/relationships")
    def get_project_relationships(project_id: str):
        """Retrieve all multidimensional relationships with event provenance for a project."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        rels = [r.model_dump(mode="json") for r in proj.world.relationships.values()]
        return {"relationships": rels}

    @app.get("/api/projects/{project_id}/relationships/{char_a_id}/{char_b_id}")
    def get_specific_relationship(project_id: str, char_a_id: str, char_b_id: str):
        """Retrieve a specific multidimensional relationship with event provenance between two characters."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        rel = proj.world.get_relationship(char_a_id, char_b_id)
        if not rel:
            raise HTTPException(status_code=404, detail="Relationship not found")
        return rel.model_dump(mode="json")

    # Character State History & Graph Endpoints (Phase E)
    @app.get("/api/projects/{project_id}/characters/{character_id}/history")
    def get_character_history(
        project_id: str,
        character_id: str,
        metric: Optional[str] = None,
        target_id: Optional[str] = None,
        sparse: bool = True,
    ):
        """Retrieve reconstructed state history time-series for a character with event provenance."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if character_id not in proj.world.characters:
            raise HTTPException(status_code=404, detail="Character not found")

        if metric:
            if metric in RELATIONSHIP_METRIC_NAMES:
                if not target_id:
                    raise HTTPException(
                        status_code=400,
                        detail=f"target_id is required for relationship metric '{metric}'",
                    )
                series = CharacterStateHistoryReconstructor.reconstruct_relationship_series(
                    proj.world,
                    character_id,
                    target_id,
                    dimension=metric,
                    project_id=project_id,
                    sparse=sparse,
                )
            else:
                series = CharacterStateHistoryReconstructor.reconstruct_character_metric_series(
                    proj.world,
                    character_id,
                    metric=metric,
                    project_id=project_id,
                    sparse=sparse,
                )
            return series.model_dump(mode="json")
        else:
            report = CharacterStateHistoryReconstructor.reconstruct_character_history(
                proj.world,
                character_id,
                target_character_id=target_id,
                project_id=project_id,
                sparse=sparse,
            )
            return report.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/relationships/{char_a_id}/{char_b_id}/history")
    def get_relationship_dimension_history(
        project_id: str,
        char_a_id: str,
        char_b_id: str,
        dimension: Optional[str] = None,
        sparse: bool = True,
    ):
        """Retrieve historical time-series for relationship dimensions with event provenance."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if char_a_id not in proj.world.characters or char_b_id not in proj.world.characters:
            raise HTTPException(status_code=404, detail="One or both characters not found")

        if dimension:
            series = CharacterStateHistoryReconstructor.reconstruct_relationship_series(
                proj.world,
                char_a_id,
                char_b_id,
                dimension=dimension,
                project_id=project_id,
                sparse=sparse,
            )
            return series.model_dump(mode="json")
        else:
            dims = sorted(list(RELATIONSHIP_METRIC_NAMES))
            res = {}
            for d in dims:
                s = CharacterStateHistoryReconstructor.reconstruct_relationship_series(
                    proj.world,
                    char_a_id,
                    char_b_id,
                    dimension=d,
                    project_id=project_id,
                    sparse=sparse,
                )
                res[d] = s.model_dump(mode="json")
            return {
                "char_a_id": char_a_id,
                "char_b_id": char_b_id,
                "dimensions": res,
            }

    @app.get("/api/projects/{project_id}/characters/{character_id}/trajectory/history")
    def get_character_trajectory_history(
        project_id: str,
        character_id: str,
        sparse: bool = True,
    ):
        """Retrieve historical time-series for archetype alignment and arc stage transitions."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if character_id not in proj.world.characters:
            raise HTTPException(status_code=404, detail="Character not found")

        trajectory_series = CharacterStateHistoryReconstructor.reconstruct_trajectory_series(
            proj.world,
            character_id,
            project_id=project_id,
            sparse=sparse,
        )
        return {
            "character_id": character_id,
            "project_id": project_id,
            "trajectory": [s.model_dump(mode="json") for s in trajectory_series],
        }

    @app.get("/api/projects/{project_id}/characters/{character_id}/history/batch")
    def get_character_history_batch(
        project_id: str,
        character_id: str,
        metrics: str,
        target_id: Optional[str] = None,
        sparse: bool = True,
    ):
        """Batch query multiple history metrics for a character."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if character_id not in proj.world.characters:
            raise HTTPException(status_code=404, detail="Character not found")

        metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
        report = CharacterStateHistoryReconstructor.reconstruct_character_history(
            proj.world,
            character_id,
            metrics=metric_list,
            target_character_id=target_id,
            project_id=project_id,
            sparse=sparse,
        )
        return report.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/causal-continuity")
    def get_causal_continuity(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if proj.causal_summary:
            return proj.causal_summary.model_dump(mode="json")
        events = sorted(proj.world.events.values(), key=lambda e: (e.tick, e.id))
        analyzer = CausalContinuityAnalyzer()
        scenes = proj.scenes or []
        summary = analyzer.analyze_causal_continuity(events, scenes)
        proj.causal_summary = summary
        store.save_project(proj)
        return summary.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/scenes")
    def get_scenes(project_id: str):
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if not proj.scenes:
            if proj.selection and proj.selection.filtered_beats:
                builder = SceneBuilder()
                proj.scenes = builder.build_scenes(proj.selection, proj.world)
                store.save_project(proj)
            else:
                return []
        return [s.model_dump(mode="json") for s in proj.scenes]

    @app.get("/api/projects/{project_id}/screenplay/quality")
    def get_screenplay_quality(project_id: str):
        proj = store.load_project(project_id)
        if not proj or not proj.screenplay:
            raise HTTPException(status_code=404, detail="Screenplay not found")
        if proj.screenplay_quality:
            return proj.screenplay_quality
        val = ScreenplayQualityValidator()
        report = val.validate_screenplay(proj.screenplay, proj.world)
        return report.to_dict()

    @app.get("/api/projects/{project_id}/storyboard/quality")
    def get_storyboard_quality(project_id: str):
        proj = store.load_project(project_id)
        if not proj or not proj.shot_plan:
            raise HTTPException(status_code=404, detail="Shot plan not found")
        if proj.storyboard_quality:
            return proj.storyboard_quality
        val = StoryboardQualityValidator()
        report = val.validate_storyboard(proj.shot_plan, proj.world)
        return report.to_dict()

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
        render_mode = req.render_mode if req else "KEYFRAMES"
        budget = req.keyframe_budget if (req and req.keyframe_budget) else 8

        asset_store = StoryboardAssetStore(store.base_dir)
        bible = proj.visual_bible or asset_store.load_visual_bible(project_id)
        if not bible:
            bible = VisualBible.from_world(proj.world)
            proj.visual_bible = bible
            asset_store.save_visual_bible(project_id, bible)

        char_packs, loc_packs, prop_packs = _build_continuity_context(proj.world, bible)

        planner = StoryboardPlanner(panels_per_page=ppp, density_mode=density)
        shot_plan = planner.plan_shots(proj.screenplay, proj.world, bible=bible, project_id=project_id, keyframe_budget=budget)
        shot_plan.render_mode = render_mode

        continuity_report = ContinuityValidator.validate_shot_plan(shot_plan.panels, bible)

        engine = get_image_provider(asset_store=asset_store)
        caps = engine.get_capabilities() if hasattr(engine, "get_capabilities") else engine.get_status()
        shot_plan.runtime_status = caps

        rendered_panels = []
        for p in shot_plan.panels:
            if render_mode == "KEYFRAMES" and not p.is_keyframe:
                previs_renderer = PrevisControlRenderer(asset_store=asset_store)
                bundle = previs_renderer.generate_control_bundle(p, bible=bible, version=1)
                p.control_bundle = bundle.to_dict()
                p.previs_svg = bundle.previs_svg
                p.image_url = None
                p.rendered_image_url = None
                p.rendered_svg = None
                p.image_status = StoryboardImageStatus.PLANNED
                p.provider = caps.get("provider", "open_model_storyboard")
                ver = StoryboardImageVersion(
                    version=1,
                    image_url="",
                    prompt_used=p.visual_prompt,
                    negative_prompt="",
                    provider=p.provider,
                    mode="previs_guide",
                    previs_available=True,
                    control_bundle=p.control_bundle,
                    continuity_mode="Open-Model Continuity Pack",
                    is_selected=True,
                    render_metadata={"previs_available": True, "label": "PREVIS GUIDE", "keyframe_deferred": True},
                )
                p.versions = [ver]
                p.selected_version = 1
                rendered_panels.append({
                    "panel_id": p.panel_id or p.id,
                    "scene_number": p.scene_number,
                    "shot_number": p.shot_number,
                    "page_number": p.page_number,
                    "shot_type": p.shot_type.value if hasattr(p.shot_type, "value") else str(p.shot_type),
                    "camera_angle": p.camera_angle.value if hasattr(p.camera_angle, "value") else str(p.camera_angle),
                    "image_url": None,
                    "rendered_svg": None,
                    "render_type": "previs_guide",
                    "provider": p.provider,
                    "mode": "previs_guide",
                    "status": "PLANNED",
                    "fallback_reason": None,
                    "provider_status": caps.get("status", "AVAILABLE") if isinstance(caps, dict) else "AVAILABLE",
                    "continuity_mode": "Open-Model Continuity Pack",
                    "mime_type": "image/png",
                    "version": 1,
                    "prompt_used": p.visual_prompt,
                    "negative_prompt": "",
                    "caption": p.caption,
                    "psychological_rationale": getattr(p, "psychological_rationale", None) or (p.metadata.get("psychological_rationale") if p.metadata else None),
                    "metadata": {"previs_available": True, "label": "PREVIS GUIDE", "keyframe_deferred": True},
                })
            else:
                res = engine.generate_panel(p, bible=bible, version=1)
                p.image_url = res.image_url if res.status == StoryboardImageStatus.READY else None
                p.rendered_image_url = p.image_url
                p.rendered_svg = None  # Never show procedural SVG as final artwork
                p.image_status = res.status
                p.provider = res.provider
                p.fallback_reason = res.fallback_reason
                p.continuity_mode = res.continuity_mode
                ctrl_dict = res.render_metadata.get("control_bundle") or p.control_bundle
                p.control_bundle = ctrl_dict
                ver = StoryboardImageVersion(
                    version=1,
                    image_url=res.image_url or "",
                    prompt_used=res.compiled_prompt,
                    negative_prompt=res.negative_prompt,
                    provider=res.provider,
                    mode=res.mode,
                    fallback_reason=res.fallback_reason,
                    mime_type=res.mime_type,
                    continuity_mode=res.continuity_mode,
                    is_selected=True,
                    control_bundle=ctrl_dict,
                    previs_available=True,
                    render_metadata=res.render_metadata,
                )
                p.versions = [ver]
                p.selected_version = 1
                rendered_panels.append(_format_rendered_panel_dict(p, res, version=1))

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
        render_mode = req.render_mode if req and req.render_mode else getattr(proj.shot_plan, "render_mode", "KEYFRAMES")
        budget = min(max(1, req.keyframe_budget if (req and req.keyframe_budget) else 8), 12)
        proj.shot_plan.render_mode = render_mode
        engine = get_image_provider(provider_type=provider_type, asset_store=asset_store)
        caps = engine.get_capabilities() if hasattr(engine, "get_capabilities") else engine.get_status()
        proj.shot_plan.runtime_status = caps

        from src.storyboard.open_model_provider import select_keyframe_indices
        kf_indices = (
            set(select_keyframe_indices(proj.shot_plan.panels, budget=budget))
            if render_mode == "KEYFRAMES"
            else set(range(min(len(proj.shot_plan.panels), 12)))
        )

        rendered_panels = []
        for idx, p in enumerate(proj.shot_plan.panels):
            target_version = len(p.versions) + 1 if p.versions else 1
            is_keyframe = idx in kf_indices
            p.is_keyframe = is_keyframe

            if render_mode == "KEYFRAMES" and not is_keyframe:
                previs_renderer = PrevisControlRenderer(asset_store=asset_store)
                bundle = previs_renderer.generate_control_bundle(p, bible=bible, version=target_version)
                p.control_bundle = bundle.to_dict()
                p.previs_svg = bundle.previs_svg
                p.image_url = None
                p.rendered_image_url = None
                p.rendered_svg = None
                p.image_status = StoryboardImageStatus.PLANNED
                p.provider = caps.get("provider", "on_demand")
                p.generation_version = target_version
                p.selected_version = target_version
                for v in p.versions:
                    v.is_selected = False
                new_ver = StoryboardImageVersion(
                    version=target_version,
                    image_url="",
                    prompt_used=p.visual_prompt,
                    negative_prompt="",
                    provider=p.provider,
                    mode="previs_guide",
                    previs_available=True,
                    control_bundle=p.control_bundle,
                    continuity_mode="Open-Model Continuity Pack",
                    is_selected=True,
                    render_metadata={"previs_available": True, "label": "PREVIS GUIDE", "keyframe_deferred": True},
                )
                p.versions.append(new_ver)
                rendered_panels.append({
                    "panel_id": p.id,
                    "scene_number": p.scene_number,
                    "shot_number": p.shot_number,
                    "page_number": p.page_number,
                    "shot_type": p.shot_type.value if hasattr(p.shot_type, "value") else str(p.shot_type),
                    "camera_angle": p.camera_angle.value if hasattr(p.camera_angle, "value") else str(p.camera_angle),
                    "image_url": None,
                    "rendered_svg": None,
                    "render_type": "previs_guide",
                    "provider": p.provider,
                    "mode": "previs_guide",
                    "status": "PLANNED",
                    "fallback_reason": None,
                    "provider_status": caps.get("provider_status", "AVAILABLE") if isinstance(caps, dict) else "AVAILABLE",
                    "continuity_mode": "Open-Model Continuity Pack",
                    "mime_type": "image/png",
                    "version": target_version,
                    "prompt_used": p.visual_prompt,
                    "negative_prompt": "",
                    "caption": p.caption,
                    "psychological_rationale": getattr(p, "psychological_rationale", None) or (p.metadata.get("psychological_rationale") if p.metadata else None),
                    "metadata": {"previs_available": True, "label": "PREVIS GUIDE", "keyframe_deferred": True},
                })
            else:
                res = engine.generate_panel(p, bible=bible, version=target_version)
                p.image_url = res.image_url if res.status == StoryboardImageStatus.READY else None
                p.rendered_image_url = p.image_url
                p.rendered_svg = None  # Never show procedural SVG as final artwork
                p.image_status = res.status
                p.provider = res.provider
                p.fallback_reason = res.fallback_reason
                p.continuity_mode = res.continuity_mode
                p.generation_version = target_version
                p.selected_version = target_version
                ctrl_dict = res.render_metadata.get("control_bundle") or p.control_bundle
                p.control_bundle = ctrl_dict
                if res.fallback_reason == "QUOTA_UNAVAILABLE":
                    p.status_message = "Image generation quota unavailable."

                for v in p.versions:
                    v.is_selected = False

                new_ver = StoryboardImageVersion(
                    version=target_version,
                    image_url=res.image_url or "",
                    prompt_used=res.compiled_prompt,
                    negative_prompt=res.negative_prompt,
                    provider=res.provider,
                    mode=res.mode,
                    fallback_reason=res.fallback_reason,
                    mime_type=res.mime_type,
                    continuity_mode=res.continuity_mode,
                    is_selected=True,
                    control_bundle=ctrl_dict,
                    previs_available=True,
                    render_metadata=res.render_metadata,
                )
                p.versions.append(new_ver)
                rendered_panels.append({
                    "panel_id": res.panel_id,
                    "scene_number": p.scene_number,
                    "shot_number": p.shot_number,
                    "page_number": p.page_number,
                    "shot_type": p.shot_type.value if hasattr(p.shot_type, "value") else str(p.shot_type),
                    "camera_angle": p.camera_angle.value if hasattr(p.camera_angle, "value") else str(p.camera_angle),
                    "image_url": res.image_url,
                    "rendered_svg": None,
                    "render_type": "ai_image" if res.image_url else "previs_guide",
                    "provider": res.provider,
                    "mode": res.mode,
                    "status": res.status.value if hasattr(res.status, "value") else str(res.status),
                    "fallback_reason": res.fallback_reason,
                    "provider_status": res.provider_status,
                    "continuity_mode": res.continuity_mode,
                    "mime_type": res.mime_type,
                    "version": target_version,
                    "prompt_used": res.compiled_prompt,
                    "negative_prompt": res.negative_prompt,
                    "caption": p.caption,
                    "metadata": res.render_metadata,
                })


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
        caps = engine.get_capabilities() if hasattr(engine, "get_capabilities") else engine.get_status()
        shot_plan.runtime_status = caps
        rendered_panels = []
        for p in shot_plan.panels:
            if not p.is_keyframe:
                previs_renderer = PrevisControlRenderer(asset_store=asset_store)
                bundle = previs_renderer.generate_control_bundle(p, bible=bible, version=1)
                p.control_bundle = bundle.to_dict()
                p.previs_svg = bundle.previs_svg
                p.image_url = None
                p.rendered_image_url = None
                p.rendered_svg = None
                p.image_status = StoryboardImageStatus.PLANNED
                p.provider = caps.get("provider", "open_model_storyboard")
                ver = StoryboardImageVersion(
                    version=1,
                    image_url="",
                    prompt_used=p.visual_prompt,
                    negative_prompt="",
                    provider=p.provider,
                    mode="previs_guide",
                    previs_available=True,
                    control_bundle=p.control_bundle,
                    continuity_mode="Open-Model Continuity Pack",
                    is_selected=True,
                    render_metadata={"previs_available": True, "label": "PREVIS GUIDE", "keyframe_deferred": True},
                )
                p.versions = [ver]
                p.selected_version = 1
                rendered_panels.append({
                    "panel_id": p.panel_id or p.id,
                    "scene_number": p.scene_number,
                    "shot_number": p.shot_number,
                    "page_number": p.page_number,
                    "shot_type": p.shot_type.value if hasattr(p.shot_type, "value") else str(p.shot_type),
                    "camera_angle": p.camera_angle.value if hasattr(p.camera_angle, "value") else str(p.camera_angle),
                    "image_url": None,
                    "rendered_svg": None,
                    "render_type": "previs_guide",
                    "provider": p.provider,
                    "mode": "previs_guide",
                    "status": "PLANNED",
                    "fallback_reason": None,
                    "provider_status": "AVAILABLE",
                    "continuity_mode": "Open-Model Continuity Pack",
                    "mime_type": "image/png",
                    "version": 1,
                    "prompt_used": p.visual_prompt,
                    "negative_prompt": "",
                    "caption": p.caption,
                    "metadata": {"previs_available": True, "label": "PREVIS GUIDE", "keyframe_deferred": True},
                })
            else:
                res = engine.generate_panel(p, bible=bible, version=1)
                p.image_url = res.image_url if res.status == StoryboardImageStatus.READY else None
                p.rendered_image_url = p.image_url
                p.rendered_svg = None  # Never show procedural SVG as final artwork
                p.image_status = res.status
                p.provider = res.provider
                p.fallback_reason = res.fallback_reason
                p.continuity_mode = res.continuity_mode
                ctrl_dict = res.render_metadata.get("control_bundle") or p.control_bundle
                p.control_bundle = ctrl_dict
                ver = StoryboardImageVersion(
                    version=1,
                    image_url=res.image_url or "",
                    prompt_used=res.compiled_prompt,
                    negative_prompt=res.negative_prompt,
                    provider=res.provider,
                    mode=res.mode,
                    fallback_reason=res.fallback_reason,
                    mime_type=res.mime_type,
                    continuity_mode=res.continuity_mode,
                    is_selected=True,
                    control_bundle=ctrl_dict,
                    previs_available=True,
                    render_metadata=res.render_metadata,
                )
                p.versions = [ver]
                p.selected_version = 1
                rendered_panels.append(_format_rendered_panel_dict(p, res, version=1))

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
        target_panel.image_url = res.image_url if res.status == StoryboardImageStatus.READY else None
        target_panel.rendered_image_url = target_panel.image_url
        target_panel.rendered_svg = None  # Never show procedural SVG as final artwork
        target_panel.image_status = res.status
        target_panel.provider = res.provider
        target_panel.fallback_reason = res.fallback_reason
        target_panel.continuity_mode = res.continuity_mode
        target_panel.generation_version = next_ver
        target_panel.selected_version = next_ver

        ctrl_dict = res.render_metadata.get("control_bundle") or target_panel.control_bundle
        target_panel.control_bundle = ctrl_dict

        for v in target_panel.versions:
            v.is_selected = False

        new_version = StoryboardImageVersion(
            version=next_ver,
            image_url=res.image_url or "",
            prompt_used=res.compiled_prompt,
            negative_prompt=res.negative_prompt,
            provider=res.provider,
            mode=res.mode,
            fallback_reason=res.fallback_reason,
            mime_type=res.mime_type,
            continuity_mode=res.continuity_mode,
            is_selected=True,
            control_bundle=ctrl_dict,
            previs_available=True,
            render_metadata=res.render_metadata,
        )
        target_panel.versions.append(new_version)

        rendered_dict = {
            "panel_id": res.panel_id,
            "scene_number": target_panel.scene_number,
            "shot_number": target_panel.shot_number,
            "page_number": target_panel.page_number,
            "shot_type": target_panel.shot_type.value if hasattr(target_panel.shot_type, "value") else str(target_panel.shot_type),
            "camera_angle": target_panel.camera_angle.value if hasattr(target_panel.camera_angle, "value") else str(target_panel.camera_angle),
            "image_url": res.image_url,
            "rendered_svg": None,
            "render_type": "ai_image" if res.image_url else "previs_guide",
            "provider": res.provider,
            "mode": res.mode,
            "status": res.status.value if hasattr(res.status, "value") else str(res.status),
            "fallback_reason": res.fallback_reason,
            "provider_status": res.provider_status,
            "continuity_mode": res.continuity_mode,
            "mime_type": res.mime_type,
            "version": next_ver,
            "prompt_used": res.compiled_prompt,
            "negative_prompt": res.negative_prompt,
            "caption": target_panel.caption,
            "metadata": res.render_metadata,
        }
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
                rendered = _format_rendered_panel_dict(p, res, version=len(p.versions))
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

    @app.post("/api/projects/{project_id}/storyboard/panels/{panel_id}/external-render")
    def external_render_panel(
        project_id: str,
        panel_id: str,
        req: Optional[ExternalRenderRequest] = None,
    ):
        """Explicitly request external AI image render for a single storyboard panel."""
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

        model_name = req.model if req else None
        engine = HuggingFaceStoryboardProvider(
            asset_store=asset_store,
            model_name=model_name,
        )

        next_ver = len(target_panel.versions) + 1
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

    @app.post("/api/projects/{project_id}/storyboard/pages/{page_number}/external-render")
    def external_render_page(
        project_id: str,
        page_number: int,
        req: Optional[ExternalRenderRequest] = None,
    ):
        """Explicitly request external AI render for panels on a single page only."""
        proj = store.load_project(project_id)
        if not proj or not proj.shot_plan:
            raise HTTPException(status_code=404, detail="Project or shot plan not found")

        page_panels = [p for p in proj.shot_plan.panels if p.page_number == page_number]
        if not page_panels:
            raise HTTPException(status_code=404, detail=f"No panels found for page {page_number}")

        asset_store = StoryboardAssetStore(store.base_dir)
        bible = proj.visual_bible or asset_store.load_visual_bible(project_id)
        if not bible:
            bible = VisualBible.from_world(proj.world)
            proj.visual_bible = bible

        model_name = req.model if req else None
        engine = HuggingFaceStoryboardProvider(
            asset_store=asset_store,
            model_name=model_name,
        )

        updated_renders = list(proj.rendered_panels or [])
        for target_panel in page_panels:
            target_idx = proj.shot_plan.panels.index(target_panel)
            next_ver = len(target_panel.versions) + 1
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
            if target_idx < len(updated_renders):
                updated_renders[target_idx] = rendered_dict
            else:
                updated_renders.append(rendered_dict)

        proj.rendered_panels = updated_renders
        store.save_project(proj)

        return {
            "project_id": project_id,
            "page_number": page_number,
            "panels_rendered": len(page_panels),
            "shot_plan": proj.shot_plan.model_dump(mode="json"),
            "rendered_panels": updated_renders,
        }

    @app.get("/api/storyboard/provider-status")
    def get_storyboard_provider_status():
        """Expose image provider availability and diagnostic status without exposing secrets."""
        provider = get_image_provider()
        return provider.get_status()

    @app.get("/api/storyboard/capabilities")
    def get_storyboard_capabilities(probe: Optional[bool] = None):
        """Expose image provider capability report without exposing secrets."""
        provider = get_image_provider()
        caps = provider.get_capabilities(probe=probe) if hasattr(provider, "get_capabilities") else provider.get_status()
        health = provider.health_check(probe=probe) if hasattr(provider, "health_check") else (
            provider.engine.health_check(probe=probe) if hasattr(provider, "engine") else {}
        )
        if isinstance(caps, dict):
            caps["provider_health"] = health
            resolved_provider_status = (
                health.get("provider_status")
                or caps.get("provider_status")
                or ("CONNECTED" if caps.get("available") else "NOT_CONFIGURED")
            )
            caps["provider_status"] = resolved_provider_status
            resolved_model_status = (
                health.get("model_status")
                or caps.get("model_status")
                or caps.get("status")
                or ("AVAILABLE" if caps.get("available") else "UNAVAILABLE")
            )
            caps["model_generation_capability"] = resolved_model_status
            caps["model_status"] = resolved_model_status
        return caps

    @app.get("/api/storyboard/smoke-test")
    def storyboard_smoke_test(prompt: Optional[str] = None):
        """Run single-request on-demand still image smoke test."""
        from src.storyboard.on_demand_provider import OnDemandStoryboardProvider
        provider = OnDemandStoryboardProvider()
        return provider.smoke_test(prompt=prompt)

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

    @app.post("/api/storyboard/configure")
    def configure_storyboard_renderer(req: ConfigureRendererRequest):
        """Configure open-model generation runtime provider, URL, and model."""
        if req.provider:
            os.environ["STORYBOARD_RENDER_PROVIDER"] = req.provider
        if req.runtime_url is not None:
            os.environ["STORYBOARD_RUNTIME_URL"] = req.runtime_url
        if req.model is not None:
            os.environ["STORYBOARD_MODEL"] = req.model
            os.environ["ON_DEMAND_MODEL"] = req.model
        if req.api_key is not None:
            os.environ["ON_DEMAND_API_KEY"] = req.api_key
            os.environ["HF_TOKEN"] = req.api_key
            os.environ["HUGGINGFACE_API_KEY"] = req.api_key

        provider = get_image_provider(provider_type=req.provider)

        caps = provider.get_capabilities() if hasattr(provider, "get_capabilities") else {}
        status = provider.get_status()
        caps_dict = caps if isinstance(caps, dict) else (caps.to_dict() if hasattr(caps, "to_dict") else {})
        health_status = caps_dict.get("status", "UNCONFIGURED")

        return {
            "status": "configured",
            "runtime_status": health_status,
            "available": caps_dict.get("available", False),
            "status_message": caps_dict.get("status_message", ""),
            "provider": req.provider,
            "runtime_url": os.environ.get("STORYBOARD_RUNTIME_URL", ""),
            "model": os.environ.get("STORYBOARD_MODEL", ""),
            "provider_status": status,
            "capabilities": caps_dict,
        }


    @app.get("/api/projects/{project_id}/storyboard/panels/{panel_id}/control-bundle")
    def get_panel_control_bundle(project_id: str, panel_id: str):
        """Expose structural guidance maps (pose, edge, depth, composition) for developer/inspector view."""
        proj = store.load_project(project_id)
        if not proj or not proj.shot_plan:
            raise HTTPException(status_code=404, detail="Project or shot plan not found")
        panel = next((p for p in proj.shot_plan.panels if p.id == panel_id or p.panel_id == panel_id), None)
        if not panel:
            raise HTTPException(status_code=404, detail=f"Panel '{panel_id}' not found")

        asset_store = StoryboardAssetStore(store.base_dir)
        previs_renderer = PrevisControlRenderer(asset_store=asset_store)
        bundle = previs_renderer.generate_control_bundle(panel, bible=proj.visual_bible)
        return {
            "panel_id": panel_id,
            "control_bundle": bundle.to_dict(),
            "previs_svg": bundle.previs_svg,
        }

    @app.get("/api/projects/{project_id}/storyboard/continuity")
    def get_project_continuity(project_id: str):
        """Expose Character, Location, and Prop continuity packs for sequence consistency."""
        proj = store.load_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        bible = proj.visual_bible
        char_packs, loc_packs, prop_packs = _build_continuity_context(proj.world, bible)
        return {
            "characters": {k: v.model_dump(mode="json") for k, v in char_packs.items()},
            "locations": {k: v.model_dump(mode="json") for k, v in loc_packs.items()},
            "props": {k: v.model_dump(mode="json") for k, v in prop_packs.items()},
        }

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
                if proj.story_outline or proj.scenes:
                    syn = SynopsisGenerator().generate_synopsis(
                        proj.story_outline,
                        proj.world,
                        proj.selection,
                        scenes=proj.scenes,
                        screenplay=proj.screenplay,
                    )
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
