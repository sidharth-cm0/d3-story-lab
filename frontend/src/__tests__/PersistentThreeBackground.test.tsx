import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useState } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

import { AppShell } from '../components/shell/AppShell';
import { PersistentGranularBackground } from '../components/shell/PersistentGranularBackground';
import { GranularThreeScene, motifToId } from '../components/granular/three/GranularThreeScene';
import { WorkspaceTransition } from '../components/motion/WorkspaceTransition';
import { viewToMotif } from '../components/granular/three/useGranularTransition';
import { setMockWebGLAvailable } from '../components/granular/three/webglDetector';
import { ProjectData, ActiveView } from '../types';

import realMissingDossierDataRaw from '../../../backend/data/projects/world_init_4bef81.json';

const realMissingDossierData = realMissingDossierDataRaw as unknown as ProjectData;

const mockProject2 = {
  ...realMissingDossierData.metadata,
  id: 'world_init_hotel_02',
  title: 'Hotel Intrigue',
};

const defaultShellProps = {
  providerName: 'gemini-flash',
  onOpenNewProject: vi.fn(),
  onDeleteProject: vi.fn(),
};

describe('Persistent Three.js Shell & Seamless Workspace Transitions (§21 Matrix)', () => {
  let originalMatchMedia: typeof window.matchMedia;

  beforeEach(() => {
    setMockWebGLAvailable(null);
    originalMatchMedia = window.matchMedia;
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
  });

  afterEach(() => {
    setMockWebGLAvailable(null);
    window.matchMedia = originalMatchMedia;
    vi.restoreAllMocks();
  });

  // --------------------------------------------------------------------------
  // 1. Exactly one canvas exists in DOM at AppShell level
  // --------------------------------------------------------------------------
  it('1. Exactly one persistent granular background container exists at AppShell level', () => {
    const { container } = render(
      <AppShell
        {...defaultShellProps}
        currentProject={realMissingDossierData.metadata}
        projects={[realMissingDossierData.metadata]}
        activeView="home"
        onSelectView={vi.fn()}
        onSelectProject={vi.fn()}
      >
        <div data-testid="workspace-content">Home Content</div>
      </AppShell>
    );

    const bgContainers = container.querySelectorAll('.app-persistent-granular-background');
    expect(bgContainers.length).toBe(1);

    const canvasWrappers = container.querySelectorAll('.granular-three-container');
    expect(canvasWrappers.length).toBe(1);

    // Canvas container must have pointer-events: none and proper z-index positioning
    const bgContainer = bgContainers[0] as HTMLElement;
    expect(bgContainer.style.pointerEvents).toBe('none');
    expect(bgContainer.style.zIndex).toBe('0');
  });

  // --------------------------------------------------------------------------
  // 2. Navigating HOME -> WORLD does not unmount canvas
  // --------------------------------------------------------------------------
  it('2. Navigating HOME -> WORLD does not unmount persistent canvas container', () => {
    function TestHarness() {
      const [activeView, setActiveView] = useState<ActiveView>('home');
      return (
        <AppShell
          {...defaultShellProps}
          currentProject={realMissingDossierData.metadata}
          projects={[realMissingDossierData.metadata]}
          activeView={activeView}
          onSelectView={setActiveView}
          onSelectProject={vi.fn()}
        >
          <div data-testid={`view-${activeView}`}>Active: {activeView}</div>
        </AppShell>
      );
    }

    const { container } = render(<TestHarness />);

    const initialBg = container.querySelector('.app-persistent-granular-background');
    const initialWrapper = container.querySelector('.granular-three-container');
    expect(initialBg).not.toBeNull();
    expect(initialWrapper).not.toBeNull();
    expect(screen.getByTestId('view-home')).toBeDefined();

    // Navigate to WORLD
    const worldTab = screen.getByRole('tab', { name: /WORLD/i });
    fireEvent.click(worldTab);

    // Canvas background element identity is preserved (no unmount/remount)
    const afterBg = container.querySelector('.app-persistent-granular-background');
    const afterWrapper = container.querySelector('.granular-three-container');
    expect(afterBg).toBe(initialBg);
    expect(afterWrapper).toBe(initialWrapper);
    expect(screen.getByTestId('view-world')).toBeDefined();
  });

  // --------------------------------------------------------------------------
  // 3. Cycling through all 8 tabs maintains single canvas and single background instance
  // --------------------------------------------------------------------------
  it('3. Cycling through all 8 tabs maintains single canvas and single background instance', () => {
    const views: ActiveView[] = [
      'home',
      'world',
      'actors',
      'arcs',
      'simulation',
      'script',
      'storyboard',
      'export',
    ];

    function AllTabsHarness() {
      const [activeView, setActiveView] = useState<ActiveView>('home');
      return (
        <div>
          <button data-testid="cycle-btn" onClick={() => {
            const nextIdx = (views.indexOf(activeView) + 1) % views.length;
            setActiveView(views[nextIdx]);
          }}>
            Cycle Tab
          </button>
          <AppShell
            {...defaultShellProps}
            currentProject={realMissingDossierData.metadata}
            projects={[realMissingDossierData.metadata]}
            activeView={activeView}
            onSelectView={setActiveView}
            onSelectProject={vi.fn()}
          >
            <div data-testid={`active-tab-${activeView}`}>{activeView.toUpperCase()}</div>
          </AppShell>
        </div>
      );
    }

    const { container } = render(<AllTabsHarness />);
    const persistentBgRef = container.querySelector('.app-persistent-granular-background');

    for (let i = 0; i < views.length; i++) {
      expect(screen.getByTestId(`active-tab-${views[i]}`)).toBeDefined();
      const currentBg = container.querySelector('.app-persistent-granular-background');
      expect(currentBg).toBe(persistentBgRef);

      const allBgs = container.querySelectorAll('.app-persistent-granular-background');
      expect(allBgs.length).toBe(1);

      fireEvent.click(screen.getByTestId('cycle-btn'));
    }
  });

  // --------------------------------------------------------------------------
  // 4. Motif updates when activeView changes
  // --------------------------------------------------------------------------
  it('4. viewToMotif correctly maps all 8 views to distinct granular motifs and topology IDs', () => {
    expect(viewToMotif('home')).toBe('hero');
    expect(viewToMotif('world')).toBe('world');
    expect(viewToMotif('actors')).toBe('actors');
    expect(viewToMotif('arcs')).toBe('arcs');
    expect(viewToMotif('simulation')).toBe('simulation');
    expect(viewToMotif('script')).toBe('script');
    expect(viewToMotif('storyboard')).toBe('storyboard');
    expect(viewToMotif('export')).toBe('export');

    // Shader topology mapping via motifToId
    expect(motifToId('hero')).toBe(0);
    expect(motifToId('world')).toBe(1);
    expect(motifToId('actors')).toBe(2);
    expect(motifToId('arcs')).toBe(3);
    expect(motifToId('simulation')).toBe(4);
    expect(motifToId('script')).toBe(5);
    expect(motifToId('storyboard')).toBe(6);
    expect(motifToId('export')).toBe(7);
  });

  // --------------------------------------------------------------------------
  // 5. Foreground controls remain clickable (pointer-events: auto)
  // --------------------------------------------------------------------------
  it('5. Foreground controls remain clickable while persistent background is non-blocking', () => {
    const onButtonClick = vi.fn();

    render(
      <AppShell
        {...defaultShellProps}
        currentProject={realMissingDossierData.metadata}
        projects={[realMissingDossierData.metadata]}
        activeView="home"
        onSelectView={vi.fn()}
        onSelectProject={vi.fn()}
      >
        <div className="workspace-pane">
          <button data-testid="interactive-cta" onClick={onButtonClick}>
            EXECUTE ACTION
          </button>
        </div>
      </AppShell>
    );

    const cta = screen.getByTestId('interactive-cta');
    expect(cta).toBeDefined();
    fireEvent.click(cta);
    expect(onButtonClick).toHaveBeenCalledTimes(1);

    // Canvas container must have pointerEvents: 'none'
    const canvasContainer = screen.getByTestId('persistent-granular-canvas');
    expect(canvasContainer.style.pointerEvents).toBe('none');
  });

  // --------------------------------------------------------------------------
  // 6. Reduced motion renders static state without morphing
  // --------------------------------------------------------------------------
  it('6. Reduced motion preference forces FALLBACK mode and disables WebGL morphing', () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
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
      <PersistentGranularBackground activeView="home" />
    );

    const canvasWrapper = container.querySelector('.granular-three-container');
    expect(canvasWrapper).not.toBeNull();
    expect(canvasWrapper?.getAttribute('data-fallback')).toBe('true');
  });

  // --------------------------------------------------------------------------
  // 7. Fallback mode works cleanly without throwing
  // --------------------------------------------------------------------------
  it('7. Fallback mode renders GranularNarrativeField without WebGL errors in headless/JSDOM', () => {
    const { container } = render(
      <PersistentGranularBackground activeView="script" />
    );

    // SVG fallback is rendered cleanly inside the persistent container
    const fallbackSvg = container.querySelector('.granular-narrative-field-wrapper');
    expect(fallbackSvg).not.toBeNull();
  });

  // --------------------------------------------------------------------------
  // 8. All 8 tabs still render without blank screens
  // --------------------------------------------------------------------------
  it('8. All 8 workspace views render valid content inside AppShell and WorkspaceTransition', () => {
    const tabConfigs: { view: ActiveView; testId: string; text: string }[] = [
      { view: 'home', testId: 'ws-view-home', text: 'HOME_PANE_CONTENT' },
      { view: 'world', testId: 'ws-view-world', text: 'WORLD_PANE_CONTENT' },
      { view: 'actors', testId: 'ws-view-actors', text: 'ACTORS_PANE_CONTENT' },
      { view: 'arcs', testId: 'ws-view-arcs', text: 'ARCS_PANE_CONTENT' },
      { view: 'simulation', testId: 'ws-view-simulation', text: 'SIMULATION_PANE_CONTENT' },
      { view: 'script', testId: 'ws-view-script', text: 'SCRIPT_PANE_CONTENT' },
      { view: 'storyboard', testId: 'ws-view-storyboard', text: 'STORYBOARD_PANE_CONTENT' },
      { view: 'export', testId: 'ws-view-export', text: 'EXPORT_PANE_CONTENT' },
    ];

    tabConfigs.forEach(({ view, testId, text }) => {
      const { unmount } = render(
        <AppShell
          {...defaultShellProps}
          currentProject={realMissingDossierData.metadata}
          projects={[realMissingDossierData.metadata]}
          activeView={view}
          onSelectView={vi.fn()}
          onSelectProject={vi.fn()}
        >
          <div data-testid={testId}>{text}</div>
        </AppShell>
      );

      expect(screen.getByTestId(testId)).toBeDefined();
      expect(screen.getByText(text)).toBeDefined();
      unmount();
    });
  });

  // --------------------------------------------------------------------------
  // 9. Project switching works without canvas unmounting
  // --------------------------------------------------------------------------
  it('9. Project switching updates project state without unmounting persistent background', () => {
    function ProjectSwitchHarness() {
      const [currentProject, setCurrentProject] = useState(realMissingDossierData.metadata);

      return (
        <div>
          <button
            data-testid="switch-proj-btn"
            onClick={() => setCurrentProject(mockProject2)}
          >
            Switch
          </button>
          <AppShell
            {...defaultShellProps}
            currentProject={currentProject}
            projects={[realMissingDossierData.metadata, mockProject2]}
            activeView="world"
            onSelectView={vi.fn()}
            onSelectProject={vi.fn()}
          >
            <div data-testid="project-title-display">{currentProject.title}</div>
          </AppShell>
        </div>
      );
    }

    const { container } = render(<ProjectSwitchHarness />);

    const bgBefore = container.querySelector('.app-persistent-granular-background');
    expect(screen.getByTestId('project-title-display').textContent).toBe('The Missing Dossier');

    // Switch project
    fireEvent.click(screen.getByTestId('switch-proj-btn'));

    expect(screen.getByTestId('project-title-display').textContent).toBe('Hotel Intrigue');
    const bgAfter = container.querySelector('.app-persistent-granular-background');
    expect(bgAfter).toBe(bgBefore);
  });

  // --------------------------------------------------------------------------
  // 10. WebGL does not mutate narrative state
  // --------------------------------------------------------------------------
  it('10. GranularThreeScene and background components treat narrative project data as strictly immutable', () => {
    const originalProjectJson = JSON.stringify(realMissingDossierData);

    const { container } = render(
      <AppShell
        {...defaultShellProps}
        currentProject={realMissingDossierData.metadata}
        projects={[realMissingDossierData.metadata]}
        activeView="simulation"
        onSelectView={vi.fn()}
        onSelectProject={vi.fn()}
      >
        <div data-testid="immutable-test">Tick: {realMissingDossierData.metadata.current_tick}</div>
      </AppShell>
    );

    expect(container).toBeDefined();

    // Narrative project state must remain 100% byte-for-byte identical
    const currentProjectJson = JSON.stringify(realMissingDossierData);
    expect(currentProjectJson).toBe(originalProjectJson);
  });

  // --------------------------------------------------------------------------
  // 11. Renderer cleanup occurs only when AppShell unmounts
  // --------------------------------------------------------------------------
  it('11. PersistentGranularBackground properly disposes Three.js resources on unmount', () => {
    // Test GranularThreeScene dispose directly
    const dummyCanvas = document.createElement('canvas');
    const mockGeomDispose = vi.fn();
    const mockMatDispose = vi.fn();
    const mockRendererDispose = vi.fn();
    const mockObserverDisconnect = vi.fn();

    const scene = Object.create(GranularThreeScene.prototype);
    scene.isDisposed = false;
    scene.animationFrameId = 1234;
    scene.visibilityHandler = vi.fn();
    scene.resizeObserver = { disconnect: mockObserverDisconnect };
    scene.geometry = { dispose: mockGeomDispose };
    scene.material = { dispose: mockMatDispose };
    scene.renderer = { dispose: mockRendererDispose, domElement: dummyCanvas };
    scene.scene = { remove: vi.fn() };
    scene.pointsMesh = {};

    GranularThreeScene.prototype.dispose.call(scene);
    expect(scene.isDisposed).toBe(true);
    expect(mockGeomDispose).toHaveBeenCalled();
    expect(mockMatDispose).toHaveBeenCalled();
    expect(mockRendererDispose).toHaveBeenCalled();
    expect(mockObserverDisconnect).toHaveBeenCalled();
    expect(scene.geometry).toBeNull();
    expect(scene.material).toBeNull();
  });

  // --------------------------------------------------------------------------
  // 12. No blank workspace during transitions (WorkspaceTransition renders children)
  // --------------------------------------------------------------------------
  it('12. WorkspaceTransition preserves and wraps view content without flash of blank content', () => {
    const { container } = render(
      <WorkspaceTransition viewKey="home">
        <div data-testid="workspace-node-home">Content Home</div>
      </WorkspaceTransition>
    );

    const wrapper = container.querySelector('.workspace-transition-container');
    expect(wrapper).not.toBeNull();
    expect(screen.getByTestId('workspace-node-home')).toBeDefined();
    expect(screen.getByText('Content Home')).toBeDefined();
  });
});
