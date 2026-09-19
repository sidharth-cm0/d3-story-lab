import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { StructureAndArcsViewer, StructureErrorBoundary } from '../components/StructureAndArcsViewer';
import { Header } from '../components/Header';
import { ProjectData } from '../types';

const mockProjectData: ProjectData = {
  metadata: {
    id: 'proj_arc_test',
    title: 'The Infiltration Mission',
    seed_prompt: 'An undercover detective infiltrates a midnight warehouse to retrieve a classified dossier.',
    input_type: 'beginning',
    target_duration_minutes: 20,
    created_at: '2026-09-14T12:00:00Z',
    updated_at: '2026-09-14T12:30:00Z',
    current_tick: 5,
    total_events: 12,
    total_scenes: 3,
    total_panels: 8,
  },
  world: {
    id: 'w_test',
    name: 'Warehouse',
    description: 'A rain-slicked depot',
    current_tick: 5,
    locations: {
      loc_wh: {
        id: 'loc_wh',
        name: 'Main Floor',
        description: 'Large depot',
        connected_locations: [],
      },
    },
    characters: {
      char_evelyn: {
        id: 'char_evelyn',
        name: 'Evelyn Cross',
        role: 'Undercover Detective',
        location_id: 'loc_wh',
        goals: ['Retrieve dossier'],
        beliefs: ['Vincent is dangerous'],
        secrets: ['Knows dossier location'],
        relationships: [],
        emotional_state: {
          happiness: 0.1,
          fear: 0.4,
          anger: 0.2,
          trust: 0.2,
          curiosity: 0.9,
        },
      },
    },
    objects: {},
    events: {},
    goals: {},
    beliefs: {},
    secrets: {},
  },
  story_blueprint: {
    story_title: 'The Infiltration Mission',
    primary_structure: 'THREE_ACT',
    secondary_structure: null,
    presentation_strategy: 'CHRONOLOGICAL',
    target_duration_minutes: 20,
    thematic_premise: 'The cost of loyalty under pressure.',
    dramatic_question: 'Will the truth be secured before the exit is permanently compromised?',
    central_conflict_type: 'Interpersonal espionage',
    stakes: 'Mission compromise and loss of cover',
    soft_constraints: {},
    fit_score: 92.0,
    fit_rationale: 'High alignment with adversarial espionage narrative.',
    selection_mode: 'AUTO',
    expected_beats: [
      {
        beat_id: 'beat_1',
        name: 'Status Quo & Setup',
        act: 'Act I',
        target_position_pct: 0.1,
        expected_dramatic_function: 'Establish primary operative and environment.',
        pressure_signal: 'Low environmental pressure; establish stakes.',
        description: 'Evelyn arrives at the warehouse.',
      },
      {
        beat_id: 'beat_2',
        name: 'Inciting Incident',
        act: 'Act I',
        target_position_pct: 0.2,
        expected_dramatic_function: 'Disrupt status quo with sudden obstacle.',
        pressure_signal: 'Introduce patrolling guard.',
        description: 'Heavy door locks behind Evelyn.',
      },
    ],
  },
  character_arcs: {
    char_evelyn: {
      character_id: 'char_evelyn',
      character_name: 'Evelyn Cross',
      starting_state: {
        role: 'Undercover Detective',
        initial_location_id: 'loc_wh',
        personality_traits: ['calculating', 'vigilant'],
      },
      major_decisions: [
        '[Tick 1] Evelyn slips through the loading bay.',
        '[Tick 3] Evelyn conceals the wire recorder.',
      ],
      key_turns: [
        {
          tick: 3,
          turn_type: 'BELIEF_FORMED',
          summary: 'Evelyn realizes the dossier has been moved.',
          shift_details: {},
        },
      ],
      relationship_deltas: {
        char_vincent: -0.35,
      },
      ending_state: {
        current_location_id: 'loc_wh',
        decisions_count: 2,
        dominant_emotion: 'Guarded vigilance',
      },
      arc_trajectory: 'TRANSFORMATIVE',
      is_observed_only: true,
    },
  },
  causal_summary: {
    overall_causal_score: 84.0,
    but_therefore_ratio: 0.75,
    and_then_count: 2,
    but_therefore_count: 6,
    total_transitions: 8,
    pressure_recommendation: 'Strong consequential escalation across beats.',
    transitions: [
      {
        from_id: 'ev_1',
        to_id: 'ev_2',
        transition_type: 'BUT_THEREFORE',
        score: 0.88,
        rationale: 'Guard approached, therefore Evelyn retreated behind crates.',
      },
      {
        from_id: 'ev_2',
        to_id: 'ev_3',
        transition_type: 'AND_THEN',
        score: 0.5,
        rationale: 'Rain continued outside.',
      },
    ],
  },
};

