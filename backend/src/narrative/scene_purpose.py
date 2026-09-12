"""Scene purpose analyzer for dramatic structure, goal tension, and pacing."""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.narrative.fountain import ScreenplayScene, ScreenplayBlockType
from src.domain.world import WorldState


class ScenePurposeType(str, Enum):
    """Dramatic function of a screenplay scene."""
    SETUP = "SETUP"
    INVESTIGATION = "INVESTIGATION"
    DISCOVERY = "DISCOVERY"
    NEGOTIATION = "NEGOTIATION"
    CONFRONTATION = "CONFRONTATION"
    ESCALATION = "ESCALATION"
    REVERSAL = "REVERSAL"
    CHASE = "CHASE"
    REVELATION = "REVELATION"
    CLIMAX = "CLIMAX"
    RESOLUTION = "RESOLUTION"


class SceneDramaticAnalysis(BaseModel):
    """Complete dramatic breakdown of a screenplay scene."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    scene_number: int
    purpose: ScenePurposeType
    dramatic_question: str
    scene_goal: str
    scene_obstacle: str
    turning_point: str
    scene_outcome: str


class ScenePurposeAnalyzer:
    """Infers narrative purpose, dramatic question, and turning points for each scene."""

    def analyze_scene(self, scene: ScreenplayScene, world: Optional[WorldState] = None) -> SceneDramaticAnalysis:
        """Infer scene purpose and pacing elements from blocks and action content."""
        blocks_text = " ".join(b.text.lower() for b in scene.blocks)
        dialogue_count = sum(1 for b in scene.blocks if b.block_type == ScreenplayBlockType.DIALOGUE)
        action_count = sum(1 for b in scene.blocks if b.block_type == ScreenplayBlockType.ACTION)

        purpose: ScenePurposeType
        dramatic_q: str
        goal: str
        obstacle: str
        turn: str
        outcome: str

        if any(w in blocks_text for w in ["climax", "explosion", "shootout", "final standoff", "cornered"]):
            purpose = ScenePurposeType.CLIMAX
            dramatic_q = "Will the protagonist survive the lethal reckoning?"
            goal = "Survive and secure the objective against overwhelming opposition."
            obstacle = "Lethal threat and cut-off retreat lines."
            turn = "An explosive escalation eliminates all room for negotiation."
            outcome = "Decisive shift in life-or-death balance."

        elif any(w in blocks_text for w in ["chase", "pursuit", "sprints", "escapes", "flee"]):
            purpose = ScenePurposeType.CHASE
            dramatic_q = "Can the target escape before the cordon tightens?"
            goal = "Break line of sight and reach extraction."
            obstacle = "Pursuers and obstructed exits."
            turn = "A sudden detour or barrier forces a desperate maneuver."
            outcome = "Protagonist slips through or is pinned down."

        elif any(w in blocks_text for w in ["confess", "secret", "truth", "unmasks", "revelation"]):
            purpose = ScenePurposeType.REVELATION
            dramatic_q = "What is the true reality behind the deception?"
            goal = "Uncover the protected secret."
            obstacle = "Carefully maintained cover stories."
            turn = "A hidden truth is exposed, shattering prior assumptions."
            outcome = "Allies and adversaries are recalibrated."

        elif any(w in blocks_text for w in ["found", "dossier", "ledger", "cache", "evidence", "discovers", "picks up"]):
            purpose = ScenePurposeType.DISCOVERY
            dramatic_q = "Will the search yield the critical physical proof?"
            goal = "Locate and secure the objective."
            obstacle = "Concealment and physical traps."
            turn = "The object is retrieved from its hidden sanctuary."
            outcome = "Evidence secured, but alarm or arrival is triggered."

        elif any(w in blocks_text for w in ["confront", "accuse", "drop it", "gun", "freeze", "standoff"]):
            purpose = ScenePurposeType.CONFRONTATION
            dramatic_q = "Who will yield when force meets defiance?"
            goal = "Force the adversary into submission."
            obstacle = "An armed or determined opponent."
            turn = "Subtext gives way to direct threat."
            outcome = "Tense standoff establishes new dominance."

        elif any(w in blocks_text for w in ["bargain", "deal", "offer", "negotiate", "what do you want"]):
            purpose = ScenePurposeType.NEGOTIATION
            dramatic_q = "Can a high-stakes compromise be struck without violence?"
            goal = "Extract terms or information."
            obstacle = "Mutual distrust and hidden leverage."
            turn = "A concealed card or leverage is played."
            outcome = "Uneasy truce or breakdown of talks."

        elif any(w in blocks_text for w in ["search", "examines", "investigates", "inspects", "tracks"]):
            purpose = ScenePurposeType.INVESTIGATION
            dramatic_q = "What traces did the adversary leave behind?"
            goal = "Piecing together clues in a hostile space."
            obstacle = "Shadows, silence, and ticking clock."
            turn = "A vital trace or disturbance is spotted."
            outcome = "Trail leads to the next critical zone."

        elif scene.scene_number == 1:
            purpose = ScenePurposeType.SETUP
            dramatic_q = "What forces and hazards define this territory?"
            goal = "Establish presence and assess the perimeter."
            obstacle = "Hostile environment and unknown variables."
            turn = "Infiltration succeeds without initial detection."
            outcome = "Protagonist is inside the operational zone."

        else:
            purpose = ScenePurposeType.ESCALATION
            dramatic_q = "Can the characters sustain control as pressure mounts?"
            goal = "Advance agenda under narrowing options."
            obstacle = "Closing exits and rising suspicion."
            turn = "A minor misstep alerts the opposition."
            outcome = "Stakes escalate to critical threshold."

        return SceneDramaticAnalysis(
            scene_number=scene.scene_number,
            purpose=purpose,
            dramatic_question=dramatic_q,
            scene_goal=goal,
            scene_obstacle=obstacle,
            turning_point=turn,
            scene_outcome=outcome,
        )
