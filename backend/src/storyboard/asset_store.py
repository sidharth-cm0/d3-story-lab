"""Secure Asset Store for Storyboard Artwork, Visual Bibles, and Reference Assets.

Guarantees strict path traversal protection, organized project folder hierarchies,
and metadata persistence for storyboard versions.
"""

from __future__ import annotations
import os
import re
import mimetypes
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from src.storyboard.visual_bible import VisualBible


ALLOWED_CATEGORIES = {"panels", "characters", "locations", "objects", "exports", "controls", "references", "previs"}
SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")
SAFE_FILENAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+\.(png|jpg|jpeg|webp|svg|json)$")


class StoryboardAssetStore:
    """Manages disk storage and retrieval of storyboard image files and visual bibles."""

    def __init__(self, base_dir: Optional[str | Path] = None):
        if base_dir is None:
            self.base_dir = Path("/workspaces/d3-story-lab/backend/data/projects")
        else:
            self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_path(self, project_id: str, category: str, filename: str) -> Path:
        """Validate components and ensure resolved path stays strictly within project sandbox."""
        if not SAFE_ID_REGEX.match(project_id):
            raise ValueError(f"Invalid project_id '{project_id}': must contain only alphanumeric, hyphen, underscore.")
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(f"Invalid category '{category}': must be one of {ALLOWED_CATEGORIES}.")
        if not SAFE_FILENAME_REGEX.match(filename) or ".." in filename:
            raise ValueError(f"Invalid filename '{filename}': illegal characters or unsafe extension.")

        project_dir = (self.base_dir / project_id / "storyboard" / category).resolve()
        target_path = (project_dir / filename).resolve()

        # Strict containment check
        if not str(target_path).startswith(str(project_dir)):
            raise PermissionError("Path traversal detected.")

        return target_path

    def get_asset_url(self, project_id: str, category: str, filename: str) -> str:
        """Return the API serving URL for a given asset."""
        return f"/api/projects/{project_id}/storyboard/assets/{category}/{filename}"

    def save_asset(
        self,
        project_id: str,
        category: str,
        filename: str,
        content: bytes | str,
    ) -> str:
        """Write asset content (image bytes or SVG string) safely to disk."""
        target_path = self._sanitize_path(project_id, category, filename)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, str):
            target_path.write_text(content, encoding="utf-8")
        else:
            target_path.write_bytes(content)

        return self.get_asset_url(project_id, category, filename)

    def load_asset(
        self,
        project_id: str,
        category: str,
        filename: str,
    ) -> Tuple[bytes, str]:
        """Read asset content from disk and determine its MIME type."""
        target_path = self._sanitize_path(project_id, category, filename)
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"Asset '{category}/{filename}' not found for project '{project_id}'.")

        data = target_path.read_bytes()
        mime_type, _ = mimetypes.guess_type(target_path.name)
        if not mime_type:
            if target_path.name.endswith(".svg"):
                mime_type = "image/svg+xml"
            elif target_path.name.endswith(".png"):
                mime_type = "image/png"
            elif target_path.name.endswith(".jpg") or target_path.name.endswith(".jpeg"):
                mime_type = "image/jpeg"
            elif target_path.name.endswith(".json"):
                mime_type = "application/json"
            else:
                mime_type = "application/octet-stream"

        return data, mime_type

    def save_visual_bible(self, project_id: str, bible: VisualBible) -> str:
        """Persist visual bible as JSON within the project directory."""
        if not SAFE_ID_REGEX.match(project_id):
            raise ValueError(f"Invalid project_id '{project_id}'.")
        target_file = (self.base_dir / project_id / "storyboard" / "visual_bible.json").resolve()
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(bible.model_dump_json(indent=2), encoding="utf-8")
        return str(target_file)

    def load_visual_bible(self, project_id: str) -> Optional[VisualBible]:
        """Load visual bible from disk if present."""
        if not SAFE_ID_REGEX.match(project_id):
            return None
        target_file = (self.base_dir / project_id / "storyboard" / "visual_bible.json").resolve()
        if not target_file.exists():
            return None
        try:
            return VisualBible.model_validate_json(target_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_panel_record(self, project_id: str, panel_id: str, version: int, record_data: Dict[str, Any]) -> str:
        """Persist metadata record for a generated storyboard panel version."""
        import json
        filename = f"{panel_id}_v{version}_record.json"
        content = json.dumps(record_data, indent=2)
        return self.save_asset(project_id, "panels", filename, content)

    def load_panel_record(self, project_id: str, panel_id: str, version: int) -> Optional[Dict[str, Any]]:
        """Load metadata record for a generated panel version."""
        import json
        filename = f"{panel_id}_v{version}_record.json"
        try:
            raw_bytes, _ = self.load_asset(project_id, "panels", filename)
            return json.loads(raw_bytes.decode("utf-8"))
        except Exception:
            return None
