import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import {
  StoryboardPromptBuilder,
  MANDATORY_STYLE_TAGS,
  DEFAULT_NEGATIVE_PROMPT,
} from '../utils/StoryboardPromptBuilder';
import {
  requestExternalPanelRender,
  requestExternalPageRender,
  PRICING_DISCLAIMER,
} from '../services/HuggingFaceService';
import { ShotCard } from '../components/ShotCard';
import { StoryboardPanel, VisualBible } from '../types';

// Mock fetch globally for API calls
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

describe('StoryboardPromptBuilder', () => {
  const samplePanel: StoryboardPanel = {
    id: 'pnl-101',
    scene_number: 1,
    panel_number: 2,
    shot_type: 'close_up',
    camera_angle: 'low_angle',
    action_description: 'Detective Miller examines a shattered glass on the wet asphalt.',
    mood: 'tense and brooding',
    subject_focus: 'Miller’s intense furrowed brow and trembling gloved hand',
    dialogue_excerpt: 'Someone was here just minutes ago.',
    location_id: 'loc_alley',
    characters_present: ['char_miller'],
    objects_in_frame: ['prop_glass'],
    lighting: 'dramatic harsh sodium streetlight through dense fog',
    visual_prompt: 'Low angle shot of detective',
    aspect_ratio: '16:9',
    source_event_ids: ['evt_1'],
  };

  const sampleBible: VisualBible = {
    style_profile: {
      id: 'noir',
      name: 'Cinematic Graphite Noir',
      medium: 'graphite pencil sketch',
      linework: 'cross-hatching',
      lighting_style: 'chiaroscuro',
      color_palette: 'grayscale',
      composition_rules: 'rule of thirds',
      artist_influences: ['Alex Toth', 'Alberto Breccia'],
      negative_constraints: 'no color',
    },
    characters: {
      char_miller: {
        character_id: 'char_miller',
        name: 'Detective Miller',
        build: 'heavy-set with weathered shoulders',
        face_features: 'sharp jawline, tired sunken eyes',
        hair: 'short receded graying hair',
        clothing: 'damp charcoal trench coat, loosened tie',
        signature_props: ['brass trench lighter'],
      },
    },
    locations: {
      loc_alley: {
        location_id: 'loc_alley',
        name: 'Industrial Back Alley',
        environment_type: 'urban exterior, rain-slicked pavement',
        architecture: 'brick tenements with rusted fire escapes',
        key_landmarks: ['overhead steam pipe', 'flickering lamp post'],
      },
    },
    objects: {
      prop_glass: {
        object_id: 'prop_glass',
        name: 'Shattered Tumbler Glass',
        form_factor: 'heavy crystal scotch tumbler',
        materials: 'faceted lead glass',
      },
    },
  };

  it('compiles shot details and VisualBible into a dense cinematic prompt', () => {
    const prompt = StoryboardPromptBuilder.buildPrompt(samplePanel, sampleBible);

    // Verify mandatory style tags are present
    expect(prompt).toContain(MANDATORY_STYLE_TAGS);

    // Verify framing & angle
    expect(prompt).toContain('close-up shot');
    expect(prompt).toContain('low-angle shot');

    // Verify action & subject focus
    expect(prompt).toContain('Detective Miller examines a shattered glass');
    expect(prompt).toContain('Miller’s intense furrowed brow');

    // Verify emotional acting & dialogue
    expect(prompt).toContain('tense and brooding');
    expect(prompt).toContain('Someone was here just minutes ago.');

    // Verify character visual traits from VisualBible
    expect(prompt).toContain('Detective Miller');
    expect(prompt).toContain('weathered shoulders');
    expect(prompt).toContain('sharp jawline');
    expect(prompt).toContain('damp charcoal trench coat');

    // Verify location details from VisualBible
    expect(prompt).toContain('Industrial Back Alley');
    expect(prompt).toContain('urban exterior');
    expect(prompt).toContain('brick tenements');

    // Verify props from VisualBible
    expect(prompt).toContain('Shattered Tumbler Glass');
    expect(prompt).toContain('heavy crystal scotch tumbler');

    // Verify lighting
    expect(prompt).toContain('dramatic harsh sodium streetlight');
  });

  it('builds negative prompt excluding digital artifacts and color', () => {
    const neg = StoryboardPromptBuilder.buildNegativePrompt();
    expect(neg).toContain('color');
    expect(neg).toContain('3d render');
    expect(neg).toContain('deformed hands');
    expect(neg).toContain(DEFAULT_NEGATIVE_PROMPT);
  });

  it('compile returns both prompt and negativePrompt together', () => {
    const result = StoryboardPromptBuilder.compile(samplePanel, sampleBible);
    expect(result.prompt).toBeDefined();
    expect(result.negativePrompt).toBeDefined();
    expect(result.prompt).toContain(MANDATORY_STYLE_TAGS);
  });
});

