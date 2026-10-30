import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  validateNarrativePattern,
  extractNarrativePatterns,
  evaluatePatternApplicability,
  executeGroundedNarrativeRetrieval,
  CANONICAL_EXTENDED_PATTERNS,
} from '../services/narrativeGenome';

import {
  exportFountainScreenplay,
  exportSynopsisMarkdown,
  exportShotPlanCSV,
  exportShotPlanJSON,
  exportCompleteProjectBundle,
} from '../services/exportService';

import {
  createNewProjectLogic,
  stepSimulationLogic,
  generateScreenplayLogic,
  simulationStore,
} from '../services/simulationEngine';

describe('D3 Story Lab — Narrative Intelligence & Production Export Suite', () => {
  // ==========================================================================
  // Test 1: Narrative Genome Schema Validation & Catalog Completeness
  // ==========================================================================
  it('1. Narrative Genome Schema: Validates canonical patterns and rejects invalid schemas', () => {
    // Check all canonical extended patterns validate
    assert.ok(CANONICAL_EXTENDED_PATTERNS.length >= 8, 'Must have at least 8 rich canonical patterns');
    CANONICAL_EXTENDED_PATTERNS.forEach((p) => {
      const res = validateNarrativePattern(p);
      assert.equal(res.valid, true, `Pattern ${p.id} must be valid`);
      assert.ok(p.pattern_id.startsWith('NG-'), `Pattern ${p.id} must have valid ID prefix`);
      assert.ok(p.dramatic_function.length > 0, `Pattern ${p.id} must have dramatic function`);
      assert.ok(p.provenance.source_type.length > 0, `Pattern ${p.id} must have provenance source`);
      assert.ok(p.rights_or_license_status.length > 0, `Pattern ${p.id} must declare license status`);
    });

    // Test invalid schema rejection
    const invalidPattern = {
      id: '',
      name: '',
      // missing dramatic_function and description
    };
    const invRes = validateNarrativePattern(invalidPattern);
    assert.equal(invRes.valid, false, 'Invalid pattern must be rejected');
    assert.ok(invRes.errors.length >= 2, 'Should return multiple validation errors');
  });

  // ==========================================================================
  // Test 2: Deterministic Pattern Extraction from Premise
  // ==========================================================================
  it('2. Pattern Extraction: Extracts abstract narrative mechanisms without verbatim copying', () => {
    const premise =
      'At midnight inside the naval submarine control center, Commander Zhang conceals an unlogged sonar contact while Lieutenant Ross races against an oxygen countdown deadline.';

    const extraction = extractNarrativePatterns(premise, { genre: 'SUBMARINE' });

    assert.ok(extraction.extracted_patterns.length > 0, 'Must extract candidate patterns');
    const patternIds = extraction.extracted_patterns.map((p) => p.id);

    // Should detect concealment (NG-001) and deadline pressure (NG-004)
    assert.ok(patternIds.includes('NG-001'), 'Must match NG-001 (Concealed Information)');
    assert.ok(patternIds.includes('NG-004'), 'Must match NG-004 (External Deadline Pressure)');

    // Verify extraction trace is inspectable
    assert.ok(extraction.extraction_trace.includes('Ingested premise payload'), 'Trace must explain process');
    assert.ok(extraction.deduplicated_count >= 0, 'Must track deduplication count');
  });

  // ==========================================================================
  // Test 3: Pattern Applicability & Contradiction Filtering
  // ==========================================================================
  it('3. Applicability Evaluator: Enforces preconditions and rejects ungrounded patterns', () => {
    // Create a real project
    const meta = createNewProjectLogic({
      seedPrompt: 'Detective inspects the locked estate study while an attorney watches silently.',
      title: 'Applicability Test Estate',
      inputType: 'beginning',
      seed: 554433,
    });

    const project = simulationStore.getProject(meta.id)!;
    assert.ok(project, 'Project must exist');

    const patConceal = CANONICAL_EXTENDED_PATTERNS.find((p) => p.id === 'NG-001')!;
    const evalResult = evaluatePatternApplicability(patConceal, project.world, 1, 1, 'GOTHIC_MYSTERY');

    // Should be applicable because 2 characters and secrets exist
    assert.equal(typeof evalResult.is_applicable, 'boolean');
    assert.ok(evalResult.applicability_score > 0, 'Must score applicability');
    assert.ok(evalResult.match_reasons.length > 0, 'Must state match reasons');

    // Test rejection when conditions are contradicted:
    // Create isolated world with 1 character and no secrets
    const emptyWorld = {
      ...project.world,
      characters: {
        lone_char: {
          ...Object.values(project.world.characters)[0],
          id: 'lone_char',
          location_id: 'loc_study',
          secrets: [],
        },
      },
    };

    const isolatedEval = evaluatePatternApplicability(patConceal, emptyWorld as any, 0, 1);
    assert.equal(isolatedEval.is_applicable, false, 'Pattern requiring multiple co-located actors with secrets must be rejected');
    assert.ok(isolatedEval.rejection_reasons.length > 0, 'Rejection reasons must be explicit and diagnosable');
  });

  // ==========================================================================
  // Test 4: Grounded Narrative RAG with Inspectable Retrieval Trace
  // ==========================================================================
  it('4. Grounded Narrative RAG: Produces verifiable claims and transparent retrieval traces', () => {
    const meta = createNewProjectLogic({
      seedPrompt: 'During an intensive hospital triage, Dr. Helen Vance protects the restricted pathogen ledger.',
      title: 'Hospital Triage RAG Test',
      inputType: 'beginning',
      seed: 887766,
    });

    // Advance 3 ticks to record historical events
    stepSimulationLogic(meta.id, 3);

    const project = simulationStore.getProject(meta.id)!;
    const events = Object.values(project.world.events || {});

    const ragRes = executeGroundedNarrativeRetrieval(
      meta.id,
      'What evidence exists regarding pathogen ledger concealment?',
      project.world,
      events
    );

    assert.equal(ragRes.status, 'success', 'RAG query must succeed');
    assert.ok(ragRes.claims.length > 0, 'Must produce structured claims');
    assert.ok(ragRes.claims[0].claim_text.length > 0, 'Claim text must be populated');

    // Verify inspectable Retrieval Trace (Part IV Section 9.4)
    assert.ok(ragRes.retrieval_trace, 'Must generate inspectable Retrieval Trace');
    const trace = ragRes.retrieval_trace!;
    assert.ok(trace.trace_id.startsWith('trace_'), 'Trace ID must be formatted');
    assert.ok(trace.candidates_evaluated.length > 0, 'Must evaluate candidates');
    assert.ok(trace.advisory_guidance && trace.advisory_guidance.length > 0, 'Must provide advisory guidance');

    // Ensure candidate evaluation tracks both matches and rejections
    const hasApplicable = trace.candidates_evaluated.some((c) => c.is_applicable);
    assert.equal(hasApplicable, true, 'At least one candidate must be applicable in a populated simulation');
  });

  // ==========================================================================
  // Test 5: Multi-Format Production Exports (Fountain, Markdown, CSV, JSON, Bundle)
  // ==========================================================================
  it('5. Production Exports: Generates verified artifacts across all supported formats', () => {
    const meta = createNewProjectLogic({
      seedPrompt: 'Marshal Cole confronts an uncooperative deputy in the frontier telegraph depot.',
      title: 'Frontier Telegraph Test',
      inputType: 'beginning',
      seed: 991122,
    });

    // Step simulation and generate screenplay & shot plan
    stepSimulationLogic(meta.id, 4);
    generateScreenplayLogic(meta.id, 'chronological');

    const project = simulationStore.getProject(meta.id)!;

    // 1. Fountain Screenplay
    const fountain = exportFountainScreenplay(project);
    assert.ok(fountain.includes('Title:'), 'Fountain must include Title block');
    assert.ok(fountain.includes('INT.') || fountain.includes('EXT.'), 'Fountain must include scene sluglines');
    assert.ok(fountain.includes('D3 Story Lab'), 'Fountain must attribute scribe engine');

    // 2. Three-Tier Synopsis Markdown
    const synopsis = exportSynopsisMarkdown(project);
    assert.ok(synopsis.includes('# Frontier Telegraph Test'), 'Synopsis must include title');
    assert.ok(synopsis.includes('## 1. Logline'), 'Synopsis must include Logline');
    assert.ok(synopsis.includes('## 2. Dramatic Premise & Stakes'), 'Synopsis must include Premise & Stakes');
    assert.ok(synopsis.includes('## 3. Sovereign Character Roster'), 'Synopsis must include Character Roster');
    assert.ok(synopsis.includes('## 4. Episodic Structure & Narrative Beats'), 'Synopsis must include Beats');
    assert.ok(synopsis.includes('## 5. Verified Historical Event Log'), 'Synopsis must include Event Log');

    // 3. Cinematic Shot Plan CSV
    const csv = exportShotPlanCSV(project);
    const csvLines = csv.trim().split('\n');
    assert.ok(csvLines.length >= 2, 'CSV must contain at least header and one data row');
    assert.ok(csvLines[0].includes('scene_number,shot_number,panel_id'), 'CSV must contain standard headers');
    assert.ok(csvLines[0].includes('camera_angle'), 'CSV must contain camera angle');
    assert.ok(csvLines[0].includes('lighting'), 'CSV must contain lighting');

    // 4. Shot Plan JSON
    const jsonStr = exportShotPlanJSON(project);
    const parsedJson = JSON.parse(jsonStr);
    assert.ok(Array.isArray(parsedJson.panels), 'Shot plan JSON must contain panels array');

    // 5. Complete Project Production Bundle
    const bundleStr = exportCompleteProjectBundle(project);
    const bundle = JSON.parse(bundleStr);
    assert.equal(bundle.bundle_version, '1.0.0');
    assert.equal(bundle.governing_principle, 'STRUCTURE_WITHOUT_PUPPETRY');
    assert.ok(bundle.world_state, 'Bundle must contain world state');
    assert.ok(Array.isArray(bundle.event_history), 'Bundle must contain event history');
    assert.ok(bundle.screenplay_document, 'Bundle must contain screenplay document');
    assert.ok(bundle.audit_provenance.is_grounded, 'Bundle must declare grounding audit provenance');
  });

  // ==========================================================================
  // Test 6: Bidirectional Provenance Integrity
  // ==========================================================================
  it('6. Bidirectional Provenance: Screenplay blocks trace to real events without hallucinated actions', () => {
    const meta = createNewProjectLogic({
      seedPrompt: 'Courtroom defense attorney presents a forensic ledger to an evasive witness.',
      title: 'Courtroom Provenance Test',
      inputType: 'beginning',
      seed: 334455,
    });

    stepSimulationLogic(meta.id, 5);
    generateScreenplayLogic(meta.id, 'chronological');

    const project = simulationStore.getProject(meta.id)!;
    const events = project.world.events || {};

    assert.ok(project.screenplay, 'Screenplay must exist');
    assert.ok(project.screenplay.scenes.length > 0, 'Scenes must exist');

    // Check each scene has source event IDs
    project.screenplay.scenes.forEach((scene) => {
      assert.ok(scene.source_event_ids.length > 0, `Scene ${scene.id} must have source event IDs`);
      scene.source_event_ids.forEach((eid) => {
        assert.ok(events[eid], `Source event ID ${eid} must exist in canonical world.events`);
      });

      // Check each block has source event IDs
      scene.blocks.forEach((block) => {
        assert.ok(Array.isArray(block.source_event_ids), 'Block must have source_event_ids array');
        block.source_event_ids.forEach((eid) => {
          assert.ok(events[eid], `Block source event ${eid} must exist in world events`);
        });
      });
    });
  });
});
