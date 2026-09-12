"""Synopsis generator for D3 Story Lab narrative pipeline.

Produces:
1. One short logline
2. One paragraph summary
3. One full episode synopsis
Grounded in completed dramatic outline and simulation events.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.narrative.completion import StoryOutline
from src.domain.world import WorldState
from src.narrative.observer import NarrativeEventSelection


class StorySynopsis(BaseModel):
    """Complete synopsis package for an episode."""
    model_config = ConfigDict(frozen=True)

    title: str
    logline: str = Field(..., description="One punchy sentence summarizing protagonist, stakes, and conflict")
    paragraph_summary: str = Field(..., description="One coherent paragraph summarizing the complete episode arc")
    full_synopsis: str = Field(..., description="Multi-paragraph comprehensive episode breakdown")
    dramatic_question: str
    genre: str
    tone: str
    target_duration_minutes: int = 20
    acts: Dict[str, str] = Field(default_factory=dict)


class SynopsisGenerator:
    """Generates three-tier synopsis grounded in story outline and simulation events."""

    def generate_synopsis(
        self,
        outline: StoryOutline,
        world: Optional[WorldState] = None,
        selection: Optional[NarrativeEventSelection] = None,
    ) -> StorySynopsis:
        """Produce logline, paragraph summary, and full synopsis."""
        char_names = [c.name for c in world.characters.values()] if world and world.characters else ["the protagonist", "the counter-agent"]
        actors_str = " and ".join(char_names[:2])

        # 1. Logline: concise, active, stakes-driven
        logline = (
            f"When {actors_str} clash over hidden motives within an isolated sanctuary, "
            f"a mounting series of external crises forces an agonizing choice between survival and the truth."
        )

        # 2. Paragraph Summary
        paragraph_summary = (
            f"In this {outline.target_duration_minutes}-minute episode of '{outline.episode_title}', {actors_str} "
            f"find themselves locked in a battle of wits and secrets. "
            f"{outline.act_structure.get('act_1', 'The encounter begins with deep suspicion.')} "
            f"As tensions escalate and the Director injects critical environmental interventions, "
            f"{outline.act_structure.get('act_2', 'a shocking revelation shatters their initial assumptions.')} "
            f"Ultimately, {outline.resolution.lower().rstrip('.')}."
        )

        # 3. Full Synopsis (Multi-paragraph)
        act1_desc = outline.act_structure.get("act_1", "The opening act establishes the initial situation.")
        act2_desc = outline.act_structure.get("act_2", "The second act escalates conflict through investigation.")
        act3_desc = outline.act_structure.get("act_3", "The final act culminates in an explosive confrontation.")

        # Ground with observed events if available
        events_grounding = ""
        if selection and selection.filtered_beats:
            beat_summaries = [b.summary for b in selection.filtered_beats[:4]]
            events_grounding = " Key simulation moments: " + "; ".join(beat_summaries) + "."

        full_synopsis = (
            f"EPISODE OVERVIEW: {outline.episode_title}\n\n"
            f"PREMISE & STAKES:\n{outline.premise}\n"
            f"Core Dramatic Question: {outline.dramatic_question}\n\n"
            f"ACT I - THE INCITING INCIDENT:\n{act1_desc}\n\n"
            f"ACT II - THE ESCALATION & MIDPOINT:\n{act2_desc}{events_grounding}\n\n"
            f"ACT III - THE CLIMAX & FALLOUT:\n{act3_desc}\n\n"
            f"RESOLUTION:\n{outline.resolution}"
        )

        return StorySynopsis(
            title=outline.episode_title,
            logline=logline,
            paragraph_summary=paragraph_summary,
            full_synopsis=full_synopsis,
            dramatic_question=outline.dramatic_question,
            genre=outline.genre,
            tone=outline.tone,
            target_duration_minutes=outline.target_duration_minutes,
            acts=outline.act_structure,
        )
