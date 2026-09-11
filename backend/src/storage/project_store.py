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


class ProjectMetadata(BaseModel):
    """Metadata describing a saved project."""
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    seed_prompt: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_tick: int = 0
    total_events: int = 0
    total_scenes: int = 0


class ProjectData(BaseModel):
    """Full snapshot of a project including world state, simulation, beats, and screenplay."""
    metadata: ProjectMetadata
    plan: Optional[WorldInitializationPlan] = None
    world: WorldState
    selection: Optional[NarrativeEventSelection] = None
    screenplay: Optional[ScreenplayDocument] = None
    fountain_text: Optional[str] = None


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
        # Update metadata stats
        updated_meta = ProjectMetadata(
            id=project.metadata.id,
            title=project.metadata.title,
            seed_prompt=project.metadata.seed_prompt,
            created_at=project.metadata.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
            current_tick=project.world.current_tick,
            total_events=len(project.world.events),
            total_scenes=len(project.screenplay.scenes) if project.screenplay else 0,
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
        for p in self.base_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "metadata" in data:
                    projects.append(ProjectMetadata.model_validate(data["metadata"]))
            except Exception:
                continue
        return sorted(projects, key=lambda x: x.updated_at, reverse=True)

    def delete_project(self, project_id: str) -> bool:
        """Delete a project file."""
        path = self._get_project_path(project_id)
        if path.exists():
            path.unlink()
            return True
        return False
