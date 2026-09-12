import React, { useState, useEffect, useCallback } from 'react';
import { ProjectMetadata, ProjectData, Event, ActiveView, StoryInputType } from './types';
import * as api from './api';
import { Header } from './components/Header';
import { SpotlightCursor } from './components/SpotlightCursor';
import { ScrollytellingHome } from './components/ScrollytellingHome';
import { NewProjectModal } from './components/NewProjectModal';
import { CharacterCards } from './components/CharacterCards';
import { WorldInspector } from './components/WorldInspector';
import { SimulationTicker } from './components/SimulationTicker';
import { ScreenplayViewer } from './components/ScreenplayViewer';
import { StoryboardViewer } from './components/StoryboardViewer';
import { ExportViewer } from './components/ExportViewer';

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

  const handleCreateProject = async (
    seedPrompt: string,
    title?: string,
    inputType?: StoryInputType,
    targetDuration?: number
  ) => {
    const meta = await api.createProject(
      seedPrompt,
      title,
      inputType || 'beginning',
      targetDuration || 20
    );
    await loadProjects();
    setCurrentProjectId(meta.id);
    setActiveView('simulation');
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

  const currentMeta = projects.find((p) => p.id === currentProjectId) || null;

  return (
    <div className="workstation-container">
      <SpotlightCursor />

      <Header
        currentProject={currentMeta}
        projects={projects}
        providerName={providerName}
        activeView={activeView}
        onSelectView={setActiveView}
        onSelectProject={(id) => {
          setCurrentProjectId(id);
          if (activeView === 'home') setActiveView('simulation');
        }}
        onOpenNewProject={() => setIsModalOpen(true)}
        onDeleteProject={handleDeleteProject}
        onRunSimulation={handleRun}
        loading={loading}
      />

      {/* Main Dynamic Viewport */}
      <main className="main-viewport">
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
              <CharacterCards world={projectData.world} />
            </div>
          ) : (
            <div className="empty-quiet" style={{ margin: 'auto' }}>
              NO ACTIVE SIMULATION. CREATE OR SELECT A PROJECT TO VIEW ACTORS.
            </div>
          )
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
      </main>



      <NewProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreate={handleCreateProject}
      />
    </div>
  );
};
