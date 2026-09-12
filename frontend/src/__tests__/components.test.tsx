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
import { ExportViewer } from '../components/ExportViewer';
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

  it('handles input type selection and duration target in NewProjectModal', () => {
    const onCreate = vi.fn();
    render(
      <NewProjectModal
        isOpen={true}
        onClose={vi.fn()}
        onCreate={onCreate}
      />
    );

    expect(screen.getByText('BEGINNING')).toBeDefined();
    expect(screen.getByText('MIDPOINT')).toBeDefined();
    expect(screen.getByText('ENDING')).toBeDefined();
    expect(screen.getByText('FULL CONCEPT')).toBeDefined();

    // Select MIDPOINT
    fireEvent.click(screen.getByText('MIDPOINT'));
    expect(screen.getByText(/You provide the dramatic twist/i)).toBeDefined();

    // Select 45 MIN duration
    fireEvent.click(screen.getByText('45 MIN'));
    expect(screen.getByText('45 MINUTES')).toBeDefined();

    // Submit form
    fireEvent.click(screen.getByText('BUILD WORLD'));
    expect(onCreate).toHaveBeenCalledWith(
      expect.any(String),
      undefined,
      'midpoint',
      45
    );
  });

  it('renders ScreenplayViewer synopsis tab with logline, summary, and act beats', () => {
    const mockProjectWithSynopsis: ProjectData = {
      metadata: {
        id: 'p_syn',
        title: 'Penthouse Conspiracy',
        seed_prompt: 'Test prompt',
        created_at: '',
        updated_at: '',
        current_tick: 1,
        total_events: 1,
        total_scenes: 1,
      },
      world: mockWorld,
      screenplay: {
        title: 'PENTHOUSE CONSPIRACY',
        credit: 'Generated by',
        author: 'D3 Story Lab',
        draft_date: '2026',
        scenes: [],
      },
      fountain_text: 'INT. PENTHOUSE - NIGHT',
      story_outline: {
        input_type: 'beginning',
        raw_input: 'Test prompt',
        episode_title: 'Penthouse Conspiracy',
        genre: 'noir thriller',
        tone: 'dark and suspenseful',
        premise: 'A reporter discovers an offshore ledger.',
        dramatic_question: 'Can Maya expose the network before she is silenced?',
        target_duration_minutes: 20,
        act_structure: {
          act_1: 'Maya infiltrates the suite.',
          act_2: 'Arjun catches her copying the files.',
          act_3: 'She flees into the storm with the encrypted drive.',
        },
        climax: 'A rooftop standoff in the rain.',
        resolution: 'The truth reaches the press.',
        key_scenes: [],
        subplot_hooks: ['Arjun has his own hidden loyalties.'],
      },
      synopsis: {
        title: 'Penthouse Conspiracy',
        logline: 'An investigative journalist uncovers a lethal conspiracy in a luxury penthouse.',
        paragraph_summary: 'Maya Lin enters an executive suite seeking financial records.',
        full_synopsis: 'In Act I, Maya gains entry. In Act II, secrets are exposed. In Act III, a desperate escape ensues.',
        dramatic_question: 'Can Maya expose the network before she is silenced?',
        genre: 'noir thriller',
        tone: 'dark and suspenseful',
        target_duration_minutes: 20,
        acts: {
          act_1: 'Maya infiltrates the suite.',
          act_2: 'Arjun catches her copying the files.',
          act_3: 'She flees into the storm with the encrypted drive.',
        },
      },
    };

    render(
      <ScreenplayViewer
        project={mockProjectWithSynopsis}
        onGenerate={vi.fn()}
        loading={false}
      />
    );

    // Switch to SYNOPSIS & BEATS tab
    const synopsisTab = screen.getByText('SYNOPSIS & BEATS');
    fireEvent.click(synopsisTab);

    expect(screen.getByText('ONE-LINE LOGLINE')).toBeDefined();
    expect(screen.getByText(/An investigative journalist uncovers a lethal conspiracy/i)).toBeDefined();
    expect(screen.getByText('ACT I: SETUP')).toBeDefined();
    expect(screen.getByText('Maya infiltrates the suite.')).toBeDefined();
    expect(screen.getByText('ACT II: CONFRONTATION')).toBeDefined();
    expect(screen.getByText('ACT III: CLIMAX & RESOLUTION')).toBeDefined();
    expect(screen.getByText('DRAMATIC QUESTION')).toBeDefined();
    expect(screen.getByText('Can Maya expose the network before she is silenced?')).toBeDefined();
  });

  it('renders ExportViewer with all download options and production bundle links', () => {
    const mockProjectForExport: ProjectData = {
      metadata: {
        id: 'p_export',
        title: 'Export Test Suite',
        seed_prompt: 'Test prompt',
        created_at: '',
        updated_at: '',
        current_tick: 1,
        total_events: 1,
        total_scenes: 1,
      },
      world: mockWorld,
      fountain_text: 'INT. PENTHOUSE - NIGHT',
      synopsis: {
        title: 'Export Test',
        logline: 'A quick test logline.',
        paragraph_summary: 'A short test summary.',
        full_synopsis: 'Complete narrative test synopsis.',
        dramatic_question: 'Will truth prevail?',
        genre: 'noir',
        tone: 'tense',
        target_duration_minutes: 20,
        acts: { act_1: 'A1', act_2: 'A2', act_3: 'A3' },
      },
      shot_plan: {
        project_title: 'Export Test',
        total_panels: 2,
        aspect_ratio: '16:9',
        total_pages: 1,
        panels: [
          {
            id: 'p1',
            scene_number: 1,
            panel_number: 1,
            shot_type: 'wide_shot',
            camera_angle: 'eye_level',
            location_id: 'loc_suite',
            characters_present: ['char_maya'],
            action_description: 'Establishing shot',
            visual_prompt: 'Establishing shot of suite',
            aspect_ratio: '16:9',
            source_event_ids: ['evt_1'],
          },
        ],
      },
    };

    render(<ExportViewer project={mockProjectForExport} />);

    expect(screen.getByText('EXPORT PRODUCTION BUNDLE')).toBeDefined();
    expect(screen.getByText('Fountain Screenplay')).toBeDefined();
    expect(screen.getByText('Story Synopsis & Arc')).toBeDefined();
    expect(screen.getByText('Cinematic Shot Plan')).toBeDefined();
    expect(screen.getByText('Storyboard & World Bundle')).toBeDefined();

    expect(screen.getByText('DOWNLOAD .FOUNTAIN')).toBeDefined();
    expect(screen.getByText('DOWNLOAD SYNOPSIS (.MD)')).toBeDefined();
    expect(screen.getByText('DOWNLOAD CSV')).toBeDefined();
    expect(screen.getByText('DOWNLOAD JSON')).toBeDefined();
    expect(screen.getByText('DOWNLOAD COMPLETE BUNDLE (.JSON)')).toBeDefined();
  });

  it('handles multi-page storyboard pagination and controls', () => {
    const mockMultiPageProject: ProjectData = {
      metadata: {
        id: 'p_multipage',
        title: 'Multi-Page Test',
        seed_prompt: 'Test prompt',
        created_at: '',
        updated_at: '',
        current_tick: 1,
        total_events: 2,
        total_scenes: 1,
      },
      world: mockWorld,
      storyboard: {
        shot_plan: {
          project_title: 'Multi-Page Test',
          total_panels: 6,
          total_pages: 2,
          aspect_ratio: '16:9',
          panels: [
            {
              id: 'pnl_p1',
              scene_number: 1,
              panel_number: 1,
              page_number: 1,
              shot_type: 'wide_shot',
              camera_angle: 'high_angle',
              location_id: 'loc_suite',
              characters_present: ['char_maya'],
              action_description: 'Page 1 wide establishing view',
              visual_prompt: 'Page 1 wide establishing shot',
              aspect_ratio: '16:9',
              source_event_ids: ['evt_1'],
            },
            {
              id: 'pnl_p2',
              scene_number: 1,
              panel_number: 2,
              page_number: 2,
              shot_type: 'close_up',
              camera_angle: 'low_angle',
              location_id: 'loc_suite',
              characters_present: ['char_maya'],
              action_description: 'Page 2 dramatic close up confrontation',
              visual_prompt: 'Page 2 dramatic close up confrontation',
              aspect_ratio: '16:9',
              source_event_ids: ['evt_2'],
            },
          ],
        },
        rendered_panels: [
          '<svg><text>PAGE 1 FRAME</text></svg>',
          '<svg><text>PAGE 2 FRAME</text></svg>',
        ],
      },
    };

    render(<StoryboardViewer project={mockMultiPageProject} />);

    expect(screen.getByText('PAGE 1 OF 2')).toBeDefined();
    expect(screen.getByText('PG 1')).toBeDefined();
    expect(screen.getByText('PG 2')).toBeDefined();
    expect(screen.getAllByText('Page 1 wide establishing view').length).toBeGreaterThan(0);
    expect(screen.getByText('↻ REGENERATE PAGE 1')).toBeDefined();

    // Switch to page 2
    fireEvent.click(screen.getByText('PG 2'));
    expect(screen.getByText('PAGE 2 OF 2')).toBeDefined();
    expect(screen.getAllByText('Page 2 dramatic close up confrontation').length).toBeGreaterThan(0);
    expect(screen.getByText('↻ REGENERATE PAGE 2')).toBeDefined();
  });

  it('handles switching to Comic Book Pages view and displays comic template sheet', () => {
    const mockProjectWithComic: ProjectData = {
      metadata: {
        id: 'p_comic',
        title: 'Neon Shadows',
        seed_prompt: 'A detective enters a rain-soaked alley.',
        created_at: '',
        updated_at: '',
        current_tick: 1,
        total_events: 1,
        total_scenes: 1,
      },
      world: mockWorld,
      screenplay: {
        title: 'NEON SHADOWS',
        credit: 'Generated by',
        author: 'D3 Story Lab',
        draft_date: '2026',
        scenes: [],
      },
      storyboard: {
        shot_plan: {
          project_title: 'Neon Shadows',
          total_panels: 1,
          total_pages: 1,
          panels_per_page: 4,
          aspect_ratio: '16:9',
          pages: [
            {
              page_number: 1,
              total_pages: 1,
              title: 'Page 1',
              layout_template: 'template_a',
              panels: [],
            },
          ],
          panels: [
            {
              id: 'pnl_comic_1',
              panel_id: 'pnl_comic_1',
              scene_number: 1,
              panel_number: 1,
              shot_number: 1,
              page_number: 1,
              shot_type: 'wide',
              camera_angle: 'low_angle',
              narrative_purpose: 'establish',
              layout_slot: 'top_hero',
              location_id: 'loc_penthouse',
              location_name: 'Dark Alleyway',
              characters_present: ['char_1'],
              character_names: ['Maya Lin'],
              action_description: 'Rain pours over neon reflections.',
              visual_prompt: 'Wide shot of dark alleyway with rain reflections.',
              caption: 'Rain pours over neon reflections.',
              sfx_label: 'THUD!',
              aspect_ratio: '16:9',
              source_event_ids: ['evt_1'],
            },
          ],
        },
        rendered_panels: ['<svg><text>COMIC ART</text></svg>'],
      },
    };

    render(<StoryboardViewer project={mockProjectWithComic} />);

    // Switch to Comic Book Pages
    const comicTabBtn = screen.getByText('📖 COMIC BOOK PAGES');
    fireEvent.click(comicTabBtn);

    expect(screen.getByText(/LAYOUT:/)).toBeDefined();
    expect(screen.getByText('THUD!')).toBeDefined();
    expect(screen.getAllByText('Rain pours over neon reflections.').length).toBeGreaterThan(0);
  });

  it('opens Panel Inspector modal when clicking a panel and shows version history', () => {
    const mockProjectWithVersions: ProjectData = {
      metadata: {
        id: 'p_versions',
        title: 'Inspector Test',
        seed_prompt: 'Testing inspector',
        created_at: '',
        updated_at: '',
        current_tick: 1,
        total_events: 1,
        total_scenes: 1,
      },
      world: mockWorld,
      screenplay: {
        title: 'INSPECTOR TEST',
        credit: 'Generated by',
        author: 'D3 Story Lab',
        draft_date: '2026',
        scenes: [],
      },
      storyboard: {
        shot_plan: {
          project_title: 'Inspector Test',
          total_panels: 1,
          total_pages: 1,
          panels_per_page: 4,
          aspect_ratio: '16:9',
          panels: [
            {
              id: 'pnl_inspect_1',
              panel_id: 'pnl_inspect_1',
              scene_number: 1,
              panel_number: 1,
              shot_number: 1,
              page_number: 1,
              shot_type: 'close_up',
              camera_angle: 'eye_level',
              narrative_purpose: 'action',
              location_id: 'loc_penthouse',
              location_name: 'Study',
              characters_present: ['char_1'],
              character_names: ['Maya Lin'],
              action_description: 'Elena examines the safe.',
              visual_prompt: 'Close up of Elena examining the safe.',
              compiled_prompt: 'High-contrast noir illustration of Elena examining the heavy safe.',
              aspect_ratio: '16:9',
              source_event_ids: ['evt_1'],
              versions: [
                {
                  version: 1,
                  image_url: '/api/test/v1.svg',
                  mode: 'fallback_comic',
                  is_selected: false,
                },
                {
                  version: 2,
                  image_url: '/api/test/v2.png',
                  mode: 'ai_image',
                  is_selected: true,
                },
              ],
            },
          ],
        },
        rendered_panels: ['<svg><text>INSPECTOR ART</text></svg>'],
      },
    };

    render(<StoryboardViewer project={mockProjectWithVersions} />);

    // Click the panel to open modal
    const panelCard = screen.getByText('Elena examines the safe.');
    fireEvent.click(panelCard);

    expect(screen.getByText('PANEL INSPECTOR & VERSION CONTROLLER')).toBeDefined();
    expect(screen.getByText('VERSION 1')).toBeDefined();
    expect(screen.getByText('VERSION 2')).toBeDefined();
    expect(screen.getByText('High-contrast noir illustration of Elena examining the heavy safe.')).toBeDefined();
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

