import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from '../components/Header';
import { CharacterCards } from '../components/CharacterCards';
import { WorldInspector } from '../components/WorldInspector';
import { SimulationTicker } from '../components/SimulationTicker';
import { ScreenplayViewer } from '../components/ScreenplayViewer';
import { ScrollytellingHome } from '../components/ScrollytellingHome';
import { NewProjectModal } from '../components/NewProjectModal';
import { StoryboardViewer } from '../components/StoryboardViewer';
import { WorldState, ProjectData } from '../types';
import { formatDisplayValue, safeExtractSvg } from '../utils/format';

const mockWorld: WorldState = {
  id: 'world_test',
  name: 'Test Hotel',
  description: 'A test simulation world',
  current_tick: 3,
  locations: {
    loc_suite: {
      id: 'loc_suite',
      name: 'Penthouse Suite',
      description: 'Top floor luxury suite',
      connected_locations: ['loc_hall'],
    },
    loc_hall: {
      id: 'loc_hall',
      name: 'Hallway',
      description: 'Carpeted hallway',
      connected_locations: ['loc_suite'],
    },
  },
  characters: {
    char_maya: {
      id: 'char_maya',
      name: 'Maya Lin',
      role: 'Investigative Journalist',
      location_id: 'loc_suite',
      goals: ['goal_1'],
      beliefs: ['bel_1'],
      secrets: ['sec_1'],
      relationships: [],
      emotional_state: {
        happiness: 0.1,
        fear: 0.5,
        anger: 0.2,
        trust: 0.4,
        curiosity: 0.9,
      },
    },
  },
  objects: {
    obj_recorder: {
      id: 'obj_recorder',
      name: 'Audio Recorder',
      description: 'Small digital voice recorder',
      location_id: 'loc_suite',
      holder_id: 'char_maya',
      portable: true,
      properties: {},
    },
  },
  goals: {
    goal_1: {
      id: 'goal_1',
      character_id: 'char_maya',
      description: 'Obtain proof of bribery',
      priority: 0.9,
      status: 'active',
    },
  },
  beliefs: {
    bel_1: {
      id: 'bel_1',
      character_id: 'char_maya',
      statement: 'The diplomat is hiding financial records',
      confidence: 0.85,
    },
  },
  secrets: {
    sec_1: {
      id: 'sec_1',
      character_id: 'char_maya',
      statement: 'Working under a fake press credential',
      known_by: [],
      importance: 1.0,
    },
  },
  events: {},
};

