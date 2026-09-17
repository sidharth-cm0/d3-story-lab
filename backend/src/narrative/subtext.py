"""Subtext and deception engine for analyzing character dialogue against private state.

Compares spoken dialogue against:
- private knowledge and discovered facts
- secrets
- beliefs
- active goals
- emotional state
- relationship state

Crucial Invariant:
Private knowledge must NEVER be exposed directly in screenplay action lines.
Instead, hidden conflict is translated into observable performance cues.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
import re
from pydantic import BaseModel, ConfigDict, Field

from src.domain.character import Character
from src.domain.world import WorldState
from src.domain.proposition import Proposition, KnowledgeItem


class DeceptionClassification(str, Enum):
    """Classification of verbal subtext and deception intent."""
    TRUTHFUL = "TRUTHFUL"
    EVASIVE = "EVASIVE"
    CONCEALING = "CONCEALING"
    HALF_TRUTH = "HALF_TRUTH"
    MISDIRECTING = "MISDIRECTING"
    LYING = "LYING"
    MANIPULATIVE = "MANIPULATIVE"
    THREATENING = "THREATENING"
    DEFLECTING = "DEFLECTING"
    VULNERABLE = "VULNERABLE"


class SubtextAnalysis(BaseModel):
    """Detailed diagnostic of spoken line intent vs internal cognition."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    speaker_id: str
    listener_id: Optional[str] = None
    dialogue: str
    classifications: List[DeceptionClassification]
    primary_classification: DeceptionClassification
    underlying_motive: str
    private_truth_summary: Optional[str] = None
    cognitive_dissonance_score: float = Field(ge=0.0, le=1.0, default=0.0)
    conflict_focus_object: Optional[str] = None
    conflict_focus_location: Optional[str] = None


