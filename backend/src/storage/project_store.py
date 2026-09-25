"""Project storage and persistence layer for D3 Story Lab."""

from __future__ import annotations
import os
import json
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.domain.world import WorldState
from src.domain.event import EventLog
from src.generator.schemas import WorldInitializationPlan
from src.narrative.observer import NarrativeEventSelection
from src.narrative.fountain import ScreenplayDocument
from src.narrative.completion import StoryOutline
from src.narrative.synopsis import StorySynopsis, sanitize_narrative_text
from src.storyboard.models import ShotPlan
from src.storyboard.visual_bible import VisualBible
from src.domain.story_structure import (
    StoryBlueprint,
    SceneData,
    CausalContinuitySummary,
    CharacterArcReport,
)
from src.domain.character_creation import CharacterInput, CharacterProfileDraft
from src.domain.conflict import ConflictGraph


class ProjectStorageError(Exception):
    """Base exception for project persistence errors."""
    pass


class ProjectCorruptedError(ProjectStorageError):
    """Raised when a project file cannot be decoded or fails schema validation."""
    pass


class ProjectMetadata(BaseModel):
    """Metadata describing a saved project."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    schema_version: int = 2
    id: str
    title: str
    seed_prompt: str
    input_type: Optional[str] = "beginning"
    target_duration_minutes: int = 20
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_tick: int = 0
    total_events: int = 0
    total_scenes: int = 0
    total_panels: int = 0
    story_structure: Optional[str] = None


class ProjectData(BaseModel):
    """Full snapshot of a project including world state, outline, screenplay, and storyboard."""
    model_config = ConfigDict(extra="ignore")

    schema_version: int = 2
    metadata: ProjectMetadata
    plan: Optional[WorldInitializationPlan] = None
    world: WorldState
    event_log: Optional[EventLog] = None
    selection: Optional[NarrativeEventSelection] = None
    screenplay: Optional[ScreenplayDocument] = None
    fountain_text: Optional[str] = None
    story_outline: Optional[StoryOutline] = None
    synopsis: Optional[StorySynopsis] = None
    shot_plan: Optional[ShotPlan] = None
    rendered_panels: Optional[List[Dict[str, Any]]] = None
    visual_bible: Optional[VisualBible] = None
    screenplay_quality: Optional[Dict[str, Any]] = None
    storyboard_quality: Optional[Dict[str, Any]] = None
    story_structure: Optional[str] = None
    story_blueprint: Optional[StoryBlueprint] = None
    scenes: Optional[List[SceneData]] = None
    causal_summary: Optional[CausalContinuitySummary] = None
    character_arcs: Optional[Dict[str, CharacterArcReport]] = None
    character_inputs: Optional[Dict[str, CharacterInput]] = None
    character_drafts: Optional[Dict[str, CharacterProfileDraft]] = None
    conflict_graph: Optional[ConflictGraph] = None


class ProjectStore:
    """Manages persistent project storage on the filesystem as JSON."""

    _locks: Dict[str, threading.Lock] = {}
    _locks_guard: threading.Lock = threading.Lock()

    @classmethod
    def _get_lock_for_path(cls, path: Path) -> threading.Lock:
        """Get or create a mutex lock serialized per canonical file path."""
        key = str(path.resolve())
        with cls._locks_guard:
            if key not in cls._locks:
                cls._locks[key] = threading.Lock()
            return cls._locks[key]

    def __init__(self, base_dir: Optional[str | Path] = None):
        if base_dir is None:
            self.base_dir = Path("/workspaces/d3-story-lab/backend/data/projects")
        else:
            self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_project_path(self, project_id_or_path: str | Path) -> Path:
        p = Path(project_id_or_path)
        if p.is_file():
            return p
        if p.is_dir():
            return p / "project.json"
        
        # Check relative to base_dir
        as_bundle = self.base_dir / project_id_or_path / "project.json"
        if as_bundle.exists():
            return as_bundle
        return self.base_dir / f"{project_id_or_path}.json"

    @staticmethod
    def normalize_project_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize legacy project dictionary (v0/v1 without schema_version) to schema version 2."""
        if not isinstance(data, dict):
            return data

        # Ensure schema_version upgraded to current
        if "schema_version" not in data or data["schema_version"] < 2:
            data["schema_version"] = 2

        # Metadata migration
        meta = data.get("metadata")
        if isinstance(meta, dict):
            if "schema_version" not in meta or meta["schema_version"] < 2:
                meta["schema_version"] = 2
            if "input_type" not in meta or meta["input_type"] is None:
                meta["input_type"] = "beginning"
            if "total_panels" not in meta:
                meta["total_panels"] = len(data.get("shot_plan", {}).get("panels", [])) if isinstance(data.get("shot_plan"), dict) else 0
            if "story_structure" not in meta:
                meta["story_structure"] = data.get("story_structure")

        # World migration: ensure propositions and facts registries exist
        world = data.get("world")
        if isinstance(world, dict):
            if "propositions" not in world:
                world["propositions"] = {}
            if "facts" not in world:
                world["facts"] = {}

        # Safe defaults for optional fields
        for field in ("story_structure", "story_blueprint", "scenes", "causal_summary", "character_arcs", "event_log", "character_inputs", "character_drafts", "conflict_graph"):
            if field not in data:
                data[field] = None

        # Sanitize legacy synopsis fields if present
        syn = data.get("synopsis")
        if isinstance(syn, dict):
            for k in ("logline", "paragraph_summary", "full_synopsis", "dramatic_question"):
                if k in syn and isinstance(syn[k], str):
                    syn[k] = sanitize_narrative_text(syn[k])
            if "acts" in syn and isinstance(syn["acts"], dict):
                for ak, av in syn["acts"].items():
                    if isinstance(av, str):
                        syn["acts"][ak] = sanitize_narrative_text(av)

        return data

    def save_project(self, project: ProjectData) -> str:
        """Save project data atomically to disk with adjacent media directory."""
        path = self._get_project_path(project.metadata.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure media directory exists alongside project file
        media_dir = path.parent / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        total_p = len(project.shot_plan.panels) if project.shot_plan else 0

        # Update metadata stats
        chosen_structure = project.story_structure or (
            project.story_blueprint.primary_structure.value if project.story_blueprint else None
        )
        updated_meta = ProjectMetadata(
            schema_version=2,
            id=project.metadata.id,
            title=project.metadata.title,
            seed_prompt=project.metadata.seed_prompt,
            input_type=project.metadata.input_type or "beginning",
            target_duration_minutes=project.metadata.target_duration_minutes,
            created_at=project.metadata.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
            current_tick=project.world.current_tick,
            total_events=len(project.world.events),
            total_scenes=len(project.screenplay.scenes) if project.screenplay else 0,
            total_panels=total_p,
            story_structure=chosen_structure,
        )

        fountain_txt = project.fountain_text
        if project.screenplay and not fountain_txt:
            fountain_txt = project.screenplay.to_fountain()

        ev_log = project.event_log
        if ev_log is None and project.world and project.world.events:
            ev_log = EventLog(events=list(project.world.events.values()))

        project_to_save = ProjectData(
            schema_version=2,
            metadata=updated_meta,
            plan=project.plan,
            world=project.world,
            event_log=ev_log,
            selection=project.selection,
            screenplay=project.screenplay,
            fountain_text=fountain_txt,
            story_outline=project.story_outline,
            synopsis=project.synopsis,
            shot_plan=project.shot_plan,
            rendered_panels=project.rendered_panels,
            visual_bible=project.visual_bible,
            screenplay_quality=project.screenplay_quality,
            storyboard_quality=project.storyboard_quality,
            story_structure=chosen_structure,
            story_blueprint=project.story_blueprint,
            scenes=project.scenes,
            causal_summary=project.causal_summary,
            character_arcs=project.character_arcs,
            character_inputs=project.character_inputs,
            character_drafts=project.character_drafts,
            conflict_graph=project.conflict_graph,
        )

        data_dict = project_to_save.model_dump(mode="json")
        lock = self._get_lock_for_path(path)
        with lock:
            temp_path = path.parent / f"{path.stem}.{uuid.uuid4().hex}.tmp"
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data_dict, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, path)
            finally:
                if temp_path.exists():
                    try:
                        temp_path.unlink(missing_ok=True)
                    except OSError:
                        pass
        return project.metadata.id

    def save_project_bundle(self, project: ProjectData, bundle_dir: str | Path) -> Path:
        """Save a complete project bundle: project.json and media/ directory."""
        bundle_path = Path(bundle_dir)
        bundle_path.mkdir(parents=True, exist_ok=True)
        media_dir = bundle_path / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        json_path = bundle_path / "project.json"

        # Update metadata
        total_p = len(project.shot_plan.panels) if project.shot_plan else 0
        chosen_structure = project.story_structure or (
            project.story_blueprint.primary_structure.value if project.story_blueprint else None
        )
        updated_meta = ProjectMetadata(
            schema_version=2,
            id=project.metadata.id,
            title=project.metadata.title,
            seed_prompt=project.metadata.seed_prompt,
            input_type=project.metadata.input_type or "beginning",
            target_duration_minutes=project.metadata.target_duration_minutes,
            created_at=project.metadata.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
            current_tick=project.world.current_tick,
            total_events=len(project.world.events),
            total_scenes=len(project.screenplay.scenes) if project.screenplay else 0,
            total_panels=total_p,
            story_structure=chosen_structure,
        )

        fountain_txt = project.fountain_text
        if project.screenplay and not fountain_txt:
            fountain_txt = project.screenplay.to_fountain()

        ev_log = project.event_log
        if ev_log is None and project.world and project.world.events:
            ev_log = EventLog(events=list(project.world.events.values()))

        project_to_save = ProjectData(
            schema_version=2,
            metadata=updated_meta,
            plan=project.plan,
            world=project.world,
            event_log=ev_log,
            selection=project.selection,
            screenplay=project.screenplay,
            fountain_text=fountain_txt,
            story_outline=project.story_outline,
            synopsis=project.synopsis,
            shot_plan=project.shot_plan,
            rendered_panels=project.rendered_panels,
            visual_bible=project.visual_bible,
            screenplay_quality=project.screenplay_quality,
            storyboard_quality=project.storyboard_quality,
            story_structure=chosen_structure,
            story_blueprint=project.story_blueprint,
            scenes=project.scenes,
            causal_summary=project.causal_summary,
            character_arcs=project.character_arcs,
            character_inputs=project.character_inputs,
            character_drafts=project.character_drafts,
            conflict_graph=project.conflict_graph,
        )

        data_dict = project_to_save.model_dump(mode="json")
        lock = self._get_lock_for_path(json_path)
        with lock:
            temp_path = bundle_path / f"project.{uuid.uuid4().hex}.tmp"
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data_dict, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, json_path)
            finally:
                if temp_path.exists():
                    try:
                        temp_path.unlink(missing_ok=True)
                    except OSError:
                        pass
        return json_path

    def load_project(self, project_id_or_path: str | Path) -> Optional[ProjectData]:
        """Load project data from disk with backward compatibility migration."""
        path = self._get_project_path(project_id_or_path)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ProjectCorruptedError(
                f"Project file at '{path}' contains corrupted or malformed JSON: {exc}"
            ) from exc
        except Exception as exc:
            raise ProjectStorageError(
                f"Failed to read project file at '{path}': {exc}"
            ) from exc

        try:
            normalized = self.normalize_project_dict(data)
            return ProjectData.model_validate(normalized)
        except Exception as exc:
            raise ProjectCorruptedError(
                f"Project data at '{path}' failed validation: {exc}"
            ) from exc

    def list_projects(self) -> List[ProjectMetadata]:
        """List metadata for all saved projects."""
        projects: List[ProjectMetadata] = []
        for file in self.base_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "metadata" in data:
                        meta = data["metadata"]
                        if "schema_version" not in meta:
                            meta["schema_version"] = 2
                        if "input_type" not in meta or meta["input_type"] is None:
                            meta["input_type"] = "beginning"
                        projects.append(ProjectMetadata.model_validate(meta))
            except Exception:
                continue
        return sorted(projects, key=lambda p: p.updated_at, reverse=True)

    def delete_project(self, project_id: str) -> bool:
        """Delete project file from disk."""
        path = self._get_project_path(project_id)
        lock = self._get_lock_for_path(path)
        with lock:
            if path.exists():
                path.unlink()
                return True
            return False
