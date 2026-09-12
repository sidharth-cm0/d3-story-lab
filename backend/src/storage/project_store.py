"""Project storage and persistence layer for D3 Story Lab."""

from __future__ import annotations
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from src.domain.world import WorldState
from src.generator.schemas import WorldInitializationPlan
from src.narrative.observer import NarrativeEventSelection
from src.narrative.fountain import ScreenplayDocument
from src.narrative.completion import StoryOutline
from src.narrative.synopsis import StorySynopsis
from src.storyboard.models import ShotPlan
from src.storyboard.visual_bible import VisualBible


class ProjectMetadata(BaseModel):
    """Metadata describing a saved project."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    title: str
    seed_prompt: str
    input_type: Optional[str] = None
    target_duration_minutes: int = 20
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_tick: int = 0
    total_events: int = 0
    total_scenes: int = 0
    total_panels: int = 0


class ProjectData(BaseModel):
    """Full snapshot of a project including world state, outline, screenplay, and storyboard."""
    model_config = ConfigDict(extra="ignore")

    metadata: ProjectMetadata
    plan: Optional[WorldInitializationPlan] = None
    world: WorldState
    selection: Optional[NarrativeEventSelection] = None
    screenplay: Optional[ScreenplayDocument] = None
    fountain_text: Optional[str] = None
    story_outline: Optional[StoryOutline] = None
    synopsis: Optional[StorySynopsis] = None
    shot_plan: Optional[ShotPlan] = None
    rendered_panels: Optional[List[Dict[str, Any]]] = None
    visual_bible: Optional[VisualBible] = None


class ProjectStore:
    """Manages persistent project storage on the filesystem as JSON."""

    def __init__(self, base_dir: Optional[str | Path] = None):
        if base_dir is None:
            self.base_dir = Path("/workspaces/d3-story-lab/backend/data/projects")
        else:
            self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_project_path(self, project_id: str) -> Path:
        return self.base_dir / f"{project_id}.json"

    def save_project(self, project: ProjectData) -> str:
        """Save project data atomically to disk."""
        path = self._get_project_path(project.metadata.id)
        total_p = len(project.shot_plan.panels) if project.shot_plan else 0

        # Update metadata stats
        updated_meta = ProjectMetadata(
            id=project.metadata.id,
            title=project.metadata.title,
            seed_prompt=project.metadata.seed_prompt,
            input_type=project.metadata.input_type,
            target_duration_minutes=project.metadata.target_duration_minutes,
            created_at=project.metadata.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
            current_tick=project.world.current_tick,
            total_events=len(project.world.events),
            total_scenes=len(project.screenplay.scenes) if project.screenplay else 0,
            total_panels=total_p,
        )

        fountain_txt = project.fountain_text
        if project.screenplay and not fountain_txt:
            fountain_txt = project.screenplay.to_fountain()

        project_to_save = ProjectData(
            metadata=updated_meta,
            plan=project.plan,
            world=project.world,
            selection=project.selection,
            screenplay=project.screenplay,
            fountain_text=fountain_txt,
            story_outline=project.story_outline,
            synopsis=project.synopsis,
            shot_plan=project.shot_plan,
            rendered_panels=project.rendered_panels,
        )

        data_dict = project_to_save.model_dump(mode="json")
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, indent=2)
        os.replace(temp_path, path)
        return project.metadata.id

    def load_project(self, project_id: str) -> Optional[ProjectData]:
        """Load project data from disk."""
        path = self._get_project_path(project_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ProjectData.model_validate(data)

    def list_projects(self) -> List[ProjectMetadata]:
        """List metadata for all saved projects."""
        projects: List[ProjectMetadata] = []
        for file in self.base_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "metadata" in data:
                        projects.append(ProjectMetadata.model_validate(data["metadata"]))
            except Exception:
                continue
        return sorted(projects, key=lambda p: p.updated_at, reverse=True)

    def delete_project(self, project_id: str) -> bool:
        """Delete project file from disk."""
        path = self._get_project_path(project_id)
        if path.exists():
            path.unlink()
            return True
        return False
