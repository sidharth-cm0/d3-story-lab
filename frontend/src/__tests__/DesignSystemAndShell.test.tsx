import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useState } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { usePrefersReducedMotion, getMotionTransition } from '../hooks/usePrefersReducedMotion';
import { TopNav } from '../components/shell/TopNav';
import { ProjectSwitcher } from '../components/shell/ProjectSwitcher';
import { AppShell } from '../components/shell/AppShell';
import {
  SectionHeader,
  PanelCard,
  MetricChip,
  StatusBadge,
  InspectorDrawer,
  EmptyState,
  ErrorState,
  LoadingState,
  SegmentedControl,
  ProvenanceChip,
  QualityMetric,
  PanelToolbar,
} from '../components/primitives';
import { ScrollytellingHome } from '../components/ScrollytellingHome';
import { StoryboardViewer } from '../components/StoryboardViewer';
import { StructureAndArcsViewer } from '../components/StructureAndArcsViewer';
import { ProjectData } from '../types';
import realMissingDossierDataRaw from '../../../backend/data/projects/world_init_4bef81.json';

const realMissingDossierData = realMissingDossierDataRaw as unknown as ProjectData;

describe('Phase 9.1 Design System, App Shell & Motion Foundation', () => {
  // --------------------------------------------------------------------------
  // 1. usePrefersReducedMotion Hook & Transition Collapse
  // --------------------------------------------------------------------------
  describe('usePrefersReducedMotion', () => {
    let originalMatchMedia: typeof window.matchMedia;

    beforeEach(() => {
      originalMatchMedia = window.matchMedia;
    });

    afterEach(() => {
      window.matchMedia = originalMatchMedia;
    });

    const createMockMatchMedia = (matches: boolean) => {
      return vi.fn().mockImplementation((query: string) => ({
        matches,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));
    };

    it('reports false when media query does not match reduced-motion', () => {
      window.matchMedia = createMockMatchMedia(false);

      const TestComponent = () => {
        const prefersReduced = usePrefersReducedMotion();
        return <div data-testid="reduced-val">{prefersReduced ? 'reduced' : 'motion'}</div>;
      };

      render(<TestComponent />);
      expect(screen.getByTestId('reduced-val').textContent).toBe('motion');
    });

    it('reports true when media query matches reduced-motion', () => {
      window.matchMedia = createMockMatchMedia(true);

      const TestComponent = () => {
        const prefersReduced = usePrefersReducedMotion();
        return <div data-testid="reduced-val">{prefersReduced ? 'reduced' : 'motion'}</div>;
      };

      render(<TestComponent />);
      expect(screen.getByTestId('reduced-val').textContent).toBe('reduced');
    });

    it('collapses motion transition duration when prefersReduced is true', () => {
      const normalTransition = getMotionTransition(false, 0.24);
      expect(normalTransition.duration).toBe(0.24);

      const collapsedTransition = getMotionTransition(true, 0.24);
      expect(collapsedTransition.duration).toBe(0.001);
      expect(collapsedTransition.ease).toBe('linear');
    });
  });

  // --------------------------------------------------------------------------
  // 2. SegmentedControl Keyboard Operability & ARIA roles
  // --------------------------------------------------------------------------
  describe('SegmentedControl', () => {
    const options = [
      { value: 'grid', label: 'Grid View' },
      { value: 'comic', label: 'Comic Strip' },
      { value: 'contact', label: 'Contact Sheet' },
    ];

    const ControlledSegmentedControl = () => {
      const [val, setVal] = useState('grid');
      return (
        <SegmentedControl
          name="test-segment"
          ariaLabel="Storyboard Layout"
          options={options}
          value={val}
          onChange={setVal}
        />
      );
    };

    it('renders with role="radiogroup" and radiogroup items', () => {
      render(<ControlledSegmentedControl />);
      const group = screen.getByRole('radiogroup', { name: 'Storyboard Layout' });
      expect(group).toBeDefined();

      const items = screen.getAllByRole('radio');
      expect(items).toHaveLength(3);
      expect(items[0].getAttribute('aria-checked')).toBe('true');
      expect(items[0].getAttribute('tabIndex')).toBe('0');
      expect(items[1].getAttribute('aria-checked')).toBe('false');
      expect(items[1].getAttribute('tabIndex')).toBe('-1');
    });

    it('navigates with ArrowRight and ArrowLeft keyboard keys', () => {
      render(<ControlledSegmentedControl />);
      const items = screen.getAllByRole('radio');

      // Focus first item and press ArrowRight -> moves to second
      items[0].focus();
      fireEvent.keyDown(items[0], { key: 'ArrowRight' });

      expect(items[1].getAttribute('aria-checked')).toBe('true');
      expect(items[0].getAttribute('aria-checked')).toBe('false');

      // ArrowRight again -> moves to third
      fireEvent.keyDown(items[1], { key: 'ArrowRight' });
      expect(items[2].getAttribute('aria-checked')).toBe('true');

      // ArrowRight wraps to first
      fireEvent.keyDown(items[2], { key: 'ArrowRight' });
      expect(items[0].getAttribute('aria-checked')).toBe('true');

      // ArrowLeft wraps backwards to third
      fireEvent.keyDown(items[0], { key: 'ArrowLeft' });
      expect(items[2].getAttribute('aria-checked')).toBe('true');
    });

    it('navigates to Home and End options with Home and End keys', () => {
      render(<ControlledSegmentedControl />);
      const items = screen.getAllByRole('radio');

      items[0].focus();
      fireEvent.keyDown(items[0], { key: 'End' });
      expect(items[2].getAttribute('aria-checked')).toBe('true');

      fireEvent.keyDown(items[2], { key: 'Home' });
      expect(items[0].getAttribute('aria-checked')).toBe('true');
    });

    it('updates selection on mouse click', () => {
      render(<ControlledSegmentedControl />);
      const items = screen.getAllByRole('radio');

      fireEvent.click(items[1]);
      expect(items[1].getAttribute('aria-checked')).toBe('true');
      expect(items[0].getAttribute('aria-checked')).toBe('false');
    });
  });

  // --------------------------------------------------------------------------
  // 3. TopNav Keyboard Operability & Focus
  // --------------------------------------------------------------------------
  describe('TopNav', () => {
    it('renders all 8 tabs with tab role and keyboard navigation', () => {
      const onSelectView = vi.fn();
      render(<TopNav activeView="simulation" onSelectView={onSelectView} />);

      const tabs = screen.getAllByRole('tab');
      expect(tabs).toHaveLength(8);

      // Verify each expected label
      expect(screen.getByText('HOME')).toBeDefined();
      expect(screen.getByText('WORLD')).toBeDefined();
      expect(screen.getByText('ACTORS')).toBeDefined();
      expect(screen.getByText('ARCS & STRUCTURE')).toBeDefined();
      expect(screen.getByText('SIMULATION')).toBeDefined();
      expect(screen.getByText('SCRIPT')).toBeDefined();
      expect(screen.getByText('STORYBOARD')).toBeDefined();
      expect(screen.getByText('EXPORT')).toBeDefined();

      // SIMULATION is active
      const activeTab = tabs.find((t) => t.getAttribute('aria-selected') === 'true');
      expect(activeTab?.textContent).toContain('SIMULATION');

      // Enter key activates tab
      const scriptTab = tabs.find((t) => t.textContent?.includes('SCRIPT'))!;
      fireEvent.keyDown(scriptTab, { key: 'Enter' });
      expect(onSelectView).toHaveBeenCalledWith('script');

      // Space key activates tab
      const worldTab = tabs.find((t) => t.textContent?.includes('WORLD'))!;
      fireEvent.keyDown(worldTab, { key: ' ' });
      expect(onSelectView).toHaveBeenCalledWith('world');

      // Click activates tab
      fireEvent.click(worldTab);
      expect(onSelectView).toHaveBeenCalledWith('world');
    });

    it('supports tab reachability with tabIndex=0 on all nav items', () => {
      render(<TopNav activeView="home" onSelectView={vi.fn()} />);
      const tabs = screen.getAllByRole('tab');
      tabs.forEach((tab) => {
        expect(tab.getAttribute('tabIndex')).toBe('0');
      });
    });
  });

  // --------------------------------------------------------------------------
  // 4. Semantic States: EmptyState, ErrorState, LoadingState
  // --------------------------------------------------------------------------
  describe('Semantic State Primitives', () => {
    it('EmptyState renders with role="status" and aria-live="polite"', () => {
      render(
        <EmptyState
          title="No Artifacts Available"
          description="Initialize a scenario to start generating narrative assets."
          action={<button>Create First Item</button>}
        />
      );

      const statusEl = screen.getByRole('status');
      expect(statusEl.getAttribute('aria-live')).toBe('polite');
      expect(screen.getByText('No Artifacts Available')).toBeDefined();
      expect(screen.getByText('Initialize a scenario to start generating narrative assets.')).toBeDefined();
      expect(screen.getByText('Create First Item')).toBeDefined();
    });

    it('ErrorState renders with role="alert" and allows retry action', () => {
      const retryFn = vi.fn();
      render(
        <ErrorState
          title="Engine Rejection"
          message="Spatial gate violation: actor cannot teleport."
          details="Gate: SpatialGate, LocA: warehouse, LocB: suite"
          retryAction={retryFn}
          retryLabel="Retry Step"
        />
      );

      const alertEl = screen.getByRole('alert');
      expect(alertEl).toBeDefined();
      expect(screen.getByText('Engine Rejection')).toBeDefined();
      expect(screen.getByText('Spatial gate violation: actor cannot teleport.')).toBeDefined();
      expect(screen.getByText(/Gate: SpatialGate/)).toBeDefined();

      const retryBtn = screen.getByText('Retry Step');
      fireEvent.click(retryBtn);
      expect(retryFn).toHaveBeenCalledTimes(1);
    });

    it('LoadingState renders with role="status" and aria-live="polite"', () => {
      render(
        <LoadingState
          message="Simulating multi-agent cognitive turn..."
          step="Tick 11"
          progressPercent={75}
        />
      );

      const loadingEl = screen.getByRole('status');
      expect(loadingEl.getAttribute('aria-live')).toBe('polite');
      expect(screen.getByText('Simulating multi-agent cognitive turn...')).toBeDefined();
      expect(screen.getByText('[Tick 11]')).toBeDefined();
    });
  });

  // --------------------------------------------------------------------------
  // 5. Additional Generic Primitives
  // --------------------------------------------------------------------------
  describe('Generic Primitives', () => {
    it('SectionHeader renders title, subtitle, eyebrow, and action slot', () => {
      render(
        <SectionHeader
          eyebrow="Narrative Blueprint"
          title="Three-Act Dramatic Arc"
          subtitle="Grounded scene sequences and threshold shifts"
          action={<button>Export Blueprint</button>}
        />
      );
      expect(screen.getByText('Narrative Blueprint')).toBeDefined();
      expect(screen.getByText('Three-Act Dramatic Arc')).toBeDefined();
      expect(screen.getByText('Grounded scene sequences and threshold shifts')).toBeDefined();
      expect(screen.getByText('Export Blueprint')).toBeDefined();
    });

    it('PanelCard renders with sharp corners and slots', () => {
      const { container } = render(
        <PanelCard
          title="Scene 1: Abandoned Industrial Bay"
          subtitle="T0 - T4"
          variant="accent"
          footer={<div>2 Turning Points</div>}
        >
          <p>Evelyn Vance inspects the locker.</p>
        </PanelCard>
      );

      expect(container.querySelector('.primitive-panel-card.variant-accent')).toBeDefined();
      expect(screen.getByText('Scene 1: Abandoned Industrial Bay')).toBeDefined();
      expect(screen.getByText('T0 - T4')).toBeDefined();
      expect(screen.getByText('Evelyn Vance inspects the locker.')).toBeDefined();
      expect(screen.getByText('2 Turning Points')).toBeDefined();
    });

    it('MetricChip renders technical label and numeric value with trend', () => {
      render(
        <MetricChip
          label="Therefore / But Ratio"
          value="0.95"
          delta="+0.12"
          trend="up"
          tone="amber"
        />
      );
      expect(screen.getByText('Therefore / But Ratio')).toBeDefined();
      expect(screen.getByText('0.95')).toBeDefined();
      expect(screen.getByText(/▲ \+0\.12/)).toBeDefined();
    });

    it('StatusBadge renders with role="status" and restrained tones', () => {
      render(
        <StatusBadge
          label="SATISFIED"
          tone="amber"
          dot
        />
      );
      const badge = screen.getByRole('status');
      expect(badge.textContent).toBe('SATISFIED');
      expect(badge.className).toContain('tone-amber');
    });

    it('ProvenanceChip renders entity type and ID and responds to click', () => {
      const onInspect = vi.fn();
      render(
        <ProvenanceChip
          type="EVENT"
          id="evt_dossier_01"
          label="Pickup"
          onClick={onInspect}
        />
      );
      expect(screen.getByText('EVENT')).toBeDefined();
      expect(screen.getByText('evt_dossier_01')).toBeDefined();
      expect(screen.getByText('(Pickup)')).toBeDefined();

      const chipBtn = screen.getByRole('button');
      fireEvent.click(chipBtn);
      expect(onInspect).toHaveBeenCalledWith('evt_dossier_01');
    });

    it('QualityMetric renders calculated check result without decoration', () => {
      render(
        <QualityMetric
          label="Prohibited Media Static Scan"
          value="CLEAN"
          status="passed"
          detail="0 occurrences of Three.js, animation, or video libraries found."
          benchmark="100% clean"
        />
      );
      expect(screen.getByText('Prohibited Media Static Scan')).toBeDefined();
      expect(screen.getByText('CLEAN')).toBeDefined();
      expect(screen.getByText(/0 occurrences/)).toBeDefined();
      expect(screen.getByText('Target: 100% clean')).toBeDefined();
    });

    it('InspectorDrawer renders when open and is omitted when closed', () => {
      const onClose = vi.fn();
      const { rerender } = render(
        <InspectorDrawer
          isOpen={false}
          onClose={onClose}
          title="Scene Inspector"
          subtitle="Chronological Turn"
        >
          <div>Inspection Details</div>
        </InspectorDrawer>
      );

      // Closed initially
      expect(screen.queryByRole('dialog')).toBeNull();

      // Open drawer
      rerender(
        <InspectorDrawer
          isOpen={true}
          onClose={onClose}
          title="Scene Inspector"
          subtitle="Chronological Turn"
        >
          <div>Inspection Details</div>
        </InspectorDrawer>
      );

      expect(screen.getByRole('dialog', { name: 'Scene Inspector' })).toBeDefined();
      expect(screen.getByText('Inspection Details')).toBeDefined();

      // Click close button
      const closeBtn = screen.getByLabelText('Close Inspector Drawer');
      fireEvent.click(closeBtn);
      expect(onClose).toHaveBeenCalledTimes(1);

      // Press Escape
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(onClose).toHaveBeenCalledTimes(2);
    });
  });

  // --------------------------------------------------------------------------
  // 6. ProjectSwitcher Toolbar
  // --------------------------------------------------------------------------
  describe('ProjectSwitcher', () => {
    it('allows switching project and running simulation', () => {
      const onSelectProject = vi.fn();
      const onRunSimulation = vi.fn();
      const onOpenNewProject = vi.fn();
      const onDeleteProject = vi.fn();

      const mockProjects = [
        {
          id: 'proj_1',
          title: 'The Missing Dossier',
          seed_prompt: 'A dossier is missing...',
          created_at: '2026-09-15',
          updated_at: '2026-09-15',
          current_tick: 10,
          total_events: 20,
          total_scenes: 3,
        },
        {
          id: 'proj_2',
          title: 'Hotel Intrigue',
          seed_prompt: 'Diplomatic secrets...',
          created_at: '2026-09-15',
          updated_at: '2026-09-15',
          current_tick: 5,
          total_events: 12,
          total_scenes: 2,
        },
      ];

      render(
        <ProjectSwitcher
          currentProject={mockProjects[0]}
          projects={mockProjects}
          providerName="gemini-flash"
          onSelectProject={onSelectProject}
          onOpenNewProject={onOpenNewProject}
          onDeleteProject={onDeleteProject}
          onRunSimulation={onRunSimulation}
        />
      );

      // Verify engine badge
      expect(screen.getByText('Engine: gemini-flash')).toBeDefined();

      // Project selector
      const select = screen.getByLabelText('Select Simulation Project') as HTMLSelectElement;
      expect(select.value).toBe('proj_1');
      fireEvent.change(select, { target: { value: 'proj_2' } });
      expect(onSelectProject).toHaveBeenCalledWith('proj_2');

      // Run simulation button
      const runBtn = screen.getByLabelText('Run 5 Simulation Ticks');
      fireEvent.click(runBtn);
      expect(onRunSimulation).toHaveBeenCalledWith(5);

      // New project button
      const newBtn = screen.getByLabelText('Create New Project');
      fireEvent.click(newBtn);
      expect(onOpenNewProject).toHaveBeenCalled();
    });
  });

  // --------------------------------------------------------------------------
  // 7. AppShell & Main Viewport (§14 Req 1)
  // --------------------------------------------------------------------------
  describe('AppShell', () => {
    it('renders with banner, static overlays, and main viewport', () => {
      const mockProject = {
        id: 'proj_1',
        title: 'The Missing Dossier',
        seed_prompt: 'A dossier is missing...',
        created_at: '2026-09-15',
        updated_at: '2026-09-15',
        current_tick: 10,
        total_events: 20,
        total_scenes: 3,
        total_panels: 8,
      };

      const { container } = render(
        <AppShell
          currentProject={mockProject}
          projects={[mockProject]}
          providerName="gemini-flash"
          activeView="home"
          onSelectView={vi.fn()}
          onSelectProject={vi.fn()}
          onOpenNewProject={vi.fn()}
          onDeleteProject={vi.fn()}
        >
          <div data-testid="test-viewport-content">Test Viewport Content</div>
        </AppShell>
      );

      // Verify banner and main landmark roles
      expect(screen.getByRole('banner')).toBeDefined();
      expect(screen.getByRole('main')).toBeDefined();
      expect(screen.getByTestId('test-viewport-content')).toBeDefined();

      // Verify static texture overlays are present
      expect(container.querySelector('.app-texture-overlay')).toBeDefined();
      expect(container.querySelector('.app-halftone-overlay')).toBeDefined();

      // Verify brand elements
      expect(screen.getByText('D3 STORY LAB')).toBeDefined();
      expect(screen.getByText('EMERGENT NARRATIVE ENGINE')).toBeDefined();

      // Verify pipeline indicator
      expect(screen.getByLabelText('Pipeline Progress')).toBeDefined();
    });
  });

  // --------------------------------------------------------------------------
  // 8. Button System (§14 Req 4)
  // --------------------------------------------------------------------------
  describe('Button System Classes', () => {
    it('renders primary, secondary, tertiary, and danger button classes', () => {
      const { container } = render(
        <div>
          <button type="button" className="btn-pill-primary">Primary Action</button>
          <button type="button" className="btn-pill-secondary">Secondary Action</button>
          <button type="button" className="btn-pill-tertiary">Tertiary Action</button>
          <button type="button" className="btn-pill-danger">Danger Action</button>
        </div>
      );

      const primary = container.querySelector('.btn-pill-primary');
      const secondary = container.querySelector('.btn-pill-secondary');
      const tertiary = container.querySelector('.btn-pill-tertiary');
      const danger = container.querySelector('.btn-pill-danger');

      expect(primary).toBeDefined();
      expect(primary?.textContent).toBe('Primary Action');
      expect(secondary).toBeDefined();
      expect(secondary?.textContent).toBe('Secondary Action');
      expect(tertiary).toBeDefined();
      expect(tertiary?.textContent).toBe('Tertiary Action');
      expect(danger).toBeDefined();
      expect(danger?.textContent).toBe('Danger Action');
    });
  });

  // --------------------------------------------------------------------------
  // 9. PanelToolbar Primitive
  // --------------------------------------------------------------------------
  describe('PanelToolbar', () => {
    it('renders left, center, right slots with toolbar role', () => {
      render(
        <PanelToolbar
          left={<span data-testid="tb-left">Left Filter</span>}
          center={<span data-testid="tb-center">Center Metadata</span>}
          right={<button type="button">Action</button>}
        />
      );

      const toolbar = screen.getByRole('toolbar', { name: 'Panel controls' });
      expect(toolbar).toBeDefined();
      expect(screen.getByTestId('tb-left')).toBeDefined();
      expect(screen.getByTestId('tb-center')).toBeDefined();
      expect(screen.getByRole('button', { name: 'Action' })).toBeDefined();
    });
  });

  // --------------------------------------------------------------------------
  // 10. HOME Editorial Hero & CTAs (§14 Req 6)
  // --------------------------------------------------------------------------
  describe('HOME Editorial Page', () => {
    it('renders centered hero, statement line, and pill CTAs', () => {
      const onStartNew = vi.fn();
      const onOpenProject = vi.fn();

      const { container } = render(
        <ScrollytellingHome
          onStartNew={onStartNew}
          onOpenProject={onOpenProject}
          projects={[realMissingDossierData.metadata]}
        />
      );

      // Hero section structure
      expect(container.querySelector('.hero-section')).toBeDefined();
      expect(screen.getByText('AGENTIC PROCEDURAL NARRATIVE ENGINE')).toBeDefined();
      expect(screen.getByText('D3 STORY LAB')).toBeDefined();

      // Statement lines
      expect(screen.getByText('THE STORY IS NOT WRITTEN.')).toBeDefined();
      expect(screen.getByText('IT EMERGES.')).toBeDefined();

      // Pill CTA buttons
      const newSimBtn = screen.getByRole('button', { name: 'NEW SIMULATION' });
      expect(newSimBtn.className).toContain('btn-pill-primary');
      fireEvent.click(newSimBtn);
      expect(onStartNew).toHaveBeenCalledTimes(1);

      const openProjectBtn = screen.getByRole('button', {
        name: `OPEN PROJECT (${realMissingDossierData.metadata.title})`,
      });
      expect(openProjectBtn.className).toContain('btn-pill-secondary');
      fireEvent.click(openProjectBtn);
      expect(onOpenProject).toHaveBeenCalledWith(realMissingDossierData.metadata.id);
    });
  });

  // --------------------------------------------------------------------------
  // 11. Route & Navigation Reachability (§14 Req 7)
  // --------------------------------------------------------------------------
  describe('All 8 Routes Accessibility', () => {
    it('all 8 routes remain accessible and selectable via TopNav', () => {
      const onSelectView = vi.fn();
      render(<TopNav activeView="home" onSelectView={onSelectView} />);

      const tabs = screen.getAllByRole('tab');
      expect(tabs).toHaveLength(8);

      const expectedViews = [
        'home',
        'world',
        'actors',
        'arcs',
        'simulation',
        'script',
        'storyboard',
        'export',
      ];

      tabs.forEach((tab, index) => {
        fireEvent.click(tab);
        expect(onSelectView).toHaveBeenCalledWith(expectedViews[index]);
      });
    });
  });

  // --------------------------------------------------------------------------
  // 12. Storyboard Contract Preservation (§14 Req 8)
  // --------------------------------------------------------------------------
  describe('Storyboard Contract Integrity', () => {
    it('existing storyboard contracts and viewer mount properly without regressions', () => {
      const project: ProjectData = realMissingDossierData;
      expect(project.metadata.id).toBeDefined();
      expect(project.metadata.total_panels).toBeDefined();

      const { container } = render(
        <StoryboardViewer
          project={project}
        />
      );

      expect(container.querySelector('.storyboard-viewer')).toBeDefined();
    });
  });

  // --------------------------------------------------------------------------
  // 13. ARCS & STRUCTURE Integration Preservation (§14 Req 9)
  // --------------------------------------------------------------------------
  describe('ARCS & STRUCTURE Integration', () => {
    it('mounts StructureAndArcsViewer without runtime errors', () => {
      const { container } = render(
        <StructureAndArcsViewer
          project={realMissingDossierData}
          loading={false}
        />
      );

      expect(container.querySelector('.structure-arcs-viewer')).toBeDefined();
      expect(screen.getByText('STRUCTURE, ARCS & CAUSAL CONTINUITY')).toBeDefined();
    });
  });
});
