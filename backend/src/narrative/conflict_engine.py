"""Deterministic baseline Conflict Engine for dramatic incompatibility and tension analysis."""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timezone

from ..domain.world import WorldState
from ..domain.character import Character
from ..domain.goal import GoalStatus
from ..domain.conflict import (
    ConflictDimension,
    ConflictEvidence,
    ConflictEdge,
    ConflictGraph,
)
from ..domain.character_creation import FieldAuthority


OPPOSING_VALUE_PAIRS: List[Tuple[Set[str], Set[str]]] = [
    (
        {"truth", "honesty", "transparency", "candor", "justice", "integrity"},
        {"secrecy", "deception", "discretion", "privacy", "covert", "denial"},
    ),
    (
        {"order", "law", "control", "rules", "obedience", "structure"},
        {"freedom", "rebellion", "chaos", "autonomy", "anarchy", "independence"},
    ),
    (
        {"loyalty", "solidarity", "family", "community", "devotion"},
        {"individualism", "self-interest", "ambition", "opportunism", "detachment"},
    ),
    (
        {"compassion", "empathy", "mercy", "peace", "kindness"},
        {"vengeance", "retribution", "dominance", "ruthlessness", "punishment"},
    ),
    (
        {"duty", "honor", "sacrifice", "responsibility"},
        {"self-preservation", "survival", "cowardice", "comfort", "escape"},
    ),
    (
        {"tradition", "stability", "caution", "preservation"},
        {"innovation", "disruption", "progress", "risk", "revolution"},
    ),
]

OPPOSING_GOAL_VERB_PAIRS: List[Tuple[Set[str], Set[str]]] = [
    (
        {"recover", "find", "discover", "reveal", "expose", "uncover", "investigate", "prove"},
        {"hide", "destroy", "conceal", "burn", "shred", "cover", "suppress", "deny"},
    ),
    (
        {"arrest", "capture", "detain", "interrogate", "confront", "catch"},
        {"escape", "flee", "evade", "avoid", "hide", "slip away"},
    ),
    (
        {"protect", "save", "defend", "preserve", "guard"},
        {"harm", "kill", "destroy", "attack", "steal", "sabotage", "eliminate"},
    ),
    (
        {"win", "acquire", "claim", "take", "secure", "obtain"},
        {"prevent", "block", "deny", "refuse", "stop"},
    ),
]

GRIEVANCE_KEYWORDS = {
    "betrayal",
    "betrayed",
    "stole",
    "theft",
    "lied",
    "grudge",
    "enemy",
    "rival",
    "rivalry",
    "fired",
    "injured",
    "deceived",
    "cheat",
    "cheated",
    "scandal",
    "broken promise",
    "lawsuit",
    "dispute",
    "hostility",
    "blackmail",
    "fraud",
}

HIERARCHY_ROLE_PAIRS = [
    ({"investigator", "detective", "police", "auditor", "inspector", "agent"}, {"suspect", "executive", "target", "fugitive", "whistleblower"}),
    ({"manager", "boss", "director", "supervisor", "lead"}, {"subordinate", "employee", "assistant", "clerk"}),
    ({"rival", "competitor", "opponent"}, {"rival", "competitor", "opponent"}),
]


