"""Loader and schema validator for Story Structures and Compatibility Matrix."""
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml
from pydantic import ValidationError

from .models import StoryStructureDefinition

DEFAULT_STRUCTURES_DIR = Path(__file__).parent / "structures"
DEFAULT_COMPATIBILITY_FILE = Path(__file__).parent / "compatibility.yaml"


class StructureLoadError(RuntimeError):
    """Raised when story structure definitions are malformed or fail schema validation."""
    pass


def load_structure_from_yaml(yaml_path: Path | str) -> StoryStructureDefinition:
    """Load and validate a single YAML structure definition.
    
    Fails loudly with StructureLoadError if the YAML is unparseable or fails schema validation.
    """
    path = Path(yaml_path)
    if not path.is_file():
        raise StructureLoadError(f"Structure definition file not found: {path}")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise StructureLoadError(f"Malformed YAML in {path.name}: {e}") from e

    if not isinstance(raw_data, dict):
        raise StructureLoadError(f"Invalid structure YAML root (expected mapping) in {path.name}")

    try:
        return StoryStructureDefinition.model_validate(raw_data)
    except ValidationError as e:
        raise StructureLoadError(f"Schema validation failed for {path.name}: {e}") from e


def load_all_structures(structures_dir: Optional[Path | str] = None) -> Dict[str, StoryStructureDefinition]:
    """Load all structure definitions from a directory.
    
    Adding a structure requires zero code changes: dropping a valid YAML file into this
    directory immediately makes it available.
    """
    s_dir = Path(structures_dir) if structures_dir else DEFAULT_STRUCTURES_DIR
    if not s_dir.is_dir():
        raise StructureLoadError(f"Structures directory not found: {s_dir}")

    definitions: Dict[str, StoryStructureDefinition] = {}
    for yml_file in sorted(s_dir.glob("*.yaml")):
        defn = load_structure_from_yaml(yml_file)
        definitions[defn.id] = defn
    for yml_file in sorted(s_dir.glob("*.yml")):
        if yml_file.stem not in definitions:
            defn = load_structure_from_yaml(yml_file)
            definitions[defn.id] = defn

    if not definitions:
        raise StructureLoadError(f"No valid structure definitions found in {s_dir}")

    return definitions


# Global registry cached at import time, fails loudly at app start if malformed
try:
    STRUCTURE_REGISTRY: Dict[str, StoryStructureDefinition] = load_all_structures()
except Exception as err:
    # We allow running without failing if running in an isolated environment that explicitly handles it,
    # but by default it validates at startup
    STRUCTURE_REGISTRY = {}
    _STARTUP_ERROR = err
else:
    _STARTUP_ERROR = None


def get_structure_registry(force_reload: bool = False) -> Dict[str, StoryStructureDefinition]:
    """Get the active structure registry, optionally reloading from disk."""
    global STRUCTURE_REGISTRY, _STARTUP_ERROR
    if _STARTUP_ERROR and not force_reload:
        raise _STARTUP_ERROR
    if force_reload or not STRUCTURE_REGISTRY:
        STRUCTURE_REGISTRY = load_all_structures()
        _STARTUP_ERROR = None
    return STRUCTURE_REGISTRY
