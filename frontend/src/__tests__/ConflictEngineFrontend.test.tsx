import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CharacterCards } from '../components/CharacterCards';
import * as api from '../api';
import { WorldState, ConflictGraph } from '../types';

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api');
  return {
    ...actual,
    getProjectConflicts: vi.fn(),
    deriveProjectConflicts: vi.fn(),
    getPairwiseConflict: vi.fn(),
    getProjectRelationships: vi.fn(),
  };
});

const mockWorld: WorldState = {
  id: 'world_conflict_test',
  name: 'Conflict Test World',
  description: 'Simulation world for testing Phase D frontend',
  current_tick: 2,
  locations: {
    loc_gallery: {
      id: 'loc_gallery',
      name: 'Private Gallery',
      description: 'Gallery room',
      connected_locations: [],
    },
  },
  characters: {
    char_arjun: {
      id: 'char_arjun',
      name: 'Arjun',
      role: 'Investigator',
      location_id: 'loc_gallery',
      goals: ['goal_1'],
      beliefs: [],
      secrets: [],
      relationships: ['rel_arjun_maya'],
      emotional_state: {
        happiness: 0.0,
        fear: 0.2,
        anger: 0.4,
        trust: -0.3,
        curiosity: 0.8,
      },
    },
    char_maya: {
      id: 'char_maya',
      name: 'Maya',
      role: 'Curator',
      location_id: 'loc_gallery',
      goals: ['goal_2'],
      beliefs: [],
      secrets: [],
      relationships: ['rel_arjun_maya'],
      emotional_state: {
        happiness: 0.1,
        fear: 0.6,
        anger: 0.2,
        trust: -0.4,
        curiosity: 0.5,
      },
    },
  },
  relationships: {
    rel_arjun_maya: {
      id: 'rel_arjun_maya',
      character_a_id: 'char_arjun',
      character_b_id: 'char_maya',
      affinity: -0.4,
      trust: -0.5,
      affection: -0.2,
      fear: 0.35,
      respect: 0.4,
      resentment: 0.6,
      suspicion: 0.75,
      dependency: 0.3,
      power_imbalance: 0.2,
      history: 'A bitter disagreement over authenticity records',
      event_provenance: {
        suspicion: ['evt_accuse_001'],
        resentment: ['evt_accuse_001'],
      },
      last_event_id: 'evt_accuse_001',
    },
  },
  objects: {},
  goals: {
    goal_1: {
      id: 'goal_1',
      character_id: 'char_arjun',
      description: 'Expose the forgery',
      priority: 0.9,
      status: 'active',
    },
    goal_2: {
      id: 'goal_2',
      character_id: 'char_maya',
      description: 'Conceal the painting provenance',
      priority: 0.85,
      status: 'active',
    },
  },
  beliefs: {},
  secrets: {},
  events: {},
};

const mockConflictGraph: ConflictGraph = {
  project_id: 'world_conflict_test',
  generated_at: '2026-09-25T12:00:00Z',
  edges: [
    {
      source_character_id: 'char_arjun',
      target_character_id: 'char_maya',
      dimensions: {
        goal_opposition: 0.9,
        relationship_tension: 0.75,
        secret_exposure_risk: 0.8,
      },
      evidence: [
        {
          dimension: 'goal_opposition',
          source_id: 'goal_1',
          target_id: 'goal_2',
          description: "Opposing objectives: 'Expose the forgery' vs 'Conceal the painting provenance'",
        },
        {
          dimension: 'relationship_tension',
          source_id: 'rel_arjun_maya',
          description: 'High suspicion and resentment accumulated',
        },
      ],
      aggregate_intensity: 0.82,
      is_analytical_only: true,
    },
  ],
};

