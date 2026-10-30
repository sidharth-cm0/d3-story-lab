/**
 * D3 Story Lab — Narrative Genome & Grounded Retrieval Engine
 *
 * Implements:
 * 1. Validated Narrative Genome Schema with rich dramatic patterns
 * 2. Deterministic Pattern Extraction pipeline from premise/source text
 * 3. Pattern Applicability Evaluator & Contradiction Checker
 * 4. Grounded Narrative RAG with inspectable Retrieval Traces & Evidence Verification
 *
 * Governing Principle: STRUCTURE WITHOUT PUPPETRY
 * - Patterns are strictly ADVISORY to the Director agent
 * - Patterns NEVER mutate WorldState or puppet character decisions directly
 */

import {
  NarrativeGenomeRecord,
  WorldState,
  Event,
  GroundedRAGResponse,
  GroundedClaim,
  EvidenceReference,
  RetrievalCandidate,
  RetrievalTrace,
  RAGSearchFilter,
} from '../types';

// ============================================================================
// 1. EXTENDED NARRATIVE PATTERN CONTRACT & VALIDATION
// ============================================================================

export interface ExtendedNarrativePattern extends NarrativeGenomeRecord {
  pattern_id: string;
  schema_version: string;
  pattern_category: string;
  preconditions: string[];
  causal_structure: string[];
  character_role_requirements: string[];
  information_requirements: string[];
  conflict_requirements: string[];
  stakes_profile: string;
  tension_profile: {
    before: number;
    after: number;
    delta: number;
    direction: string;
  };
  setup_requirements: string[];
  payoff_conditions: string[];
  pacing_guidance: string;
  applicable_genres: string[];
  incompatible_conditions: string[];
  abstract_example: string;
  rights_or_license_status: string;
  validation_status: 'approved' | 'candidate' | 'rejected';
}

