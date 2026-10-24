"""Typed domain models for Grounded RAG and Narrative Knowledge Base in D3 Story Lab.

CRITICAL INVARIANTS:
1. STRUCTURE WITHOUT PUPPETRY:
   - RAG is strictly advisory and observational.
   - Zero mutation of canonical WorldState or EventLog.
2. CATEGORICAL FIREWALL:
   - Must strictly segregate:
     a) Canonical Story Facts (verified simulation events)
     b) Character Knowledge (subjective beliefs, boundaries)
     c) Narrative Interpretations (analyzer inferences)
     d) Retrieved Knowledge (abstract patterns, genome)
     e) Recommendations (unrealized optional suggestions)
3. TRACEABLE PROVENANCE:
   - Every factual claim citing an event or pattern must carry verifiable IDs.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


class EvidenceCategory(str, Enum):
    """Rigorous categorization of narrative information sources."""

    CANONICAL_FACT = "canonical_fact"          # What actually happened in simulation (immutable EventLog)
    CHARACTER_KNOWLEDGE = "character_knowledge"  # What a specific actor subjectively perceives/believes
    NARRATIVE_INTERPRETATION = "narrative_interpretation"  # Analytical inference (tension, pacing, arc)
    RETRIEVED_KNOWLEDGE = "retrieved_knowledge"  # Abstract dramatic principles / Narrative Genome records
    RECOMMENDATION = "recommendation"          # Advisory suggestions for environmental pressure


class ClaimVerificationStatus(str, Enum):
    """Deterministic verification state of an evidence-backed statement."""

    VERIFIED = "verified"          # Entity/event ID exists and substantiates the claim
    UNSUPPORTED = "unsupported"    # Entity/event ID not found or disconnected from claim
    CONTRADICTORY = "contradictory"# Evidence reveals opposing or conflicting truths
    CATEGORY_MISMATCH = "category_mismatch" # Retrieved principle or recommendation cited as factual event
    OUTDATED = "outdated"          # Factual state superseded by subsequent simulation events
    INFERRED = "inferred"          # Analytical deduction without direct physical event observation


class RAGAnswerStatus(str, Enum):
    """Overall reliability status of a Grounded RAG response."""

    SUCCESS = "success"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONTRADICTION_DISCLOSED = "contradiction_disclosed"
    NO_RELEVANT_PATTERNS = "no_relevant_patterns"


class NarrativeKnowledgeRecord(BaseModel):
    """Curated knowledge record representing an abstract narrative or dramatic pattern."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(..., description="Unique immutable pattern identifier, e.g. 'NG-001'")
    schema_version: str = Field(default="1.0.0", description="Schema specification version")
    title: str = Field(..., description="Human-readable title of pattern")
    content: str = Field(..., description="Comprehensive textual description of dramatic mechanism")
    pattern_type: str = Field(default="narrative_pattern", description="Category of knowledge")

    dramatic_function: str = Field(..., description="Primary dramatic function (e.g. ESCALATION, REVELATION)")
    conflict_types: List[str] = Field(default_factory=list, description="Associated conflict archetypes")
    causal_relations: List[str] = Field(default_factory=list, description="Causal relations enabled or caused")
    tension_direction: str = Field(default="sustained", description="Vector of tension progression")
    setup_payoff_role: Optional[str] = Field(default=None, description="Role in setup/payoff lifecycle")
    genre_tags: List[str] = Field(default_factory=list, description="Applicable narrative genres")

    applicability_conditions: List[str] = Field(default_factory=list, description="Preconditions for pattern relevance")
    counter_conditions: List[str] = Field(default_factory=list, description="Conditions where pattern must NOT be applied")
    limitations: List[str] = Field(default_factory=list, description="Known dramatic limitations or failure modes")

    source_type: str = Field(default="system-authored", description="Origin category (e.g. system-authored, curated)")
    source_reference: str = Field(default="core_patterns.json", description="Source document or origin citation")
    license: str = Field(default="MIT", description="Licensing and usage terms")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Detailed creation provenance")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Authoritative pattern confidence score")
    raw_attributes: Dict[str, Any] = Field(default_factory=dict, description="Supplemental genome attributes")


class EvidenceReference(BaseModel):
    """Stable, traceable evidence reference substantiating narrative claims."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(..., description="Unique evidence reference ID")
    category: EvidenceCategory = Field(..., description="Categorical firewall domain")
    entity_type: str = Field(..., description="'event', 'character', 'secret', 'belief', 'pattern', 'conflict'")
    entity_id: str = Field(..., description="Actual ID in project or knowledge base")
    tick: Optional[int] = Field(default=None, description="Simulation tick if applicable")
    summary: str = Field(..., description="Explainable description of what this evidence proves")
    source_reference: Optional[str] = Field(default=None, description="Origin document or log identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GroundedClaim(BaseModel):
    """Individual assertion verified against canonical story facts or retrieved knowledge."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    claim_id: str = Field(..., description="Identifier for claim")
    claim_text: str = Field(..., description="The factual or interpretive assertion")
    category: EvidenceCategory = Field(..., description="Firewall category of the assertion")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="IDs of cited EvidenceReference items")
    verification_status: ClaimVerificationStatus = Field(default=ClaimVerificationStatus.VERIFIED)
    verification_notes: Optional[str] = Field(default=None, description="Detailed audit trail from validator")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Structured claim parameters for validation")


class RAGSearchFilter(BaseModel):
    """Search and ranking parameters for querying narrative knowledge."""

    model_config = ConfigDict(extra="ignore")

    query: Optional[str] = None
    dramatic_functions: Optional[List[str]] = None
    conflict_types: Optional[List[str]] = None
    genres: Optional[List[str]] = None
    tension_directions: Optional[List[str]] = None
    min_score: float = 0.05
    top_k: int = 5
    mode: Literal["lexical", "semantic", "hybrid"] = "hybrid"


class RAGSearchResult(BaseModel):
    """Scored and explainable retrieval match."""

    model_config = ConfigDict(extra="ignore")

    record: NarrativeKnowledgeRecord
    score: float
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    match_reasons: List[str] = Field(default_factory=list)


class GroundedRAGResponse(BaseModel):
    """Complete, validated answer to a narrative intelligence query."""

    model_config = ConfigDict(extra="ignore")

    query: str
    project_id: Optional[str] = None
    status: RAGAnswerStatus = RAGAnswerStatus.SUCCESS
    answer: str
    claims: List[GroundedClaim] = Field(default_factory=list)
    evidence: List[EvidenceReference] = Field(default_factory=list)
    retrieved_pattern_ids: List[str] = Field(default_factory=list)
    unresolved_conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    advisory_only: Literal[True] = True
    confidence: float = 1.0
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
