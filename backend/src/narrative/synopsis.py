"""[LEGACY / MIGRATED] Synopsis generator for D3 Story Lab narrative pipeline.

Produces:
1. One short logline
2. One paragraph summary
3. One full episode synopsis
Grounded in completed dramatic outline, scenes, and simulation events.
Free of internal architecture vocabulary.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
import re
from pydantic import BaseModel, ConfigDict, Field

from src.narrative.completion import StoryOutline
from src.domain.world import WorldState
from src.narrative.observer import NarrativeEventSelection
from src.narrative.fountain import ScreenplayDocument


def sanitize_narrative_text(text: str) -> str:
    """Purge internal engine and architecture vocabulary from narrative text."""
    replacements = [
        (r"\bthe Director injects critical environmental interventions,?\b", "unforeseen environmental obstacles arise,"),
        (r"\bDirector injects critical environmental interventions,?\b", "unforeseen environmental obstacles arise,"),
        (r"\bDirector interventions?\b", "environmental complications"),
        (r"\bDirector triggers?\b", "unforeseen events trigger"),
        (r"\bsecond sovereign actor\b", "second operative"),
        (r"\bsovereign actors?\b", "operatives"),
        (r"\bSufficiency Gate\b", "narrative milestone"),
        (r"\bBeatPressure\b", "dramatic tension"),
        (r"\bsimulation ticks?\b", "moments"),
        (r"\bActionProposal\b", "action"),
        (r"\bStateSnapshotDiffer\b", "state difference"),
    ]
    result = text
    for pattern, repl in replacements:
        result = re.sub(pattern, repl, result, flags=re.IGNORECASE)
    return result


class StorySynopsis(BaseModel):
    """Complete synopsis package for an episode."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    title: str
    logline: str = Field(..., description="One punchy sentence summarizing protagonist, stakes, and conflict")
    paragraph_summary: str = Field(..., description="One coherent paragraph summarizing the complete episode arc")
    full_synopsis: str = Field(..., description="Multi-paragraph comprehensive episode breakdown")
    dramatic_question: str
    genre: str = "Neo-Noir Thriller"
    tone: str = "Tense, atmospheric, high-stakes"
    target_duration_minutes: int = 20
    acts: Dict[str, str] = Field(default_factory=dict)


