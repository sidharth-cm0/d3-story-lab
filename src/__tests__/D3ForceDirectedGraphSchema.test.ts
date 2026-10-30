import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  createNewProjectLogic,
  getTemporalGraphLogic,
  stepSimulationLogic,
  TEMPORAL_GRAPH_SCHEMA_VERSION,
} from '../services/simulationEngine';
import {
  TemporalGraphSnapshot,
  TemporalGraphEdge,
  TemporalGraphNode,
} from '../types';

describe('D3 Force-Directed Graph & Versioned Schema (Canonical vs Hypothesis)', () => {
  test('1. Versioned Schema: Emits schema_version 2.1.0 with complete epistemic counts', () => {
    const proj = createNewProjectLogic(
      'Deep beneath the Arctic ice shelf, a research station discovers an extraterrestrial signal.',
      'SCI_FI',
      'beginning',
      20,
      'AUTO',
      undefined,
      undefined,
      'CHRONOLOGICAL',
      101
    );

    // Step simulation 4 ticks to generate verified events
    for (let t = 0; t < 4; t++) {
      stepSimulationLogic(proj.id, 1);
    }

    const snapshot: TemporalGraphSnapshot = getTemporalGraphLogic(proj.id);

    assert.equal(snapshot.schema_version, '2.1.0');
    assert.equal(snapshot.schema_version, TEMPORAL_GRAPH_SCHEMA_VERSION);
    assert.equal(snapshot.project_id, proj.id);
    assert.ok(snapshot.tick >= 4, `Tick should be >= 4, got ${snapshot.tick}`);
    assert.ok(typeof snapshot.canonical_edge_count === 'number' && snapshot.canonical_edge_count > 0);
    assert.ok(typeof snapshot.hypothesis_edge_count === 'number' && snapshot.hypothesis_edge_count > 0);
    assert.ok(typeof snapshot.causal_event_count === 'number' && snapshot.causal_event_count > 0);
  });

  test('2. Node Differentiation: Distinct character entities and causal event nodes', () => {
    const proj = createNewProjectLogic(
      'In a storm-isolated Victorian manor, the family will is contested amidst sudden disappearances.',
      'GOTHIC_MYSTERY',
      'beginning',
      20,
      'AUTO',
      undefined,
      undefined,
      'CHRONOLOGICAL',
      202
    );

    for (let t = 0; t < 3; t++) {
      stepSimulationLogic(proj.id, 1);
    }

    const snapshot = getTemporalGraphLogic(proj.id);

    const characterNodes = snapshot.nodes.filter((n) => n.node_type === 'character');
    const causalEventNodes = snapshot.nodes.filter((n) => n.node_type === 'causal_event');

    assert.ok(characterNodes.length >= 2, 'Must include character nodes');
    assert.ok(causalEventNodes.length >= 1, 'Must include causal event nodes');

    // Validate character node contract
    const cNode = characterNodes[0];
    assert.ok(cNode.name, 'Character must have name');
    assert.ok(cNode.role, 'Character must have role');
    assert.ok(cNode.emotional_state, 'Character must have emotional_state');
    assert.ok(typeof cNode.secrets_count === 'number', 'Character must track secrets_count');

    // Validate causal event node contract
    const eNode = causalEventNodes[0];
    assert.ok(eNode.id.startsWith('evt_node_'), `Event node id should start with evt_node_, got ${eNode.id}`);
    assert.ok(typeof eNode.tick === 'number', 'Event node must have tick');
    assert.ok(eNode.description, 'Event node must have event description');
    assert.ok(typeof eNode.significance === 'number', 'Event node must have significance metric');
  });

  test('3. Epistemic Separation: Distinguishes canonical ground-truth from analytical hypotheses', () => {
    const proj = createNewProjectLogic(
      'Onboard a deep-submergence naval patrol, the acoustic sonar picks up unchartered metallic pulses.',
      'SUBMARINE',
      'beginning',
      20,
      'AUTO',
      undefined,
      undefined,
      'CHRONOLOGICAL',
      303
    );

    for (let t = 0; t < 5; t++) {
      stepSimulationLogic(proj.id, 1);
    }

    const snapshot = getTemporalGraphLogic(proj.id);

    const canonicalEdges = snapshot.edges.filter((e) => e.edge_category === 'canonical');
    const hypothesisEdges = snapshot.edges.filter((e) => e.edge_category === 'analytical_hypothesis');

    assert.ok(canonicalEdges.length > 0, 'Must have canonical edges');
    assert.ok(hypothesisEdges.length > 0, 'Must have analytical hypothesis edges');

    // Verify CANONICAL properties
    for (const cEdge of canonicalEdges) {
      assert.equal(cEdge.edge_category, 'canonical');
      assert.equal(cEdge.verification_status, 'canonical_verified');
      assert.equal(cEdge.confidence, 1.0, 'Canonical edges must have 100% (1.0) confidence');
      assert.ok(
        cEdge.epistemic_source === 'canonical_world_state' || cEdge.epistemic_source === 'immutable_event_log',
        `Canonical source must be world state or event log, got ${cEdge.epistemic_source}`
      );
    }

    // Verify ANALYTICAL HYPOTHESIS properties
    for (const hEdge of hypothesisEdges) {
      assert.equal(hEdge.edge_category, 'analytical_hypothesis');
      assert.ok(
        hEdge.verification_status === 'hypothesis_supported' || hEdge.verification_status === 'hypothesis_provisional',
        `Hypothesis verification status unexpected: ${hEdge.verification_status}`
      );
      assert.ok(
        hEdge.confidence !== undefined && hEdge.confidence < 1.0 && hEdge.confidence >= 0.5,
        `Hypothesis confidence must be fractional < 1.0, got ${hEdge.confidence}`
      );
      assert.equal(hEdge.epistemic_source, 'narrative_intelligence_observer');
      assert.ok(hEdge.hypothesis_rationale && hEdge.hypothesis_rationale.length > 20, 'Must contain analytical rationale');
      assert.ok(Array.isArray(hEdge.falsification_conditions) && hEdge.falsification_conditions.length >= 1, 'Must define falsification conditions');
    }
  });

  test('4. Causal Agency: Links actors to causal events with verifiable provenance', () => {
    const proj = createNewProjectLogic(
      'Emergency room surgical unit faces a mass casualty surge with dwindling plasma reserves.',
      'MEDICAL',
      'beginning',
      20,
      'AUTO',
      undefined,
      undefined,
      'CHRONOLOGICAL',
      404
    );

    for (let t = 0; t < 4; t++) {
      stepSimulationLogic(proj.id, 1);
    }

    const snapshot = getTemporalGraphLogic(proj.id);

    // Look for causal action edges (Character -> Event)
    const causalActionEdges = snapshot.edges.filter((e) => e.edge_kind === 'causal_action');
    assert.ok(causalActionEdges.length > 0, 'Should record causal action edges linking characters to events');

    const actionEdge = causalActionEdges[0];
    assert.ok(actionEdge.source_id, 'Source must be character id');
    assert.ok(actionEdge.target_id.startsWith('evt_node_'), 'Target must be causal event node id');
    assert.ok(actionEdge.evidence_event_ids.length > 0, 'Must cite exact event id evidence');
  });

  test('5. Replay Determinism: Identical tick query produces identical graph topologies', () => {
    const proj = createNewProjectLogic(
      'A disgraced detective is assigned to protect a witness in an underground high-stakes courtroom.',
      'COURTROOM',
      'beginning',
      20,
      'AUTO',
      undefined,
      undefined,
      'CHRONOLOGICAL',
      505
    );

    for (let t = 0; t < 3; t++) {
      stepSimulationLogic(proj.id, 1);
    }

    const snapshot1 = getTemporalGraphLogic(proj.id, 2);
    const snapshot2 = getTemporalGraphLogic(proj.id, 2);

    assert.equal(snapshot1.nodes.length, snapshot2.nodes.length);
    assert.equal(snapshot1.edges.length, snapshot2.edges.length);
    assert.equal(snapshot1.canonical_edge_count, snapshot2.canonical_edge_count);
    assert.equal(snapshot1.hypothesis_edge_count, snapshot2.hypothesis_edge_count);

    // Compare edge IDs
    const ids1 = snapshot1.edges.map((e) => e.id).sort();
    const ids2 = snapshot2.edges.map((e) => e.id).sort();
    assert.deepEqual(ids1, ids2);
  });
});
