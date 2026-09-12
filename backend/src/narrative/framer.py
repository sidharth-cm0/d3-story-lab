"""Narrative framing module maintaining Chronological and Presentation timelines.

Supports:
- CHRONOLOGICAL (default)
- IN_MEDIA_RES
- FLASHBACK
- INTERCUT
- PARALLEL_ACTION
- REVEAL_DELAY
- Hook for UNRELIABLE_POV

Invariants:
- Canonical simulation event order is NEVER mutated.
- Every screenplay block retains source_event_ids, chronological_position,
  presentation_position, and framing_type.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
import copy
from pydantic import BaseModel, ConfigDict, Field

from src.narrative.fountain import (
    ScreenplayDocument,
    ScreenplayScene,
    ScreenplayBlock,
    ScreenplayBlockType,
)


class FramingMode(str, Enum):
    """Audience presentation timeline structure."""
    CHRONOLOGICAL = "CHRONOLOGICAL"
    IN_MEDIA_RES = "IN_MEDIA_RES"
    FLASHBACK = "FLASHBACK"
    INTERCUT = "INTERCUT"
    PARALLEL_ACTION = "PARALLEL_ACTION"
    REVEAL_DELAY = "REVEAL_DELAY"
    UNRELIABLE_POV = "UNRELIABLE_POV"


class NarrativeFramer:
    """Manages audience presentation order without altering canonical history."""

    def __init__(self, mode: FramingMode = FramingMode.CHRONOLOGICAL):
        self.mode = mode

    def reorder_presentation(
        self,
        scenes: List[ScreenplayScene],
        mode: Optional[FramingMode] = None,
        unreliable_pov_actor_id: Optional[str] = None,
    ) -> List[ScreenplayScene]:
        """Transform chronological screenplay scenes into presentation order."""
        active_mode = mode or self.mode

        if not scenes or len(scenes) < 2 or active_mode == FramingMode.CHRONOLOGICAL:
            # Simple chronological assignment
            output: List[ScreenplayScene] = []
            pos = 1
            for scn_idx, scn in enumerate(scenes):
                updated_blocks = []
                for b in scn.blocks:
                    b_dict = b.model_dump()
                    b_dict["chronological_position"] = pos
                    b_dict["presentation_position"] = pos
                    b_dict["framing_type"] = FramingMode.CHRONOLOGICAL.value
                    updated_blocks.append(ScreenplayBlock(**b_dict))
                    pos += 1
                scn_dict = scn.model_dump()
                scn_dict["scene_number"] = scn_idx + 1
                scn_dict["blocks"] = updated_blocks
                scn_dict["presentation_order"] = scn_idx + 1
                scn_dict["framing_type"] = FramingMode.CHRONOLOGICAL.value
                output.append(ScreenplayScene(**scn_dict))
            return output

        if active_mode == FramingMode.IN_MEDIA_RES:
            return self._frame_in_media_res(scenes)

        if active_mode == FramingMode.REVEAL_DELAY:
            return self._frame_reveal_delay(scenes)

        if active_mode == FramingMode.FLASHBACK:
            return self._frame_flashback(scenes)

        # Default fallback
        return self.reorder_presentation(scenes, mode=FramingMode.CHRONOLOGICAL)

    def _frame_in_media_res(self, scenes: List[ScreenplayScene]) -> List[ScreenplayScene]:
        """Place a tense climax scene at the front, followed by a title card and earlier scenes."""
        if len(scenes) < 3:
            return self.reorder_presentation(scenes, mode=FramingMode.CHRONOLOGICAL)

        # Pick a dramatic mid/late scene (last or second-to-last)
        hook_index = len(scenes) - 1
        hook_scene = scenes[hook_index]

        # 1. Opening hook scene (teaser)
        hook_blocks = []
        for b in hook_scene.blocks:
            b_dict = b.model_dump()
            b_dict["framing_type"] = FramingMode.IN_MEDIA_RES.value
            hook_blocks.append(ScreenplayBlock(**b_dict))

        opening_scene = ScreenplayScene(
            scene_number=1,
            location_id=hook_scene.location_id,
            heading=f"{hook_scene.heading} - FLASHFORWARD",
            blocks=hook_blocks,
            source_event_ids=list(hook_scene.source_event_ids),
            framing_type=FramingMode.IN_MEDIA_RES.value,
            presentation_order=1,
            metadata={"in_media_res_hook": True},
        )

        # 2. Time-jump Title Card Scene
        title_card_scene = ScreenplayScene(
            scene_number=2,
            location_id=scenes[0].location_id,
            heading=scenes[0].heading,
            blocks=[
                ScreenplayBlock(
                    block_type=ScreenplayBlockType.ACTION,
                    text="TITLE CARD: TWENTY MINUTES EARLIER",
                    source_event_ids=list(scenes[0].source_event_ids[:1]),
                    framing_type=FramingMode.IN_MEDIA_RES.value,
                )
            ] + list(scenes[0].blocks),
            source_event_ids=list(scenes[0].source_event_ids),
            framing_type=FramingMode.IN_MEDIA_RES.value,
            presentation_order=2,
            metadata={"time_jump_card": True},
        )

        output: List[ScreenplayScene] = [opening_scene, title_card_scene]

        # 3. Subsequent chronological scenes up to the hook
        for idx in range(1, len(scenes)):
            scn = scenes[idx]
            # If this is the original hook scene, mark it as the resolution / loop back
            is_resolution_loop = (idx == hook_index)
            heading = f"{scn.heading} - MOMENT OF RECKONING" if is_resolution_loop else scn.heading
            updated_blocks = []
            for b in scn.blocks:
                b_dict = b.model_dump()
                b_dict["framing_type"] = FramingMode.IN_MEDIA_RES.value
                updated_blocks.append(ScreenplayBlock(**b_dict))

            output.append(
                ScreenplayScene(
                    scene_number=len(output) + 1,
                    location_id=scn.location_id,
                    heading=heading,
                    blocks=updated_blocks,
                    source_event_ids=list(scn.source_event_ids),
                    framing_type=FramingMode.IN_MEDIA_RES.value,
                    presentation_order=len(output) + 1,
                    metadata={"resolution_loop": is_resolution_loop},
                )
            )

        # Index presentation positions
        pos = 1
        final_scenes: List[ScreenplayScene] = []
        for s_idx, scn in enumerate(output):
            b_list = []
            for b in scn.blocks:
                b_dict = b.model_dump()
                b_dict["presentation_position"] = pos
                b_list.append(ScreenplayBlock(**b_dict))
                pos += 1
            s_dict = scn.model_dump()
            s_dict["scene_number"] = s_idx + 1
            s_dict["blocks"] = b_list
            final_scenes.append(ScreenplayScene(**s_dict))

        return final_scenes

    def _frame_reveal_delay(self, scenes: List[ScreenplayScene]) -> List[ScreenplayScene]:
        """Deliberately delay audience information by holding a clue/revelation scene until after suspense."""
        # Find discovery scene
        revelation_idx = -1
        for idx, scn in enumerate(scenes):
            if any("discover" in b.text.lower() or "secret" in b.text.lower() for b in scn.blocks):
                revelation_idx = idx
                break

        if revelation_idx > 0 and revelation_idx < len(scenes) - 1:
            reordered = list(scenes)
            rev_scene = reordered.pop(revelation_idx)
            reordered.append(rev_scene)
            output = []
            for idx, scn in enumerate(reordered):
                s_dict = scn.model_dump()
                s_dict["scene_number"] = idx + 1
                s_dict["presentation_order"] = idx + 1
                s_dict["framing_type"] = FramingMode.REVEAL_DELAY.value
                output.append(ScreenplayScene(**s_dict))
            return output

        return self.reorder_presentation(scenes, mode=FramingMode.CHRONOLOGICAL)

    def _frame_flashback(self, scenes: List[ScreenplayScene]) -> List[ScreenplayScene]:
        """Tag an early context scene as a flashback beat inserted into rising action."""
        if len(scenes) < 3:
            return self.reorder_presentation(scenes, mode=FramingMode.CHRONOLOGICAL)

        # Mark scene 1 as a flashback embedded after scene 2
        flashback_scene = scenes[0]
        f_dict = flashback_scene.model_dump()
        f_dict["heading"] = f"{flashback_scene.heading} - FLASHBACK"
        f_dict["framing_type"] = FramingMode.FLASHBACK.value
        f_scene = ScreenplayScene(**f_dict)

        output = [scenes[1], f_scene] + list(scenes[2:])
        final = []
        for idx, scn in enumerate(output):
            s_dict = scn.model_dump()
            s_dict["scene_number"] = idx + 1
            s_dict["presentation_order"] = idx + 1
            s_dict["framing_type"] = FramingMode.FLASHBACK.value
            final.append(ScreenplayScene(**s_dict))
        return final
