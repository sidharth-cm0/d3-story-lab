import React, { useState, useEffect, useCallback } from 'react';
import { ProjectMetadata, ProjectData, Event, ActiveView, StoryInputType } from './types';
import * as api from './api';
import { AppShell } from './components/shell';
import { SpotlightCursor } from './components/SpotlightCursor';
import { ScrollytellingHome } from './components/ScrollytellingHome';
import { NewProjectModal } from './components/NewProjectModal';
import { CharacterCards } from './components/CharacterCards';
import { WorldInspector } from './components/WorldInspector';
import { SimulationTicker } from './components/SimulationTicker';
import { ScreenplayViewer } from './components/ScreenplayViewer';
import { StoryboardViewer } from './components/StoryboardViewer';
import { ExportViewer } from './components/ExportViewer';
import { StructureAndArcsViewer } from './components/StructureAndArcsViewer';

export const App: React.FC = () => {
  const [projects, setProjects] = useState<ProjectMetadata[]>([]);
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(null);
  const [projectData, setProjectData] = useState<ProjectData | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [providerName, setProviderName] = useState<string>('mock');
  const [activeView, setActiveView] = useState<ActiveView>('home');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load initial engine health & project list
  useEffect(() => {
    api.fetchHealth()
      .then((h) => setProviderName(h.provider))
      .catch(() => setProviderName('mock'));

    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const list = await api.fetchProjects();
      setProjects(list);
      if (list.length > 0 && !currentProjectId) {
        setCurrentProjectId(list[0].id);
      }
    } catch (err) {
      console.error('Failed to load projects', err);
    }
  };

  const loadCurrentProject = useCallback(async (id: string) => {
    try {
      const data = await api.fetchProject(id);
      setProjectData(data);
      const evts = Object.values(data.world.events || {}).sort(
        (a, b) => a.tick - b.tick || a.id.localeCompare(b.id)
      );
      setEvents(evts);
    } catch (err) {
      console.error('Failed to load project details', err);
    }
  }, []);

  useEffect(() => {
    if (currentProjectId) {
      loadCurrentProject(currentProjectId);
    }
  }, [currentProjectId, loadCurrentProject]);

  const [diversityReport, setDiversityReport] = useState<any | null>(null);
  const [showDiversityModal, setShowDiversityModal] = useState(false);

  const handleCreateProject = async (
    seedPrompt: string,
    title?: string,
    inputType?: StoryInputType,
    targetDuration?: number,
    structureMode?: string,
    structureType?: string,
    secondaryStructure?: string,
    presentationStrategy?: string,
    seed?: number | string,
    lifecycleMode?: string
  ) => {
    const meta = await api.createProject(
      seedPrompt,
      title,
      inputType || 'beginning',
      targetDuration || 20,
      structureMode || 'AUTO',
      structureType,
      secondaryStructure,
      presentationStrategy || 'CHRONOLOGICAL',
      seed,
      lifecycleMode
    );
    await loadProjects();
    setCurrentProjectId(meta.id);
    setActiveView('arcs');
  };

  const handleReplay = async () => {
    if (!currentProjectId) return;
    setLoading(true);
    try {
      const replayed = await api.replaySimulation(currentProjectId);
      await loadProjects();
      setCurrentProjectId(replayed.metadata.id);
      await loadCurrentProject(replayed.metadata.id);
    } catch (err) {
      console.error('Replay error', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAlternativeRun = async () => {
    if (!currentProjectId) return;
    setLoading(true);
    try {
      const altMeta = await api.alternativeRun(currentProjectId);
      await loadProjects();
      setCurrentProjectId(altMeta.id);
      await loadCurrentProject(altMeta.id);
    } catch (err) {
      console.error('Alternative run error', err);
    } finally {
      setLoading(false);
    }
  };

  const handleShowDiversity = async () => {
    try {
      const rep = await api.fetchDiversityReport();
      setDiversityReport(rep);
      setShowDiversityModal(true);
    } catch (err) {
      console.error('Diversity report error', err);
    }
  };

  const handleDeleteProject = async (id: string) => {
    await api.deleteProject(id);
    const updated = projects.filter((p) => p.id !== id);
    setProjects(updated);
    if (updated.length > 0) {
      setCurrentProjectId(updated[0].id);
    } else {
      setCurrentProjectId(null);
      setProjectData(null);
      setEvents([]);
      setActiveView('home');
    }
  };

  const handleStep = async (ticks: number) => {
    if (!currentProjectId) return;
    setLoading(true);
    try {
      await api.stepSimulation(currentProjectId, ticks);
      await loadCurrentProject(currentProjectId);
    } catch (err) {
      console.error('Step error', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async (numTicks: number) => {
    if (!currentProjectId) return;
    setLoading(true);
    try {
      await api.runSimulation(currentProjectId, numTicks);
      await loadCurrentProject(currentProjectId);
    } catch (err) {
      console.error('Run error', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateScreenplay = async () => {
    if (!currentProjectId) return;
    setLoading(true);
    try {
      await api.generateScreenplay(currentProjectId);
      await loadCurrentProject(currentProjectId);
    } catch (err) {
      console.error('Generate screenplay error', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectView = useCallback((view: ActiveView) => {
    if (view === activeView) return;
    if (typeof document !== 'undefined' && 'startViewTransition' in document) {
      (document as any).startViewTransition(() => {
        setActiveView(view);
      });
    } else {
      setActiveView(view);
    }
  }, [activeView]);

  const currentMeta = projects.find((p) => p.id === currentProjectId) || null;

  return (
    <AppShell
      currentProject={currentMeta}
      projects={projects}
      providerName={providerName}
      activeView={activeView}
      onSelectView={handleSelectView}
      onSelectProject={(id) => {
        setCurrentProjectId(id);
        if (activeView === 'home') handleSelectView('simulation');
      }}
      onOpenNewProject={() => setIsModalOpen(true)}
      onDeleteProject={handleDeleteProject}
      onRunSimulation={handleRun}
      loading={loading}
    >
      <SpotlightCursor />

      {activeView === 'home' && (
        <ScrollytellingHome
          onStartNew={() => setIsModalOpen(true)}
          onOpenProject={(id) => {
            setCurrentProjectId(id);
            setActiveView('simulation');
          }}
          projects={projects}
        />
      )}

      {activeView === 'world' && (
        projectData ? (
          <div className="view-page-container">
            <WorldInspector world={projectData.world} />
          </div>
        ) : (
          <div className="empty-quiet" style={{ margin: 'auto' }}>
            NO ACTIVE SIMULATION. CREATE OR SELECT A PROJECT TO INSPECT WORLD TOPOLOGY.
          </div>
        )
      )}

      {activeView === 'actors' && (
        projectData ? (
          <div className="view-page-container">
            <CharacterCards
              world={projectData.world}
              projectId={currentProjectId || undefined}
              onCharacterCreated={() => {
                if (currentProjectId) loadCurrentProject(currentProjectId);
              }}
            />
          </div>
        ) : (
          <div className="empty-quiet" style={{ margin: 'auto' }}>
            NO ACTIVE SIMULATION. CREATE OR SELECT A PROJECT TO VIEW ACTORS.
          </div>
        )
      )}

      {activeView === 'arcs' && (
        <div className="view-page-container full-height">
          <StructureAndArcsViewer
            project={projectData}
            loading={loading}
          />
        </div>
      )}

      {activeView === 'simulation' && (
        projectData ? (
          <div className="view-page-container full-height">
            <SimulationTicker
              world={projectData.world}
              events={events}
              onStep={handleStep}
              onRun={handleRun}
              loading={loading}
              onReplay={handleReplay}
              onAlternativeRun={handleAlternativeRun}
              onShowDiversity={handleShowDiversity}
              metadata={currentMeta}
            />
          </div>
        ) : (
          <div className="empty-standby-screen">
            <span className="empty-logo">❖</span>
            <h2 className="empty-title">NO ACTIVE SIMULATION</h2>
            <p className="empty-desc">
              The sandbox requires a narrative premise or incident report before autonomous actors can be spawned.
            </p>
            <button className="btn-cinematic-primary" onClick={() => setIsModalOpen(true)}>
              START WITH A SPARK
            </button>
          </div>
        )
      )}

      {activeView === 'script' && (
        projectData ? (
          <div className="view-page-container full-height">
            <ScreenplayViewer
              project={projectData}
              onGenerate={handleGenerateScreenplay}
              loading={loading}
            />
          </div>
        ) : (
          <div className="empty-quiet" style={{ margin: 'auto' }}>
            NO ACTIVE PROJECT. SELECT A PROJECT TO TRANSCRIBE SCREENPLAY.
          </div>
        )
      )}

      {activeView === 'storyboard' && (
        projectData ? (
          <div className="view-page-container full-height">
            <StoryboardViewer
              project={projectData}
              loading={loading}
            />
          </div>
        ) : (
          <div className="empty-quiet" style={{ margin: 'auto' }}>
            NO ACTIVE PROJECT. SELECT A PROJECT TO PREPARE STORYBOARD FRAMES.
          </div>
        )
      )}

      {activeView === 'export' && (
        projectData ? (
          <div className="view-page-container full-height">
            <ExportViewer project={projectData} />
          </div>
        ) : (
          <div className="empty-quiet" style={{ margin: 'auto' }}>
            NO ACTIVE PROJECT. SELECT A PROJECT TO EXPORT PRODUCTION ARTIFACTS.
          </div>
        )
      )}

      <NewProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreate={handleCreateProject}
      />

      {showDiversityModal && diversityReport && (
        <div
          className="modal-overlay"
          onClick={() => setShowDiversityModal(false)}
          role="dialog"
          aria-modal="true"
        >
          <div className="modal-card cinematic-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '640px' }}>
            <div className="modal-header cinematic-modal-header">
              <div className="modal-header-text">
                <div className="modal-kicker">SIMULATION DIVERSITY & DETERMINISM AUDIT</div>
                <h2 className="modal-title">CROSS-SIMULATION ANALYSIS</h2>
                <p className="modal-subtitle">
                  Deterministic PRNG fingerprint verification proving premise isolation and absence of simulation lock-in.
                </p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowDiversityModal(false)}
              >
                ✕
              </button>
            </div>
            <div className="modal-body cinematic-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                <div className="stat-pill" style={{ flexDirection: 'column', alignItems: 'flex-start', padding: '12px' }}>
                  <span className="pill-lbl">TOTAL RUNS</span>
                  <strong className="pill-num" style={{ fontSize: '20px' }}>{diversityReport.total_simulations}</strong>
                </div>
                <div className="stat-pill" style={{ flexDirection: 'column', alignItems: 'flex-start', padding: '12px' }}>
                  <span className="pill-lbl">PREMISES</span>
                  <strong className="pill-num text-amber" style={{ fontSize: '20px' }}>{diversityReport.distinct_premises}</strong>
                </div>
                <div className="stat-pill" style={{ flexDirection: 'column', alignItems: 'flex-start', padding: '12px' }}>
                  <span className="pill-lbl">FINGERPRINT COLLISIONS</span>
                  <strong className="pill-num" style={{ fontSize: '20px', color: diversityReport.fingerprint_collision_count === 0 ? '#4ade80' : '#f87171' }}>
                    {diversityReport.fingerprint_collision_count}
                  </strong>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">GENRE DISTRIBUTION</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {Object.entries(diversityReport.genre_distribution || {}).map(([g, count]) => (
                    <span key={g} className="badge-object-dim" style={{ fontSize: '11px', padding: '4px 8px' }}>
                      {g}: <strong>{count as any}</strong>
                    </span>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">SOVEREIGN AGENTS IN PLAY ({diversityReport.unique_character_names?.length || 0})</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {diversityReport.unique_character_names?.map((name: string) => (
                    <span key={name} className="stat-pill" style={{ fontSize: '11px', padding: '2px 8px' }}>
                      {name}
                    </span>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">AUDIT VERDICT</label>
                <p style={{ color: 'var(--text-secondary)', fontSize: '12px', lineHeight: 1.5, background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '4px', borderLeft: '3px solid #f59e0b' }}>
                  {diversityReport.summary}
                </p>
              </div>
            </div>
            <div className="modal-actions cinematic-modal-footer">
              <button
                type="button"
                className="btn-cinematic-primary"
                onClick={() => setShowDiversityModal(false)}
              >
                CLOSE AUDIT
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
};
