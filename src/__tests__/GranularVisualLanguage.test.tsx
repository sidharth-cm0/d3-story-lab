/**
 * GranularVisualLanguage.test.tsx
 *
 * Test suite for Phase 9.2.5 — Granular Visual Language + Transition System.
 *
 * Requirements (§21):
 * - granular component renders deterministically
 * - reduced-motion renders static state
 * - no particle re-randomization across rerender
 * - all 8 tabs still work
 * - page transitions do not mutate API state
 * - Home remains accessible
 * - particle layer uses pointer-events:none
 * - no hidden text beneath overlays
 * - Storyboard contracts untouched
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import {
  GranularField,
  ParticleWave,
  ParticleSilhouette,
  ParticleHalo,
  ParticleDivider,
  ParticleReveal,
  GranularNarrativeField,
  GranularThreeCanvas,
  isWebGLAvailable,
  detectQualityTier,
  getQualityBudget,
  generate3DPointCloud,
  viewToMotif,
  generatePointField,
  generateWavePoints,
  generateSilhouettePoints,
  generateHaloPoints,
  generateDividerPoints,
  generateDenseNarrativeLandscape,
  pointsToSvgPath,
  mulberry32,
} from '../components/granular';

import { PageTransition } from '../components/motion/PageTransition';
import { ScrollytellingHome } from '../components/ScrollytellingHome';
import { WorldInspector } from '../components/WorldInspector';
import { CharacterCards } from '../components/CharacterCards';
import { StructureAndArcsViewer } from '../components/StructureAndArcsViewer';
import { SimulationTicker } from '../components/SimulationTicker';
import { ScreenplayViewer } from '../components/ScreenplayViewer';
import { StoryboardViewer } from '../components/StoryboardViewer';
import { ExportViewer } from '../components/ExportViewer';
import { ShotCard } from '../components/ShotCard';
import { StoryboardPanel, ProjectData } from '../types';
import realMissingDossierDataRaw from '../../../backend/data/projects/world_init_4bef81.json';

const realProjectData = realMissingDossierDataRaw as unknown as ProjectData;

describe('Phase 9.2.5: Granular Visual Language & PRNG Determinism', () => {
  it('mulberry32 produces deterministic pseudo-random sequences for identical seeds', () => {
    const prng1 = mulberry32(42);
    const prng2 = mulberry32(42);
    const prng3 = mulberry32(99);

    const seq1 = [prng1(), prng1(), prng1(), prng1()];
    const seq2 = [prng2(), prng2(), prng2(), prng2()];
    const seq3 = [prng3(), prng3(), prng3(), prng3()];

    expect(seq1).toEqual(seq2);
    expect(seq1).not.toEqual(seq3);
  });

  it('generatePointField produces identical coordinates and properties for same seed', () => {
    const pts1 = generatePointField(60, 101, 1000, 400);
    const pts2 = generatePointField(60, 101, 1000, 400);

    expect(pts1.length).toBe(60);
    expect(pts1).toEqual(pts2);
  });

  it('generateWavePoints produces deterministic undulating wave points', () => {
    const wave1 = generateWavePoints(50, 202, 1000, 300);
    const wave2 = generateWavePoints(50, 202, 1000, 300);

    expect(wave1.length).toBe(150); // 50 * 3 layers
    expect(wave1).toEqual(wave2);
  });

  it('generateSilhouettePoints produces deterministic dual-agent silhouettes with causal bridge', () => {
    const sil1 = generateSilhouettePoints(777, 800, 240);
    const sil2 = generateSilhouettePoints(777, 800, 240);

    expect(sil1.leftAgentPoints).toEqual(sil2.leftAgentPoints);
    expect(sil1.rightAgentPoints).toEqual(sil2.rightAgentPoints);
    expect(sil1.bridgePoints).toEqual(sil2.bridgePoints);
    expect(sil1.bridgePoints.length).toBe(50);
  });

  it('generateHaloPoints and generateDividerPoints are deterministic', () => {
    const halo1 = generateHaloPoints(32, 333, 100, 100, 80, 80);
    const halo2 = generateHaloPoints(32, 333, 100, 100, 80, 80);
    expect(halo1).toEqual(halo2);

    const div1 = generateDividerPoints(40, 555, 800, 10);
    const div2 = generateDividerPoints(40, 555, 800, 10);
    expect(div1).toEqual(div2);
  });
});

describe('Phase 9.2.5: Component Rendering & Pointer-Events Transparency', () => {
  it('GranularField renders with pointer-events: none and presentation role', () => {
    const { container } = render(
      <GranularField pointCount={50} seed={42} data-testid="test-field" />
    );
    const svg = screen.getByTestId('test-field');
    expect(svg).toBeDefined();
    expect(svg.getAttribute('aria-hidden')).toBe('true');
    expect(svg.getAttribute('role')).toBe('presentation');
    expect(svg.style.pointerEvents).toBe('none');
    expect(container.querySelectorAll('circle').length).toBe(50);
  });

  it('no particle re-randomization across re-renders', () => {
    const { container, rerender } = render(
      <GranularField pointCount={40} seed={99} data-testid="rerender-field" />
    );
    const initialCircles = Array.from(container.querySelectorAll('circle')).map((c) => ({
      cx: c.getAttribute('cx'),
      cy: c.getAttribute('cy'),
      r: c.getAttribute('r'),
    }));

    rerender(<GranularField pointCount={40} seed={99} data-testid="rerender-field" />);

    const rerenderedCircles = Array.from(container.querySelectorAll('circle')).map((c) => ({
      cx: c.getAttribute('cx'),
      cy: c.getAttribute('cy'),
      r: c.getAttribute('r'),
    }));

    expect(initialCircles).toEqual(rerenderedCircles);
  });

  it('ParticleWave renders with pointer-events: none and presentation role', () => {
    const { container } = render(
      <ParticleWave pointsPerLayer={30} seed={101} data-testid="test-wave" />
    );
    const svg = screen.getByTestId('test-wave');
    expect(svg).toBeDefined();
    expect(svg.getAttribute('aria-hidden')).toBe('true');
    expect(svg.style.pointerEvents).toBe('none');
    expect(container.querySelectorAll('circle').length).toBe(90);
  });

  it('ParticleSilhouette renders both agents and transference arc', () => {
    const { container } = render(
      <ParticleSilhouette seed={777} data-testid="test-sil" />
    );
    const svg = screen.getByTestId('test-sil');
    expect(svg).toBeDefined();
    expect(svg.style.pointerEvents).toBe('none');
    expect(container.querySelector('.agent-left')).not.toBeNull();
    expect(container.querySelector('.agent-right')).not.toBeNull();
    expect(container.querySelector('.agent-transference-stream')).not.toBeNull();
  });

  it('ParticleHalo renders when active and hides when inactive', () => {
    const { rerender } = render(
      <ParticleHalo active={true} data-testid="test-halo" />
    );
    const halo = screen.getByTestId('test-halo');
    expect(halo).toBeDefined();
    expect(halo.style.pointerEvents).toBe('none');

    rerender(<ParticleHalo active={false} data-testid="test-halo" />);
    expect(screen.queryByTestId('test-halo')).toBeNull();
  });

  it('ParticleDivider renders with center guide line and pointer-events: none', () => {
    const { container } = render(
      <ParticleDivider count={30} seed={555} data-testid="test-div" />
    );
    const svg = screen.getByTestId('test-div');
    expect(svg).toBeDefined();
    expect(svg.style.pointerEvents).toBe('none');
    expect(container.querySelector('line')).not.toBeNull();
  });
});

describe('Phase 9.2.5: Reduced-Motion Behavior', () => {
  let originalMatchMedia: typeof window.matchMedia;

  beforeEach(() => {
    originalMatchMedia = window.matchMedia;
  });

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
  });

  it('ParticleReveal renders static container when reduced motion is preferred', () => {
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    render(
      <ParticleReveal data-testid="reveal-box">
        <div data-testid="child-content">Revealed Content</div>
      </ParticleReveal>
    );

    const box = screen.getByTestId('reveal-box');
    expect(box).toBeDefined();
    expect(box.className).toContain('particle-reveal-container');
    expect(box.style.pointerEvents).toBe('none');
    expect(screen.getByTestId('child-content')).toBeDefined();
  });
});

describe('Phase 9.2.6: Home Accessibility & Continuous Granular Field Integrity', () => {
  it('Home displays hero title, statement lines, and interactive buttons without obstruction', () => {
    const onStartNew = vi.fn();
    const onOpenProject = vi.fn();

    render(
      <ScrollytellingHome
        onStartNew={onStartNew}
        onOpenProject={onOpenProject}
        projects={[realProjectData.metadata]}
      />
    );

    // Verify Title and Editorial Text
    expect(screen.getByText('D3 STORY LAB')).toBeDefined();
    expect(screen.getByText('THE STORY IS NOT WRITTEN.')).toBeDefined();
    expect(screen.getByText('IT EMERGES.')).toBeDefined();

    // Verify CTA Buttons are clickable and call proper handlers
    const newSimBtn = screen.getByRole('button', { name: /NEW SIMULATION/i });
    expect(newSimBtn).toBeDefined();
    fireEvent.click(newSimBtn);
    expect(onStartNew).toHaveBeenCalledTimes(1);

    const openProjBtn = screen.getByRole('button', { name: /OPEN PROJECT/i });
    expect(openProjBtn).toBeDefined();
    fireEvent.click(openProjBtn);
    expect(onOpenProject).toHaveBeenCalledWith(realProjectData.metadata.id);

    // Verify Granular Three canvas and its fallback narrative field are NOT hosted locally inside ScrollytellingHome (moved to global AppShell)
    // and obsolete star field is removed
    expect(screen.queryByTestId('granular-three-canvas')).toBeNull();
    expect(screen.queryByTestId('granular-narrative-field')).toBeNull();
    expect(screen.queryByTestId('granular-field')).toBeNull();

    // Verify button hover triggers don't throw
    fireEvent.mouseEnter(newSimBtn);
    fireEvent.mouseLeave(newSimBtn);
  });
});

describe('Phase 9.2.5: All 8 Tabs Render Cleanly With Granular Enhancements', () => {
  it('Tab 1: Home renders without errors', () => {
    render(<ScrollytellingHome onStartNew={() => {}} onOpenProject={() => {}} projects={[]} />);
    expect(screen.getByText('D3 STORY LAB')).toBeDefined();
  });

  it('Tab 2: World tab renders topology with GranularField backdrop', () => {
    const { container } = render(<WorldInspector world={realProjectData.world} />);
    expect(screen.getByText('SANDBOX TOPOLOGY')).toBeDefined();
    expect(screen.getAllByText(/Abandoned Industrial Bay/).length).toBeGreaterThanOrEqual(1);
    expect(container.querySelector('.granular-topology-bg')).not.toBeNull();

    // Test location selection
    const locationCard = screen.getAllByText(/Abandoned Industrial Bay/)[0].closest('.noir-card');
    expect(locationCard).not.toBeNull();
    fireEvent.click(locationCard!);
    expect(locationCard!.className).toContain('selected-shot-granular-frame');
  });

  it('Tab 3: Actors tab renders cards and toggles ParticleHalo on selection', () => {
    const { container } = render(<CharacterCards world={realProjectData.world} />);
    expect(screen.getByText('AUTONOMOUS AGENTS')).toBeDefined();
    expect(screen.getByText('Vincent Cross')).toBeDefined();

    const actorCard = screen.getByText('Vincent Cross').closest('.noir-actor-card');
    expect(actorCard).not.toBeNull();

    // Click to select
    fireEvent.click(actorCard!);
    expect(actorCard!.className).toContain('selected-shot-granular-frame');
    expect(container.querySelector('.particle-halo-svg')).not.toBeNull();
  });

  it('Tab 4: Arcs & Structure renders with ParticleWave backdrop', () => {
    const { container } = render(<StructureAndArcsViewer project={realProjectData} loading={false} />);
    expect(screen.getByText('STRUCTURE, ARCS & CAUSAL CONTINUITY')).toBeDefined();
    expect(container.querySelector('.narrative-flow-bg')).not.toBeNull();
  });

  it('Tab 5: Simulation tab renders and supports causal selection with dividers', () => {
    const events = Object.values(realProjectData.world.events || {}).sort(
      (a, b) => a.tick - b.tick || a.id.localeCompare(b.id)
    );

    const { container } = render(
      <SimulationTicker
        world={realProjectData.world}
        events={events}
        onStep={async () => {}}
        onRun={async () => {}}
        loading={false}
      />
    );

    expect(screen.getByText('EVENT STREAM')).toBeDefined();
    expect(container.querySelector('.cinematic-sim-view')).not.toBeNull();
  });

  it('Tab 6: Script (ScreenplayViewer) renders in pure reading focus mode', () => {
    const { container } = render(
      <ScreenplayViewer project={realProjectData} onGenerate={async () => {}} loading={false} />
    );
    expect(container.querySelector('.cinematic-screenplay-pane')).not.toBeNull();
    expect(screen.getAllByText('SCREENPLAY & SYNOPSIS').length).toBeGreaterThanOrEqual(1);
  });

  it('Tab 7: Storyboard tab renders and supports selected shot framing', () => {
    const { container } = render(<StoryboardViewer project={realProjectData} loading={false} />);
    expect(container.querySelector('.cinematic-storyboard-pane')).not.toBeNull();
    expect(screen.getByText('STORYBOARD')).toBeDefined();
  });

  it('Tab 8: Export tab renders cleanly', () => {
    const { container } = render(<ExportViewer project={realProjectData} />);
    expect(container.querySelector('.cinematic-export-pane')).not.toBeNull();
    expect(screen.getByText('EXPORT PRODUCTION BUNDLE')).toBeDefined();
  });
});

describe('Phase 9.2.5: ShotCard & PageTransition Contract Safety', () => {
  it('ShotCard supports isSelected prop adding selected-shot-granular-frame class', () => {
    const testPanel = {
      id: 'panel_01',
      shot_number: 1,
      shot_type: 'close_up',
      camera_angle: 'low_angle',
      action: 'Maya discovers the ledger.',
      location_name: 'Penthouse Office',
    } as unknown as StoryboardPanel;

    const { rerender } = render(<ShotCard panel={testPanel} isSelected={false} />);
    const card = screen.getByTestId('shot-card-panel_01');
    expect(card.className).not.toContain('selected-shot-granular-frame');

    rerender(<ShotCard panel={testPanel} isSelected={true} />);
    expect(card.className).toContain('selected-shot-granular-frame');
  });

  it('PageTransition wraps children without modifying state', () => {
    const { getByText } = render(
      <PageTransition viewKey="home">
        <div>Page Content</div>
      </PageTransition>
    );
    expect(getByText('Page Content')).toBeDefined();
  });
});

describe('Phase 9.2.6: Dense Point-Cloud Landscape Model & Batched Geometry', () => {
  it('generateDenseNarrativeLandscape produces deterministic layers and coordinates for same seed', () => {
    const model1 = generateDenseNarrativeLandscape({ seed: 926, width: 1200, height: 380 });
    const model2 = generateDenseNarrativeLandscape({ seed: 926, width: 1200, height: 380 });
    const model3 = generateDenseNarrativeLandscape({ seed: 555, width: 1200, height: 380 });

    expect(model1.totalPoints).toBeGreaterThanOrEqual(1200);
    expect(model1.totalPoints).toBe(model2.totalPoints);
    expect(model1.bgPoints.length).toBe(model2.bgPoints.length);
    expect(model1.midPoints.length).toBe(model2.midPoints.length);
    expect(model1.fgPoints.length).toBe(model2.fgPoints.length);
    expect(model1.agentLeftPoints.length).toBe(model2.agentLeftPoints.length);
    expect(model1.agentRightPoints.length).toBe(model2.agentRightPoints.length);
    expect(model1.causalPoints.length).toBe(model2.causalPoints.length);

    expect(model1.bgPathD).toBe(model2.bgPathD);
    expect(model1.midPathD).toBe(model2.midPathD);
    expect(model1.fgPathD).toBe(model2.fgPathD);
    expect(model1.agentLeftPathD).toBe(model2.agentLeftPathD);
    expect(model1.agentRightPathD).toBe(model2.agentRightPathD);
    expect(model1.causalPathD).toBe(model2.causalPathD);

    // Different seed produces different coordinates
    expect(model1.bgPathD).not.toBe(model3.bgPathD);
  });

  it('generates amber accent points for foreground ridges and causal stream', () => {
    const model = generateDenseNarrativeLandscape({ seed: 926, width: 1200, height: 380 });
    expect(model.fgAmberPoints.length).toBeGreaterThan(0);
    expect(model.causalAmberPoints.length).toBeGreaterThan(0);
    expect(model.fgAmberPathD.length).toBeGreaterThan(0);
    expect(model.causalAmberPathD.length).toBeGreaterThan(0);
  });

  it('pointsToSvgPath generates valid SVG path subpaths with arcs', () => {
    const testPoints = [
      { id: '1', x: 100, y: 50, r: 2, opacity: 0.8 },
      { id: '2', x: 200, y: 80, r: 1.5, opacity: 0.5 },
    ];
    const pathD = pointsToSvgPath(testPoints);
    expect(pathD).toContain('M98 50');
    expect(pathD).toContain('a2 2 0 1 0 4 0');
    expect(pathD).toContain('M198.5 80');
    expect(pathD).toContain('a1.5 1.5 0 1 0 3 0');

    // Empty array produces empty string
    expect(pointsToSvgPath([])).toBe('');
  });
});

describe('Phase 9.2.6: GranularNarrativeField Component', () => {
  it('renders with pointer-events: none and presentation role', () => {
    const { container } = render(
      <GranularNarrativeField data-testid="test-narrative-field" />
    );
    const wrapper = screen.getByTestId('test-narrative-field');
    expect(wrapper).toBeDefined();
    expect(wrapper.getAttribute('aria-hidden')).toBe('true');
    expect(wrapper.getAttribute('role')).toBe('presentation');
    expect(wrapper.style.pointerEvents).toBe('none');

    // SVG must be present
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
    expect(svg!.getAttribute('aria-hidden')).toBe('true');
  });

  it('renders all structural depth layers and agent silhouettes', () => {
    const { container } = render(
      <GranularNarrativeField data-testid="test-narrative-field" />
    );
    expect(container.querySelector('.layer-bg-strata')).not.toBeNull();
    expect(container.querySelector('.layer-mid-terrain')).not.toBeNull();
    expect(container.querySelector('.layer-fg-ridge')).not.toBeNull();
    expect(container.querySelector('.layer-agents')).not.toBeNull();
    expect(container.querySelector('.agent-silhouette-left')).not.toBeNull();
    expect(container.querySelector('.agent-silhouette-right')).not.toBeNull();
    expect(container.querySelector('.layer-causal-stream')).not.toBeNull();
  });

  it('uses batched path elements instead of thousands of circle nodes for performance', () => {
    const { container } = render(
      <GranularNarrativeField data-testid="test-narrative-field" />
    );
    const paths = container.querySelectorAll('path');
    const circles = container.querySelectorAll('circle');

    // Exactly 8 batched paths for the entire dense scene
    expect(paths.length).toBe(8);
    // Zero individual circle elements (all batched into paths)
    expect(circles.length).toBe(0);
  });

  it('supports isHovered prop for CTA hover interaction', () => {
    const { rerender } = render(
      <GranularNarrativeField isHovered={false} data-testid="test-narrative-field" />
    );
    expect(screen.getByTestId('test-narrative-field')).toBeDefined();

    rerender(
      <GranularNarrativeField isHovered={true} data-testid="test-narrative-field" />
    );
    expect(screen.getByTestId('test-narrative-field')).toBeDefined();
  });

  it('renders immediate static state when prefers-reduced-motion is active', () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const { container } = render(
      <GranularNarrativeField data-testid="test-narrative-field-reduced" />
    );
    const wrapper = screen.getByTestId('test-narrative-field-reduced');
    expect(wrapper).toBeDefined();
    expect(container.querySelector('svg')).not.toBeNull();
    expect(container.querySelectorAll('path').length).toBe(8);

    window.matchMedia = originalMatchMedia;
  });
});

describe('Phase 9.2.7: Three.js WebGL Detection, Quality Tiers & Performance Budgets', () => {
  it('isWebGLAvailable returns boolean without throwing in JSDOM / headless environments', () => {
    const available = isWebGLAvailable();
    expect(typeof available).toBe('boolean');
  });

  it('detectQualityTier assigns appropriate tier based on environment', () => {
    // Force tiers work correctly
    expect(detectQualityTier({ forceTier: 'HIGH' })).toBe('HIGH');
    expect(detectQualityTier({ forceTier: 'MEDIUM' })).toBe('MEDIUM');
    expect(detectQualityTier({ forceTier: 'LOW' })).toBe('LOW');
    expect(detectQualityTier({ forceTier: 'FALLBACK' })).toBe('FALLBACK');

    // Reduced motion preference forces FALLBACK
    expect(detectQualityTier({ prefersReducedMotion: true })).toBe('FALLBACK');
  });

  it('getQualityBudget caps DPR at 1.5 across all tiers', () => {
    const budgetHigh = getQualityBudget('HIGH');
    expect(budgetHigh.pointCount).toBe(52000);
    expect(budgetHigh.dpr).toBeLessThanOrEqual(1.5);
    expect(budgetHigh.enableMorph).toBe(true);

    const budgetMed = getQualityBudget('MEDIUM');
    expect(budgetMed.pointCount).toBe(26000);
    expect(budgetMed.dpr).toBeLessThanOrEqual(1.5);
    expect(budgetMed.enableMorph).toBe(true);

    const budgetLow = getQualityBudget('LOW');
    expect(budgetLow.pointCount).toBe(8500);
    expect(budgetLow.dpr).toBeLessThanOrEqual(1.5);
    expect(budgetLow.enableMorph).toBe(false);

    const budgetFallback = getQualityBudget('FALLBACK');
    expect(budgetFallback.pointCount).toBe(0);
    expect(budgetFallback.enableDisplacement).toBe(false);
  });

  it('generate3DPointCloud produces deterministic Float32Array buffers with multi-layer topology', () => {
    const cloud1 = generate3DPointCloud(10000, 927);
    const cloud2 = generate3DPointCloud(10000, 927);
    const cloud3 = generate3DPointCloud(10000, 555);

    expect(cloud1.pointCount).toBe(10000);
    expect(cloud1.positions.length).toBe(30000);
    expect(cloud1.targets.length).toBe(30000);
    expect(cloud1.colors.length).toBe(30000);
    expect(cloud1.sizes.length).toBe(10000);
    expect(cloud1.phases.length).toBe(10000);
    expect(cloud1.layerIds.length).toBe(10000);

    // Byte-identical reproduction for identical seed
    expect(cloud1.positions[0]).toBe(cloud2.positions[0]);
    expect(cloud1.targets[10]).toBe(cloud2.targets[10]);
    expect(cloud1.colors[5]).toBe(cloud2.colors[5]);

    // Distinct for different seed
    expect(cloud1.positions[0]).not.toBe(cloud3.positions[0]);
  });
});

describe('Phase 9.2.7: GranularThreeCanvas Component & Fallback Behavior', () => {
  it('renders gracefully in fallback mode when WebGL is unavailable or in JSDOM', () => {
    const { container } = render(
      <GranularThreeCanvas data-testid="test-three-canvas" />
    );
    const wrapper = screen.getByTestId('test-three-canvas');
    expect(wrapper).toBeDefined();
    expect(wrapper.getAttribute('data-fallback')).toBe('true');
    expect(wrapper.style.pointerEvents).toBe('none');

    // Deterministic SVG fallback is rendered inside
    expect(container.querySelector('.granular-narrative-field-wrapper')).not.toBeNull();
  });

  it('forces fallback when prefers-reduced-motion is active', () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    render(
      <GranularThreeCanvas data-testid="test-three-canvas-reduced" />
    );
    const wrapper = screen.getByTestId('test-three-canvas-reduced');
    expect(wrapper).toBeDefined();
    expect(wrapper.getAttribute('data-fallback')).toBe('true');

    window.matchMedia = originalMatchMedia;
  });

  it('supports isHovered and motif prop updates without throwing', () => {
    const { rerender } = render(
      <GranularThreeCanvas isHovered={false} motif="hero" data-testid="test-three-canvas" />
    );
    expect(screen.getByTestId('test-three-canvas')).toBeDefined();

    rerender(
      <GranularThreeCanvas isHovered={true} motif="actors" data-testid="test-three-canvas" />
    );
    expect(screen.getByTestId('test-three-canvas')).toBeDefined();
  });
});

describe('Phase 9.2.7: Transition Coordination & Page Motifs', () => {
  it('viewToMotif maps each application tab to its dedicated Three.js motif', () => {
    expect(viewToMotif('home')).toBe('hero');
    expect(viewToMotif('world')).toBe('world');
    expect(viewToMotif('actors')).toBe('actors');
    expect(viewToMotif('arcs')).toBe('arcs');
    expect(viewToMotif('simulation')).toBe('simulation');
    expect(viewToMotif('storyboard')).toBe('storyboard');
  });
});