class SubtextAnalyzer:
    """Analyzes actor dialogue in the context of canonical private knowledge."""

    def __init__(self) -> None:
        pass

    def analyze(
        self,
        speaker: Character,
        dialogue: str,
        world: WorldState,
        listener_id: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
    ) -> SubtextAnalysis:
        """Compare actor's spoken line against private secrets, beliefs, and emotional tension."""
        meta = event_metadata or {}
        text_lower = dialogue.lower()
        classifications: List[DeceptionClassification] = []

        # 1. Gather private knowledge (typed KnowledgeItem or legacy secrets/facts/beliefs)
        secret_nouns = ["dossier", "ledger", "key", "safe", "money", "stolen", "bribe", "murder", "weapon", "vault", "cabinet"]
        matched_secret = None
        matched_kitem: Optional[KnowledgeItem] = None
        matched_prop: Optional[Proposition] = None
        focus_object = None
        focus_location = None

        has_typed_knowledge = bool(getattr(speaker, "knowledge", None))

        if has_typed_knowledge:
            # TYPED KNOWLEDGE MODE (Rules 4 & 5 compliance):
            # Only examine the speaker's own KnowledgeItem entries.
            # Never examine other characters' knowledge or unheld world propositions.
            # Do NOT read legacy known_facts or beliefs when typed knowledge is present.
            for pid, k_item in speaker.knowledge.items():
                prop = world.propositions.get(pid)
                if not prop:
                    continue
                prop_text = f"{prop.subject} {prop.predicate} {prop.object} {prop.id}".lower()
                for word in secret_nouns:
                    if word in prop_text:
                        matched_kitem = k_item
                        matched_prop = prop
                        if word in ["dossier", "ledger", "key", "safe", "money", "cabinet", "vault"]:
                            focus_object = word
                        break
                if matched_kitem:
                    break

            loc_id = getattr(speaker, "current_location_id", None) or getattr(speaker, "location_id", None)
            if not focus_object and loc_id and loc_id in world.locations:
                for obj_id, obj in world.objects.items():
                    if obj.location_id == loc_id:
                        focus_object = obj.name.lower()
                        break
        else:
            # LEGACY FALLBACK MODE (Backward compatibility for legacy projects):
            private_secrets = [
                s for s in world.secrets.values()
                if s.character_id == speaker.id or speaker.id in s.known_by
            ]
            private_facts = []
            if hasattr(world, "facts") and world.facts:
                for f in world.facts.values():
                    if f.discovered_by == speaker.id or (hasattr(speaker, "known_facts") and f.id in (speaker.known_facts or [])):
                        private_facts.append(f.statement.lower())

            speaker_beliefs = [
                b.statement.lower() for b in world.beliefs.values()
                if b.character_id == speaker.id
            ]

            for sec in private_secrets:
                s_stmt = sec.statement.lower()
                for word in secret_nouns:
                    if word in s_stmt:
                        matched_secret = sec
                        if word in ["dossier", "ledger", "key", "safe", "money", "cabinet", "vault"]:
                            focus_object = word
                        break
                if matched_secret:
                    break

            loc_id = getattr(speaker, "current_location_id", None) or getattr(speaker, "location_id", None)
            if not focus_object and loc_id and loc_id in world.locations:
                for obj_id, obj in world.objects.items():
                    if obj.location_id == loc_id:
                        focus_object = obj.name.lower()
                        break

        # 2. Check for Denial / Lying / Concealment
        denial_patterns = [
            r"\b(haven't|have not|didn't|did not|don't|do not|never|no idea|nothing|clean)\b",
            r"\b(wasn't me|not me|saw nothing|haven't seen|nowhere)\b",
        ]
        is_denial = any(re.search(pat, text_lower) for pat in denial_patterns)

        evasion_patterns = [
            r"\b(who knows|why do you ask|what does it matter|none of your business|ask someone else|maybe|could be)\b",
            r"\b(why would i|what are you talking about|that's irrelevant|irrelevant)\b",
        ]
        is_evasion = any(re.search(pat, text_lower) for pat in evasion_patterns)

        threatening_patterns = [
            r"\b(regret|watch out|or else|stay back|die|kill|threat|consequences|step aside|don't push me|leave now)\b",
            r"\b(warning you|final warning|make you pay)\b",
        ]
        is_threatening = any(re.search(pat, text_lower) for pat in threatening_patterns)

        manipulative_patterns = [
            r"\b(trust me|we're together|for your own good|help me help you|between friends|think about what happens)\b",
            r"\b(you owe me|you need me|we have a deal)\b",
        ]
        is_manipulative = any(re.search(pat, text_lower) for pat in manipulative_patterns)

        vulnerable_patterns = [
            r"\b(scared|terrified|help me|can't do this|i'm sorry|forgive me|please|too much|in over my head)\b",
        ]
        is_vulnerable = any(re.search(pat, text_lower) for pat in vulnerable_patterns)

        half_truth_patterns = [
            r"\b(i was there, but|only saw|just a minute|partly|not entirely|that's all i know)\b",
        ]
        is_half_truth = any(re.search(pat, text_lower) for pat in half_truth_patterns)

        misdirection_patterns = [
            r"\b(dock|warehouse|corridor|check with|look at|he went|she took|over there|not here)\b",
        ]
        is_misdirection = any(re.search(pat, text_lower) for pat in misdirection_patterns)

        dissonance = 0.0

        # Assess conflict with private knowledge
        if has_typed_knowledge and matched_kitem and matched_prop:
            believed_val = matched_kitem.believed_truth_value
            # Compare subjective belief against canonical world truth (records false belief perspective)
            matches_canonical = (believed_val == matched_prop.truth_value)

            if believed_val is True:
                # Subjectively believes proposition is true; denying or concealing it constitutes deception
                if is_denial:
                    classifications.append(DeceptionClassification.LYING)
                    classifications.append(DeceptionClassification.CONCEALING)
                    dissonance = 0.85
                elif is_evasion:
                    classifications.append(DeceptionClassification.EVASIVE)
                    classifications.append(DeceptionClassification.DEFLECTING)
                    dissonance = 0.70
                elif is_misdirection:
                    classifications.append(DeceptionClassification.MISDIRECTING)
                    classifications.append(DeceptionClassification.CONCEALING)
                    dissonance = 0.75
                elif is_half_truth:
                    classifications.append(DeceptionClassification.HALF_TRUTH)
                    classifications.append(DeceptionClassification.CONCEALING)
                    dissonance = 0.60
            else:
                # Subjectively believes proposition is FALSE; denying it is truthful from character's perspective
                if is_misdirection:
                    classifications.append(DeceptionClassification.MISDIRECTING)
                    dissonance = 0.50
        elif matched_secret:
            if is_denial:
                classifications.append(DeceptionClassification.LYING)
                classifications.append(DeceptionClassification.CONCEALING)
                dissonance = 0.85
            elif is_evasion:
                classifications.append(DeceptionClassification.EVASIVE)
                classifications.append(DeceptionClassification.DEFLECTING)
                dissonance = 0.70
            elif is_misdirection:
                classifications.append(DeceptionClassification.MISDIRECTING)
                classifications.append(DeceptionClassification.CONCEALING)
                dissonance = 0.75
            elif is_half_truth:
                classifications.append(DeceptionClassification.HALF_TRUTH)
                classifications.append(DeceptionClassification.CONCEALING)
                dissonance = 0.60
        else:
            if is_threatening:
                classifications.append(DeceptionClassification.THREATENING)
            if is_manipulative:
                classifications.append(DeceptionClassification.MANIPULATIVE)
            if is_evasion:
                classifications.append(DeceptionClassification.EVASIVE)
                classifications.append(DeceptionClassification.DEFLECTING)
            if is_vulnerable:
                classifications.append(DeceptionClassification.VULNERABLE)
            if is_half_truth:
                classifications.append(DeceptionClassification.HALF_TRUTH)
            if is_misdirection:
                classifications.append(DeceptionClassification.MISDIRECTING)

        # If no classifications were added by the deception check (e.g. false belief denial), check tone/style
        if not classifications:
            if is_threatening:
                classifications.append(DeceptionClassification.THREATENING)
            if is_manipulative:
                classifications.append(DeceptionClassification.MANIPULATIVE)
            if is_evasion:
                classifications.append(DeceptionClassification.EVASIVE)
                classifications.append(DeceptionClassification.DEFLECTING)
            if is_vulnerable:
                classifications.append(DeceptionClassification.VULNERABLE)
            if is_half_truth:
                classifications.append(DeceptionClassification.HALF_TRUTH)
            if is_misdirection:
                classifications.append(DeceptionClassification.MISDIRECTING)

        # Emotional amplification
        emotions = speaker.emotional_state
        if emotions.fear > 0.65 or emotions.anger > 0.65:
            dissonance = min(1.0, dissonance + 0.15)

        # Default fallback to TRUTHFUL if no deception/subtext flags triggered
        if not classifications:
            classifications.append(DeceptionClassification.TRUTHFUL)

        primary = classifications[0]

        # Motive extraction
        if DeceptionClassification.LYING in classifications:
            motive = "Protecting confidential knowledge by outright denial."
        elif DeceptionClassification.DEFLECTING in classifications or DeceptionClassification.EVASIVE in classifications:
            motive = "Shifting inquiry away from guarded territory."
        elif DeceptionClassification.MISDIRECTING in classifications:
            motive = "Directing interlocutor's suspicion toward false targets."
        elif DeceptionClassification.THREATENING in classifications:
            motive = "Establishing dominance and enforcing compliance through intimidation."
        elif DeceptionClassification.MANIPULATIVE in classifications:
            motive = "Leveraging psychological pressure to guide the other party's choices."
        elif DeceptionClassification.VULNERABLE in classifications:
            motive = "Revealing authentic emotional duress under mounting crisis."
        elif DeceptionClassification.HALF_TRUTH in classifications:
            motive = "Disclosing safe superficial details to obscure critical facts."
        else:
            motive = "Direct, transparent communication of observations."

        if has_typed_knowledge and matched_prop:
            private_truth = f"{matched_prop.subject} {matched_prop.predicate} {matched_prop.object}"
        elif matched_secret:
            private_truth = matched_secret.statement
        else:
            private_truth = None

        return SubtextAnalysis(
            speaker_id=speaker.id,
            listener_id=listener_id,
            dialogue=dialogue,
            classifications=classifications,
            primary_classification=primary,
            underlying_motive=motive,
            private_truth_summary=private_truth,
            cognitive_dissonance_score=round(dissonance, 2),
            conflict_focus_object=focus_object,
            conflict_focus_location=focus_location,
        )