class SynopsisGenerator:
    """Generates three-tier synopsis grounded in story outline, scenes, and simulation events."""

    def generate_synopsis_from_grounded_data(
        self,
        world: WorldState,
        screenplay: Optional[ScreenplayDocument] = None,
        scenes: Optional[List[Any]] = None,
        projections: Optional[List[Any]] = None,
        title: str = "UNTITLED EPISODE",
    ) -> StorySynopsis:
        """Synthesize a three-tier synopsis directly from Phase 5/6/7 grounded scene and screenplay data."""
        char_names = [c.name for c in world.characters.values()] if world.characters else ["Vincent Cross", "Evelyn Vance"]
        actors_str = " and ".join(char_names[:2])
        loc_names = [loc.name for loc in world.locations.values()] if world.locations else ["the facility"]
        main_loc = loc_names[0] if loc_names else "an isolated sector"

        # 1. Logline
        logline = (
            f"When {actors_str} confront each other inside {main_loc}, "
            f"unfolding discoveries and mounting distrust force a decisive test of survival and loyalty."
        )

        # 2. Extract scene summaries from screenplay or scenes
        scene_descs: List[str] = []
        if screenplay and screenplay.scenes:
            for sc in screenplay.scenes:
                loc_clean = sc.heading.replace("INT. ", "").replace("EXT. ", "").split(" - ")[0].title()
                # Find representative action or dialogue
                actions = [b.text for b in sc.blocks if b.block_type.value in ("ACTION", "action")]
                act_snip = actions[0] if actions else f"Operatives maneuver through {loc_clean}."
                scene_descs.append(f"At {loc_clean}, {act_snip.rstrip('.')}.")
        elif scenes:
            for sc in scenes:
                loc_id = getattr(sc, "location_id", "the location").replace("_", " ").title()
                scene_descs.append(f"In {loc_id}, operatives pursue conflicting objectives under mounting tension.")

        act1_desc = scene_descs[0] if len(scene_descs) > 0 else f"Initial infiltration and perimeter assessment in {main_loc}."
        act2_desc = scene_descs[1] if len(scene_descs) > 1 else "Tension escalates as contradictory evidence and hidden motives collide."
        act3_desc = scene_descs[2] if len(scene_descs) > 2 else "A tense final confrontation forces an irreversible resolution."

        # 3. Paragraph Summary
        paragraph_summary = (
            f"In this high-stakes narrative episode, {actors_str} find themselves locked in a battle of wits and secrets. "
            f"{act1_desc} As tensions escalate and unforeseen environmental obstacles arise, {act2_desc} "
            f"Ultimately, {act3_desc.lower().rstrip('.')}."
        )

        # 4. Full Episode Synopsis
        full_synopsis = (
            f"EPISODE OVERVIEW: {title}\n\n"
            f"LOCATION & SETTING:\nEvents unfold within {', '.join(loc_names)}.\n\n"
            f"CORE DRAMATIC QUESTION:\nWill truth survive the clash of concealed objectives between {actors_str}?\n\n"
            f"ACT I - SETUP & INFILTRATION:\n{act1_desc}\n\n"
            f"ACT II - INVESTIGATION & CONFRONTATION:\n{act2_desc}\n\n"
            f"ACT III - REVERSAL & CLIMAX:\n{act3_desc}\n\n"
            f"RESOLUTION:\nOperatives separate as the consequences of the classified asset take hold."
        )

        acts = {
            "act_1": act1_desc,
            "act_2": act2_desc,
            "act_3": act3_desc,
        }

        return StorySynopsis(
            title=title,
            logline=sanitize_narrative_text(logline),
            paragraph_summary=sanitize_narrative_text(paragraph_summary),
            full_synopsis=sanitize_narrative_text(full_synopsis),
            dramatic_question=f"Will truth survive the clash of concealed objectives between {actors_str}?",
            genre="Neo-Noir Psychological Thriller",
            tone="Atmospheric, suspenseful, grounded",
            target_duration_minutes=20,
            acts=acts,
        )

    def generate_synopsis(
        self,
        outline: Optional[StoryOutline] = None,
        world: Optional[WorldState] = None,
        selection: Optional[NarrativeEventSelection] = None,
        scenes: Optional[List[Any]] = None,
        screenplay: Optional[ScreenplayDocument] = None,
        projections: Optional[List[Any]] = None,
    ) -> StorySynopsis:
        """Produce logline, paragraph summary, and full synopsis with zero internal engine terms."""
        # Route to grounded generator when scenes or screenplay are available
        if world and (screenplay or scenes or projections):
            ep_title = (screenplay.title if screenplay else (outline.episode_title if outline else "THE SIMULATION"))
            return self.generate_synopsis_from_grounded_data(
                world=world,
                screenplay=screenplay,
                scenes=scenes,
                projections=projections,
                title=ep_title,
            )

        char_names = [c.name for c in world.characters.values()] if world and world.characters else ["the protagonist", "the counter-agent"]
        actors_str = " and ".join(char_names[:2])
        duration = outline.target_duration_minutes if outline else 20
        ep_title = outline.episode_title if outline else "Untitled Episode"
        act_struct = outline.act_structure if outline else {}
        premise = outline.premise if outline else "Operatives confront opposing agendas in an enclosed facility."
        dram_q = outline.dramatic_question if outline else "Will the operatives survive their conflicting loyalties?"
        resolution = outline.resolution if outline else "One operative departs with the asset while the other retreats."

        # 1. Logline: concise, active, stakes-driven
        raw_logline = (
            f"When {actors_str} clash over hidden motives within an isolated sanctuary, "
            f"a mounting series of external crises forces an agonizing choice between survival and the truth."
        )
        logline = sanitize_narrative_text(raw_logline)

        # 2. Paragraph Summary
        act1_raw = act_struct.get("act_1", "The encounter begins with deep suspicion.")
        act2_raw = act_struct.get("act_2", "a shocking revelation shatters their initial assumptions.")
        raw_para = (
            f"In this {duration}-minute episode of '{ep_title}', {actors_str} "
            f"find themselves locked in a battle of wits and secrets. "
            f"{act1_raw} "
            f"As tensions escalate and unforeseen environmental obstacles arise, "
            f"{act2_raw} "
            f"Ultimately, {resolution.lower().rstrip('.')}."
        )
        paragraph_summary = sanitize_narrative_text(raw_para)

        # 3. Full Synopsis (Multi-paragraph)
        act1_desc = sanitize_narrative_text(act_struct.get("act_1", "The opening act establishes the initial situation."))
        act2_desc = sanitize_narrative_text(act_struct.get("act_2", "The second act escalates conflict through investigation."))
        act3_desc = sanitize_narrative_text(act_struct.get("act_3", "The final act culminates in an explosive confrontation."))

        # Ground with observed events if available
        events_grounding = ""
        if selection and selection.filtered_beats:
            beat_summaries = [b.summary for b in selection.filtered_beats[:4]]
            events_grounding = " Key simulation moments: " + "; ".join(beat_summaries) + "."

        raw_full = (
            f"EPISODE OVERVIEW: {ep_title}\n\n"
            f"PREMISE & STAKES:\n{premise}\n"
            f"Core Dramatic Question: {dram_q}\n\n"
            f"ACT I - THE INCITING INCIDENT:\n{act1_desc}\n\n"
            f"ACT II - THE ESCALATION & MIDPOINT:\n{act2_desc}{events_grounding}\n\n"
            f"ACT III - THE CLIMAX & FALLOUT:\n{act3_desc}\n\n"
            f"RESOLUTION:\n{resolution}"
        )
        full_synopsis = sanitize_narrative_text(raw_full)

        clean_acts = {k: sanitize_narrative_text(v) for k, v in act_struct.items()}

        return StorySynopsis(
            title=ep_title,
            logline=logline,
            paragraph_summary=paragraph_summary,
            full_synopsis=full_synopsis,
            dramatic_question=sanitize_narrative_text(dram_q),
            genre=outline.genre if outline else "Neo-Noir Thriller",
            tone=outline.tone if outline else "Tense, atmospheric, high-contrast",
            target_duration_minutes=duration,
            acts=clean_acts,
        )