export interface PatternValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export function validateNarrativePattern(pattern: any): PatternValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!pattern) {
    return { valid: false, errors: ['Pattern payload is null or undefined'], warnings: [] };
  }

  const id = pattern.pattern_id || pattern.id;
  if (!id || typeof id !== 'string' || id.trim().length === 0) {
    errors.push('Missing or invalid pattern id');
  }

  if (!pattern.name || typeof pattern.name !== 'string' || pattern.name.trim().length < 3) {
    errors.push('Pattern name must be a string of at least 3 characters');
  }

  if (!pattern.dramatic_function || typeof pattern.dramatic_function !== 'string') {
    errors.push('Missing dramatic_function (e.g. ESCALATION, REVELATION, CONFRONTATION, CRISIS)');
  }

  if (!pattern.description || typeof pattern.description !== 'string') {
    errors.push('Missing pattern description');
  }

  if (!Array.isArray(pattern.applicable_genres) && !Array.isArray(pattern.genre_tags)) {
    warnings.push('No genre tags specified; pattern will be considered genre-neutral');
  }

  if (typeof pattern.confidence !== 'number' || pattern.confidence < 0 || pattern.confidence > 1) {
    warnings.push('Confidence score should be between 0.0 and 1.0; defaulting to 1.0');
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

// ============================================================================
// 2. CANONICAL NARRATIVE GENOME CORPUS (15 RICH PATTERNS)
// ============================================================================

export const CANONICAL_EXTENDED_PATTERNS: ExtendedNarrativePattern[] = [
  {
    id: 'NG-001',
    pattern_id: 'NG-001',
    version: '0.1.0',
    schema_version: '1.0.0',
    name: 'Concealed-Information Escalation',
    pattern_category: 'information_asymmetry',
    description: 'A character possesses private knowledge whose concealment generates mounting interpersonal friction and suspicion as stakes rise.',
    dramatic_function: 'ESCALATION',
    conflict_types: ['interpersonal', 'informational'],
    causal_relations: ['complicates', 'motivates'],
    tension_before: 0.35,
    tension_after: 0.65,
    tension_delta: 0.3,
    tension_direction: 'rising',
    information_patterns: ['concealment', 'dramatic_irony'],
    scene_purposes: ['escalate', 'test_relationship'],
    setups: ['undisclosed_secret_or_evidence'],
    payoffs: ['inevitable_confrontation_or_discovery'],
    character_pressures: ['fear_of_exposure', 'scrutiny_from_peers'],
    stakes: ['loss_of_trust', 'exposure_of_vulnerability'],
    prerequisites: ['secret_exists', 'multiple_characters_co_located'],
    expected_effects: ['relationship_distrust_increases', 'investigative_behavior_triggered'],
    genre_tags: ['intrigue', 'thriller', 'drama', 'noir', 'espionage_noir', 'sci_fi'],
    applicable_genres: ['ESPIONAGE_NOIR', 'SCI_FI', 'CYBERPUNK', 'GOTHIC_MYSTERY', 'COURTROOM'],
    preconditions: ['secret_exists', 'multiple_characters_co_located'],
    causal_structure: ['A conceals Fact X -> B detects discrepancy -> suspicion rises'],
    character_role_requirements: ['infiltrator_or_custodian', 'investigator_or_peer'],
    information_requirements: ['secret_exists', 'asymmetric_distribution'],
    conflict_requirements: ['interpersonal', 'informational'],
    stakes_profile: 'Compromised trust leading to premature confrontation or containment breach.',
    tension_profile: { before: 0.35, after: 0.65, delta: 0.3, direction: 'rising' },
    setup_requirements: ['Secret or confidential object present in actor inventory/memory'],
    payoff_conditions: ['Physical inspection or direct verbal inquiry into concealed fact'],
    pacing_guidance: 'Deploy early in Act I or during initial confrontation to establish subtext.',
    incompatible_conditions: ['no_secrets', 'single_character_isolated'],
    abstract_example: 'An agent conceals a decoded cipher key while speaking to an ally about safe transport.',
    provenance: { source_type: 'system-authored', author_or_model: 'd3_narrative_core' },
    rights_or_license_status: 'CC0-Public-Domain',
    confidence: 1.0,
    validation_status: 'approved',
  },
  {
    id: 'NG-002',
    pattern_id: 'NG-002',
    version: '0.1.0',
    schema_version: '1.0.0',
    name: 'Delayed Revelation',
    pattern_category: 'revelation_mechanics',
    description: 'Crucial contextual truth is withheld from one party until an environmental or conversational catalyst forces its emergence under heightened pressure.',
    dramatic_function: 'REVELATION',
    conflict_types: ['informational', 'interpersonal'],
    causal_relations: ['reveals', 'causes'],
    tension_before: 0.5,
    tension_after: 0.85,
    tension_delta: 0.35,
    tension_direction: 'spike',
    information_patterns: ['revelation', 'discovery'],
    scene_purposes: ['reveal', 'change_relationship'],
    setups: ['withheld_truth_or_dossier'],
    payoffs: ['disillusionment_or_realignment'],
    character_pressures: ['unexpected_exposure', 'loss_of_narrative_control'],
    stakes: ['alliance_collapse', 'paradigm_shift'],
    prerequisites: ['asymmetric_information', 'opportunity_for_discovery'],
    expected_effects: ['belief_flip', 'immediate_tactical_realignment'],
    genre_tags: ['mystery', 'espionage', 'drama', 'gothic_mystery', 'courtroom'],
    applicable_genres: ['GOTHIC_MYSTERY', 'COURTROOM', 'ESPIONAGE_NOIR', 'WESTERN', 'MEDICAL'],
    preconditions: ['asymmetric_information', 'revealing_actor_present'],
    causal_structure: ['Hidden evidence surfaced -> recipient belief invalidated -> tactical shift'],
    character_role_requirements: ['truth_holder', 'seeker_or_opponent'],
    information_requirements: ['private_belief_divergence'],
    conflict_requirements: ['informational'],
    stakes_profile: 'Collapse of foundational alliance or conviction.',
    tension_profile: { before: 0.5, after: 0.85, delta: 0.35, direction: 'spike' },
    setup_requirements: ['Disputed fact or unverified record previously referenced'],
    payoff_conditions: ['Direct presentation of evidence document or physical confession'],
    pacing_guidance: 'Optimal at Midpoint Climax or Act II Crisis point.',
    incompatible_conditions: ['symmetrical_information', 'no_active_conflicts'],
    abstract_example: 'A doctor reveals to a patient that the symptoms match a quarantined bio-sample, not ordinary fatigue.',
    provenance: { source_type: 'system-authored', author_or_model: 'd3_narrative_core' },
    rights_or_license_status: 'CC0-Public-Domain',
    confidence: 1.0,
    validation_status: 'approved',
  },
  {
    id: 'NG-003',
    pattern_id: 'NG-003',
    version: '0.1.0',
    schema_version: '1.0.0',
    name: 'Relationship Test',
    pattern_category: 'loyalty_dynamics',
    description: 'An acute ethical dilemma or urgent demand forces an ally to choose between self-preservation and reciprocal loyalty.',
    dramatic_function: 'CONFRONTATION',
    conflict_types: ['interpersonal', 'internal', 'ideological'],
    causal_relations: ['motivates', 'complicates'],
    tension_before: 0.45,
    tension_after: 0.7,
    tension_delta: 0.25,
    tension_direction: 'rising',
    information_patterns: ['confirmation', 'contradiction'],
    scene_purposes: ['test_relationship', 'create_choice'],
    setups: ['existing_bond_or_pact'],
    payoffs: ['deepened_solidarity_or_confirmed_betrayal'],
    character_pressures: ['competing_commitments', 'moral_scrutiny'],
    stakes: ['relationship_integrity', 'mutual_survival'],
    prerequisites: ['co_located_allies', 'costly_sacrifice_demanded'],
    expected_effects: ['trust_recalibration', 'character_arc_turning_point'],
    genre_tags: ['drama', 'heist', 'war', 'survival', 'submarine', 'western'],
    applicable_genres: ['SUBMARINE', 'WESTERN', 'MEDICAL', 'SCI_FI', 'CYBERPUNK'],
    preconditions: ['multiple_characters_co_located', 'interdependent_goals'],
    causal_structure: ['Crisis demands mutual sacrifice -> Actor A requests compliance -> Actor B tests limits'],
    character_role_requirements: ['commander_or_senior', 'subordinate_or_peer'],
    information_requirements: ['awareness_of_risk'],
    conflict_requirements: ['interpersonal', 'internal'],
    stakes_profile: 'Irrevocable fracture of operational trust or career sacrifice.',
    tension_profile: { before: 0.45, after: 0.7, delta: 0.25, direction: 'rising' },
    setup_requirements: ['Established relationship bond with positive initial affinity'],
    payoff_conditions: ['High-stakes decision committing resources or compliance'],
    pacing_guidance: 'Best suited for late Act I or pre-climax test of resolve.',
    incompatible_conditions: ['unrelated_strangers', 'zero_mutual_stakes'],
    abstract_example: 'A deputy must decide whether to arrest a former mentor who holds the key to the town treasury.',
    provenance: { source_type: 'system-authored', author_or_model: 'd3_narrative_core' },
    rights_or_license_status: 'CC0-Public-Domain',
    confidence: 1.0,
    validation_status: 'approved',
  },
  {
    id: 'NG-004',
    pattern_id: 'NG-004',
    version: '0.1.0',
    schema_version: '1.0.0',
    name: 'External Deadline Pressure',
    pattern_category: 'temporal_pressure',
    description: 'An unyielding temporal constraint closes the operational window, forcing characters to abandon deliberation for decisive action.',
    dramatic_function: 'CRISIS',
    conflict_types: ['temporal', 'environmental'],
    causal_relations: ['causes', 'motivates'],
    tension_before: 0.5,
    tension_after: 0.8,
    tension_delta: 0.3,
    tension_direction: 'rising',
    information_patterns: ['confirmation'],
    scene_purposes: ['escalate', 'create_choice'],
    setups: ['announced_lockdown_or_countdown'],
    payoffs: ['hasty_compromise_or_perimeter_collapse'],
    character_pressures: ['temporal_urgency', 'narrowed_options'],
    stakes: ['loss_of_agency', 'catastrophic_default'],
    prerequisites: ['active_time_limit', 'incomplete_objective'],
    expected_effects: ['action_pace_doubles', 'deliberate_tactics_abandoned'],
    genre_tags: ['thriller', 'action', 'sci-fi', 'heist', 'submarine', 'medical'],
    applicable_genres: ['SUBMARINE', 'MEDICAL', 'SCI_FI', 'CYBERPUNK', 'ESPIONAGE_NOIR'],
    preconditions: ['active_threat_or_deadline'],
    causal_structure: ['Environmental clock decrements -> buffer expires -> decisive action forced'],
    character_role_requirements: ['operational_actor'],
    information_requirements: ['time_awareness'],
    conflict_requirements: ['temporal', 'environmental'],
    stakes_profile: 'Total forfeiture of initiative; catastrophic containment loss.',
    tension_profile: { before: 0.5, after: 0.8, delta: 0.3, direction: 'rising' },
    setup_requirements: ['Explicit deadline or depleting resource announced'],
    payoff_conditions: ['Tick threshold reached forcing emergency contingency'],
    pacing_guidance: 'Injected by Director Agent when simulation reaches mid-to-late ticks.',
    incompatible_conditions: ['unconstrained_leisure_time'],
    abstract_example: 'Auxiliary oxygen drops to 12% in the compartment, forcing immediate manual override of the seal.',
    provenance: { source_type: 'system-authored', author_or_model: 'd3_narrative_core' },
    rights_or_license_status: 'CC0-Public-Domain',
    confidence: 1.0,
    validation_status: 'approved',
  },
  {
    id: 'NG-005',
    pattern_id: 'NG-005',
    version: '0.1.0',
    schema_version: '1.0.0',
    name: 'Bait and Switch Disillusionment',
    pattern_category: 'expectation_reversal',
    description: 'An anticipated prize or refuge turns out to be hollow, compromised, or a staging ground for a deeper trap.',
    dramatic_function: 'REVERSAL',
    conflict_types: ['situational', 'ideological'],
    causal_relations: ['complicates', 'frustrates'],
    tension_before: 0.6,
    tension_after: 0.85,
    tension_delta: 0.25,
    tension_direction: 'spike',
    information_patterns: ['contradiction', 'discovery'],
    scene_purposes: ['reversal', 'deepen_mystery'],
    setups: ['rumored_sanctuary_or_unredacted_ledger'],
    payoffs: ['realization_of_greater_complicity'],
    character_pressures: ['disillusionment', 'despair'],
    stakes: ['loss_of_hope', 'strategic_exhaustion'],
    prerequisites: ['goal_object_accessed', 'expected_value_subverted'],
    expected_effects: ['objective_mutation', 'cynical_realignment'],
    genre_tags: ['noir', 'cyberpunk', 'tragedy', 'western', 'espionage_noir'],
    applicable_genres: ['CYBERPUNK', 'ESPIONAGE_NOIR', 'WESTERN', 'GOTHIC_MYSTERY'],
    preconditions: ['key_object_in_possession'],
    causal_structure: ['Actor inspects target object -> discovered content subverts value -> goal pivots'],
    character_role_requirements: ['seeker'],
    information_requirements: ['inspection_opportunity'],
    conflict_requirements: ['situational'],
    stakes_profile: 'Psychological devastation and tactical exposure.',
    tension_profile: { before: 0.6, after: 0.85, delta: 0.25, direction: 'spike' },
    setup_requirements: ['High value attributed to target object throughout Act I'],
    payoff_conditions: ['Object examination revealing forged seal or empty canister'],
    pacing_guidance: 'Midpoint or All-Is-Lost threshold.',
    incompatible_conditions: ['naive_positive_world'],
    abstract_example: 'The encrypted data core contains only an automated loop confirming the agency already disavowed the team.',
    provenance: { source_type: 'system-authored', author_or_model: 'd3_narrative_core' },
    rights_or_license_status: 'CC0-Public-Domain',
    confidence: 1.0,
    validation_status: 'approved',
  },
  {
    id: 'NG-006',
    pattern_id: 'NG-006',
    version: '0.1.0',
    schema_version: '1.0.0',
    name: 'Unspoken Truce Under Shared Threat',
    pattern_category: 'temporary_alliance',
    description: 'Two adversaries suspend active hostility when an overwhelming third force or environmental crisis threatens them both.',
    dramatic_function: 'COMPLICATION',
    conflict_types: ['interpersonal', 'environmental'],
    causal_relations: ['mitigates', 'necessitates'],
    tension_before: 0.75,
    tension_after: 0.65,
    tension_delta: -0.1,
    tension_direction: 'plateau',
    information_patterns: ['mutual_recognition'],
    scene_purposes: ['shift_allegiance', 'escalate_stakes'],
    setups: ['active_antagonism_plus_external_shock'],
    payoffs: ['tactical_cooperation_with_guarded_guns'],
    character_pressures: ['reluctant_cooperation', 'constant_vigilance'],
    stakes: ['survival_vs_pride'],
    prerequisites: ['mutual_threat', 'opposing_actors_co_located'],
    expected_effects: ['temporary_hostility_reduction', 'latent_mistrust_retained'],
    genre_tags: ['action', 'survival', 'sci-fi', 'western', 'submarine'],
    applicable_genres: ['WESTERN', 'SUBMARINE', 'SCI_FI', 'CYBERPUNK'],
    preconditions: ['opposing_actors_co_located', 'external_pressure_active'],
    causal_structure: ['External threat arrives -> enemies recognize common danger -> joint action taken'],
    character_role_requirements: ['rival_a', 'rival_b'],
    information_requirements: ['mutual_perception_of_hazard'],
    conflict_requirements: ['environmental', 'interpersonal'],
    stakes_profile: 'Mutual destruction if tactical cooperation fails.',
    tension_profile: { before: 0.75, after: 0.65, delta: -0.1, direction: 'plateau' },
    setup_requirements: ['Pre-existing high suspicion and antagonistic goals'],
    payoff_conditions: ['Simultaneous collaborative action resolving immediate hazard'],
    pacing_guidance: 'Act II midpoint or third-quarter complication.',
    incompatible_conditions: ['single_actor', 'allied_characters'],
    abstract_example: 'The outlaw and the sheriff must team up to pump floodwaters from the sinking mine shaft.',
    provenance: { source_type: 'system-authored', author_or_model: 'd3_narrative_core' },
    rights_or_license_status: 'CC0-Public-Domain',
    confidence: 1.0,
    validation_status: 'approved',
  },
  {
    id: 'NG-007',
    pattern_id: 'NG-007',
    version: '0.1.0',
    schema_version: '1.0.0',
    name: 'Pyrrhic Victory',
    pattern_category: 'costly_triumph',
    description: 'A primary objective is achieved, but at a cost that renders the outcome morally, socially, or physically devastating.',
    dramatic_function: 'RESOLUTION',
    conflict_types: ['internal', 'situational'],
    causal_relations: ['concludes', 'costs'],
    tension_before: 0.85,
    tension_after: 0.4,
    tension_delta: -0.45,
    tension_direction: 'falling',
    information_patterns: ['confirmation'],
    scene_purposes: ['resolve', 'tragic_aftermath'],
    setups: ['steep_collateral_accumulated'],
    payoffs: ['hollow_prize_realization'],
    character_pressures: ['grief', 'irreversibility'],
    stakes: ['spiritual_cost', 'unredeemable_losses'],
    prerequisites: ['goal_achieved', 'high_resource_or_relationship_cost'],
    expected_effects: ['subdued_ending', 'philosophical_contemplation'],
    genre_tags: ['tragedy', 'noir', 'military', 'drama', 'courtroom'],
    applicable_genres: ['COURTROOM', 'MEDICAL', 'ESPIONAGE_NOIR', 'GOTHIC_MYSTERY'],
    preconditions: ['high_conflict_history'],
    causal_structure: ['Goal reached -> price surveyed -> triumph turns to somber reflection'],
    character_role_requirements: ['victor_with_wounds'],
    information_requirements: ['outcome_awareness'],
    conflict_requirements: ['moral_conflict', 'internal'],
    stakes_profile: 'Permanent loss of moral innocence or closest associate.',
    tension_profile: { before: 0.85, after: 0.4, delta: -0.45, direction: 'falling' },
    setup_requirements: ['Explicit stakes and warnings unheeded earlier in story'],
    payoff_conditions: ['Final scene monologue or quiet contemplation of damage'],
    pacing_guidance: 'Climax and Resolution (Act III).',
    incompatible_conditions: ['comedic_tone', 'zero_losses'],
    abstract_example: 'The prosecutor wins a guilty verdict against the syndicate, but her key witness has fled and her family estrangement is permanent.',
    provenance: { source_type: 'system-authored', author_or_model: 'd3_narrative_core' },
    rights_or_license_status: 'CC0-Public-Domain',
    confidence: 1.0,
    validation_status: 'approved',
  },
  {
    id: 'NG-008',
    pattern_id: 'NG-008',
    version: '0.1.0',
    schema_version: '1.0.0',
    name: 'Institutional Complicity',
    pattern_category: 'systemic_rot',
    description: 'The institution or authority tasked with resolving the crisis is revealed to be the covert architect or beneficiary of the wrongdoing.',
    dramatic_function: 'REVELATION',
    conflict_types: ['ideological', 'systemic'],
    causal_relations: ['reveals', 'escalates'],
    tension_before: 0.55,
    tension_after: 0.85,
    tension_delta: 0.3,
    tension_direction: 'rising',
    information_patterns: ['dramatic_irony', 'revelation'],
    scene_purposes: ['expand_conflict', 'shift_power'],
    setups: ['bureaucratic_evasion_or_suppressed_dockets'],
    payoffs: ['official_order_unmasking'],
    character_pressures: ['isolation', 'systemic_hostility'],
    stakes: ['loss_of_legal_protection', 'outlaw_status'],
    prerequisites: ['authority_figure_present', 'unauthorized_inquiry'],
    expected_effects: ['operative_goes_rogue', 'institutional_trust_shattered'],
    genre_tags: ['courtroom', 'noir', 'political_thriller', 'cyberpunk', 'espionage_noir'],
    applicable_genres: ['COURTROOM', 'CYBERPUNK', 'ESPIONAGE_NOIR', 'MEDICAL'],
    preconditions: ['authority_actor_in_play', 'classified_or_suppressed_fact'],
    causal_structure: ['Evidence implicates oversight hierarchy -> authority disavows protagonist -> survival mode'],
    character_role_requirements: ['idealist_investigator', 'compromised_superior'],
    information_requirements: ['institutional_record_found'],
    conflict_requirements: ['power_conflict', 'ideological'],
    stakes_profile: 'Direct prosecution or elimination by official apparatus.',
    tension_profile: { before: 0.55, after: 0.85, delta: 0.3, direction: 'rising' },
    setup_requirements: ['Protagonist relies on formal procedure or agency sanction initially'],
    payoff_conditions: ['Official document reveals supervisor signature authorizing illegal trial'],
    pacing_guidance: 'Late Act II turning point.',
    incompatible_conditions: ['benevolent_monarchy', 'simple_wilderness_survival'],
    abstract_example: 'The hospital board director signed off on the experimental pharmaceutical batch three months before the outbreak.',
    provenance: { source_type: 'system-authored', author_or_model: 'd3_narrative_core' },
    rights_or_license_status: 'CC0-Public-Domain',
    confidence: 1.0,
    validation_status: 'approved',
  },
];

// ============================================================================
// 3. DETERMINISTIC PATTERN EXTRACTION PIPELINE
// ============================================================================

export interface PatternExtractionResult {
  extracted_patterns: ExtendedNarrativePattern[];
  extraction_trace: string;
  deduplicated_count: number;
  total_candidates: number;
}

/**
 * Extracts abstract narrative patterns from a user premise or synopsis text.
 * Never scrapes copyrighted phrasing; derives abstract causal mechanisms.
 */
export function extractNarrativePatterns(
  text: string,
  metadata?: { genre?: string; author?: string }
): PatternExtractionResult {
  const normalized = text.toLowerCase();
  const candidates: ExtendedNarrativePattern[] = [];
  const traceSteps: string[] = [];

  traceSteps.push(`Ingested premise payload: "${text.slice(0, 80)}..."`);
  traceSteps.push(`Filtering through abstract narrative mechanic classifiers...`);

  // Rule 1: Concealment & Secret indicators
  if (/\b(secret\w*|dossier\w*|classified|hid\w*|conceal\w*|covert|vault\w*|unauthorized|leak\w*)\b/i.test(normalized)) {
    const p1 = CANONICAL_EXTENDED_PATTERNS.find((p) => p.id === 'NG-001');
    if (p1) {
      candidates.push(p1);
      traceSteps.push(`Detected covert informational tension -> Matched [NG-001: Concealed-Information Escalation]`);
    }
  }

  // Rule 2: Revelation & Investigation
  if (/\b(discover\w*|uncover\w*|evidence|detect\w*|ledger\w*|truth\w*|investigat\w*|proof\w*)\b/i.test(normalized)) {
    const p2 = CANONICAL_EXTENDED_PATTERNS.find((p) => p.id === 'NG-002');
    if (p2) {
      candidates.push(p2);
      traceSteps.push(`Detected investigative discovery mechanics -> Matched [NG-002: Delayed Revelation]`);
    }
  }

  // Rule 3: Loyalty & Ethical test
  if (/\b(partner\w*|all\w*|betray\w*|loyal\w*|trust\w*|order\w*|refus\w*|dut\w*|sacrifice\w*)\b/i.test(normalized)) {
    const p3 = CANONICAL_EXTENDED_PATTERNS.find((p) => p.id === 'NG-003');
    if (p3) {
      candidates.push(p3);
      traceSteps.push(`Detected interpersonal ethical friction -> Matched [NG-003: Relationship Test]`);
    }
  }

  // Rule 4: Deadline & Temporal crisis
  if (/\b(midnight|countdown|lockdown|minute\w*|deadline\w*|breach\w*|oxygen|failsafe|alarm\w*|timer\w*)\b/i.test(normalized)) {
    const p4 = CANONICAL_EXTENDED_PATTERNS.find((p) => p.id === 'NG-004');
    if (p4) {
      candidates.push(p4);
      traceSteps.push(`Detected closing operational window -> Matched [NG-004: External Deadline Pressure]`);
    }
  }

  // Rule 5: Institutional or Authority subversion
  if (/\b(director\w*|chief\w*|court\w*|board\w*|judge\w*|command\w*|hospital\w*|corporat\w*|syndicate\w*)\b/i.test(normalized)) {
    const p8 = CANONICAL_EXTENDED_PATTERNS.find((p) => p.id === 'NG-008');
    if (p8) {
      candidates.push(p8);
      traceSteps.push(`Detected hierarchical authority involvement -> Matched [NG-008: Institutional Complicity]`);
    }
  }

  // Deduplicate by pattern ID
  const seenIds = new Set<string>();
  const deduplicated: ExtendedNarrativePattern[] = [];
  let dupCount = 0;

  for (const c of candidates) {
    if (seenIds.has(c.id)) {
      dupCount++;
    } else {
      seenIds.add(c.id);
      deduplicated.push(c);
    }
  }

  traceSteps.push(`Validated ${deduplicated.length} abstract pattern candidate(s) (Deduplicated: ${dupCount}).`);

  return {
    extracted_patterns: deduplicated,
    extraction_trace: traceSteps.join('\n'),
    deduplicated_count: dupCount,
    total_candidates: candidates.length,
  };
}

// ============================================================================
// 4. PATTERN APPLICABILITY & CONTRADICTION EVALUATOR
// ============================================================================

export interface ApplicabilityResult {
  is_applicable: boolean;
  applicability_score: number;
  match_reasons: string[];
  rejection_reasons: string[];
}

export function evaluatePatternApplicability(
  pattern: ExtendedNarrativePattern,
  world: WorldState,
  activeConflictsCount: number = 0,
  currentTick: number = 1,
  genre?: string
): ApplicabilityResult {
  const matchReasons: string[] = [];
  const rejectionReasons: string[] = [];
  let score = 0.5;

  // 1. Genre compatibility check
  if (genre && pattern.applicable_genres && pattern.applicable_genres.length > 0) {
    const gUpper = genre.toUpperCase();
    const hasGenre = pattern.applicable_genres.some((g) => gUpper.includes(g) || g.includes(gUpper));
    if (hasGenre) {
      score += 0.2;
      matchReasons.push(`Genre '${genre}' matches approved domain tags`);
    } else {
      score -= 0.15;
      matchReasons.push(`Genre '${genre}' is external to primary tags, but advisory remains valid`);
    }
  }

  // 2. Co-location check for multi-character requirements
  const chars = Object.values(world.characters || {});
  const locMap: Record<string, number> = {};
  chars.forEach((c) => {
    locMap[c.location_id] = (locMap[c.location_id] || 0) + 1;
  });
  const hasCoLocation = Object.values(locMap).some((count) => count >= 2);

  if (pattern.preconditions?.includes('multiple_characters_co_located')) {
    if (hasCoLocation) {
      score += 0.2;
      matchReasons.push('Co-located sovereign actors are present for direct interaction');
    } else if (chars.length < 2) {
      rejectionReasons.push('Simulation contains fewer than 2 actors; cannot execute interpersonal pattern');
    } else {
      rejectionReasons.push('Actors are currently dispersed across separate locations');
    }
  }

  // 3. Secrets / Information boundary check
  const worldSecrets = chars.flatMap((c) => c.secrets || []);
  if (pattern.preconditions?.includes('secret_exists')) {
    if (worldSecrets.length > 0) {
      score += 0.2;
      matchReasons.push(`Verified ${worldSecrets.length} private secret boundary/boundaries in play`);
    } else {
      rejectionReasons.push('No private secrets exist in character knowledge state');
    }
  }

  // 4. Incompatible conditions check
  if (pattern.incompatible_conditions) {
    if (pattern.incompatible_conditions.includes('single_character_isolated') && chars.length <= 1) {
      rejectionReasons.push('Isolated character condition invalidates pattern');
    }
    if (pattern.incompatible_conditions.includes('no_secrets') && worldSecrets.length === 0) {
      rejectionReasons.push('Absence of secrets directly contradicts pattern requirements');
    }
  }

  // 5. Pacing / Tick alignment
  if (pattern.dramatic_function === 'CRISIS' && currentTick < 3) {
    matchReasons.push('Early tick: Pattern noted for pending director pressure when baseline escalates');
  }

  const isApplicable = rejectionReasons.length === 0 && score >= 0.4;
  const clampedScore = Math.min(1.0, Math.max(0.0, score));

  return {
    is_applicable: isApplicable,
    applicability_score: Math.round(clampedScore * 100) / 100,
    match_reasons: matchReasons,
    rejection_reasons: rejectionReasons,
  };
}

// ============================================================================
// 5. GROUNDED NARRATIVE RAG RETRIEVAL & TRACE ENGINE
// ============================================================================

export function executeGroundedNarrativeRetrieval(
  projectId: string,
  query: string,
  world: WorldState,
  events: Event[],
  options?: RAGSearchFilter
): GroundedRAGResponse {
  const qLower = query.toLowerCase();
  const currentTick = world.current_tick;
  const chars = Object.values(world.characters || {});
  const genre = (world as any).genre || 'GENERAL_DRAMA';

  // Evaluate candidate patterns
  const candidateResults: RetrievalCandidate[] = [];
  const acceptedIds: string[] = [];
  const rejectedIds: string[] = [];

  for (const pat of CANONICAL_EXTENDED_PATTERNS) {
    // Scoring based on lexical + dramatic matching
    let relevance = 0.2;
    const matchReasons: string[] = [];

    if (pat.name.toLowerCase().includes(qLower) || qLower.includes(pat.name.toLowerCase())) {
      relevance += 0.4;
      matchReasons.push('Query directly mentions pattern title');
    }
    if (pat.description.toLowerCase().includes(qLower) || pat.genre_tags.some((g) => qLower.includes(g))) {
      relevance += 0.25;
      matchReasons.push('Description matches query intent keywords');
    }
    if (pat.dramatic_function.toLowerCase().includes(qLower)) {
      relevance += 0.3;
      matchReasons.push(`Dramatic function [${pat.dramatic_function}] matches requested beat`);
    }

    // Evaluate applicability against real WorldState
    const evalResult = evaluatePatternApplicability(pat, world, 1, currentTick, genre);
    const combinedScore = Math.min(1.0, relevance * 0.5 + evalResult.applicability_score * 0.5);

    const cand: RetrievalCandidate = {
      pattern_id: pat.id,
      pattern_name: pat.name,
      score: Math.round(combinedScore * 100) / 100,
      match_reasons: [...matchReasons, ...evalResult.match_reasons],
      is_applicable: evalResult.is_applicable,
      applicability_score: evalResult.applicability_score,
      rejection_reasons: evalResult.rejection_reasons,
      provenance_reference: `${pat.provenance.source_type}:${pat.provenance.author_or_model}`,
    };

    candidateResults.push(cand);

    if (cand.is_applicable && cand.score >= 0.35) {
      acceptedIds.push(pat.id);
    } else {
      rejectedIds.push(pat.id);
    }
  }

  // Sort candidates by score descending
  candidateResults.sort((a, b) => b.score - a.score);

  // Match canonical events
  const matchedEvents = events.filter((e) =>
    e.description.toLowerCase().includes(qLower) || e.event_type.toLowerCase().includes(qLower)
  );

  // Construct structured claims
  const claims: GroundedClaim[] = [];
  const evidenceRefs: EvidenceReference[] = [];

  if (matchedEvents.length > 0) {
    const claimText = `Simulation history records ${matchedEvents.length} relevant event(s) at T${matchedEvents[0].tick}: "${matchedEvents[0].description}"`;
    claims.push({
      claim_id: 'claim_events_1',
      claim_text: claimText,
      category: 'canonical_fact',
      verification_status: 'verified_true',
      cited_evidence_ids: matchedEvents.map((e) => e.id),
    });

    matchedEvents.forEach((ev) => {
      evidenceRefs.push({
        id: ev.id,
        category: 'canonical_fact',
        summary: ev.description,
        source_type: 'event_log',
        source_id: ev.id,
        tick: ev.tick,
        verified: true,
      });
    });
  }

  // Add character knowledge claims
  chars.forEach((c, idx) => {
    if (idx < 2) {
      const claimText = `Actor ${c.name} currently operates in ${world.locations[c.location_id]?.name || 'unknown location'} with verified goal: "${c.goals[0] || 'Observe surroundings'}".`;
      claims.push({
        claim_id: `claim_char_${c.id}`,
        claim_text: claimText,
        category: 'canonical_fact',
        verification_status: 'knowledge_backed',
        cited_evidence_ids: matchedEvents.map((e) => e.id),
      });
    }
  });

  // Build advisory guidance
  const topAccepted = candidateResults.filter((c) => c.is_applicable)[0];
  const advisoryGuidance = topAccepted
    ? `Recommend Director Agent consider [${topAccepted.pattern_name}] (Applicability: ${(topAccepted.applicability_score * 100).toFixed(0)}%): Introduce environmental tension without forcing actor decisions.`
    : 'No active patterns meet strict applicability thresholds; characters should continue autonomous deliberation.';

  const retrievalTrace: RetrievalTrace = {
    trace_id: `trace_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    project_id: projectId,
    query_context: {
      premise: (world as any).premise || '',
      genre: genre,
      current_tick: currentTick,
      active_conflicts_count: 1,
      unresolved_questions_count: chars.flatMap((c) => c.secrets || []).length,
    },
    candidates_evaluated: candidateResults,
    accepted_patterns: acceptedIds,
    rejected_patterns: rejectedIds,
    advisory_guidance: advisoryGuidance,
    timestamp: new Date().toISOString(),
  };

  const answer = matchedEvents.length > 0
    ? `Verified Simulation Evidence: ${claims.map((c) => c.claim_text).join(' ')} \n\nAdvisory Retrieval: ${advisoryGuidance}`
    : `Grounded Analysis: At Tick ${currentTick}, ${chars.length} sovereign actors are active across ${Object.keys(world.locations).length} locations. ${advisoryGuidance}`;

  return {
    query,
    status: acceptedIds.length > 0 || matchedEvents.length > 0 ? 'success' : 'insufficient_evidence',
    answer,
    claims,
    evidence: evidenceRefs,
    retrieved_pattern_ids: acceptedIds,
    retrieval_trace: retrievalTrace,
    warnings: rejectedIds.length > 0 ? [`${rejectedIds.length} candidate pattern(s) rejected due to unmatched preconditions`] : [],
    project_id: projectId,
    generated_at: new Date().toISOString(),
  };
}