describe('Frontend Workstation Components', () => {
  it('renders Header with brand and provider status', () => {
    render(
      <Header
        currentProject={null}
        projects={[]}
        providerName="mock"
        onSelectProject={vi.fn()}
        onOpenNewProject={vi.fn()}
        onDeleteProject={vi.fn()}
      />
    );
    expect(screen.getByText('D3 STORY LAB')).toBeDefined();
    expect(screen.getByText('Engine: mock')).toBeDefined();
  });

  it('renders CharacterCards with emotions and toggles private state isolation', () => {
    render(<CharacterCards world={mockWorld} />);
    expect(screen.getByText('Maya Lin')).toBeDefined();
    expect(screen.getByText('Investigative Journalist')).toBeDefined();
    expect(screen.getByText('Obtain proof of bribery')).toBeDefined();

    // Toggle private boundaries
    const toggleBtn = screen.getByText(/Inspect Private Boundaries/i);
    fireEvent.click(toggleBtn);

    // Private secrets and beliefs are revealed in debug mode
    expect(screen.getByText(/Working under a fake press credential/i)).toBeDefined();
    expect(screen.getByText(/The diplomat is hiding financial records/i)).toBeDefined();
  });

  it('renders WorldInspector and switches between rooms and props', () => {
    render(<WorldInspector world={mockWorld} />);
    expect(screen.getByText('Penthouse Suite')).toBeDefined();

    const propsBtn = screen.getByText(/Props/i);
    fireEvent.click(propsBtn);
    expect(screen.getByText('Audio Recorder')).toBeDefined();
  });

  it('renders SimulationTicker with tick stats and controls', () => {
    const onStep = vi.fn();
    const onRun = vi.fn();
    render(
      <SimulationTicker
        world={mockWorld}
        events={[
          {
            id: 'evt_1',
            tick: 1,
            event_type: 'character_spoke',
            actor_ids: ['char_maya'],
            location_id: 'loc_suite',
            description: 'Maya says: Where is the ledger?',
            metadata: {},
          },
        ]}
        onStep={onStep}
        onRun={onRun}
        loading={false}
      />
    );
    expect(screen.getByText('T1')).toBeDefined();
    expect(screen.getByText('Maya says: Where is the ledger?')).toBeDefined();

    fireEvent.click(screen.getByText('Step 1 Tick'));
    expect(onStep).toHaveBeenCalledWith(1);
  });

  it('renders ScreenplayViewer with Fountain formatted scene', () => {
    const mockProject: ProjectData = {
      metadata: {
        id: 'p1',
        title: 'Penthouse Confrontation',
        seed_prompt: 'Test prompt',
        created_at: '',
        updated_at: '',
        current_tick: 1,
        total_events: 1,
        total_scenes: 1,
      },
      world: mockWorld,
      screenplay: {
        title: 'PENTHOUSE CONFRONTATION',
        credit: 'Generated by',
        author: 'D3 Story Lab',
        draft_date: '2026',
        scenes: [
          {
            scene_number: 1,
            location_id: 'loc_suite',
            heading: 'INT. PENTHOUSE SUITE - NIGHT',
            source_event_ids: ['evt_1'],
            blocks: [
              {
                id: 'b1',
                block_type: 'character',
                text: 'MAYA LIN',
                source_event_ids: ['evt_1'],
              },
              {
                id: 'b2',
                block_type: 'dialogue',
                text: 'Tell me the truth.',
                source_event_ids: ['evt_1'],
              },
            ],
          },
        ],
      },
      fountain_text: 'INT. PENTHOUSE SUITE - NIGHT\n\nMAYA LIN\nTell me the truth.',
    };

    render(
      <ScreenplayViewer
        project={mockProject}
        onGenerate={vi.fn()}
        loading={false}
      />
    );

    expect(screen.getByText('INT. PENTHOUSE SUITE - NIGHT')).toBeDefined();
    expect(screen.getByText('MAYA LIN')).toBeDefined();
    expect(screen.getByText('"Tell me the truth."')).toBeDefined();
  });

  it('renders ScrollytellingHome narrative sequence and sections', () => {
    render(
      <ScrollytellingHome
        onStartNew={vi.fn()}
        onOpenProject={vi.fn()}
        projects={[]}
      />
    );

    expect(screen.getByText('AGENTIC PROCEDURAL NARRATIVE ENGINE')).toBeDefined();
    expect(screen.getByText('THE STORY IS NOT WRITTEN.')).toBeDefined();
    expect(screen.getByText('IT EMERGES.')).toBeDefined();
    expect(screen.getByText(/DROP IN/i)).toBeDefined();
    expect(screen.getByText(/AN IDEA/i)).toBeDefined();
    expect(screen.getByText(/LET THEM/i)).toBeDefined();
    expect(screen.getByText(/LOOSE/i)).toBeDefined();
    expect(screen.getByText(/NOT PUPPETRY/i)).toBeDefined();
    expect(screen.getByText(/WATCH/i)).toBeDefined();
    expect(screen.getByText(/FROM EVENT/i)).toBeDefined();
  });

  it('renders NewProjectModal with spark prompt and BUILD WORLD button', () => {
    const onCreate = vi.fn();
    render(
      <NewProjectModal
        isOpen={true}
        onClose={vi.fn()}
        onCreate={onCreate}
      />
    );

    expect(screen.getByText('START WITH A SPARK.')).toBeDefined();
    expect(screen.getByText('BUILD WORLD')).toBeDefined();
    expect(screen.getByText(/"A journalist disappears after receiving a sealed file."/i)).toBeDefined();
  });

  it('distinguishes Director environmental interventions and inspects causality', () => {
    render(
      <SimulationTicker
        world={mockWorld}
        events={[
          {
            id: 'evt_dir_1',
            tick: 2,
            event_type: 'environment_incident',
            actor_ids: [],
            location_id: 'loc_suite',
            description: 'The power fails abruptly across the floor.',
            metadata: { incident_type: 'LIGHTS FAIL' },
          },
        ]}
        onStep={vi.fn()}
        onRun={vi.fn()}
        loading={false}
      />
    );

    expect(screen.getByText('DIRECTOR: LIGHTS FAIL')).toBeDefined();
    expect(screen.getByText('The power fails abruptly across the floor.')).toBeDefined();
    expect(screen.getByText('WHY DID THIS HAPPEN?')).toBeDefined();
    expect(screen.getByText('DIRECTOR AGENT')).toBeDefined();
    expect(screen.getByText(/Environmental Pacing Engine/i)).toBeDefined();
  });

  it('renders StoryboardViewer with shot framing panels', () => {
    const mockProjectWithStoryboard: ProjectData = {
      metadata: {
        id: 'p1',
        title: 'Penthouse Confrontation',
        seed_prompt: 'Test prompt',
        created_at: '',
        updated_at: '',
        current_tick: 1,
        total_events: 1,
        total_scenes: 1,
      },
      world: mockWorld,
      screenplay: {
        title: 'PENTHOUSE CONFRONTATION',
        credit: 'Generated by',
        author: 'D3 Story Lab',
        draft_date: '2026',
        scenes: [],
      },
      storyboard: {
        shot_plan: {
          project_title: 'Penthouse Confrontation',
          total_panels: 1,
          aspect_ratio: '16:9',
          panels: [
            {
              id: 'pnl_1',
              scene_number: 1,
              panel_number: 1,
              shot_type: 'close_up',
              camera_angle: 'low_angle',
              location_id: 'loc_suite',
              characters_present: ['char_maya'],
              action_description: 'Maya reaches for the hidden tape.',
              dialogue_excerpt: 'Tell me where it is.',
              visual_prompt: 'Cinematic low angle close up of Maya reaching under mahogany desk',
              aspect_ratio: '16:9',
              source_event_ids: ['evt_1'],
            },
          ],
        },
        rendered_panels: ['<svg><text>FRAME 01</text></svg>'],
      },
    };

    render(
      <StoryboardViewer
        project={mockProjectWithStoryboard}
      />
    );

    expect(screen.getByText('STORYBOARD')).toBeDefined();
    expect(screen.getByText('CLOSE UP')).toBeDefined();
    expect(screen.getByText('LOW ANGLE')).toBeDefined();
    expect(screen.getByText('Maya reaches for the hidden tape.')).toBeDefined();
    expect(screen.getByText('"Tell me where it is."')).toBeDefined();
  });

  it('renders StoryboardViewer with rendered_panels as objects without any [object Object]', () => {
    const mockProjectWithObjectPanels: ProjectData = {
      metadata: {
        id: 'p1',
        title: 'Penthouse Confrontation',
        seed_prompt: 'Test prompt',
        created_at: '',
        updated_at: '',
        current_tick: 1,
        total_events: 1,
        total_scenes: 1,
      },
      world: mockWorld,
      screenplay: {
        title: 'PENTHOUSE CONFRONTATION',
        credit: 'Generated by',
        author: 'D3 Story Lab',
        draft_date: '2026',
        scenes: [],
      },
      storyboard: {
        shot_plan: {
          project_title: 'Penthouse Confrontation',
          total_panels: 1,
          aspect_ratio: '16:9',
          panels: [
            {
              id: 'pnl_1',
              scene_number: 1,
              panel_number: 1,
              shot_number: 1,
              shot_type: 'close_up',
              camera_angle: 'low_angle',
              location_id: 'loc_suite',
              location_name: 'Penthouse Suite',
              characters_present: ['char_maya'],
              character_names: ['Maya Lin'],
              action: 'Maya reaches for the hidden tape.',
              action_description: 'Maya reaches for the hidden tape.',
              visual_description: 'Low-key lighting, dramatic shadows',
              lighting: 'Low-key lighting',
              mood: 'Tense',
              prompt: 'Close up shot, low angle. Maya Lin in Penthouse Suite.',
              visual_prompt: 'Cinematic low angle close up of Maya reaching under mahogany desk',
              aspect_ratio: '16:9',
              source_event_ids: ['evt_1'],
              source_screenplay_block_ids: ['b1', 'b2'],
            },
          ],
        },
        rendered_panels: [
          {
            panel_id: 'pnl_1',
            panel_number: 1,
            render_type: 'svg_placeholder',
            svg_data: '<svg id="test-svg-rendered"><text>FRAME 01 RENDERED</text></svg>',
            prompt_used: 'Close up shot, low angle.',
            is_mock: true,
          } as any,
        ],
      },
    };

    const { container } = render(
      <StoryboardViewer project={mockProjectWithObjectPanels} />
    );

    // Verify DOM contains zero instances of [object Object]
    expect(container.innerHTML).not.toContain('[object Object]');
    expect(screen.getByText(/SHOT 01/)).toBeDefined();
    expect(screen.getAllByText(/Penthouse Suite/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Maya Lin/).length).toBeGreaterThan(0);
    expect(screen.getByText('Maya reaches for the hidden tape.')).toBeDefined();
    expect(screen.getByText('PROMPT & DETAILS')).toBeDefined();
  });

  it('renders Causality Inspector with zero instances of [object Object] for complex event data', () => {
    const { container } = render(
      <SimulationTicker
        world={mockWorld}
        events={[
          {
            id: 'evt_complex',
            tick: 4,
            event_type: 'character_spoke',
            actor_ids: ['char_maya'],
            location_id: 'loc_suite',
            description: 'Maya speaks with urgency.',
            metadata: {
              speech_act: 'accuse',
              custom_data: { nested: 'value' },
            },
          },
        ]}
        onStep={vi.fn()}
        onRun={vi.fn()}
        loading={false}
      />
    );

    // Verify DOM contains zero instances of [object Object]
    expect(container.innerHTML).not.toContain('[object Object]');
    expect(screen.getAllByText('Maya Lin').length).toBeGreaterThan(0);
    expect(screen.getByText(/Trust -15%, Tension escalated/i)).toBeDefined();
  });
});

