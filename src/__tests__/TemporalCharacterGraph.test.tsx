import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TemporalCharacterGraph } from '../components/temporal_graph/TemporalCharacterGraph';
import { GroundedRAGInquiry } from '../components/temporal_graph/GroundedRAGInquiry';
import * as api from '../api';
import { TemporalGraphSnapshot, GroundedRAGResponse } from '../types';

const mockSnapshot: TemporalGraphSnapshot = {
  project_id: 'proj_test_1',
  tick: 3,
  max_tick: 5,
  event_count: 8,
  summary: 'Projection at Tick 3 / 5: 2 nodes, 1 edge.',
  generated_at: '2026-10-24T20:00:00Z',
  nodes: [
    {
      id: 'char_cross',
      name: 'Evelyn Cross',
      role: 'Detective',
      location_id: 'loc_bay',
      location_name: 'Harbor Bay',
      goals: ['goal_dossier'],
      beliefs: { prop_theft_occurred: true },
      emotional_state: { trust: 0.2, fear: 0.1, anger: 0.4, happiness: 0.0, curiosity: 0.7 },
      active_conflicts: [
        { peer_id: 'char_vane', aggregate_intensity: 0.85, dimensions: { goal_opposition: 0.85 } },
      ],
      secrets_count: 1,
      inventory_count: 2,
    },
    {
      id: 'char_vane',
      name: 'Vincent Vane',
      role: 'Smuggler',
      location_id: 'loc_bay',
      location_name: 'Harbor Bay',
      goals: ['goal_escape'],
      beliefs: { prop_theft_occurred: false },
      emotional_state: { trust: -0.3, fear: 0.5, anger: 0.6, happiness: -0.2, curiosity: 0.3 },
      active_conflicts: [
        { peer_id: 'char_cross', aggregate_intensity: 0.85, dimensions: { goal_opposition: 0.85 } },
      ],
      secrets_count: 2,
      inventory_count: 1,
    },
  ],
  edges: [
    {
      id: 'rel_cross_vane',
      source_id: 'char_cross',
      target_id: 'char_vane',
      source_name: 'Evelyn Cross',
      target_name: 'Vincent Vane',
      relationship_type: 'hostile',
      dimensions: {
        affinity: -0.6,
        trust: -0.5,
        suspicion: 0.9,
        fear: 0.3,
        resentment: 0.7,
      },
      aggregate_intensity: 0.65,
      directionality: 'mutual',
      evidence_event_ids: ['evt_01', 'evt_02'],
      recent_event_id: 'evt_02',
      first_observed_tick: 1,
      last_changed_tick: 3,
    },
  ],
};

const mockRAGResponse: GroundedRAGResponse = {
  query: 'What narrative patterns resemble the current conflict?',
  status: 'success',
  answer: 'The primary conflict between Cross and Vane aligns with the Cat-and-Mouse Investigation pattern (NG-002).',
  claims: [
    {
      claim_id: 'clm_1',
      claim_text: 'Cross and Vane are in acute hostile opposition evidenced by mutual suspicion and interrogations.',
      category: 'canonical_fact',
      verification_status: 'verified_true',
      cited_evidence_ids: ['evt_02'],
    },
    {
      claim_id: 'clm_2',
      claim_text: 'The dynamic exhibits classic Pressure and Concealment characteristics.',
      category: 'narrative_interpretation',
      verification_status: 'sound_inference',
      cited_evidence_ids: ['k_NG-002'],
    },
  ],
  evidence: [
    {
      id: 'evt_02',
      category: 'canonical_fact',
      summary: 'Interrogation event at harbor warehouse',
      source_type: 'EVENT',
      source_id: 'evt_02',
      tick: 3,
      verified: true,
    },
    {
      id: 'k_NG-002',
      category: 'retrieved_principle',
      summary: 'Cat-and-Mouse Dynamic',
      source_type: 'KNOWLEDGE_RECORD',
      source_id: 'NG-002',
      verified: true,
    },
  ],
  generated_at: '2026-10-24T20:00:00Z',
};

