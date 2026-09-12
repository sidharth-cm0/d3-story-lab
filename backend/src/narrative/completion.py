"""Story Completion Layer driven by Director / Narrative Engine.

Accepts incomplete narrative input from ANY point (beginning, midpoint, ending, full concept)
and synthesizes a complete 20-minute episode structure.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Optional, Any
import re
from pydantic import BaseModel, ConfigDict, Field

from src.providers.base import LLMProvider


class StoryInputType(str, Enum):
    """Classification of narrative seed input."""
    BEGINNING = "beginning"
    MIDPOINT = "midpoint"
    ENDING = "ending"
    FULL_CONCEPT = "full_concept"


class ActBeat(BaseModel):
    """An individual dramatic beat in the episode structure."""
    model_config = ConfigDict(frozen=True)

    beat_number: int
    act: str  # "Act I", "Act II", "Act III"
    title: str
    description: str
    conflict: str
    location_hint: str
    tension_level: float = Field(default=0.5, ge=0.0, le=1.0)


class StoryOutline(BaseModel):
    """Complete 20-minute episode narrative outline synthesized from input."""
    model_config = ConfigDict(frozen=True)

    input_type: StoryInputType
    raw_input: str
    episode_title: str
    genre: str
    tone: str
    target_duration_minutes: int = 20
    premise: str
    dramatic_question: str
    act_structure: Dict[str, str] = Field(
        default_factory=lambda: {
            "act_1": "Act I: Setup & Inciting Incident",
            "act_2": "Act II: Escalation & Midpoint Reversal",
            "act_3": "Act III: Climax & Resolution",
        }
    )
    key_scenes: List[ActBeat] = Field(default_factory=list)
    climax: str
    resolution: str
    subplot_hooks: List[str] = Field(default_factory=list)


class StoryCompletionEngine:
    """Classifies incomplete story inputs and generates complete dramatic outlines."""

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider

    def classify_input(self, seed_text: str, declared_type: Optional[str] = None) -> StoryInputType:
        """Determine whether input is beginning, midpoint, ending, or full concept."""
        if declared_type:
            cleaned = declared_type.strip().lower().replace(" ", "_")
            for t in StoryInputType:
                if t.value == cleaned:
                    return t

        text_lower = seed_text.lower().strip()

        # Ending indicators: escape, aftermath, final, ends, loses, destroyed, resolved, survived, left behind
        ending_keywords = [
            "escapes", "escaped", "finally", "aftermath", "survives", "survived",
            "burns down", "loses the evidence", "walks away into", "in the end",
            "arrested", "resolution", "dead", "collapsed", "flees into the night"
        ]
        if any(w in text_lower for w in ending_keywords) and len(text_lower.split()) < 35:
            return StoryInputType.ENDING

        # Midpoint indicators: discovers, realizes, turns out, betrays, partner is lying, betrayal, trapped, learns truth
        midpoint_keywords = [
            "discovers", "realizes", "turns out", "betrays", "is lying", "double-cross",
            "finds out", "uncovers", "shocking revelation", "trap closes", "caught between",
            "partner is", "secret identity", "evidence points to"
        ]
        if any(w in text_lower for w in midpoint_keywords) and len(text_lower.split()) < 35:
            return StoryInputType.MIDPOINT

        # Beginning indicators: enters, arrives, wakes up, receives, discovers body, gets call, first day, walks into
        beginning_keywords = [
            "enters", "arrives", "wakes up", "receives a", "walks into", "knocks on",
            "approaches", "breaks into", "starts", "hired to", "steps inside"
        ]
        if any(w in text_lower for w in beginning_keywords) and len(text_lower.split()) < 35:
            return StoryInputType.BEGINNING

        # Long text or multi-sentence premise
        if len(text_lower.split()) >= 18:
            return StoryInputType.FULL_CONCEPT

        return StoryInputType.BEGINNING

    def complete_story(
        self,
        seed_text: str,
        declared_type: Optional[str] = None,
        target_duration_minutes: int = 20,
    ) -> StoryOutline:
        """Infer missing narrative pieces and generate a complete dramatic episode outline."""
        input_type = self.classify_input(seed_text, declared_type)

        # Build clean title
        words = [w for w in re.sub(r"[^a-zA-Z0-9\s]", "", seed_text).split() if len(w) > 2]
        title_slug = " ".join(words[:4]).title() if words else "Untitled Incident"

        if input_type == StoryInputType.BEGINNING:
            return self._complete_from_beginning(seed_text, title_slug, target_duration_minutes)
        elif input_type == StoryInputType.MIDPOINT:
            return self._complete_from_midpoint(seed_text, title_slug, target_duration_minutes)
        elif input_type == StoryInputType.ENDING:
            return self._complete_from_ending(seed_text, title_slug, target_duration_minutes)
        else:
            return self._complete_from_full_concept(seed_text, title_slug, target_duration_minutes)

    def _complete_from_beginning(self, seed: str, title: str, duration: int) -> StoryOutline:
        """Input is beginning -> infer middle escalation, reversal, and ending resolution."""
        premise = f"Beginning: {seed}. In pursuit of the truth, hidden motives clash in an enclosed space before a fatal revelation."
        question = "Will the protagonist secure the truth before the perimeter is breached and the truth buried?"

        act_1 = f"Act I: Setup. {seed}. The protagonist arrives, establishing the stakes and noting anomalies in the environment."
        act_2 = "Act II: Escalation & Reversal. A second sovereign actor is discovered inside; an encrypted asset creates intense mutual distrust when external alarms trip."
        act_3 = "Act III: Climax & Resolution. Under severe environmental crisis, the actors make a desperate choice: alliance or betrayal, escaping as the truth is irrevocably transformed."

        key_scenes = [
            ActBeat(
                beat_number=1,
                act="Act I",
                title="Threshold Infiltration",
                description=f"Opening beat: {seed}. Atmosphere of guarded tension.",
                conflict="Vulnerability vs curiosity upon entering unknown territory",
                location_hint="Perimeter Entry",
                tension_level=0.3,
            ),
            ActBeat(
                beat_number=2,
                act="Act I",
                title="The Inciting Disruption",
                description="Discovery of fresh signs of occupancy: warm coffee, an active terminal, or displaced furniture.",
                conflict="Awareness that the protagonist is not alone",
                location_hint="Inner Corridor",
                tension_level=0.45,
            ),
            ActBeat(
                beat_number=3,
                act="Act II",
                title="Midpoint Confrontation",
                description="Direct encounter with another actor holding a vital physical asset. Verbal standoff and leverage exchange.",
                conflict="Opposing claims over the objective",
                location_hint="Central Chamber / Vault",
                tension_level=0.7,
            ),
            ActBeat(
                beat_number=4,
                act="Act II",
                title="Environmental Breach",
                description="The Director triggers an external crisis (power failure, locked blast doors, incoming security).",
                conflict="Time running out as outside forces close in",
                location_hint="Central Chamber",
                tension_level=0.85,
            ),
            ActBeat(
                beat_number=5,
                act="Act III",
                title="The Reckoning & Climax",
                description="A high-stakes gamble to secure the asset while evading containment.",
                conflict="Survival vs sacrifice of the evidence",
                location_hint="Exit Corridor",
                tension_level=0.95,
            ),
            ActBeat(
                beat_number=6,
                act="Act III",
                title="Aftermath & Resolution",
                description="The dust settles. The protagonist emerges into the open, carrying the psychological weight of the encounter.",
                conflict="Lingering consequences of the secrets unveiled",
                location_hint="Outer Perimeter",
                tension_level=0.2,
            ),
        ]

        return StoryOutline(
            input_type=StoryInputType.BEGINNING,
            raw_input=seed,
            episode_title=f"The Threshold: {title}",
            genre="Neo-Noir Psychological Thriller",
            tone="Moody, claustrophobic, high-contrast chiaroscuro",
            target_duration_minutes=duration,
            premise=premise,
            dramatic_question=question,
            act_structure={"act_1": act_1, "act_2": act_2, "act_3": act_3},
            key_scenes=key_scenes,
            climax="The confrontation reaches boiling point as the facility locks down, forcing an immediate sacrifice.",
            resolution="One actor escapes with partial truth; the other vanishes into the shadows.",
            subplot_hooks=["An unlisted frequency broadcasts an encrypted distress beacon."],
        )

    def _complete_from_midpoint(self, seed: str, title: str, duration: int) -> StoryOutline:
        """Input is midpoint -> infer setup (how we got here) and ending (how it resolves)."""
        premise = f"Midpoint shift: {seed}. A bond forged in secrecy fractures when deceptive evidence comes to light."
        question = "Can the investigator navigate the partner's deception without falling into the enemy's trap?"

        act_1 = "Act I: Infiltration & Covert Alliance. The partners establish their operational base, appearing aligned on a mission to recover classified assets."
        act_2 = f"Act II: The Fractured Bond. {seed}. Contradictory documents surface, sparking intense covert observation and verbal traps."
        act_3 = "Act III: The Trap Springs. Forced to choose between loyalty and justice, an inescapable standoff unfolds as the true conspirators arrive."

        key_scenes = [
            ActBeat(
                beat_number=1,
                act="Act I",
                title="Apparent Accord",
                description="Two operatives convene in a secure staging area, reviewing target dossiers.",
                conflict="Superficial harmony concealing private agendas",
                location_hint="Safehouse / Briefing Suite",
                tension_level=0.35,
            ),
            ActBeat(
                beat_number=2,
                act="Act I",
                title="The Inconsistency",
                description="A subtle procedural flaw or mismatched timestamp triggers suspicion.",
                conflict="Internal doubt begins eroding operational trust",
                location_hint="Inner Archive",
                tension_level=0.5,
            ),
            ActBeat(
                beat_number=3,
                act="Act II",
                title="The Midpoint Fracture",
                description=f"{seed}. Hard evidence of deceit is verified.",
                conflict="Active deception exposed between primary partners",
                location_hint="Executive Office",
                tension_level=0.8,
            ),
            ActBeat(
                beat_number=4,
                act="Act II",
                title="Counter-Interrogation",
                description="A razor-sharp dialogue confrontation with hidden subtext and concealed weapons.",
                conflict="Testing who knows what and who is recording",
                location_hint="Executive Office",
                tension_level=0.88,
            ),
            ActBeat(
                beat_number=5,
                act="Act III",
                title="The Direct Confrontation",
                description="Director intervention triggers building alarm; guns drawn, ultimatums delivered.",
                conflict="Direct showdown before the arrival of authorities",
                location_hint="Corridor Staging",
                tension_level=0.98,
            ),
            ActBeat(
                beat_number=6,
                act="Act III",
                title="Cold Realization",
                description="The liar is disarmed or confesses the deeper blackmail that forced their hand.",
                conflict="Bittersweet closure and irreconcilable distance",
                location_hint="Emergency Exit",
                tension_level=0.25,
            ),
        ]

        return StoryOutline(
            input_type=StoryInputType.MIDPOINT,
            raw_input=seed,
            episode_title=f"The False Partner: {title}",
            genre="Espionage Noir Drama",
            tone="Paranoid, razor-sharp, atmospheric shadow",
            target_duration_minutes=duration,
            premise=premise,
            dramatic_question=question,
            act_structure={"act_1": act_1, "act_2": act_2, "act_3": act_3},
            key_scenes=key_scenes,
            climax="The partner confesses under gunpoint that their family is held hostage, resetting the moral compass of the confrontation.",
            resolution="The evidence is divided; both walk away scarred, knowing their alliance is dead.",
            subplot_hooks=["A third operative monitors the wiretap from an unmarked surveillance van."],
        )

    def _complete_from_ending(self, seed: str, title: str, duration: int) -> StoryOutline:
        """Input is ending -> reverse-engineer setup and confrontation that caused this conclusion."""
        premise = f"Endpoint outcome: {seed}. Tracking back from this pyrrhic survival reveals a desperate gamble against overwhelming odds."
        question = "Was the survival worth the catastrophic loss of the evidence that could have exposed the syndicate?"

        act_1 = "Act I: The Heist Infiltration. The operative breaches the fortified location to extract the smoking-gun asset."
        act_2 = "Act II: The Counter-Measure & Inferno. An unexpected adversary triggers automated security measures, escalating into physical conflict as flames ignite."
        act_3 = f"Act III: The Pyrrhic Flight. {seed}. The final sprint through collapsing infrastructure."

        key_scenes = [
            ActBeat(
                beat_number=1,
                act="Act I",
                title="The Silent Insertion",
                description="Careful reconnaissance and bypassing perimeter locks into the holding facility.",
                conflict="Technical challenge vs creeping dread",
                location_hint="Perimeter Gate",
                tension_level=0.3,
            ),
            ActBeat(
                beat_number=2,
                act="Act I",
                title="Touching the Asset",
                description="The operative locates the target dossier or device, confirming its catastrophic contents.",
                conflict="Exhilaration vs the realization of a trap",
                location_hint="Secure Archive",
                tension_level=0.55,
            ),
            ActBeat(
                beat_number=3,
                act="Act II",
                title="The Ambush",
                description="An opposing guard or rival agent ambushes the protagonist; violence breaks out, damaging electrical conduits.",
                conflict="Physical struggle for custody of the evidence",
                location_hint="Storage Depot",
                tension_level=0.75,
            ),
            ActBeat(
                beat_number=4,
                act="Act II",
                title="The Spread of Chaos",
                description="Fire erupts across the depot. Smoke reduces visibility to zero. Exit paths seal.",
                conflict="Environment turns deadly, threatening both combatants",
                location_hint="Burning Depot",
                tension_level=0.9,
            ),
            ActBeat(
                beat_number=5,
                act="Act III",
                title="The Terminal Sacrifice",
                description=f"{seed}. Reaching the exit requires dropping the evidence into the inferno.",
                conflict="Life vs mission validation",
                location_hint="Industrial Loading Bay",
                tension_level=1.0,
            ),
            ActBeat(
                beat_number=6,
                act="Act III",
                title="Smoldering Horizon",
                description="Collapsing against the wet asphalt outside as the building is consumed in ash.",
                conflict="Survival achieved, but total failure of objective",
                location_hint="Exterior Alleyway",
                tension_level=0.2,
            ),
        ]

        return StoryOutline(
            input_type=StoryInputType.ENDING,
            raw_input=seed,
            episode_title=f"Ashes of Truth: {title}",
            genre="Hardboiled Crime Noir",
            tone="Visceral, bleak, high kinetic urgency",
            target_duration_minutes=duration,
            premise=premise,
            dramatic_question=question,
            act_structure={"act_1": act_1, "act_2": act_2, "act_3": act_3},
            key_scenes=key_scenes,
            climax=f"{seed}. The decisive moment where survival demands abandoning the physical proof.",
            resolution="The protagonist watches the flames consume everything, knowing only their memory preserves the truth.",
            subplot_hooks=["A corrupt detective observes the fire from across the street with a quiet smile."],
        )

    def _complete_from_full_concept(self, seed: str, title: str, duration: int) -> StoryOutline:
        """Full concept provided -> structure into balanced 3-act episodic architecture."""
        premise = f"Premise: {seed}. In an isolated urban sanctuary, two figures circle each other across an ideological chasm."
        question = "Can truth withstand the crushing weight of institutional self-preservation?"

        act_1 = "Act I: The Staging. Two distinct actors enter a contained environment, their opposing roles and secrets primed for collision."
        act_2 = "Act II: The Crucible. Covert probing escalates into overt interrogation as external director interventions force secrets to the surface."
        act_3 = "Act III: The Reckoning. When escape becomes conditional on revelation, a definitive moral boundary is crossed."

        key_scenes = [
            ActBeat(
                beat_number=1,
                act="Act I",
                title="Arrival and Cold Assessment",
                description="Initial convergence in the designated space. Non-verbal sizing up.",
                conflict="Guarded courtesy masking predatory surveillance",
                location_hint="Main Suite",
                tension_level=0.3,
            ),
            ActBeat(
                beat_number=2,
                act="Act I",
                title="Inspection of the Asset",
                description="A sensitive object is introduced or inspected, prompting subtle defensive maneuvers.",
                conflict="Control over physical evidence",
                location_hint="Main Suite Desk",
                tension_level=0.5,
            ),
            ActBeat(
                beat_number=3,
                act="Act II",
                title="Direct Inquest",
                description="The first verbal accusation lands; secrets are tested against known facts.",
                conflict="Truth vs polished deniability",
                location_hint="Main Suite",
                tension_level=0.75,
            ),
            ActBeat(
                beat_number=4,
                act="Act II",
                title="External Shock",
                description="Director triggers an environmental disruption (phone ring, blackout, or knocking).",
                conflict="Shared external panic shifting internal power dynamics",
                location_hint="Main Suite Threshold",
                tension_level=0.88,
            ),
            ActBeat(
                beat_number=5,
                act="Act III",
                title="The Breaking Point",
                description="The definitive choice: confess, destroy the asset, or strike a pact.",
                conflict="Irreversible moral compromise",
                location_hint="Adjoining Corridor",
                tension_level=0.96,
            ),
            ActBeat(
                beat_number=6,
                act="Act III",
                title="Resolution Beat",
                description="The consequence of the decision locks in. One party departs; the other remains altered.",
                conflict="Living with the fallout",
                location_hint="Main Suite / Exit",
                tension_level=0.2,
            ),
        ]

        return StoryOutline(
            input_type=StoryInputType.FULL_CONCEPT,
            raw_input=seed,
            episode_title=title or "The Penthouse Protocol",
            genre="Chamber Neo-Noir",
            tone="Tense, deliberate, shadowed",
            target_duration_minutes=duration,
            premise=premise,
            dramatic_question=question,
            act_structure={"act_1": act_1, "act_2": act_2, "act_3": act_3},
            key_scenes=key_scenes,
            climax="Secrets collapse in an explosive revelation as outside authorities arrive at the door.",
            resolution="A clandestine transaction is completed in the dark, altering both characters forever.",
            subplot_hooks=["A hidden audio bug pulses on an encrypted civilian frequency."],
        )
