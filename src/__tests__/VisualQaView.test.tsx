import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { VisualQaView } from '../components/VisualQaView';
import { StoryboardPanel } from '../types';

describe('VisualQaView Component', () => {
  const samplePanels: StoryboardPanel[] = ([

    {
      id: 'shot-1',
      panel_id: 'shot-1',
      shot_number: 1,
      shot_type: 'wide_shot',
      camera_angle: 'eye_level',
      action: 'Elena approaches abandoned warehouse entrance at midnight.',
      image_url: '/api/assets/panels/shot-1.png', // real raster image
      rendered_svg: '<svg data-testid="svg-shot-1"><rect /></svg>',
    },
    {
      id: 'shot-2',
      panel_id: 'shot-2',
      shot_number: 2,
      action: 'Elena checks the severed chain.',
    },
    {
      id: 'shot-3',
      panel_id: 'shot-3',
      shot_number: 3,
      action: 'Elena steps into darkness.',
    },
    {
      id: 'shot-4',
      panel_id: 'shot-4',
      shot_number: 4,
      shot_type: 'medium_shot',
      camera_angle: 'low_angle',
      action: 'Elena creeps past crates under airborne dust.',
      image_url: undefined, // unconnected / unrendered
      rendered_svg: '<svg data-testid="svg-shot-4"><circle /></svg>',
    },
    {
      id: 'shot-5',
      panel_id: 'shot-5',
      shot_number: 5,
      shot_type: 'close_up',
      camera_angle: 'eye_level',
      action: 'Elena discovers stolen classified dossier.',
      image_url: undefined,
      rendered_svg: '<svg data-testid="svg-shot-5"><path /></svg>',
    },
    {
      id: 'shot-6',
      panel_id: 'shot-6',
      shot_number: 6,
      action: 'Elena opens the folder.',
    },
    {
      id: 'shot-7',
      panel_id: 'shot-7',
      shot_number: 7,
      action: 'A shadow moves on the catwalk.',
    },
    {
      id: 'shot-8',
      panel_id: 'shot-8',
      shot_number: 8,
      shot_type: 'medium_shot',
      camera_angle: 'dutch_angle',
      action: 'Gunfire erupts as Elena dives with dossier.',
      image_url: undefined,
      rendered_svg: '<svg data-testid="svg-shot-8"><polygon /></svg>',
    },
  ] as unknown as StoryboardPanel[]);

  it('renders all 4 required keyframes: Shot 1, Shot 4, Shot 5, Shot 8', () => {

    render(
      <VisualQaView
        panels={samplePanels}
        capabilities={{
          provider: 'comfyui',
          model: 'sdxl_storyboard_graphite_v1',
          available: false,
          status: 'RUNTIME_UNREACHABLE',
        }}
      />
    );

    // Verify shot cards
    expect(screen.getByTestId('qa-card-shot-1')).toBeDefined();
    expect(screen.getByTestId('qa-card-shot-4')).toBeDefined();
    expect(screen.getByTestId('qa-card-shot-5')).toBeDefined();
    expect(screen.getByTestId('qa-card-shot-8')).toBeDefined();

    // Verify Shot 2, 3, 6, 7 are NOT in QA keyframe grid
    expect(screen.queryByTestId('qa-card-shot-2')).toBeNull();
    expect(screen.queryByTestId('qa-card-shot-3')).toBeNull();
    expect(screen.queryByTestId('qa-card-shot-6')).toBeNull();
    expect(screen.queryByTestId('qa-card-shot-7')).toBeNull();
  });

  it('displays real raster image for Shot 1 and unconnected warning for unrendered shots', () => {
    render(
      <VisualQaView
        panels={samplePanels}
        capabilities={{
          provider: 'comfyui',
          model: 'sdxl_storyboard_graphite_v1',
          available: false,
          status: 'RUNTIME_UNREACHABLE',
        }}
      />
    );

    // Shot 1 has real raster image
    const shot1Img = screen.getByTestId('qa-image-shot-1') as HTMLImageElement;
    expect(shot1Img.src).toContain('/api/assets/panels/shot-1.png');

    // Shot 4 is unrendered without runtime -> shows unconnected message
    expect(screen.getByTestId('qa-unconnected-shot-4')).toBeDefined();
    expect(screen.getAllByText('Open-model storyboard runtime not connected.').length).toBeGreaterThan(0);
  });

  it('toggles previs guide for unrendered shot without displaying SVG as final artwork', () => {
    render(
      <VisualQaView
        panels={samplePanels}
        capabilities={{
          provider: 'comfyui',
          model: 'sdxl_storyboard_graphite_v1',
          available: false,
          status: 'RUNTIME_UNREACHABLE',
        }}
      />
    );

    // Initially previs guide is hidden
    expect(screen.queryByTestId('qa-previs-shot-4')).toBeNull();

    // Find the toggle button in shot 4
    const toggleBtns = screen.getAllByText('Previs guide available');
    expect(toggleBtns.length).toBeGreaterThan(0);
    fireEvent.click(toggleBtns[0]);

    // Now previs guide is revealed for inspection only
    expect(screen.getByTestId('qa-previs-shot-4')).toBeDefined();
  });

  it('includes manual checkboxes for character, prop, camera, and style consistency plus notes', () => {
    render(
      <VisualQaView
        panels={samplePanels}
        capabilities={{
          provider: 'comfyui',
          model: 'sdxl_storyboard_graphite_v1',
          available: true,
          status: 'RUNTIME_READY',
        }}
      />
    );

    // Verify all 4 checkboxes exist on Shot 5
    const charBox = screen.getByTestId('qa-check-character-5') as HTMLInputElement;
    const propBox = screen.getByTestId('qa-check-prop-5') as HTMLInputElement;
    const cameraBox = screen.getByTestId('qa-check-camera-5') as HTMLInputElement;
    const styleBox = screen.getByTestId('qa-check-style-5') as HTMLInputElement;
    const notesInput = screen.getByTestId('qa-notes-5') as HTMLTextAreaElement;

    expect(charBox.checked).toBe(false);
    fireEvent.click(charBox);
    expect(charBox.checked).toBe(true);

    expect(propBox.checked).toBe(false);
    fireEvent.click(propBox);
    expect(propBox.checked).toBe(true);

    expect(cameraBox.checked).toBe(false);
    fireEvent.click(cameraBox);
    expect(cameraBox.checked).toBe(true);

    expect(styleBox.checked).toBe(false);
    fireEvent.click(styleBox);
    expect(styleBox.checked).toBe(true);

    fireEvent.change(notesInput, { target: { value: 'Classified folder stamp clearly legible' } });
    expect(notesInput.value).toBe('Classified folder stamp clearly legible');
  });
});
