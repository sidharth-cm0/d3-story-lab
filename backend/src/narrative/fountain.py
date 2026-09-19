"""Fountain screenplay data models and formatter."""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional, Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScreenplayBlockType(str, Enum):
    """Fountain screenplay element types."""
    SCENE_HEADING = "scene_heading"
    ACTION = "action"
    CHARACTER = "character"
    PARENTHETICAL = "parenthetical"
    DIALOGUE = "dialogue"
    TRANSITION = "transition"


class ScreenplayBlock(BaseModel):
    """An individual element of a screenplay linked to underlying simulation events."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    # Prompt 2 Canonical Interface
    block_id: str = Field(default_factory=lambda: f"blk_{uuid.uuid4().hex[:8]}")
    scene_id: str = ""
    source_event_ids: List[str] = Field(default_factory=list)
    element_type: Literal["SLUGLINE", "ACTION", "CHARACTER_CUE", "DIALOGUE", "PARENTHETICAL", "TRANSITION"] = "ACTION"
    content: str = ""
    character_id: Optional[str] = None
    presentation_position: int = 1

    # Backward-compatible mirrored attributes
    id: str = Field(default_factory=lambda: f"blk_{uuid.uuid4().hex[:8]}")
    block_type: ScreenplayBlockType = ScreenplayBlockType.ACTION
    text: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chronological_position: Optional[int] = None
    framing_type: str = "CHRONOLOGICAL"
    derived_from_event_id: Optional[str] = None
    derived_from_actor_state_ids: List[str] = Field(default_factory=list)
    cue_type: Optional[str] = None
    is_performance_cue: bool = False

    @model_validator(mode="before")
    @classmethod
    def sync_block_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. ID synchronization: id <-> block_id
            b_id = data.get("block_id") or data.get("id") or f"blk_{uuid.uuid4().hex[:8]}"
            data["id"] = b_id
            data["block_id"] = b_id

            # 2. Text / Content synchronization: text <-> content
            text_val = data.get("content") if "content" in data and data["content"] is not None else data.get("text", "")
            data["text"] = str(text_val)
            data["content"] = str(text_val)

            # 3. Element type / Block type synchronization
            elem_to_block = {
                "SLUGLINE": ScreenplayBlockType.SCENE_HEADING,
                "ACTION": ScreenplayBlockType.ACTION,
                "CHARACTER_CUE": ScreenplayBlockType.CHARACTER,
                "DIALOGUE": ScreenplayBlockType.DIALOGUE,
                "PARENTHETICAL": ScreenplayBlockType.PARENTHETICAL,
                "TRANSITION": ScreenplayBlockType.TRANSITION,
            }
            block_to_elem = {
                ScreenplayBlockType.SCENE_HEADING: "SLUGLINE",
                ScreenplayBlockType.ACTION: "ACTION",
                ScreenplayBlockType.CHARACTER: "CHARACTER_CUE",
                ScreenplayBlockType.DIALOGUE: "DIALOGUE",
                ScreenplayBlockType.PARENTHETICAL: "PARENTHETICAL",
                ScreenplayBlockType.TRANSITION: "TRANSITION",
            }
            if "element_type" in data and data["element_type"]:
                el = data["element_type"]
                if el in elem_to_block:
                    data["block_type"] = elem_to_block[el]
            elif "block_type" in data and data["block_type"]:
                bt = data["block_type"]
                if isinstance(bt, str):
                    for b_enum in ScreenplayBlockType:
                        if b_enum.value == bt or b_enum.name == bt:
                            bt = b_enum
                            break
                if bt in block_to_elem:
                    data["element_type"] = block_to_elem[bt]
                elif str(bt).upper() in elem_to_block:
                    data["element_type"] = str(bt).upper()
                    data["block_type"] = elem_to_block[str(bt).upper()]

            # 4. Positions: presentation_position <-> chronological_position
            pos = data.get("presentation_position") or data.get("chronological_position") or 1
            data["presentation_position"] = int(pos)
            data["chronological_position"] = int(pos)
        return data


class ScreenplayScene(BaseModel):
    """A scene containing ordered screenplay blocks."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    scene_number: int = Field(ge=1)
    location_id: str
    heading: str
    blocks: List[ScreenplayBlock] = Field(default_factory=list)
    source_event_ids: List[str] = Field(default_factory=list)
    framing_type: str = "CHRONOLOGICAL"
    presentation_order: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScreenplayDocument(BaseModel):
    """Complete Fountain-compatible screenplay with event provenance."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = "UNTITLED SIMULATION"
    credit: str = "Generated by"
    author: str = "D3 Story Lab"
    draft_date: str = "2026"
    scenes: List[ScreenplayScene] = Field(default_factory=list)

    def to_fountain(self) -> str:
        """Render the screenplay document into canonical Fountain text format."""
        lines: List[str] = []

        # Title Page
        lines.append(f"Title: {self.title}")
        lines.append(f"Credit: {self.credit}")
        lines.append(f"Author: {self.author}")
        lines.append(f"Draft date: {self.draft_date}\n\n")

        for scene in self.scenes:
            # Scene Heading (e.g. INT. HOTEL PENTHOUSE - NIGHT)
            lines.append(scene.heading.upper())
            lines.append("")

            for idx, block in enumerate(scene.blocks):
                if block.block_type == ScreenplayBlockType.SCENE_HEADING:
                    # Avoid repeating the scene heading if the first block is the same slugline
                    if idx == 0 and block.text.strip().upper() == scene.heading.strip().upper():
                        continue
                    lines.append(block.text.upper())
                    lines.append("")
                elif block.block_type == ScreenplayBlockType.ACTION:
                    lines.append(block.text)
                    lines.append("")
                elif block.block_type == ScreenplayBlockType.CHARACTER:
                    lines.append(block.text.upper())
                elif block.block_type == ScreenplayBlockType.PARENTHETICAL:
                    lines.append(f"({block.text.strip('()')})")
                elif block.block_type == ScreenplayBlockType.DIALOGUE:
                    lines.append(block.text)
                    lines.append("")
                elif block.block_type == ScreenplayBlockType.TRANSITION:
                    lines.append(f"{block.text.upper()}:")
                    lines.append("")

        return "\n".join(lines).strip() + "\n"

    def get_provenance_map(self) -> Dict[str, List[str]]:
        """Map each block ID to its underlying simulation event IDs."""
        prov: Dict[str, List[str]] = {}
        for scene in self.scenes:
            for block in scene.blocks:
                prov[block.id] = block.source_event_ids
        return prov