class ConflictEngine:
    """Pure, deterministic conflict derivation engine.

    CRITICAL INVARIANTS:
    1. ConflictEngine is strictly analytical / observational.
    2. Conflict scores create dramatic PRESSURE and OPPORTUNITY only.
    3. Conflict derivation NEVER mutates WorldState, creates Events, or forces confrontation actions.
    4. Respects FieldAuthority.USER_LOCKED on pre-existing ConflictEdges.
    """

    @classmethod
    def derive_pairwise_conflict(
        cls,
        world: WorldState,
        char_a_id: str,
        char_b_id: str,
        existing_edge: Optional[ConflictEdge] = None,
    ) -> ConflictEdge:
        """Deterministically derive a ConflictEdge between two characters based on canonical state.

        REQUIRED ARCHITECTURE:
        LOCKED DESIGN PREMISE + CURRENT RUNTIME DERIVATION = CURRENT CONFLICT EDGE.

        Explicit authorial design-premise dimensions are preserved when user-locked.
        Runtime dimensions are always freshly derived from current canonical state.
        Aggregate intensity is recomputed from the final merged dimensions.
        Traceable evidence distinguishes user-authored design evidence from runtime-derived evidence.
        """
        char_a = world.characters.get(char_a_id)
        char_b = world.characters.get(char_b_id)

        if not char_a or not char_b:
            return ConflictEdge(
                source_character_id=char_a_id,
                target_character_id=char_b_id,
                dimensions={},
                evidence=[],
                aggregate_intensity=0.0,
            )

        # 1. Determine user-locked design dimensions and evidence from existing edge
        locked_dims: Set[ConflictDimension] = set()
        user_evidence: List[ConflictEvidence] = []
        user_dimensions: Dict[ConflictDimension, float] = {}

        if existing_edge:
            if existing_edge.locked_dimensions:
                locked_dims = set(existing_edge.locked_dimensions)
            elif existing_edge.is_locked or existing_edge.authority == FieldAuthority.USER_LOCKED:
                # Edge-level lock: preserve all existing dimensions as user-locked design intent
                locked_dims = set(existing_edge.dimensions.keys())

            for d in locked_dims:
                if d in existing_edge.dimensions:
                    user_dimensions[d] = existing_edge.dimensions[d]

            for ev in existing_edge.evidence:
                if ev.is_user_authored or ev.dimension in locked_dims:
                    if not ev.is_user_authored:
                        ev = ConflictEvidence(
                            dimension=ev.dimension,
                            source_id=ev.source_id,
                            target_id=ev.target_id,
                            description=ev.description,
                            metadata=ev.metadata,
                            is_user_authored=True,
                        )
                    user_evidence.append(ev)

        # 2. Freshly derive runtime conflict dimensions and evidence from current canonical state
        runtime_dimensions: Dict[ConflictDimension, float] = {}
        runtime_evidence: List[ConflictEvidence] = []

        # 1. Goal Opposition
        cls._evaluate_goal_opposition(world, char_a, char_b, runtime_dimensions, runtime_evidence)

        # 2. Value Opposition
        cls._evaluate_value_opposition(char_a, char_b, runtime_dimensions, runtime_evidence)

        # 3. Belief Contradiction
        cls._evaluate_belief_contradiction(world, char_a, char_b, runtime_dimensions, runtime_evidence)

        # 4. Resource Competition
        cls._evaluate_resource_competition(world, char_a, char_b, runtime_dimensions, runtime_evidence)

        # 5. Secret Exposure Risk
        cls._evaluate_secret_exposure_risk(world, char_a, char_b, runtime_dimensions, runtime_evidence)

        # 6. Relationship Tension
        cls._evaluate_relationship_tension(world, char_a, char_b, runtime_dimensions, runtime_evidence)

        # 7. Dependency
        cls._evaluate_dependency(world, char_a, char_b, runtime_dimensions, runtime_evidence)

        # 8. Historical Grievance
        cls._evaluate_historical_grievance(world, char_a, char_b, runtime_dimensions, runtime_evidence)

        # 9. Power Conflict
        cls._evaluate_power_conflict(world, char_a, char_b, runtime_dimensions, runtime_evidence)

        # 10. Moral Conflict
        cls._evaluate_moral_conflict(char_a, char_b, runtime_dimensions, runtime_evidence)

        # 3. Merge: Unlocked dimensions use fresh derivation; locked dimensions preserve design intent
        merged_dimensions: Dict[ConflictDimension, float] = dict(runtime_dimensions)
        for d in locked_dims:
            if d in user_dimensions:
                merged_dimensions[d] = user_dimensions[d]

        merged_evidence: List[ConflictEvidence] = list(user_evidence)
        for ev in runtime_evidence:
            merged_evidence.append(ev)

        # 4. Recompute Aggregate Intensity from final merged dimensions
        agg_intensity = 0.0
        if merged_dimensions:
            raw_sum = sum(merged_dimensions.values())
            scale_factor = max(1.0, len(merged_dimensions) * 0.6)
            agg_intensity = round(min(1.0, raw_sum / scale_factor), 2)

        is_edge_locked = bool(locked_dims)
        if is_edge_locked:
            edge_authority = FieldAuthority.USER_LOCKED
        elif existing_edge and existing_edge.authority == FieldAuthority.USER_PREFERRED:
            edge_authority = FieldAuthority.USER_PREFERRED
        else:
            edge_authority = FieldAuthority.SYSTEM_INFERRED

        return ConflictEdge(
            source_character_id=char_a_id,
            target_character_id=char_b_id,
            dimensions=merged_dimensions,
            evidence=merged_evidence,
            aggregate_intensity=agg_intensity,
            last_updated=datetime.now(timezone.utc).isoformat(),
            is_analytical_only=True,
            authority=edge_authority,
            is_locked=is_edge_locked,
            locked_dimensions=sorted(list(locked_dims), key=lambda d: d.value),
        )

    @classmethod
    def derive_conflict_graph(
        cls,
        world: WorldState,
        project_id: str,
        existing_graph: Optional[ConflictGraph] = None,
    ) -> ConflictGraph:
        """Derive full ConflictGraph for all character pairs in the world."""
        existing_edges_map: Dict[Tuple[str, str], ConflictEdge] = {}
        if existing_graph:
            for e in existing_graph.edges:
                existing_edges_map[(e.source_character_id, e.target_character_id)] = e

        char_ids = sorted(list(world.characters.keys()))
        edges: List[ConflictEdge] = []

        # Derive pairwise edges for all distinct character pairs (undirected pairing with canonical edge)
        for i in range(len(char_ids)):
            for j in range(i + 1, len(char_ids)):
                c1_id = char_ids[i]
                c2_id = char_ids[j]
                existing_e = existing_edges_map.get((c1_id, c2_id)) or existing_edges_map.get((c2_id, c1_id))
                edge = cls.derive_pairwise_conflict(world, c1_id, c2_id, existing_edge=existing_e)
                edges.append(edge)

        return ConflictGraph(
            project_id=project_id,
            edges=edges,
            generated_at=datetime.now(timezone.utc).isoformat(),
            derived_at_tick=world.current_tick,
        )

    # -------------------------------------------------------------------------
    # Dimension Evaluators
    # -------------------------------------------------------------------------

    @classmethod
    def _evaluate_goal_opposition(
        cls,
        world: WorldState,
        char_a: Character,
        char_b: Character,
        dimensions: Dict[ConflictDimension, float],
        evidence: List[ConflictEvidence],
    ) -> None:
        all_goals_a = world.get_character_goals(char_a.id)
        all_goals_b = world.get_character_goals(char_b.id)
        active_goals_a = [g for g in all_goals_a if g.status == GoalStatus.ACTIVE]
        active_goals_b = [g for g in all_goals_b if g.status == GoalStatus.ACTIVE]

        # Include conscious_want from dynamics as fallback only if character has no registered goals in world
        wants_a = [char_a.dynamics.conscious_want] if (char_a.dynamics and char_a.dynamics.conscious_want and not all_goals_a) else []
        wants_b = [char_b.dynamics.conscious_want] if (char_b.dynamics and char_b.dynamics.conscious_want and not all_goals_b) else []

        max_opp_score = 0.0

        all_a_descs = [(g.id, g.description, g.priority) for g in active_goals_a] + [("want_a", w, 0.7) for w in wants_a]
        all_b_descs = [(g.id, g.description, g.priority) for g in active_goals_b] + [("want_b", w, 0.7) for w in wants_b]

        for id_a, desc_a, prio_a in all_a_descs:
            words_a = set(re.findall(r"\w+", desc_a.lower()))
            for id_b, desc_b, prio_b in all_b_descs:
                words_b = set(re.findall(r"\w+", desc_b.lower()))

                # Check verb opposition pairs
                for set1, set2 in OPPOSING_GOAL_VERB_PAIRS:
                    opposed = (words_a & set1 and words_b & set2) or (words_a & set2 and words_b & set1)
                    if opposed:
                        score = round(min(1.0, 0.5 + 0.5 * max(prio_a, prio_b)), 2)
                        max_opp_score = max(max_opp_score, score)
                        evidence.append(
                            ConflictEvidence(
                                dimension=ConflictDimension.GOAL_OPPOSITION,
                                source_id=id_a,
                                target_id=id_b,
                                description=f"Opposing objectives: '{desc_a}' vs '{desc_b}'",
                                metadata={"actor_a": char_a.name, "actor_b": char_b.name, "score": score},
                            )
                        )
                        break

                # Check cross-reference antagonistic targeting
                if char_b.name.lower() in desc_a.lower() and any(k in desc_a.lower() for k in ["confront", "expose", "investigate", "accuse", "stop"]):
                    score = round(min(1.0, 0.6 + 0.4 * prio_a), 2)
                    max_opp_score = max(max_opp_score, score)
                    evidence.append(
                        ConflictEvidence(
                            dimension=ConflictDimension.GOAL_OPPOSITION,
                            source_id=id_a,
                            target_id=char_b.id,
                            description=f"{char_a.name}'s goal directly targets {char_b.name}: '{desc_a}'",
                            metadata={"actor_a": char_a.name, "actor_b": char_b.name, "score": score},
                        )
                    )

        if max_opp_score > 0.0:
            dimensions[ConflictDimension.GOAL_OPPOSITION] = max_opp_score

    @classmethod
    def _evaluate_value_opposition(
        cls,
        char_a: Character,
        char_b: Character,
        dimensions: Dict[ConflictDimension, float],
        evidence: List[ConflictEvidence],
    ) -> None:
        if not char_a.dynamics or not char_b.dynamics:
            return

        values_a = [v.lower().strip() for v in [char_a.dynamics.core_value, char_a.dynamics.shadow_value] if v]
        values_b = [v.lower().strip() for v in [char_b.dynamics.core_value, char_b.dynamics.shadow_value] if v]

        max_val_score = 0.0

        for va in values_a:
            words_a = set(re.findall(r"\w+", va))
            for vb in values_b:
                words_b = set(re.findall(r"\w+", vb))
                for set1, set2 in OPPOSING_VALUE_PAIRS:
                    if (words_a & set1 and words_b & set2) or (words_a & set2 and words_b & set1):
                        score = 0.75
                        max_val_score = max(max_val_score, score)
                        evidence.append(
                            ConflictEvidence(
                                dimension=ConflictDimension.VALUE_OPPOSITION,
                                source_id=f"val_{va}",
                                target_id=f"val_{vb}",
                                description=f"Fundamental value clash: '{va}' ({char_a.name}) vs '{vb}' ({char_b.name})",
                                metadata={"actor_a": char_a.name, "actor_b": char_b.name, "value_a": va, "value_b": vb},
                            )
                        )

        if max_val_score > 0.0:
            dimensions[ConflictDimension.VALUE_OPPOSITION] = max_val_score

    @classmethod
    def _evaluate_belief_contradiction(
        cls,
        world: WorldState,
        char_a: Character,
        char_b: Character,
        dimensions: Dict[ConflictDimension, float],
        evidence: List[ConflictEvidence],
    ) -> None:
        beliefs_a = world.get_character_beliefs(char_a.id)
        beliefs_b = world.get_character_beliefs(char_b.id)

        max_belief_score = 0.0

        for ba in beliefs_a:
            sa = ba.statement.lower()
            for bb in beliefs_b:
                sb = bb.statement.lower()

                # Contradiction pattern 1: One believes other is lying / guilty / framed
                if (char_b.name.lower() in sa and any(w in sa for w in ["lying", "guilty", "fraud", "stole", "corrupt"])) or (
                    char_a.name.lower() in sb and any(w in sb for w in ["lying", "guilty", "fraud", "stole", "corrupt"])
                ):
                    score = round(min(1.0, 0.4 + 0.3 * (ba.confidence + bb.confidence)), 2)
                    max_belief_score = max(max_belief_score, score)
                    evidence.append(
                        ConflictEvidence(
                            dimension=ConflictDimension.BELIEF_CONTRADICTION,
                            source_id=ba.id,
                            target_id=bb.id,
                            description=f"Accusatory belief contradiction: '{ba.statement}' vs '{bb.statement}'",
                            metadata={"actor_a": char_a.name, "actor_b": char_b.name, "score": score},
                        )
                    )

                # Contradiction pattern 2: Polar opposite assertions about same topic
                common_tokens = set(re.findall(r"\w+", sa)) & set(re.findall(r"\w+", sb))
                neg_words = {"not", "never", "innocent", "false", "denies", "did not"}
                if common_tokens - {"the", "is", "a", "an", "and", "in", "to", "that", "of"}:
                    has_neg_a = any(nw in sa for nw in neg_words)
                    has_neg_b = any(nw in sb for nw in neg_words)
                    if has_neg_a != has_neg_b and ba.confidence > 0.5 and bb.confidence > 0.5:
                        score = round(min(1.0, 0.3 + 0.35 * (ba.confidence + bb.confidence)), 2)
                        max_belief_score = max(max_belief_score, score)
                        evidence.append(
                            ConflictEvidence(
                                dimension=ConflictDimension.BELIEF_CONTRADICTION,
                                source_id=ba.id,
                                target_id=bb.id,
                                description=f"Contradictory factual beliefs regarding common subject: '{ba.statement}' vs '{bb.statement}'",
                                metadata={"actor_a": char_a.name, "actor_b": char_b.name, "score": score},
                            )
                        )

        if max_belief_score > 0.0:
            dimensions[ConflictDimension.BELIEF_CONTRADICTION] = max_belief_score

    @classmethod
    def _evaluate_resource_competition(
        cls,
        world: WorldState,
        char_a: Character,
        char_b: Character,
        dimensions: Dict[ConflictDimension, float],
        evidence: List[ConflictEvidence],
    ) -> None:
        goals_a = world.get_character_goals(char_a.id)
        goals_b = world.get_character_goals(char_b.id)

        all_text_a = " ".join([g.description for g in goals_a] + char_a.inventory)
        all_text_b = " ".join([g.description for g in goals_b] + char_b.inventory)

        max_res_score = 0.0

        for obj in world.objects.values():
            name_lower = obj.name.lower()
            in_a = (name_lower in all_text_a.lower()) or (obj.holder_id == char_a.id)
            in_b = (name_lower in all_text_b.lower()) or (obj.holder_id == char_b.id)

            if in_a and in_b:
                # Contested resource
                score = 0.70
                if obj.holder_id in (char_a.id, char_b.id):
                    # One holds what both want
                    score = 0.85
                max_res_score = max(max_res_score, score)
                evidence.append(
                    ConflictEvidence(
                        dimension=ConflictDimension.RESOURCE_COMPETITION,
                        source_id=obj.id,
                        target_id=None,
                        description=f"Both characters contend for possession of '{obj.name}'",
                        metadata={"object_id": obj.id, "object_name": obj.name, "holder": obj.holder_id},
                    )
                )

        if max_res_score > 0.0:
            dimensions[ConflictDimension.RESOURCE_COMPETITION] = max_res_score

    @classmethod
    def _evaluate_secret_exposure_risk(
        cls,
        world: WorldState,
        char_a: Character,
        char_b: Character,
        dimensions: Dict[ConflictDimension, float],
        evidence: List[ConflictEvidence],
    ) -> None:
        secrets_a = world.get_character_secrets(char_a.id)
        secrets_b = world.get_character_secrets(char_b.id)

        max_sec_score = 0.0

        # Does A hold a secret referencing B that B doesn't yet know?
        for sa in secrets_a:
            if char_b.name.lower() in sa.statement.lower() and char_b.id not in sa.known_by:
                score = round(min(1.0, 0.5 + 0.4 * sa.importance), 2)
                max_sec_score = max(max_sec_score, score)
                evidence.append(
                    ConflictEvidence(
                        dimension=ConflictDimension.SECRET_EXPOSURE_RISK,
                        source_id=sa.id,
                        target_id=char_b.id,
                        description=f"{char_a.name} holds compromising secret involving {char_b.name}",
                        metadata={"holder": char_a.name, "target": char_b.name, "importance": sa.importance},
                    )
                )

        # Does B hold a secret referencing A that A doesn't yet know?
        for sb in secrets_b:
            if char_a.name.lower() in sb.statement.lower() and char_a.id not in sb.known_by:
                score = round(min(1.0, 0.5 + 0.4 * sb.importance), 2)
                max_sec_score = max(max_sec_score, score)
                evidence.append(
                    ConflictEvidence(
                        dimension=ConflictDimension.SECRET_EXPOSURE_RISK,
                        source_id=sb.id,
                        target_id=char_a.id,
                        description=f"{char_b.name} holds compromising secret involving {char_a.name}",
                        metadata={"holder": char_b.name, "target": char_a.name, "importance": sb.importance},
                    )
                )

        if max_sec_score > 0.0:
            dimensions[ConflictDimension.SECRET_EXPOSURE_RISK] = max_sec_score

    @classmethod
    def _evaluate_relationship_tension(
        cls,
        world: WorldState,
        char_a: Character,
        char_b: Character,
        dimensions: Dict[ConflictDimension, float],
        evidence: List[ConflictEvidence],
    ) -> None:
        rel = world.get_relationship(char_a.id, char_b.id)
        if not rel:
            return

        tension_indicators = []
        if rel.resentment > 0.15:
            tension_indicators.append(f"resentment={rel.resentment:.2f}")
        if rel.suspicion > 0.15:
            tension_indicators.append(f"suspicion={rel.suspicion:.2f}")
        if rel.affinity < -0.15:
            tension_indicators.append(f"hostility={-rel.affinity:.2f}")
        if rel.trust < -0.15:
            tension_indicators.append(f"distrust={-rel.trust:.2f}")

        if tension_indicators:
            raw_tension = (
                max(0.0, rel.resentment)
                + max(0.0, rel.suspicion)
                + max(0.0, -rel.affinity)
                + max(0.0, -rel.trust)
            ) / 2.0
            score = round(min(1.0, max(0.25, raw_tension)), 2)
            dimensions[ConflictDimension.RELATIONSHIP_TENSION] = score
            evidence.append(
                ConflictEvidence(
                    dimension=ConflictDimension.RELATIONSHIP_TENSION,
                    source_id=rel.id,
                    target_id=None,
                    description=f"Interpersonal strain: {', '.join(tension_indicators)}",
                    metadata={"relationship_id": rel.id, "metrics": tension_indicators, "score": score},
                )
            )

    @classmethod
    def _evaluate_dependency(
        cls,
        world: WorldState,
        char_a: Character,
        char_b: Character,
        dimensions: Dict[ConflictDimension, float],
        evidence: List[ConflictEvidence],
    ) -> None:
        rel = world.get_relationship(char_a.id, char_b.id)
        if not rel:
            return

        if abs(rel.dependency) > 0.25:
            score = round(min(1.0, abs(rel.dependency)), 2)
            dimensions[ConflictDimension.DEPENDENCY] = score
            direction_desc = (
                f"{char_a.name} is reliant upon {char_b.name}"
                if rel.dependency > 0
                else f"{char_b.name} is reliant upon {char_a.name}"
            )
            evidence.append(
                ConflictEvidence(
                    dimension=ConflictDimension.DEPENDENCY,
                    source_id=rel.id,
                    target_id=None,
                    description=f"Asymmetrical interpersonal reliance: {direction_desc} (dependency={rel.dependency:.2f})",
                    metadata={"relationship_id": rel.id, "dependency": rel.dependency},
                )
            )

    @classmethod
    def _evaluate_historical_grievance(
        cls,
        world: WorldState,
        char_a: Character,
        char_b: Character,
        dimensions: Dict[ConflictDimension, float],
        evidence: List[ConflictEvidence],
    ) -> None:
        rel = world.get_relationship(char_a.id, char_b.id)
        if not rel or not rel.history:
            return

        hist_lower = rel.history.lower()
        matched_grievances = [kw for kw in GRIEVANCE_KEYWORDS if kw in hist_lower]

        if matched_grievances:
            score = round(min(1.0, 0.45 + 0.15 * len(matched_grievances)), 2)
            dimensions[ConflictDimension.HISTORICAL_GRIEVANCE] = score
            evidence.append(
                ConflictEvidence(
                    dimension=ConflictDimension.HISTORICAL_GRIEVANCE,
                    source_id=rel.id,
                    target_id=None,
                    description=f"Past history carries grievance markers: {', '.join(matched_grievances)} ('{rel.history}')",
                    metadata={"relationship_id": rel.id, "matched_keywords": matched_grievances},
                )
            )

    @classmethod
    def _evaluate_power_conflict(
        cls,
        world: WorldState,
        char_a: Character,
        char_b: Character,
        dimensions: Dict[ConflictDimension, float],
        evidence: List[ConflictEvidence],
    ) -> None:
        rel = world.get_relationship(char_a.id, char_b.id)
        role_a = (char_a.role or "").lower()
        role_b = (char_b.role or "").lower()

        max_power_score = 0.0

        if rel and abs(rel.power_imbalance) > 0.25:
            score = round(min(1.0, abs(rel.power_imbalance)), 2)
            max_power_score = max(max_power_score, score)
            dominant = char_a.name if rel.power_imbalance > 0 else char_b.name
            subordinate = char_b.name if rel.power_imbalance > 0 else char_a.name
            evidence.append(
                ConflictEvidence(
                    dimension=ConflictDimension.POWER_CONFLICT,
                    source_id=rel.id,
                    target_id=None,
                    description=f"Explicit power hierarchy: {dominant} holds structural dominance over {subordinate} ({rel.power_imbalance:+.2f})",
                    metadata={"relationship_id": rel.id, "power_imbalance": rel.power_imbalance},
                )
            )

        words_a = set(re.findall(r"\w+", role_a))
        words_b = set(re.findall(r"\w+", role_b))

        for set1, set2 in HIERARCHY_ROLE_PAIRS:
            if (words_a & set1 and words_b & set2) or (words_a & set2 and words_b & set1):
                score = 0.65
                max_power_score = max(max_power_score, score)
                evidence.append(
                    ConflictEvidence(
                        dimension=ConflictDimension.POWER_CONFLICT,
                        source_id=f"role_{char_a.id}",
                        target_id=f"role_{char_b.id}",
                        description=f"Role asymmetry: '{char_a.role}' vs '{char_b.role}'",
                        metadata={"role_a": char_a.role, "role_b": char_b.role},
                    )
                )
                break

        if max_power_score > 0.0:
            dimensions[ConflictDimension.POWER_CONFLICT] = max_power_score

    @classmethod
    def _evaluate_moral_conflict(
        cls,
        char_a: Character,
        char_b: Character,
        dimensions: Dict[ConflictDimension, float],
        evidence: List[ConflictEvidence],
    ) -> None:
        if not char_a.dynamics or not char_b.dynamics:
            return

        mb_a = (char_a.dynamics.moral_boundary or "").lower()
        mb_b = (char_b.dynamics.moral_boundary or "").lower()

        strat_a = (char_a.dynamics.conflict_strategy or "").lower()
        strat_b = (char_b.dynamics.conflict_strategy or "").lower()

        shadow_a = (char_a.dynamics.shadow_value or "").lower()
        shadow_b = (char_b.dynamics.shadow_value or "").lower()

        max_moral_score = 0.0

        # Check if A's moral boundary forbids B's strategy or shadow value
        if mb_a:
            for bad_kw in ["lie", "deceive", "harm", "manipulate", "betray", "steal"]:
                if bad_kw in mb_a and (bad_kw in strat_b or bad_kw in shadow_b):
                    score = 0.70
                    max_moral_score = max(max_moral_score, score)
                    evidence.append(
                        ConflictEvidence(
                            dimension=ConflictDimension.MORAL_CONFLICT,
                            source_id=f"moral_{char_a.id}",
                            target_id=f"dynamics_{char_b.id}",
                            description=f"{char_a.name}'s moral boundary ('{char_a.dynamics.moral_boundary}') condemns {char_b.name}'s strategy/shadow value ('{char_b.dynamics.conflict_strategy or char_b.dynamics.shadow_value}')",
                            metadata={"actor_a": char_a.name, "actor_b": char_b.name},
                        )
                    )

        # Check reverse: B's moral boundary forbids A's strategy or shadow value
        if mb_b:
            for bad_kw in ["lie", "deceive", "harm", "manipulate", "betray", "steal"]:
                if bad_kw in mb_b and (bad_kw in strat_a or bad_kw in shadow_a):
                    score = 0.70
                    max_moral_score = max(max_moral_score, score)
                    evidence.append(
                        ConflictEvidence(
                            dimension=ConflictDimension.MORAL_CONFLICT,
                            source_id=f"moral_{char_b.id}",
                            target_id=f"dynamics_{char_a.id}",
                            description=f"{char_b.name}'s moral boundary ('{char_b.dynamics.moral_boundary}') condemns {char_a.name}'s strategy/shadow value ('{char_a.dynamics.conflict_strategy or char_a.dynamics.shadow_value}')",
                            metadata={"actor_a": char_b.name, "actor_b": char_a.name},
                        )
                    )

        if max_moral_score > 0.0:
            dimensions[ConflictDimension.MORAL_CONFLICT] = max_moral_score