describe('Security & External Render Architecture', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('verifies frontend environment exposes zero Hugging Face tokens', () => {
    const meta = import.meta as any;
    expect(meta.env?.VITE_HF_TOKEN).toBeUndefined();
  });

  it('provides exact required pricing disclaimer', () => {
    expect(PRICING_DISCLAIMER).toBe(
      'Optional external provider. Availability, quotas and pricing depend on the provider/account.'
    );
  });

  it('delegates panel external render to backend endpoint without frontend credentials', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        panel_id: 'pnl_42',
        version: 2,
        panel: { id: 'pnl_42', mode: 'ai_image' },
        rendered_panel: { image_url: '/api/projects/proj_1/storyboard/assets/panels/pnl_42_v2.jpg' },
      }),
    });

    const result = await requestExternalPanelRender('proj_1', 'pnl_42');
    expect(result.version).toBe(2);
    expect(result.renderedPanel.image_url).toContain('/api/projects/proj_1/storyboard/assets/panels/');

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/projects/proj_1/storyboard/panels/pnl_42/external-render'),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'huggingface', model: 'stabilityai/stable-diffusion-xl-base-1.0' }),
      })
    );
  });

  it('delegates page external render to backend page endpoint', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        project_id: 'proj_1',
        page_number: 1,
        panels_rendered: 4,
        shot_plan: {},
        rendered_panels: [],
      }),
    });

    const result = await requestExternalPageRender('proj_1', 1);
    expect(result.panelsRendered).toBe(4);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/projects/proj_1/storyboard/pages/1/external-render'),
      expect.objectContaining({
        method: 'POST',
      })
    );
  });
});

describe('ShotCard Component', () => {
  const testPanel: StoryboardPanel = {
    id: 'shot-card-1',
    scene_number: 1,
    panel_number: 3,
    shot_number: 3,
    shot_type: 'extreme_close_up',
    camera_angle: 'high_angle',
    action_description: 'A trembling hand reaches for the rusted revolver.',
    dialogue_excerpt: 'Don’t move.',
    location_id: 'loc_warehouse',
    location_name: 'Abandoned Warehouse',
    characters_present: ['char_marcus'],
    character_names: ['Marcus'],
    visual_prompt: 'Cinematic high angle extreme close up of trembling hand reaching for gun',
    aspect_ratio: '16:9',
    source_event_ids: ['evt_2'],
    rendered_svg: '<svg data-testid="offline-svg"><rect width="100" height="100"/></svg>',
  };

  it('renders clean artwork-first shot card with metadata header, action, and PREVIS GUIDE badge', () => {
    render(<ShotCard panel={testPanel} projectId="proj_test" />);

    expect(screen.getByText(/SHOT 03/)).toBeDefined();
    expect(screen.getByText(/EXTREME CLOSE UP/)).toBeDefined();
    expect(screen.getByText(/\/ HIGH ANGLE/)).toBeDefined();
    expect(screen.getByText(/A trembling hand reaches for the rusted revolver./)).toBeDefined();
    expect(screen.getByText(/Don’t move./)).toBeDefined();
    expect(screen.getByText(/Abandoned Warehouse/)).toBeDefined();
    expect(screen.getByText(/Marcus/)).toBeDefined();
    expect(screen.getByText('PREVIS GUIDE')).toBeDefined();
  });

  it('shows unrendered state and reveals previs guide on toggle', () => {
    const { container } = render(<ShotCard panel={testPanel} projectId="proj_test" />);
    expect(screen.getByText('Storyboard render unavailable')).toBeDefined();
    const previsBtn = screen.getByText('Previs guide available');
    fireEvent.click(previsBtn);
    const svgEl = container.querySelector('svg[data-testid="offline-svg"]');
    expect(svgEl).not.toBeNull();
  });

  it('renders seamless image container and OPEN-MODEL STORYBOARD badge when external image is present', () => {
    const panelWithAiImage: StoryboardPanel = {
      ...testPanel,
      image_url: '/api/projects/proj_test/storyboard/assets/panels/shot-card-1_v2.jpg',
      mode: 'ai_image',
      rendered_svg: undefined,
    };

    render(<ShotCard panel={panelWithAiImage} projectId="proj_test" />);
    expect(screen.getByText('OPEN-MODEL STORYBOARD')).toBeDefined();
    const img = screen.getByRole('img');
    expect(img).toBeDefined();
    expect(img.getAttribute('src')).toBe('/api/projects/proj_test/storyboard/assets/panels/shot-card-1_v2.jpg');
    expect(img.className).toContain('shot-image-seamless');
  });

  it('triggers onSelect when clicked', () => {
    const onSelect = vi.fn();
    render(<ShotCard panel={testPanel} projectId="proj_test" onSelect={onSelect} />);

    const card = screen.getByTestId('shot-card-shot-card-1');
    fireEvent.click(card);
    expect(onSelect).toHaveBeenCalledWith(testPanel);
  });

  it('triggers external render on explicit button click and shows skeleton loader', async () => {
    mockFetch.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                json: async () => ({
                  panel_id: 'shot-card-1',
                  version: 2,
                  panel: { ...testPanel, mode: 'ai_image' },
                  rendered_panel: {},
                }),
              }),
            50
          )
        )
    );

    render(<ShotCard panel={testPanel} projectId="proj_test" />);

    const renderBtn = screen.getByTitle(/RENDER THIS PANEL EXTERNALLY/i);
    expect(renderBtn).toBeDefined();

    fireEvent.click(renderBtn);

    // Verify skeleton loader appears during generation
    expect(screen.getByTestId('shot-skeleton-loader')).toBeDefined();

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/external-render'),
        expect.anything()
      );
    });
  });
});
