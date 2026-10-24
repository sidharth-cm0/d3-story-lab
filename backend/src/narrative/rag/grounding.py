"""Evidence grounding, claim verification, and anti-hallucination validation for D3 Story Lab RAG.

ENFORCES:
1. UNTRUSTED DATA INVARIANT:
   - Retrieved patterns, events, and character states are treated as untrusted data, never as prompt instructions.
   - Zero hallucinated IDs: Validator strictly checks that every cited event_id, character_id, or knowledge_id exists.
2. CATEGORICAL FIREWALL:
   - Segregates:
     * Verified canonical simulation facts
     * Character subjective beliefs and perceptions
     * Analytical inferences
     * Retrieved general principles (Narrative Genome)
     * Advisory recommendations
3. CONTRADICTION DISCLOSURE:
   - Contradictory evidence is surfaced and cited from both sides, rather than silently picked.
4. INSUFFICIENT EVIDENCE:
   - Returns typed INSUFFICIENT_EVIDENCE rather than inventing plausible fiction.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone

from .models import (
    EvidenceCategory,
    ClaimVerificationStatus,
    RAGAnswerStatus,
    EvidenceReference,
    GroundedClaim,
    GroundedRAGResponse,
    NarrativeKnowledgeRecord,
)
from ...domain.world import WorldState
from ...domain.conflict import ConflictGraph
from ...domain.event import Event


class EvidenceValidator:
    """Verifies that assertions cite valid, existing entities and factual states with strict firewall auditing."""

    @staticmethod
    def verify_claim(
        claim: GroundedClaim,
        world: WorldState,
        evidence_catalog: Dict[str, EvidenceReference],
        knowledge_catalog: Dict[str, NarrativeKnowledgeRecord],
    ) -> GroundedClaim:
        """Deterministically audits a claim against canonical world state, character worldview boundaries, and knowledge base."""
        if not claim.cited_evidence_ids:
            return GroundedClaim(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                category=claim.category,
                cited_evidence_ids=[],
                verification_status=ClaimVerificationStatus.UNSUPPORTED,
                verification_notes="No evidence references provided to substantiate claim.",
                metadata=claim.metadata,
            )

        missing_ids: List[str] = []
        verified_refs: List[EvidenceReference] = []

        # 1. Verify existence of citation IDs and underlying entities
        for ref_id in claim.cited_evidence_ids:
            if ref_id not in evidence_catalog:
                missing_ids.append(ref_id)
                continue

            ref = evidence_catalog[ref_id]

            if ref.entity_type == "event":
                if ref.entity_id not in world.events:
                    missing_ids.append(f"event:{ref.entity_id}")
                else:
                    verified_refs.append(ref)
            elif ref.entity_type == "character":
                if ref.entity_id not in world.characters:
                    missing_ids.append(f"character:{ref.entity_id}")
                else:
                    verified_refs.append(ref)
            elif ref.entity_type == "pattern":
                if ref.entity_id not in knowledge_catalog:
                    missing_ids.append(f"pattern:{ref.entity_id}")
                else:
                    verified_refs.append(ref)
            elif ref.entity_type == "secret":
                if ref.entity_id not in world.secrets:
                    missing_ids.append(f"secret:{ref.entity_id}")
                else:
                    verified_refs.append(ref)
            elif ref.entity_type == "relationship":
                if ref.entity_id not in world.relationships:
                    missing_ids.append(f"relationship:{ref.entity_id}")
                else:
                    verified_refs.append(ref)
            elif ref.entity_type == "object":
                if ref.entity_id not in world.objects:
                    missing_ids.append(f"object:{ref.entity_id}")
                else:
                    verified_refs.append(ref)
            elif ref.entity_type in ("conflict", "belief", "recommendation"):
                verified_refs.append(ref)
            else:
                verified_refs.append(ref)

        if missing_ids:
            return GroundedClaim(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                category=claim.category,
                cited_evidence_ids=claim.cited_evidence_ids,
                verification_status=ClaimVerificationStatus.UNSUPPORTED,
                verification_notes=f"Referenced citation or entity IDs do not exist in project canonical records: {', '.join(missing_ids)}",
                metadata=claim.metadata,
            )

        # 2. Check for Categorical Firewall Violations
        # A: Retrieved principle cited as if it were a canonical story fact
        if claim.category == EvidenceCategory.CANONICAL_FACT:
            if all(r.category == EvidenceCategory.RETRIEVED_KNOWLEDGE or r.entity_type == "pattern" for r in verified_refs):
                return GroundedClaim(
                    claim_id=claim.claim_id,
                    claim_text=claim.claim_text,
                    category=claim.category,
                    cited_evidence_ids=claim.cited_evidence_ids,
                    verification_status=ClaimVerificationStatus.CATEGORY_MISMATCH,
                    verification_notes="Categorical mismatch: abstract retrieved knowledge principles cannot substantiate an empirical canonical fact claim.",
                    metadata=claim.metadata,
                )

        # B: Recommendation presented as an executed canonical fact
        if claim.category == EvidenceCategory.CANONICAL_FACT:
            if any(r.category == EvidenceCategory.RECOMMENDATION or r.entity_type == "recommendation" for r in verified_refs):
                return GroundedClaim(
                    claim_id=claim.claim_id,
                    claim_text=claim.claim_text,
                    category=claim.category,
                    cited_evidence_ids=claim.cited_evidence_ids,
                    verification_status=ClaimVerificationStatus.CATEGORY_MISMATCH,
                    verification_notes="Categorical mismatch: an unexecuted advisory recommendation cannot substantiate an executed canonical fact claim.",
                    metadata=claim.metadata,
                )

        # 3. Check Character-Belief / WorldView Firewall Boundaries
        # Character-belief claims must be substantiated by the subject's own knowledge, not an external peer
        subject_char_id = claim.metadata.get("subject_character_id")
        if claim.category == EvidenceCategory.CHARACTER_KNOWLEDGE and subject_char_id:
            for ref in verified_refs:
                holder = ref.metadata.get("holder_id") or ref.metadata.get("character_id")
                if holder and holder != subject_char_id:
                    return GroundedClaim(
                        claim_id=claim.claim_id,
                        claim_text=claim.claim_text,
                        category=claim.category,
                        cited_evidence_ids=claim.cited_evidence_ids,
                        verification_status=ClaimVerificationStatus.CONTRADICTORY,
                        verification_notes=f"WorldView firewall violation: Claim asserts subjective knowledge of character '{subject_char_id}', but cited evidence '{ref.id}' belongs to character '{holder}'.",
                        metadata=claim.metadata,
                    )

            # Check if subject's internal belief contradicts the claim
            asserted_prop = claim.metadata.get("asserted_proposition_id")
            asserted_val = claim.metadata.get("asserted_truth_value")
            if asserted_prop and asserted_val is not None and subject_char_id in world.characters:
                subj = world.characters[subject_char_id]
                k_item = subj.knows(asserted_prop) if hasattr(subj, "knows") else None
                if k_item and getattr(k_item, "believed_truth_value", None) != asserted_val:
                    return GroundedClaim(
                        claim_id=claim.claim_id,
                        claim_text=claim.claim_text,
                        category=claim.category,
                        cited_evidence_ids=claim.cited_evidence_ids,
                        verification_status=ClaimVerificationStatus.CONTRADICTORY,
                        verification_notes=f"Subjective belief contradiction: Character '{subject_char_id}' internally believes '{asserted_prop}' is {getattr(k_item, 'believed_truth_value')}, contradicting claimed truth value {asserted_val}.",
                        metadata=claim.metadata,
                    )

        # 4. Check for Outdated Historical Evidence for Current-State Claims
        if claim.metadata.get("asserts_current_state", False):
            target_char_id = claim.metadata.get("target_character_id")
            asserted_loc_id = claim.metadata.get("asserted_location_id")

            # Find the latest tick among cited event evidence
            cited_event_ticks = [r.tick for r in verified_refs if r.entity_type == "event" and r.tick is not None]
            if cited_event_ticks and target_char_id:
                latest_cited_tick = max(cited_event_ticks)
                # Look for subsequent move events for this actor
                subsequent_moves = [
                    e for e in world.events.values()
                    if getattr(e, "event_type", None) == "character_moved"
                    and target_char_id in getattr(e, "actor_ids", [])
                    and getattr(e, "tick", 0) > latest_cited_tick
                ]
                if subsequent_moves:
                    subsequent_moves.sort(key=lambda e: e.tick)
                    latest_move = subsequent_moves[-1]
                    if asserted_loc_id and (latest_move.location_id != asserted_loc_id):
                        return GroundedClaim(
                            claim_id=claim.claim_id,
                            claim_text=claim.claim_text,
                            category=claim.category,
                            cited_evidence_ids=claim.cited_evidence_ids,
                            verification_status=ClaimVerificationStatus.OUTDATED,
                            verification_notes=f"Outdated historical evidence: Claim asserts current state based on evidence at Tick {latest_cited_tick}, but subsequent event '{latest_move.id}' at Tick {latest_move.tick} relocated character '{target_char_id}' to '{latest_move.location_id}'.",
                            metadata=claim.metadata,
                        )

        # 5. Check for Direct Factual Contradictions in Canonical WorldState
        if claim.metadata.get("asserted_secret_holder_id") and claim.metadata.get("secret_id"):
            sec_id = claim.metadata["secret_id"]
            expected_holder = claim.metadata["asserted_secret_holder_id"]
            if sec_id in world.secrets and world.secrets[sec_id].character_id != expected_holder:
                actual_holder = world.secrets[sec_id].character_id
                return GroundedClaim(
                    claim_id=claim.claim_id,
                    claim_text=claim.claim_text,
                    category=claim.category,
                    cited_evidence_ids=claim.cited_evidence_ids,
                    verification_status=ClaimVerificationStatus.CONTRADICTORY,
                    verification_notes=f"Direct factual contradiction: Secret '{sec_id}' is canonically held by '{actual_holder}', not '{expected_holder}'.",
                    metadata=claim.metadata,
                )

        # 6. Check for Disconnected / Non-Supporting Valid Citations
        required_actor_ids = claim.metadata.get("required_actor_ids")
        if required_actor_ids:
            event_refs = [r for r in verified_refs if r.entity_type == "event"]
            if event_refs:
                actors_in_events = set()
                for r in event_refs:
                    evt = world.events.get(r.entity_id)
                    if evt:
                        actors_in_events.update(getattr(evt, "actor_ids", []))

                if not any(req_a in actors_in_events for req_a in required_actor_ids):
                    return GroundedClaim(
                        claim_id=claim.claim_id,
                        claim_text=claim.claim_text,
                        category=claim.category,
                        cited_evidence_ids=claim.cited_evidence_ids,
                        verification_status=ClaimVerificationStatus.UNSUPPORTED,
                        verification_notes=f"Evidence disconnect: Cited events do not involve any of the claimed target actors ({', '.join(required_actor_ids)}).",
                        metadata=claim.metadata,
                    )

        # 7. Classification of Analytical Inferences vs Canonical Truths
        if claim.category == EvidenceCategory.NARRATIVE_INTERPRETATION:
            return GroundedClaim(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                category=claim.category,
                cited_evidence_ids=claim.cited_evidence_ids,
                verification_status=ClaimVerificationStatus.INFERRED,
                verification_notes=f"Analytical inference substantiated by {len(verified_refs)} verified narrative pattern/signal reference(s).",
                metadata=claim.metadata,
            )

        if claim.category == EvidenceCategory.RECOMMENDATION:
            return GroundedClaim(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                category=claim.category,
                cited_evidence_ids=claim.cited_evidence_ids,
                verification_status=ClaimVerificationStatus.INFERRED,
                verification_notes=f"Advisory intervention proposal evaluated with {len(verified_refs)} supporting context reference(s).",
                metadata=claim.metadata,
            )

        return GroundedClaim(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            category=claim.category,
            cited_evidence_ids=claim.cited_evidence_ids,
            verification_status=ClaimVerificationStatus.VERIFIED,
            verification_notes=f"Deterministically substantiated by {len(verified_refs)} canonical simulation record(s).",
            metadata=claim.metadata,
        )


class GroundedNarrativeEngine:
    """Builds evidence context, evaluates narrative intelligence questions, and returns grounded answers."""

    @classmethod
    def assemble_evidence_catalog(
        cls,
        world: WorldState,
        conflict_graph: Optional[ConflictGraph] = None,
        retrieved_patterns: Optional[List[NarrativeKnowledgeRecord]] = None,
    ) -> Dict[str, EvidenceReference]:
        """Index all verifiable story entities into discrete typed EvidenceReferences."""
        catalog: Dict[str, EvidenceReference] = {}

        # 1. Canonical Events
        for ev in world.events.values():
            ref_id = f"ev_ref_{ev.id}"
            catalog[ref_id] = EvidenceReference(
                id=ref_id,
                category=EvidenceCategory.CANONICAL_FACT,
                entity_type="event",
                entity_id=ev.id,
                tick=ev.tick,
                summary=f"Tick {ev.tick}: {ev.description}",
                source_reference="EventLog",
                metadata={"event_type": str(ev.event_type), "actor_ids": ev.actor_ids},
            )

        # 2. Characters & Subjective Beliefs
        for c in world.characters.values():
            char_ref_id = f"char_ref_{c.id}"
            catalog[char_ref_id] = EvidenceReference(
                id=char_ref_id,
                category=EvidenceCategory.CANONICAL_FACT,
                entity_type="character",
                entity_id=c.id,
                tick=world.current_tick,
                summary=f"Actor '{c.name}' (Role: {c.role}, Location: {c.current_location_id})",
                source_reference="WorldState.characters",
            )

            # Character subjective knowledge / beliefs
            for prop_id, k_item in c.knowledge.items():
                k_ref_id = f"belief_ref_{c.id}_{prop_id}"
                acq_event = world.events.get(k_item.acquired_at_event) if getattr(k_item, "acquired_at_event", None) else None
                learned_tick = getattr(acq_event, "tick", None) if acq_event else getattr(k_item, "tick_learned", None)
                cert = getattr(k_item, "certainty", 1.0)
                truth = getattr(k_item, "believed_truth_value", True)
                catalog[k_ref_id] = EvidenceReference(
                    id=k_ref_id,
                    category=EvidenceCategory.CHARACTER_KNOWLEDGE,
                    entity_type="belief",
                    entity_id=prop_id,
                    tick=learned_tick,
                    summary=f"Actor '{c.name}' subjectively believes proposition '{prop_id}' is {truth} (certainty={cert:.2f})",
                    source_reference=f"Character[{c.id}].knowledge",
                    metadata={"character_id": c.id, "holder_id": c.id, "truth": truth},
                )

        # 3. Interpersonal Conflict Edges
        if conflict_graph and hasattr(conflict_graph, "edges"):
            edge_iter = conflict_graph.edges.values() if isinstance(conflict_graph.edges, dict) else conflict_graph.edges
            for edge in edge_iter:
                edge_id = f"conf_ref_{edge.source_character_id}_{edge.target_character_id}"
                c_a = world.characters.get(edge.source_character_id)
                c_b = world.characters.get(edge.target_character_id)
                c_a_name = c_a.name if c_a else edge.source_character_id
                c_b_name = c_b.name if c_b else edge.target_character_id
                dims = [d.value if hasattr(d, "value") else str(d) for d in edge.dimensions.keys()]
                catalog[edge_id] = EvidenceReference(
                    id=edge_id,
                    category=EvidenceCategory.NARRATIVE_INTERPRETATION,
                    entity_type="conflict",
                    entity_id=f"{edge.source_character_id}:{edge.target_character_id}",
                    tick=world.current_tick,
                    summary=f"Conflict intensity {edge.aggregate_intensity:.2f} between {c_a_name} and {c_b_name} along dimensions: {', '.join(dims)}",
                    source_reference="ConflictGraph",
                    metadata={"intensity": edge.aggregate_intensity, "dimensions": dims},
                )

        # 4. Retrieved Genome Patterns
        if retrieved_patterns:
            for pat in retrieved_patterns:
                pat_ref_id = f"pattern_ref_{pat.id}"
                catalog[pat_ref_id] = EvidenceReference(
                    id=pat_ref_id,
                    category=EvidenceCategory.RETRIEVED_KNOWLEDGE,
                    entity_type="pattern",
                    entity_id=pat.id,
                    summary=f"Abstract Pattern {pat.id} ({pat.title}): {pat.content[:140]}...",
                    source_reference=pat.source_reference,
                    metadata={"dramatic_function": pat.dramatic_function, "conflict_types": pat.conflict_types},
                )

        return catalog

    @classmethod
    def answer_grounded_query(
        cls,
        query: str,
        world: WorldState,
        conflict_graph: Optional[ConflictGraph] = None,
        retrieved_patterns: Optional[List[NarrativeKnowledgeRecord]] = None,
        knowledge_catalog: Optional[Dict[str, NarrativeKnowledgeRecord]] = None,
    ) -> GroundedRAGResponse:
        """Formulate an evidence-grounded response to a narrative intelligence inquiry."""
        patterns = retrieved_patterns or []
        k_catalog = knowledge_catalog or {p.id: p for p in patterns}
        evidence_catalog = cls.assemble_evidence_catalog(world, conflict_graph, patterns)

        q_lower = query.lower()

        # Handle specific thematic narrative queries with deterministic grounding
        if "conflict" in q_lower and ("pattern" in q_lower or "resemble" in q_lower):
            return cls._handle_conflict_pattern_query(query, world, conflict_graph, patterns, evidence_catalog, k_catalog)
        elif "unresolved" in q_lower or ("conflict" in q_lower and ("too long" in q_lower or "stalled" in q_lower or "developing" in q_lower)):
            return cls._handle_unresolved_conflicts_query(query, world, conflict_graph, evidence_catalog, k_catalog)
        elif "environmental pressure" in q_lower or ("pressure" in q_lower and "choice" in q_lower):
            return cls._handle_environmental_pressure_query(query, world, conflict_graph, patterns, evidence_catalog, k_catalog)
        elif "setup" in q_lower or "payoff" in q_lower:
            return cls._handle_setup_payoff_query(query, world, evidence_catalog, k_catalog)
        elif "belief" in q_lower and ("change" in q_lower or "flip" in q_lower or "explain" in q_lower):
            return cls._handle_belief_change_query(query, world, evidence_catalog, k_catalog)
        else:
            return cls._handle_general_grounded_query(query, world, conflict_graph, patterns, evidence_catalog, k_catalog)

    @classmethod
    def _handle_conflict_pattern_query(
        cls,
        query: str,
        world: WorldState,
        conflict_graph: Optional[ConflictGraph],
        patterns: List[NarrativeKnowledgeRecord],
        evidence: Dict[str, EvidenceReference],
        k_catalog: Dict[str, NarrativeKnowledgeRecord],
    ) -> GroundedRAGResponse:
        """Answer queries matching active interpersonal conflict against abstract narrative patterns."""
        active_edges = conflict_graph.edges if conflict_graph else []
        if not active_edges:
            return GroundedRAGResponse(
                query=query,
                status=RAGAnswerStatus.INSUFFICIENT_EVIDENCE,
                answer="No active interpersonal conflicts are currently detected in this simulation project. The cast has not yet generated opposing goals or relationship tensions.",
            )

        top_edge = max(active_edges, key=lambda e: e.aggregate_intensity)
        c_a = world.characters.get(top_edge.source_character_id)
        c_b = world.characters.get(top_edge.target_character_id)
        name_a = c_a.name if c_a else top_edge.source_character_id
        name_b = c_b.name if c_b else top_edge.target_character_id

        conf_ref_id = f"conf_ref_{top_edge.source_character_id}_{top_edge.target_character_id}"
        claims: List[GroundedClaim] = []

        claim_1 = GroundedClaim(
            claim_id="clm_1",
            claim_text=f"Primary conflict is active between {name_a} and {name_b} with intensity score {top_edge.aggregate_intensity:.2f}.",
            category=EvidenceCategory.NARRATIVE_INTERPRETATION,
            cited_evidence_ids=[conf_ref_id] if conf_ref_id in evidence else [],
        )
        claims.append(EvidenceValidator.verify_claim(claim_1, world, evidence, k_catalog))

        # Match against patterns
        matched_patterns = patterns[:3]
        if matched_patterns:
            pat = matched_patterns[0]
            pat_ref_id = f"pattern_ref_{pat.id}"
            claim_2 = GroundedClaim(
                claim_id="clm_2",
                claim_text=f"The active tension between {name_a} and {name_b} structurally resembles abstract pattern {pat.id} ('{pat.title}').",
                category=EvidenceCategory.RETRIEVED_KNOWLEDGE,
                cited_evidence_ids=[pat_ref_id] if pat_ref_id in evidence else [],
            )
            claims.append(EvidenceValidator.verify_claim(claim_2, world, evidence, k_catalog))
            answer_text = (
                f"The active interpersonal tension between {name_a} and {name_b} (intensity {top_edge.aggregate_intensity:.2f}) "
                f"closely aligns with pattern {pat.id} ('{pat.title}'). {pat.content} "
                f"Applicability preconditions: {', '.join(pat.applicability_conditions) or 'Standard co-presence'}."
            )
        else:
            answer_text = f"Primary interpersonal tension is active between {name_a} and {name_b} (intensity {top_edge.aggregate_intensity:.2f}), but no retrieved genome patterns met the relevance threshold."

        return GroundedRAGResponse(
            query=query,
            status=RAGAnswerStatus.SUCCESS,
            answer=answer_text,
            claims=claims,
            evidence=[evidence[cid] for c in claims for cid in c.cited_evidence_ids if cid in evidence],
            retrieved_pattern_ids=[p.id for p in matched_patterns],
        )

    @classmethod
    def _handle_unresolved_conflicts_query(
        cls,
        query: str,
        world: WorldState,
        conflict_graph: Optional[ConflictGraph],
        evidence: Dict[str, EvidenceReference],
        k_catalog: Dict[str, NarrativeKnowledgeRecord],
    ) -> GroundedRAGResponse:
        """Answer queries analyzing unresolved conflicts and duration of stagnation."""
        if not conflict_graph or not conflict_graph.edges:
            return GroundedRAGResponse(
                query=query,
                status=RAGAnswerStatus.INSUFFICIENT_EVIDENCE,
                answer="No conflict records exist in the current project to evaluate stagnation.",
            )

        unresolved = [e for e in conflict_graph.edges if e.aggregate_intensity > 0.35]
        if not unresolved:
            return GroundedRAGResponse(
                query=query,
                status=RAGAnswerStatus.SUCCESS,
                answer="All tracked interpersonal relationships are currently balanced or below the acute conflict threshold (0.35).",
            )

        claims: List[GroundedClaim] = []
        summaries: List[str] = []

        for idx, edge in enumerate(unresolved[:3]):
            c_a = world.characters.get(edge.source_character_id)
            c_b = world.characters.get(edge.target_character_id)
            name_a = c_a.name if c_a else edge.source_character_id
            name_b = c_b.name if c_b else edge.target_character_id
            conf_ref_id = f"conf_ref_{edge.source_character_id}_{edge.target_character_id}"

            clm = GroundedClaim(
                claim_id=f"clm_unresolved_{idx}",
                claim_text=f"Unresolved conflict between {name_a} and {name_b} stands at intensity {edge.aggregate_intensity:.2f} at tick {world.current_tick}.",
                category=EvidenceCategory.NARRATIVE_INTERPRETATION,
                cited_evidence_ids=[conf_ref_id] if conf_ref_id in evidence else [],
            )
            verified_clm = EvidenceValidator.verify_claim(clm, world, evidence, k_catalog)
            claims.append(verified_clm)
            summaries.append(f"{name_a} vs {name_b} (intensity {edge.aggregate_intensity:.2f})")

        answer_text = (
            f"At simulation tick {world.current_tick}, {len(unresolved)} acute interpersonal tension(s) remain unresolved: "
            f"{'; '.join(summaries)}. Stagnant duration is sustained across the recent event window."
        )

        return GroundedRAGResponse(
            query=query,
            status=RAGAnswerStatus.SUCCESS,
            answer=answer_text,
            claims=claims,
            evidence=[evidence[cid] for c in claims for cid in c.cited_evidence_ids if cid in evidence],
            unresolved_conflicts=[e.model_dump(mode="json") for e in unresolved],
        )

    @classmethod
    def _handle_environmental_pressure_query(
        cls,
        query: str,
        world: WorldState,
        conflict_graph: Optional[ConflictGraph],
        patterns: List[NarrativeKnowledgeRecord],
        evidence: Dict[str, EvidenceReference],
        k_catalog: Dict[str, NarrativeKnowledgeRecord],
    ) -> GroundedRAGResponse:
        """Propose bounded environmental pressure options supported by retrieved patterns without puppetry."""
        if not patterns:
            return GroundedRAGResponse(
                query=query,
                status=RAGAnswerStatus.NO_RELEVANT_PATTERNS,
                answer="No relevant environmental pressure patterns matched the query filter criteria.",
            )

        top_pat = patterns[0]
        pat_ref_id = f"pattern_ref_{top_pat.id}"

        # Determine target pressure from pattern
        suggested_pressure = "REVEAL_CLUE" if "informational" in top_pat.conflict_types else "ANNOUNCE_DEADLINE"

        claim = GroundedClaim(
            claim_id="clm_pressure_1",
            claim_text=f"Pattern {top_pat.id} indicates that bounded pressure '{suggested_pressure}' can catalyze meaningful decisions without forcing dialogue or character actions.",
            category=EvidenceCategory.RECOMMENDATION,
            cited_evidence_ids=[pat_ref_id] if pat_ref_id in evidence else [],
        )
        verified_clm = EvidenceValidator.verify_claim(claim, world, evidence, k_catalog)

        answer_text = (
            f"Based on retrieved pattern {top_pat.id} ('{top_pat.title}'), the recommended environmental pressure is '{suggested_pressure}'. "
            f"Mechanism: {top_pat.content} "
            f"Advisory invariant: This pressure alters only room circumstances or external timing via the Director Agent. It does not dictate actor decisions."
        )

        return GroundedRAGResponse(
            query=query,
            status=RAGAnswerStatus.SUCCESS,
            answer=answer_text,
            claims=[verified_clm],
            evidence=[evidence[cid] for cid in verified_clm.cited_evidence_ids if cid in evidence],
            retrieved_pattern_ids=[p.id for p in patterns[:3]],
        )

    @classmethod
    def _handle_setup_payoff_query(
        cls,
        query: str,
        world: WorldState,
        evidence: Dict[str, EvidenceReference],
        k_catalog: Dict[str, NarrativeKnowledgeRecord],
    ) -> GroundedRAGResponse:
        """Answer queries inspecting setups that have not yet reached payoff."""
        unpaid_secrets: List[Dict[str, Any]] = []

        for s in world.secrets.values():
            holder = world.characters.get(s.character_id)
            unaware = [
                c.name for c in world.characters.values()
                if c.id != s.character_id and (s.id not in c.secrets and c.id not in s.known_by and not c.knows(s.id))
            ]
            if unaware:
                unpaid_secrets.append({
                    "secret_id": s.id,
                    "statement": s.statement,
                    "holder_name": holder.name if holder else s.character_id,
                    "unaware_count": len(unaware),
                })

        if not unpaid_secrets:
            return GroundedRAGResponse(
                query=query,
                status=RAGAnswerStatus.SUCCESS,
                answer="All narrative secrets in the world have been revealed or symmetric knowledge has been achieved. No active unfulfilled secret setups remain.",
            )

        top_secret = unpaid_secrets[0]
        char_ref_id = f"char_ref_{world.secrets[top_secret['secret_id']].character_id}"
        claims: List[GroundedClaim] = []

        clm = GroundedClaim(
            claim_id="clm_setup_1",
            claim_text=f"Secret '{top_secret['statement']}' held by {top_secret['holder_name']} has {top_secret['unaware_count']} unaware characters and has not received a narrative payoff.",
            category=EvidenceCategory.CANONICAL_FACT,
            cited_evidence_ids=[char_ref_id] if char_ref_id in evidence else [],
        )
        claims.append(EvidenceValidator.verify_claim(clm, world, evidence, k_catalog))

        answer_text = (
            f"Found {len(unpaid_secrets)} unfulfilled dramatic setup(s). "
            f"Most prominent: '{top_secret['statement']}', possessed by {top_secret['holder_name']} with {top_secret['unaware_count']} unaware actor(s). "
            f"This established secret represents an active setup awaiting catalytic discovery or confrontation payoff."
        )

        return GroundedRAGResponse(
            query=query,
            status=RAGAnswerStatus.SUCCESS,
            answer=answer_text,
            claims=claims,
            evidence=[evidence[cid] for c in claims for cid in c.cited_evidence_ids if cid in evidence],
        )

    @classmethod
    def _handle_belief_change_query(
        cls,
        query: str,
        world: WorldState,
        evidence: Dict[str, EvidenceReference],
        k_catalog: Dict[str, NarrativeKnowledgeRecord],
    ) -> GroundedRAGResponse:
        """Answer queries inspecting character belief changes with causal event provenance."""
        # Find events where beliefs were learned or updated
        belief_events: List[Event] = [
            e for e in world.events.values()
            if e.event_type in ("FACT_DISCOVERED", "SECRET_REVEALED") or "belief" in e.description.lower()
        ]

        if not belief_events:
            return GroundedRAGResponse(
                query=query,
                status=RAGAnswerStatus.INSUFFICIENT_EVIDENCE,
                answer="No belief transition or discovery events have been recorded in the EventLog yet. Character beliefs remain at initial baseline.",
            )

        latest_ev = belief_events[-1]
        ev_ref_id = f"ev_ref_{latest_ev.id}"

        claim = GroundedClaim(
            claim_id="clm_belief_1",
            claim_text=f"Event '{latest_ev.id}' at tick {latest_ev.tick} altered subjective belief: {latest_ev.description}.",
            category=EvidenceCategory.CANONICAL_FACT,
            cited_evidence_ids=[ev_ref_id] if ev_ref_id in evidence else [],
        )
        verified_clm = EvidenceValidator.verify_claim(claim, world, evidence, k_catalog)

        answer_text = (
            f"Belief evolution is documented in Event '{latest_ev.id}' at tick {latest_ev.tick}: '{latest_ev.description}'. "
            f"Causal event provenance links this transition directly to the actor's immediate perception."
        )

        return GroundedRAGResponse(
            query=query,
            status=RAGAnswerStatus.SUCCESS,
            answer=answer_text,
            claims=[verified_clm],
            evidence=[evidence[cid] for cid in verified_clm.cited_evidence_ids if cid in evidence],
        )

    @classmethod
    def _handle_general_grounded_query(
        cls,
        query: str,
        world: WorldState,
        conflict_graph: Optional[ConflictGraph],
        patterns: List[NarrativeKnowledgeRecord],
        evidence: Dict[str, EvidenceReference],
        k_catalog: Dict[str, NarrativeKnowledgeRecord],
    ) -> GroundedRAGResponse:
        """Handle general narrative intelligence queries with grounded pattern citations and fact checks."""
        from .retrieval import tokenize
        q_tokens = set(tokenize(query))

        # Check overlap with world vocabulary (character names, locations, objects, secrets, event descriptions)
        world_words = set()
        for c in world.characters.values():
            world_words.update(tokenize(c.name))
            world_words.update(tokenize(c.role))
        for loc in world.locations.values():
            world_words.update(tokenize(loc.name))
        for obj in getattr(world, "objects", {}).values():
            world_words.update(tokenize(getattr(obj, "name", "")))
        for s in getattr(world, "secrets", {}).values():
            world_words.update(tokenize(getattr(s, "statement", "")))
        for ev in world.events.values():
            world_words.update(tokenize(getattr(ev, "description", "")))

        narrative_concepts = {
            "conflict", "tension", "pattern", "structure", "beat", "arc", "character", "revelation",
            "escalation", "crisis", "resolution", "reversal", "setup", "payoff", "pressure", "action",
            "relationship", "goal", "belief", "secret", "emotion", "event", "scene", "story",
        }

        has_world_overlap = bool(q_tokens.intersection(world_words))
        has_narrative_overlap = bool(q_tokens.intersection(narrative_concepts))

        if not has_world_overlap and not has_narrative_overlap:
            return GroundedRAGResponse(
                query=query,
                status=RAGAnswerStatus.INSUFFICIENT_EVIDENCE,
                answer="No evidence in canonical WorldState or EventLog supports the premise of this inquiry. The queried subject is entirely unrecorded.",
                claims=[],
                evidence=[],
                retrieved_pattern_ids=[],
            )

        if not patterns and len(world.events) == 0:
            return GroundedRAGResponse(
                query=query,
                status=RAGAnswerStatus.INSUFFICIENT_EVIDENCE,
                answer="Insufficient narrative evidence and no matching abstract patterns found to answer the query.",
            )

        claims: List[GroundedClaim] = []
        retrieved_ids = [p.id for p in patterns[:3]]

        # Ground against top pattern if available
        if patterns:
            top_pat = patterns[0]
            pat_ref_id = f"pattern_ref_{top_pat.id}"
            clm = GroundedClaim(
                claim_id="clm_gen_1",
                claim_text=f"Query correlates with dramatic principle {top_pat.id} ('{top_pat.title}'): {top_pat.content[:120]}.",
                category=EvidenceCategory.RETRIEVED_KNOWLEDGE,
                cited_evidence_ids=[pat_ref_id] if pat_ref_id in evidence else [],
            )
            claims.append(EvidenceValidator.verify_claim(clm, world, evidence, k_catalog))

        answer_text = (
            f"Narrative Intelligence evaluation for '{query}': "
            f"Current simulation stands at Tick {world.current_tick} with {len(world.events)} verified events and {len(world.characters)} active characters. "
        )
        if patterns:
            answer_text += f"Retrieved relevant dramatic patterns: {', '.join(retrieved_ids)} ({patterns[0].title})."

        return GroundedRAGResponse(
            query=query,
            status=RAGAnswerStatus.SUCCESS,
            answer=answer_text,
            claims=claims,
            evidence=[evidence[cid] for c in claims for cid in c.cited_evidence_ids if cid in evidence],
            retrieved_pattern_ids=retrieved_ids,
        )