describe('StructureAndArcsViewer Component', () => {
  it('renders Story Blueprint tab with primary structure, fit score, and beat cards', () => {
    render(<StructureAndArcsViewer project={mockProjectData} />);

    expect(screen.getByText('STRUCTURE, ARCS & CAUSAL CONTINUITY')).toBeDefined();
    expect(screen.getByText('THREE ACT')).toBeDefined();
    expect(screen.getByText('92/100')).toBeDefined();
    expect(screen.getByText(/Will the truth be secured before the exit is permanently compromised/)).toBeDefined();
    expect(screen.getByText('Status Quo & Setup')).toBeDefined();
    expect(screen.getByText('Inciting Incident')).toBeDefined();
    expect(screen.getAllByText(/DIRECTOR PRESSURE SIGNAL/).length).toBeGreaterThanOrEqual(1);
  });

  it('switches to Character Arcs tab and renders autonomous decisions and turns', () => {
    render(<StructureAndArcsViewer project={mockProjectData} />);

    const arcsBtn = screen.getByText(/CHARACTER ARCS/);
    fireEvent.click(arcsBtn);

    expect(screen.getAllByText('Evelyn Cross').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('TRANSFORMATIVE').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/OBSERVATIONAL ONLY/)).toBeDefined();
    expect(screen.getByText(/Evelyn slips through the loading bay/)).toBeDefined();
    expect(screen.getByText(/Evelyn realizes the dossier has been moved/)).toBeDefined();
  });

  it('switches to Causal Continuity tab and renders Therefore/But metrics and transition list', () => {
    render(<StructureAndArcsViewer project={mockProjectData} />);

    const causalBtn = screen.getByText('CAUSAL CONTINUITY');
    fireEvent.click(causalBtn);

    expect(screen.getByText('84/100')).toBeDefined();
    expect(screen.getByText(/Strong Causal Escalation/)).toBeDefined();
    expect(screen.getByText('THEREFORE / BUT')).toBeDefined();
    expect(screen.getByText('AND THEN')).toBeDefined();
    expect(screen.getByText(/Guard approached, therefore Evelyn retreated behind crates/)).toBeDefined();
  });

  it('renders Header with Arcs & Structure navigation and pipeline progress bar', () => {
    const onSelectView = vi.fn();
    render(
      <Header
        currentProject={mockProjectData.metadata}
        projects={[mockProjectData.metadata]}
        providerName="mock"
        activeView="arcs"
        onSelectView={onSelectView}
        onSelectProject={vi.fn()}
        onOpenNewProject={vi.fn()}
        onDeleteProject={vi.fn()}
      />
    );

    expect(screen.getByText('ARCS & STRUCTURE')).toBeDefined();
    expect(screen.getAllByText('WORLD').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/SIMULATION/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/SCREENPLAY/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('SHOT PLAN').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('EXPORT READY')).toBeDefined();
  });

  it('regression: handles string-formatted relationship deltas from real Phase 6 backend without blank screen crash', () => {
    const realBackendProjectData: ProjectData = {
      ...mockProjectData,
      character_arcs: {
        char_alpha: {
          character_id: 'char_alpha',
          character_name: 'Vincent Cross',
          starting_state: { role: 'Infiltrator' },
          major_decisions: ['[Tick 1] Vincent Cross said to Evelyn Vance: "What do you know about dossier?"'],
          key_turns: [],
          relationship_deltas: {
            'Evelyn Vance': 'Affinity: +0.4, Trust: +0.5',
          },
          ending_state: {
            total_decisions_made: 9,
            dominant_emotion: 'Balanced',
          },
          arc_trajectory: 'NO_ARC_DETECTED',
          is_observed_only: true,
        },
      },
    };

    render(<StructureAndArcsViewer project={realBackendProjectData} />);

    const arcsBtn = screen.getByText(/CHARACTER ARCS/);
    fireEvent.click(arcsBtn);

    expect(screen.getAllByText('Vincent Cross').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('RELATIONSHIP AFFINITY DELTAS')).toBeDefined();
    expect(screen.getByText('Evelyn Vance:')).toBeDefined();
    expect(screen.getByText('Affinity: +0.4, Trust: +0.5')).toBeDefined();
  });

  it('supports LOADING and NO_DATA lifecycle states safely without blank screen', () => {
    // 1. NO_DATA state when project is null
    const { unmount } = render(<StructureAndArcsViewer project={null} loading={false} />);
    expect(screen.getByText('NO ACTIVE SIMULATION')).toBeDefined();
    expect(screen.getByText(/The narrative framework requires an active simulation project/)).toBeDefined();
    unmount();

    // 2. LOADING state
    render(<StructureAndArcsViewer project={null} loading={true} />);
    expect(screen.getByText(/Analyzing narrative structure/)).toBeDefined();
  });

  it('renders beat status badges on expected beats when present', () => {
    const projectWithBeatStatuses: ProjectData = {
      ...mockProjectData,
      story_blueprint: {
        ...mockProjectData.story_blueprint!,
        expected_beats: [
          {
            beat_id: 'beat_1',
            name: 'Status Quo & Setup',
            act: 'Act I',
            target_position_pct: 0.1,
            expected_dramatic_function: 'Establish primary operative and environment.',
            pressure_signal: 'Low environmental pressure.',
            description: 'Setup beat.',
            status: 'SATISFIED',
          },
          {
            beat_id: 'beat_2',
            name: 'Inciting Incident',
            act: 'Act I',
            target_position_pct: 0.2,
            expected_dramatic_function: 'Disrupt status quo.',
            pressure_signal: 'Patrolling guard.',
            description: 'Inciting beat.',
            status: 'PENDING',
          },
        ],
      },
    };

    render(<StructureAndArcsViewer project={projectWithBeatStatuses} />);

    expect(screen.getByText('SATISFIED')).toBeDefined();
    expect(screen.getByText('PENDING')).toBeDefined();
  });

  it('renders scene objectives, subtext analyses, and performance cues under causal continuity', () => {
    const projectWithScenesAndCues: ProjectData = {
      ...mockProjectData,
      scenes: [
        {
          scene_id: 'scene_01',
          heading: 'INT. ABANDONED BAY - MIDNIGHT',
          purpose: 'CONFRONTATION',
          objective: {
            pov_character_id: 'char_alpha',
            wants: 'Secure the transit dossier',
            obstacle: 'Guarded perimeter',
            outcome: 'PARTIAL',
          },
          subtext_analyses: [
            {
              spoken_intent: 'CONCEALING',
              spoken_dialogue: 'I have nothing for you.',
              private_truth: 'Dossier is hidden in desk.',
            },
          ],
          performance_cues: [
            {
              cue_type: 'EYE_MOVEMENT',
              observable_action: 'Glances toward the desk before making direct eye contact.',
            },
          ],
        },
      ],
    };

    render(<StructureAndArcsViewer project={projectWithScenesAndCues} />);

    const causalBtn = screen.getByText('CAUSAL CONTINUITY');
    fireEvent.click(causalBtn);

    expect(screen.getByText('SCENES & DRAMATIC GROUNDING (1)')).toBeDefined();
    expect(screen.getByText('INT. ABANDONED BAY - MIDNIGHT')).toBeDefined();
    expect(screen.getByText('CONFRONTATION')).toBeDefined();
    expect(screen.getByText(/Secure the transit dossier/)).toBeDefined();
    expect(screen.getByText('DIALOGUE SUBTEXT (1)')).toBeDefined();
    expect(screen.getByText('[CONCEALING]')).toBeDefined();
    expect(screen.getByText('"I have nothing for you."')).toBeDefined();
    expect(screen.getByText(/Truth: Dossier is hidden in desk/)).toBeDefined();
    expect(screen.getByText('PERFORMANCE CUES (1)')).toBeDefined();
    expect(screen.getByText('EYE_MOVEMENT:')).toBeDefined();
    expect(screen.getByText(/Glances toward the desk/)).toBeDefined();
  });

  it('StructureErrorBoundary safely catches runtime exceptions without blank screen', () => {
    const BadComponent = () => {
      throw new Error('Simulated runtime render crash');
    };

    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <StructureErrorBoundary>
        <BadComponent />
      </StructureErrorBoundary>
    );

    expect(screen.getByText('STRUCTURE & ARCS DIAGNOSTIC ERROR')).toBeDefined();
    expect(screen.getByText('Simulated runtime render crash')).toBeDefined();
    expect(screen.getByText('RETRY DIAGNOSTICS')).toBeDefined();

    spy.mockRestore();
  });
});
