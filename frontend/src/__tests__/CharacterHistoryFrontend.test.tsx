import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { CharacterCards } from '../components/CharacterCards';
import * as api from '../api';
import { WorldState, CharacterHistorySeries } from '../types';

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api');
  return {
    ...actual,
    getProjectConflicts: vi.fn(),
    deriveProjectConflicts: vi.fn(),
    getPairwiseConflict: vi.fn(),
    getProjectRelationships: vi.fn(),
    getRelationshipDimensionHistory: vi.fn(),
    getCharacterHistory: vi.fn(),
    getCharacterTrajectoryHistory: vi.fn(),
    getCharacterHistoryBatch: vi.fn(),
  };
});

const mockWorld: WorldState = {
  id: 'world_history_test',
  name: 'History Test World',
  description: 'Simulation world for testing Phase E frontend',
  current_tick: 5,
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
        curiosity: 0.3,
      },
    },
  },
  objects: {},
  events: {},
  beliefs: {},
  secrets: {},
  goals: {
    goal_1: {
      id: 'goal_1',
      character_id: 'char_arjun',
      description: 'Audit records',
      priority: 0.9,
      status: 'active',
    },
    goal_2: {
      id: 'goal_2',
      character_id: 'char_maya',
      description: 'Pass audit',
      priority: 0.8,
      status: 'active',
    },
  },
  relationships: {
    rel_arjun_maya: {
      id: 'rel_arjun_maya',
      character_a_id: 'char_arjun',
      character_b_id: 'char_maya',
      affinity: -0.2,
      trust: -0.3,
      affection: 0.0,
      fear: 0.3,
      dependency: 0.0,
      respect: 0.4,
      resentment: 0.5,
      suspicion: 0.6,
      power_imbalance: 0.1,
      last_event_id: 'evt_002',
      event_provenance: {
        trust: ['evt_002'],
        suspicion: ['evt_002'],
      },
    },
  },
};

describe('Phase E: Character State History Frontend Integration', () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getProjectConflicts).mockResolvedValue({ project_id: 'world_history_test', edges: [] });
  });

  it('renders Trust History toggle button for character relationships', () => {
    render(<CharacterCards world={mockWorld} projectId="proj_test_e" />);
    const buttons = screen.getAllByRole('button', { name: /trust history/i });
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('fetches and displays reconstructed history timeline with event provenance on click', async () => {
    const mockSeries: CharacterHistorySeries = {
      character_id: 'char_arjun',
      target_character_id: 'char_maya',
      metric: 'trust',
      display_name: 'Trust vs Maya',
      is_sparse: true,
      is_analytical_only: true,
      points: [
        {
          tick: 0,
          value: 0.0,
          event_ids: [],
          label: 'Initial baseline',
        },
        {
          tick: 2,
          value: -0.3,
          event_ids: ['evt_002'],
          label: 'Arjun formally accused Maya of fabricating invoices.',
        },
      ],
    };

    vi.mocked(api.getRelationshipDimensionHistory).mockResolvedValueOnce(mockSeries);

    render(<CharacterCards world={mockWorld} projectId="proj_test_e" />);

    const buttons = screen.getAllByRole('button', { name: /trust history/i });
    fireEvent.click(buttons[0]);

    expect(api.getRelationshipDimensionHistory).toHaveBeenCalledWith(
      'proj_test_e',
      expect.any(String),
      expect.any(String),
      'trust',
      true
    );

    // Check button state
    await waitFor(() => {
      expect(screen.getByText(/hide history/i)).toBeTruthy();
    });

    await waitFor(() => {
      expect(screen.getByText('T+0')).toBeTruthy();
      expect(screen.getByText('T+2')).toBeTruthy();
      expect(screen.getByText('evt:evt_002')).toBeTruthy();
    });
  });

  it('exports API functions for character history and trajectory querying', () => {
    expect(typeof api.getCharacterHistory).toBe('function');
    expect(typeof api.getRelationshipDimensionHistory).toBe('function');
    expect(typeof api.getCharacterTrajectoryHistory).toBe('function');
    expect(typeof api.getCharacterHistoryBatch).toBe('function');
  });
});