describe('TemporalCharacterGraph Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders graph nodes, relationship edge badges, and timeline scrubber', async () => {
    vi.spyOn(api, 'fetchTemporalGraph').mockResolvedValue(mockSnapshot);

    render(<TemporalCharacterGraph projectId="proj_test_1" initialTick={3} />);

    // Check title and tick badge
    expect(await screen.findByText(/Temporal Character-Relationship Graph/i)).toBeDefined();
    expect(screen.getByText('Tick 3 / 5')).toBeDefined();

    // Check nodes rendered
    expect(screen.getByText('Evelyn Cross')).toBeDefined();
    expect(screen.getByText('Vincent Vane')).toBeDefined();

    // Check edge relationship type badge
    expect(screen.getByText('HOSTILE')).toBeDefined();
  });

  it('clicking a character node opens the character inspector drawer', async () => {
    vi.spyOn(api, 'fetchTemporalGraph').mockResolvedValue(mockSnapshot);

    render(<TemporalCharacterGraph projectId="proj_test_1" initialTick={3} />);

    const crossNode = await screen.findByText('Evelyn Cross');
    fireEvent.click(crossNode);

    // Inspector opens with character details
    expect(await screen.findByText('Character Inspection @ Tick 3')).toBeDefined();
    expect(screen.getAllByText('Detective').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Harbor Bay', { exact: false }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('prop_theft_occurred')).toBeDefined();
  });

  it('supports compare snapshots diff mode', async () => {
    vi.spyOn(api, 'fetchTemporalGraph').mockResolvedValue(mockSnapshot);
    vi.spyOn(api, 'fetchTemporalGraphDiff').mockResolvedValue({
      project_id: 'proj_test_1',
      from_tick: 1,
      to_tick: 3,
      node_changes: [
        {
          character_id: 'char_cross',
          change_type: 'location_changed',
          description: 'Evelyn Cross moved to Harbor Bay',
        },
      ],
      edge_changes: [
        {
          edge_id: 'rel_cross_vane',
          source_id: 'char_cross',
          target_id: 'char_vane',
          change_type: 'dimensions_shifted',
          description: 'Suspicion rose to 0.90',
        },
      ],
      causal_event_ids: ['evt_02'],
      summary: 'Diff from Tick 1 to 3: 1 node delta, 1 edge delta.',
    });

    render(<TemporalCharacterGraph projectId="proj_test_1" initialTick={3} />);

    const diffBtn = await screen.findByText('Compare Snapshots (Diff)');
    fireEvent.click(diffBtn);

    const computeBtn = await screen.findByText('Compute Diff');
    fireEvent.click(computeBtn);

    expect(await screen.findByText('Evelyn Cross moved to Harbor Bay')).toBeDefined();
    expect(screen.getByText('Suspicion rose to 0.90')).toBeDefined();
  });
});

describe('GroundedRAGInquiry Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders inquiry interface and executes grounded query with evidence citations', async () => {
    vi.spyOn(api, 'queryNarrativeRAG').mockResolvedValue(mockRAGResponse);

    render(<GroundedRAGInquiry projectId="proj_test_1" />);

    expect(screen.getByText(/Narrative Intelligence & Grounded RAG/i)).toBeDefined();

    // Click preset query button
    const presetBtn = screen.getByText('What narrative patterns resemble the current conflict?');
    fireEvent.click(presetBtn);

    // Wait for synthesis response
    expect(await screen.findByText(/Cat-and-Mouse Investigation pattern/)).toBeDefined();
    expect(screen.getByText(/canonical fact/i)).toBeDefined();
    expect(screen.getAllByText('evt_02', { exact: false }).length).toBeGreaterThanOrEqual(1);
  });

  it('executes retrieval benchmark comparing BM25 vs local feature embeddings', async () => {
    vi.spyOn(api, 'fetchNarrativeRAGBenchmark').mockResolvedValue({
      query: 'confrontation revelation',
      embedding_model: 'local-feature-hashing-128d',
      index_version: '1.0',
      lexical: [{ id: 'NG-001', title: 'Sudden Revelation', score: 3.5 }],
      semantic: [{ id: 'NG-002', title: 'Cat-and-Mouse', score: 0.82 }],
      hybrid: [{ id: 'NG-001', title: 'Sudden Revelation', score: 2.1 }],
    });

    render(<GroundedRAGInquiry projectId="proj_test_1" />);

    const benchBtn = screen.getByText('BM25 vs Embedding Benchmark');
    fireEvent.click(benchBtn);

    expect(await screen.findByText(/Retrieval Benchmark: BM25 Lexical vs Local Feature Embeddings/)).toBeDefined();
    expect(screen.getByText('BM25 Lexical Hits')).toBeDefined();
    expect(screen.getByText('Local Semantic Hits')).toBeDefined();
    expect(screen.getByText('Hybrid Merged Ranking')).toBeDefined();
  });
});