describe('formatDisplayValue and safeExtractSvg utilities', () => {
  it('safely formats primitives, null, and undefined without [object Object]', () => {
    expect(formatDisplayValue('Test string')).toBe('Test string');
    expect(formatDisplayValue(42)).toBe('42');
    expect(formatDisplayValue(true)).toBe('Yes');
    expect(formatDisplayValue(false)).toBe('No');
    expect(formatDisplayValue(null)).toBe('—');
    expect(formatDisplayValue(undefined)).toBe('—');
    expect(formatDisplayValue('')).toBe('—');
  });

  it('safely formats arrays and joins them cleanly', () => {
    expect(formatDisplayValue(['Suite', 'Corridor', 'Lobby'])).toBe('Suite, Corridor, Lobby');
    expect(formatDisplayValue([])).toBe('—');
  });

  it('extracts human-readable narrative fields from objects and NEVER outputs [object Object]', () => {
    expect(formatDisplayValue({ name: 'Maya Lin', id: 'char_1' })).toBe('Maya Lin');
    expect(formatDisplayValue({ statement: 'Morgan knows the code' })).toBe('Morgan knows the code');
    expect(formatDisplayValue({ description: 'A mahogany desk with scratches' })).toBe('A mahogany desk with scratches');
    expect(formatDisplayValue({ title: 'Operation Midnight' })).toBe('Operation Midnight');
    expect(formatDisplayValue({ summary: 'Tense negotiation' })).toBe('Tense negotiation');
    expect(formatDisplayValue({ text: 'Some spoken dialogue text' })).toBe('Some spoken dialogue text');

    // Arbitrary object without standard keys
    const arbitraryObj = { code: 'XYZ', level: 3 };
    const formatted = formatDisplayValue(arbitraryObj);
    expect(formatted).not.toContain('[object Object]');
    expect(formatted).toContain('code: XYZ');

    // Empty object
    expect(formatDisplayValue({})).toBe('—');
  });

  it('extracts SVG content from strings and API panel objects safely', () => {
    expect(safeExtractSvg('<svg>direct</svg>')).toBe('<svg>direct</svg>');
    expect(safeExtractSvg({ svg_data: '<svg>from_data</svg>' })).toBe('<svg>from_data</svg>');
    expect(safeExtractSvg(null)).toBe('');
    expect(safeExtractSvg(undefined)).toBe('');
    expect(safeExtractSvg({})).toBe('');
  });
});

