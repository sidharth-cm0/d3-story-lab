"""Social interaction model and grounded dialogue generation for D3 Story Lab."""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
from src.domain.world import WorldState
from src.domain.character import Character
from src.domain.goal import Goal


class SocialIntent(str, Enum):
    """Semantic intent of a social dialogue action."""
    QUESTION = "question"
    ANSWER = "answer"
    ACCUSE = "accuse"
    DENY = "deny"
    REVEAL = "reveal"
    LIE = "lie"
    WARN = "warn"
    REQUEST = "request"
    THREATEN = "threaten"
    COOPERATE = "cooperate"
    DEFLECT = "deflect"


class SocialDialogueGenerator:
    """Generates situationally grounded dialogue candidates honoring conversational memory and boundaries."""

    @staticmethod
    def generate_candidates(
        actor: Character,
        target: Any,
        goals: List[Goal],
        world: Any,
    ) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []

        is_view = hasattr(world, "perceivable_objects")
        if is_view:
            actor_beliefs = []
            actor_secrets = []
            actor_facts = []
            actor_memories = []
            trust = world.relationship_trust.get(target.id, 0.0)
            objs = world.perceivable_objects
            events = world.recent_events
        else:
            actor_beliefs = world.get_character_beliefs(actor.id)
            actor_secrets = world.get_character_secrets(actor.id)
            actor_facts = world.get_character_facts(actor.id)
            actor_memories = world.get_character_memories(actor.id)

            relationship = next(
                (
                    r for r in getattr(world, "relationships", {}).values()
                    if (r.character_a_id == actor.id and r.character_b_id == target.id)
                    or (r.character_a_id == target.id and r.character_b_id == actor.id)
                ),
                None,
            )
            trust = relationship.trust if relationship else 0.0
            objs = world.objects
            events = list(world.events.values())

        # Topic extraction from active goals or accessible objects
        primary_topic = "the situation"
        for g in goals:
            g_desc = g.description.lower()
            for word in ["documents", "dossier", "ledger", "safe", "access card", "forgery", "wiretap", "evidence", "briefcase", "escape"]:
                if word in g_desc:
                    primary_topic = word
                    break
            if primary_topic != "the situation":
                break

        if primary_topic == "the situation":
            for obj in objs.values():
                if obj.location_id == actor.current_location_id or getattr(obj, "holder_id", None) == actor.id:
                    primary_topic = obj.name.lower()
                    break

        # Check last speech between actor and target from history
        last_speech = None
        for ev in reversed(events):
            if ev.event_type.value == "character_spoke" and actor.id in ev.actor_ids and target.id in ev.actor_ids:
                last_speech = ev
                break

        partner_just_spoke = last_speech and last_speech.metadata.get("speaker_id") == target.id
        partner_intent = last_speech.metadata.get("speech_act") or last_speech.metadata.get("social_intent") if partner_just_spoke else None
        partner_topic = last_speech.metadata.get("topic") if partner_just_spoke else primary_topic
        topic_to_use = partner_topic or primary_topic

        # Check if actor has contradiction evidence regarding target & topic
        has_contradiction = False
        contradiction_detail = ""
        for m in actor_memories:
            m_text = m.summary.lower()
            if target.name.lower() in m_text and (topic_to_use in m_text or "dossier" in m_text or "document" in m_text or "room" in m_text):
                has_contradiction = True
                contradiction_detail = m.summary
                break
        if not has_contradiction:
            for f in actor_facts:
                f_text = f.statement.lower()
                if target.id in f.related_entities and (topic_to_use in f_text or "dossier" in f_text or "document" in f_text):
                    has_contradiction = True
                    contradiction_detail = f.statement
                    break

        # 1. Targeted responses when partner just spoke
        if partner_just_spoke:
            # Partner asked a QUESTION
            if partner_intent == SocialIntent.QUESTION.value:
                # If actor has a secret to protect: deny, deflect, or lie
                if actor_secrets:
                    candidates.append({
                        "social_intent": SocialIntent.DENY.value,
                        "dialogue": f"I had nothing to do with {topic_to_use}, {target.name}. My hands are clean.",
                        "topic": topic_to_use,
                        "claim": f"I had nothing to do with {topic_to_use}",
                        "truth_status": "truthful" if not any(topic_to_use in s.statement.lower() for s in actor_secrets) else "lie",
                        "base_utility": 0.88,
                    })
                    candidates.append({
                        "social_intent": SocialIntent.DEFLECT.value,
                        "dialogue": f"Why are you questioning me about {topic_to_use}? You should check the corridor cameras.",
                        "topic": topic_to_use,
                        "claim": f"Check corridor cameras for {topic_to_use}",
                        "truth_status": "deflection",
                        "base_utility": 0.82,
                    })
                else:
                    candidates.append({
                        "social_intent": SocialIntent.ANSWER.value,
                        "dialogue": f"Regarding {topic_to_use}, I am conducting my own inquiry here.",
                        "topic": topic_to_use,
                        "claim": f"Inquiring into {topic_to_use}",
                        "truth_status": "truthful",
                        "base_utility": 0.85,
                    })

            # Partner DENIED or DEFLECTED
            elif partner_intent in (SocialIntent.DENY.value, SocialIntent.DEFLECT.value):
                if has_contradiction:
                    candidates.append({
                        "social_intent": SocialIntent.ACCUSE.value,
                        "dialogue": f"That's a lie, {target.name}. I know you were seen near the {topic_to_use}!",
                        "topic": topic_to_use,
                        "claim": f"{target.name} was seen near {topic_to_use}",
                        "truth_status": "truthful",
                        "base_utility": 0.95,
                    })
                else:
                    candidates.append({
                        "social_intent": SocialIntent.THREATEN.value,
                        "dialogue": f"Denials won't save you, {target.name}. Security is on their way.",
                        "topic": topic_to_use,
                        "claim": "Security is arriving",
                        "truth_status": "uncertain",
                        "base_utility": 0.82,
                    })
                    candidates.append({
                        "social_intent": SocialIntent.REQUEST.value,
                        "dialogue": f"If you're innocent, {target.name}, prove it and help me check the room.",
                        "topic": topic_to_use,
                        "claim": "Requesting proof of innocence",
                        "truth_status": "truthful",
                        "base_utility": 0.78,
                    })

            # Partner ACCUSED actor
            elif partner_intent == SocialIntent.ACCUSE.value:
                if actor_secrets:
                    is_cornered = actor.emotional_state.fear > 0.2 or actor.emotional_state.anger > 0.2
                    candidates.append({
                        "social_intent": SocialIntent.REVEAL.value,
                        "dialogue": f"Fine! You want the truth, {target.name}? {actor_secrets[0].statement}",
                        "topic": "secret_confession",
                        "claim": actor_secrets[0].statement,
                        "truth_status": "truthful",
                        "base_utility": 1.15 if is_cornered else 0.78,
                    })
                candidates.append({
                    "social_intent": SocialIntent.DEFLECT.value,
                    "dialogue": f"You're making baseless claims, {target.name}. Where is your proof?",
                    "topic": topic_to_use,
                    "claim": "Accusation lacks proof",
                    "truth_status": "deflection",
                    "base_utility": 0.84,
                })
                candidates.append({
                    "social_intent": SocialIntent.THREATEN.value,
                    "dialogue": f"Back off, {target.name}, or you won't like what happens next.",
                    "topic": topic_to_use,
                    "claim": "Warning of consequences",
                    "truth_status": "threat",
                    "base_utility": 0.76,
                })

            # Partner REVEALED a secret
            elif partner_intent == SocialIntent.REVEAL.value:
                candidates.append({
                    "social_intent": SocialIntent.COOPERATE.value,
                    "dialogue": f"Now that you've told the truth, {target.name}, we need to secure this evidence together.",
                    "topic": "cooperation",
                    "claim": "Securing evidence together",
                    "truth_status": "truthful",
                    "base_utility": 0.95,
                })
                candidates.append({
                    "social_intent": SocialIntent.ANSWER.value,
                    "dialogue": f"I knew it. We have to report this before whoever ordered this finds us.",
                    "topic": "reporting_truth",
                    "claim": "Escaping and reporting",
                    "truth_status": "truthful",
                    "base_utility": 0.90,
                })

        # 2. General conversation initiation & continuation
        # Question if unasked or new topic
        candidates.append({
            "social_intent": SocialIntent.QUESTION.value,
            "dialogue": f"What do you know about {primary_topic}, {target.name}?",
            "topic": primary_topic,
            "claim": f"Inquiring about {primary_topic}",
            "truth_status": "truthful",
            "base_utility": 0.75,
        })

        if has_contradiction:
            candidates.append({
                "social_intent": SocialIntent.ACCUSE.value,
                "dialogue": f"Stop playing games, {target.name}. I have evidence regarding {primary_topic}!",
                "topic": primary_topic,
                "claim": f"Evidence exists regarding {primary_topic}",
                "truth_status": "truthful",
                "base_utility": 0.88,
            })

        if trust >= 0.0:
            candidates.append({
                "social_intent": SocialIntent.COOPERATE.value,
                "dialogue": f"If we pool what we know about {primary_topic}, {target.name}, we both get out cleanly.",
                "topic": "cooperation",
                "claim": "Proposing cooperation",
                "truth_status": "truthful",
                "base_utility": 0.70,
            })

        candidates.append({
            "social_intent": SocialIntent.WARN.value,
            "dialogue": f"Time is running out, {target.name}. Whoever orchestrates this isn't leaving loose ends.",
            "topic": "warning",
            "claim": "Warning of time pressure",
            "truth_status": "truthful",
            "base_utility": 0.65,
        })

        return candidates
