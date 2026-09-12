"""Kinetic transition planner for cinematic shot continuity and graphic matches."""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.models import StoryboardPanel, ShotType, ShotPurpose


class TransitionType(str, Enum):
    """Cinematic transition techniques between adjacent storyboard panels."""
    MATCH_CUT = "MATCH_CUT"
    GRAPHIC_MATCH = "GRAPHIC_MATCH"
    ACTION_MATCH = "ACTION_MATCH"
    EYELINE_CUT = "EYELINE_CUT"
    TRACKING_CONTINUATION = "TRACKING_CONTINUATION"
    WHIP_PAN = "WHIP_PAN"
    RACK_FOCUS = "RACK_FOCUS"
    INSERT_TO_REACTION = "INSERT_TO_REACTION"
    REVEAL = "REVEAL"
    CUT = "CUT"


class TransitionLink(BaseModel):
    """A planned cinematic transition connecting two sequential storyboard panels."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_shot_number: int
    target_shot_number: int
    transition_type: TransitionType
    visual_link: str
    rationale: str


class TransitionPlanner:
    """Detects opportunities for kinetic and thematic transitions between panels."""

    @staticmethod
    def plan_transitions(panels: List[StoryboardPanel]) -> List[TransitionLink]:
        """Analyze sequential shot pairs and assign motivated cinematic transitions."""
        links: List[TransitionLink] = []
        if len(panels) < 2:
            return links

        for i in range(len(panels) - 1):
            p1 = panels[i]
            p2 = panels[i + 1]
            s1_num = p1.shot_number or (i + 1)
            s2_num = p2.shot_number or (i + 2)

            t_type = TransitionType.CUT
            v_link = "Standard narrative cut"
            rationale = "Direct progression to next dramatic beat."

            desc1 = f"{p1.action} {p1.visual_description} {p1.caption}".lower()
            desc2 = f"{p2.action} {p2.visual_description} {p2.caption}".lower()

            # 1. INSERT -> REACTION / RACK FOCUS
            if p1.shot_type == ShotType.INSERT and p2.shot_type in (ShotType.CLOSE_UP, ShotType.REACTION):
                t_type = TransitionType.INSERT_TO_REACTION
                v_link = "Physical clue to facial micro-expression"
                rationale = "Immediate emotional payoff following discovery of evidence."
            elif p1.narrative_purpose == ShotPurpose.CLUE and p2.narrative_purpose == ShotPurpose.REVELATION:
                t_type = TransitionType.RACK_FOCUS
                v_link = "Focal plane transfers from prop to actor gaze"
                rationale = "Dynamic shift in attention from the incriminating object to realization."

            # 2. GRAPHIC MATCH (Similar circular/geometric shapes)
            elif (
                any(w in desc1 for w in ["dial", "watch", "clock", "wheel", "lens", "compass", "coin"]) and
                any(w in desc2 for w in ["dial", "watch", "clock", "wheel", "lens", "compass", "coin"])
            ):
                t_type = TransitionType.GRAPHIC_MATCH
                v_link = "Circular motif visual symmetry"
                rationale = "Thematic connection bridged through identical geometric form."

            # 3. ACTION MATCH (Ongoing kinetic movement)
            elif (
                any(w in desc1 for w in ["runs", "sprints", "strikes", "kicks", "dives", "leaps", "draws gun"]) and
                any(w in desc2 for w in ["runs", "sprints", "lands", "fires", "hits", "impact", "continues"])
            ):
                t_type = TransitionType.ACTION_MATCH
                v_link = "Kinetic vector momentum"
                rationale = "Maintains physical velocity seamlessly across changing camera angles."

            # 4. TRACKING CONTINUATION
            elif (
                ("track" in p1.camera_movement.lower() or "pan" in p1.camera_movement.lower()) and
                ("track" in p2.camera_movement.lower() or "pan" in p2.camera_movement.lower())
            ):
                t_type = TransitionType.TRACKING_CONTINUATION
                v_link = "Lateral camera velocity"
                rationale = "Continuous camera flow following character through extended corridor."

            # 5. EYELINE CUT (Dialogue ping-pong between characters)
            elif (
                p1.narrative_purpose == ShotPurpose.DIALOGUE and
                p2.narrative_purpose == ShotPurpose.DIALOGUE and
                p1.characters_present != p2.characters_present
            ):
                t_type = TransitionType.EYELINE_CUT
                v_link = "Complementary 180-degree gaze vectors"
                rationale = "Maintains spatial orientation and tension between conversing actors."

            # 6. WHIP PAN
            elif any(w in desc1 for w in ["sudden", "whirls", "alarm", "explosion", "spin"]):
                t_type = TransitionType.WHIP_PAN
                v_link = "High-speed directional blur streak"
                rationale = "Visceral shock cuts audience rapidly to source of crisis."

            # 7. REVEAL
            elif p1.shot_type in (ShotType.CLOSE_UP, ShotType.MEDIUM) and p2.shot_type == ShotType.WIDE and p2.narrative_purpose == ShotPurpose.ESTABLISH:
                t_type = TransitionType.REVEAL
                v_link = "Tight subject expands to cavernous scale"
                rationale = "Dramatic reveal recontextualizes subject within hostile environment."

            link = TransitionLink(
                source_shot_number=s1_num,
                target_shot_number=s2_num,
                transition_type=t_type,
                visual_link=v_link,
                rationale=rationale,
            )
            links.append(link)

            # Store on target panel
            p2.transition_type = t_type.value
            p2.transition_source_shot = s1_num
            p2.transition_target_shot = s2_num
            p2.visual_link = v_link

        return links