describe('Phase D: Conflict Engine & Multidimensional Relationships Frontend', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getProjectConflicts).mockResolvedValue(mockConflictGraph);
    vi.mocked(api.deriveProjectConflicts).mockResolvedValue(mockConflictGraph);
  });

  it('renders multidimensional relationship dimensions and event provenance tags', async () => {
    render(<CharacterCards world={mockWorld} projectId="world_conflict_test" />);

    // Peer relationship cards should render
    expect(screen.getAllByText('RELATIONSHIPS').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/▸ Maya/).length).toBeGreaterThan(0);

    // Dimension pills
    expect(screen.getAllByText(/Trust: -0.50/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Affinity: -0.40/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Suspicion: \+0.75/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Resentment: \+0.60/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Fear: \+0.35/).length).toBeGreaterThan(0);

    // Event provenance tag
    expect(screen.getAllByText(/evt: se_001/).length).toBeGreaterThan(0);
  });

  it('renders high-level dramatic conflict summary with intensity pills and active dimensions', async () => {
    render(<CharacterCards world={mockWorld} projectId="world_conflict_test" />);

    await waitFor(() => {
      expect(screen.getAllByText('DRAMATIC CONFLICT (ANALYSIS)').length).toBeGreaterThan(0);
    });

    // Pairwise conflict targets and intensity pills
    expect(screen.getAllByText('vs Maya').length).toBeGreaterThan(0);
    expect(screen.getAllByText('HIGH (82%)').length).toBeGreaterThan(0);

    // Active dimension tags
    expect(screen.getAllByText('GOAL OPPOSITION').length).toBeGreaterThan(0);
    expect(screen.getAllByText('RELATIONSHIP TENSION').length).toBeGreaterThan(0);
  });

  it('expands and collapses traceable conflict evidence on click', async () => {
    render(<CharacterCards world={mockWorld} projectId="world_conflict_test" />);

    await waitFor(() => {
      expect(screen.getAllByText('vs Maya').length).toBeGreaterThan(0);
    });

    // Evidence panel initially not visible
    expect(screen.queryByText('TRACEABLE CONFLICT EVIDENCE')).toBeNull();

    // Click to expand evidence
    const conflictCard = screen.getAllByText('vs Maya')[0];
    fireEvent.click(conflictCard);

    // Evidence panel is now visible
    expect(screen.getByText('TRACEABLE CONFLICT EVIDENCE')).toBeDefined();
    expect(screen.getByText(/Opposing objectives: 'Expose the forgery'/)).toBeDefined();

    // Click again to collapse
    fireEvent.click(conflictCard);
    expect(screen.queryByText('TRACEABLE CONFLICT EVIDENCE')).toBeNull();
  });

  it('calls deriveProjectConflicts when Analyze Conflicts button is clicked', async () => {
    render(<CharacterCards world={mockWorld} projectId="world_conflict_test" />);

    const analyzeBtn = screen.getByText('⚡ Analyze Conflicts');
    expect(analyzeBtn).toBeDefined();

    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(api.deriveProjectConflicts).toHaveBeenCalledWith('world_conflict_test');
    });
  });

  it('renders locked indicator, user-authored evidence badge, and derived_at_tick', async () => {
    const lockedConflictGraph: ConflictGraph = {
      project_id: 'world_conflict_test',
      generated_at: '2026-09-25T12:00:00Z',
      derived_at_tick: 5,
      edges: [
        {
          source_character_id: 'char_arjun',
          target_character_id: 'char_maya',
          dimensions: {
            moral_conflict: 0.95,
            relationship_tension: 0.4,
          },
          evidence: [
            {
              dimension: 'moral_conflict',
              source_id: 'moral_premise_1',
              description: 'User-specified moral boundary clash',
              is_user_authored: true,
            },
            {
              dimension: 'relationship_tension',
              source_id: 'rel_arjun_maya',
              description: 'Runtime tension',
              is_user_authored: false,
            },
          ],
          aggregate_intensity: 0.75,
          is_analytical_only: true,
          is_locked: true,
          locked_dimensions: ['moral_conflict'],
        },
      ],
    };

    vi.mocked(api.getProjectConflicts).mockResolvedValue(lockedConflictGraph);

    render(<CharacterCards world={mockWorld} projectId="world_conflict_test" />);

    await waitFor(() => {
      expect(screen.getAllByText('(TICK 5)').length).toBeGreaterThan(0);
      expect(screen.getAllByText('LOCKED').length).toBeGreaterThan(0);
    });

    // Expand evidence
    const conflictCard = screen.getAllByText('vs Maya')[0];
    fireEvent.click(conflictCard);

    expect(screen.getByText('[USER DESIGN]')).toBeDefined();
    expect(screen.getByText('User-specified moral boundary clash')).toBeDefined();
  });
});
