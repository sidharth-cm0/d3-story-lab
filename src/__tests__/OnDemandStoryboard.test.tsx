import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { StoryboardViewer } from '../components/StoryboardViewer';
import * as api from '../api';

vi.mock('../api', async (importOriginal) => {
  const actual: any = await importOriginal();
  return {
    ...actual,
    fetchCapabilities: vi.fn(),
    generateStoryboard: vi.fn(),
    getStoryboardStatus: vi.fn(),
    configureRenderer: vi.fn(),
    fetchVisualBible: vi.fn().mockResolvedValue(null),
  };
});

describe('Low-Cost On-Demand Storyboard UI & Controls', () => {
  const mockProject: any = {
    id: 'proj_warehouse_123',
    metadata: {
      id: 'proj_warehouse_123',
      title: 'Warehouse Investigation',
      created_at: '2026-09-13T00:00:00Z',
    },
    title: 'Warehouse Investigation',
    status: 'completed',
    created_at: '2026-09-13T00:00:00Z',
    world: {
      locations: {},
      characters: {},
      secrets: {},
      timeline: [],
    },
    screenplay: {
      title: 'Warehouse Investigation',
      blocks: [],
      scenes: [],
    },
    storyboard: {
      shot_plan: {
        id: 'plan_1',
        project_id: 'proj_warehouse_123',
        panels: [
          {
            id: 'shot_1',
            scene_number: 1,
            shot_number: 1,
            page_number: 1,
            shot_type: 'wide',
            camera_angle: 'eye_level',
            action_description: 'Detective approaches warehouse doorway.',
            is_keyframe: true,
            aspect_ratio: '16:9',
            source_event_ids: ['evt_1'],
          },
          {
            id: 'shot_2',
            scene_number: 1,
            shot_number: 2,
            page_number: 1,
            shot_type: 'medium',
            camera_angle: 'eye_level',
            action_description: 'Detective checks the severed padlock.',
            aspect_ratio: '16:9',
            source_event_ids: ['evt_2'],
          },
          {
            id: 'shot_3',
            scene_number: 1,
            shot_number: 3,
            page_number: 2,
            shot_type: 'close_up',
            camera_angle: 'low_angle',
            action_description: 'Detective discovers classified dossier.',
            is_keyframe: true,
            aspect_ratio: '16:9',
            source_event_ids: ['evt_3'],
          },
        ],
      },
      rendered_panels: [],
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (api.fetchCapabilities as any).mockResolvedValue({
      provider: 'on_demand',
      available: false,
      status: 'QUOTA_UNAVAILABLE',
      status_message: 'Image generation quota unavailable.',
      pricing_disclaimer: 'Free/limited provider availability depends on current quota.',
    });
  });

  it('renders provider selector defaulting to ON-DEMAND and budget selector defaulting to 8', async () => {
    render(<StoryboardViewer project={mockProject} />);

    // Provider select
    const providerSelect = screen.getByTestId('select-storyboard-provider') as HTMLSelectElement;
    expect(providerSelect.value).toBe('on_demand');
    expect(screen.getByText('ON-DEMAND')).toBeDefined();
    expect(screen.getByText('COMFYUI')).toBeDefined();

    // Budget select
    const budgetSelect = screen.getByTestId('select-keyframe-budget') as HTMLSelectElement;
    expect(budgetSelect.value).toBe('8');
    expect(screen.getByText('KEYFRAMES 4')).toBeDefined();
    expect(screen.getByText('KEYFRAMES 8')).toBeDefined();
    expect(screen.getByText('KEYFRAMES 12')).toBeDefined();

    // Generate action button
    expect(
      screen.getByRole('button', { name: /GENERATE SELECTED STORYBOARD FRAMES/i })
    ).toBeDefined();

    // Quota disclaimer in header
    await waitFor(() => {
      expect(
        screen.getByText(/Free\/limited provider availability depends on current quota/i)
      ).toBeDefined();
    });
  });

  it('opens confirmation modal showing exact image count before generating', async () => {
    render(<StoryboardViewer project={mockProject} />);

    const generateBtn = screen.getByRole('button', {
      name: /GENERATE SELECTED STORYBOARD FRAMES/i,
    });

    // Click to open confirmation modal (with default budget 8)
    fireEvent.click(generateBtn);

    // Modal title and confirmation message
    expect(screen.getByText('Confirm Storyboard Generation')).toBeDefined();
    expect(screen.getByText(/Generates still storyboard images \(PNG\/JPEG\/WebP\)/i)).toBeDefined();
    expect(screen.getByText(/D3 Story Lab does NOT generate video or animations/i)).toBeDefined();

    // Cancel closes the modal
    const cancelBtn = screen.getByRole('button', { name: 'Cancel' });
    fireEvent.click(cancelBtn);

    expect(screen.queryByText('Confirm Storyboard Generation')).toBeNull();
  });

  it('updates generation count when budget is changed to 4 or 12', async () => {
    render(<StoryboardViewer project={mockProject} />);

    const budgetSelect = screen.getByTestId('select-keyframe-budget');
    const generateBtn = screen.getByRole('button', {
      name: /GENERATE SELECTED STORYBOARD FRAMES/i,
    });

    // Switch to budget 4
    fireEvent.change(budgetSelect, { target: { value: '4' } });
    fireEvent.click(generateBtn);

    expect(screen.getByText('4 storyboard images will be generated.')).toBeDefined();

    // Close and switch to budget 12
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    fireEvent.change(budgetSelect, { target: { value: '12' } });
    fireEvent.click(generateBtn);

    expect(screen.getByText('12 storyboard images will be generated.')).toBeDefined();
  });

  it('calls generateStoryboard with selected provider and budget on confirm', async () => {
    (api.generateStoryboard as any).mockResolvedValue({
      shot_plan: mockProject.storyboard.shot_plan,
      rendered_panels: [],
    });

    render(<StoryboardViewer project={mockProject} />);

    // Select budget 4
    const budgetSelect = screen.getByTestId('select-keyframe-budget');
    fireEvent.change(budgetSelect, { target: { value: '4' } });

    // Open modal
    fireEvent.click(
      screen.getByRole('button', { name: /GENERATE SELECTED STORYBOARD FRAMES/i })
    );

    // Click Confirm & Generate
    const confirmBtn = screen.getByRole('button', { name: /Confirm & Generate/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api.generateStoryboard).toHaveBeenCalledWith(
        'proj_warehouse_123',
        'on_demand',
        'KEYFRAMES',
        4
      );
    });
  });
});
