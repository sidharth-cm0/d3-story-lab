import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import { ScrollytellingHome } from '../components/ScrollytellingHome';
import { WorldInspector } from '../components/WorldInspector';
import { CharacterCards } from '../components/CharacterCards';
import { StructureAndArcsViewer } from '../components/StructureAndArcsViewer';
import { SimulationTicker } from '../components/SimulationTicker';
import { ScreenplayViewer } from '../components/ScreenplayViewer';
import { StoryboardViewer } from '../components/StoryboardViewer';
import { ExportViewer } from '../components/ExportViewer';
import { ProjectData } from '../types';

import realMissingDossierDataRaw from '../../../backend/data/projects/world_init_4bef81.json';

const realMissingDossierData = realMissingDossierDataRaw as unknown as ProjectData;

describe('Pre-Phase-7 Live UI Integration & Tab Acceptance: The Missing Dossier (T10)', () => {
  it('verifies selected project identity and character preservation', () => {
    expect(realMissingDossierData.metadata.id).toBe('world_init_4bef81');
    expect(realMissingDossierData.metadata.title).toBe('The Missing Dossier');
    expect(realMissingDossierData.metadata.current_tick).toBeGreaterThanOrEqual(10);

    const characterNames = Object.values(realMissingDossierData.world.characters).map((c) => c.name);
    expect(characterNames).toContain('Vincent Cross');
    expect(characterNames).toContain('Evelyn Vance');
  });

  it('TAB 1: HOME renders without blank screen', () => {
    const { container } = render(
      <ScrollytellingHome
        projects={[realMissingDossierData.metadata]}
        onStartNew={vi.fn()}
        onOpenProject={vi.fn()}
      />
    );
    expect(container.querySelector('.scrolly-container')).toBeDefined();
    expect(screen.getByText('D3 STORY LAB')).toBeDefined();
    expect(screen.getAllByText('The Missing Dossier').length).toBeGreaterThanOrEqual(1);
  });

  it('TAB 2: WORLD renders world locations and objects without blank screen', () => {
    const { container } = render(<WorldInspector world={realMissingDossierData.world} />);
    expect(container.querySelector('.world-inspector-pane')).toBeDefined();
    expect(screen.getByText('SANDBOX TOPOLOGY')).toBeDefined();
    expect(screen.getAllByText(/Abandoned Industrial Bay/).length).toBeGreaterThanOrEqual(1);
  });

  it('TAB 3: ACTORS renders Vincent Cross and Evelyn Vance cards without blank screen', () => {
    const { container } = render(<CharacterCards world={realMissingDossierData.world} />);
    expect(container.querySelector('.character-cards')).toBeDefined();
    expect(screen.getByText('Vincent Cross')).toBeDefined();
    expect(screen.getByText('Evelyn Vance')).toBeDefined();
  });

  it('TAB 4: ARCS & STRUCTURE renders Blueprint, Arcs, and Causal Continuity without blank screen', () => {
    const { container } = render(
      <StructureAndArcsViewer
        project={realMissingDossierData}
        loading={false}
      />
    );
    expect(container.querySelector('.structure-arcs-view')).toBeDefined();
    expect(screen.getByText('STRUCTURE, ARCS & CAUSAL CONTINUITY')).toBeDefined();

    // 1. Blueprint Subtab
    expect(screen.getByText('PRIMARY STRUCTURE')).toBeDefined();
    expect(screen.getByText('THREE ACT')).toBeDefined();
    expect(screen.getByText(/Will the truth be secured before the exit is permanently compromised/)).toBeDefined();

    // 2. Character Arcs Subtab (Regression test for string delta toFixed crash)
    const arcsBtn = screen.getByText(/CHARACTER ARCS/);
    fireEvent.click(arcsBtn);
    expect(screen.getAllByText('Vincent Cross').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Evelyn Vance').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('RELATIONSHIP AFFINITY DELTAS')).toBeDefined();
    expect(screen.getByText('Affinity: +0.4, Trust: +0.5')).toBeDefined();

    // 3. Causal Continuity Subtab
    const causalBtn = screen.getByText('CAUSAL CONTINUITY');
    fireEvent.click(causalBtn);
    expect(screen.getByText('CAUSAL CONTINUITY SCORE')).toBeDefined();
    expect(screen.getAllByText(/THEREFORE \/ BUT/).length).toBeGreaterThanOrEqual(1);
  });

  it('TAB 5: SIMULATION renders ticker and events without blank screen', () => {
    const events = Object.values(realMissingDossierData.world.events || {}).sort(
      (a, b) => a.tick - b.tick || a.id.localeCompare(b.id)
    );
    const { container } = render(
      <SimulationTicker
        world={realMissingDossierData.world}
        events={events}
        onStep={vi.fn()}
        onRun={vi.fn()}
        loading={false}
      />
    );
    expect(container.querySelector('.cinematic-sim-view')).toBeDefined();
    expect(screen.getAllByText(/T\d+/).length).toBeGreaterThanOrEqual(1);
  });

  it('TAB 6: SCRIPT renders screenplay viewer without blank screen', () => {
    const { container } = render(
      <ScreenplayViewer
        project={realMissingDossierData}
        onGenerate={vi.fn()}
        loading={false}
      />
    );
    expect(container.querySelector('.screenplay-viewer')).toBeDefined();
    expect(screen.getAllByText('SCREENPLAY').length).toBeGreaterThanOrEqual(1);
  });

  it('TAB 7: STORYBOARD renders shot plan and frames without blank screen', () => {
    const { container } = render(
      <StoryboardViewer
        project={realMissingDossierData}
        loading={false}
      />
    );
    expect(container.querySelector('.cinematic-storyboard-pane')).toBeDefined();
    expect(screen.getByText('STORYBOARD')).toBeDefined();
  });

  it('TAB 8: EXPORT renders production export package without blank screen', () => {
    const { container } = render(<ExportViewer project={realMissingDossierData} />);
    expect(container.querySelector('.cinematic-export-pane')).toBeDefined();
    expect(screen.getByText('EXPORT PRODUCTION BUNDLE')).toBeDefined();
    expect(screen.getByText('Fountain Screenplay')).toBeDefined();
  });
});
