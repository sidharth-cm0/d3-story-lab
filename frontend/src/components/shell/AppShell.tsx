import React from 'react';
import { ProjectMetadata, ActiveView } from '../../types';
import { TopNav } from './TopNav';
import { ProjectSwitcher } from './ProjectSwitcher';

export interface AppShellProps {
  currentProject: ProjectMetadata | null;
  projects: ProjectMetadata[];
  providerName: string;
  activeView: ActiveView;
  onSelectView: (view: ActiveView) => void;
  onSelectProject: (id: string) => void;
  onOpenNewProject: () => void;
  onDeleteProject: (id: string) => void;
  onRunSimulation?: (ticks: number) => void;
  loading?: boolean;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentProject,
  projects,
  providerName,
  activeView,
  onSelectView,
  onSelectProject,
  onOpenNewProject,
  onDeleteProject,
  onRunSimulation,
  loading = false,
  children,
}) => {
  return (
    <div className="workstation-container editorial-shell">
      {/* Static Visual Texture Overlays (Zero Animation / Static CSS-only) */}
      <div className="app-texture-overlay" aria-hidden="true" />
      <div className="app-halftone-overlay" aria-hidden="true" />

      {/* Top Header & Navigation */}
      <header className="app-header" role="banner">
        <div className="header-main-row">
          {/* Brand Identity */}
          <div
            className="brand-section"
            onClick={() => onSelectView('home')}
            role="button"
            tabIndex={0}
            aria-label="Go to Home"
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onSelectView('home');
              }
            }}
          >
            <span className="brand-logo" aria-label="D3 Story Lab icon">❖</span>
            <div>
              <h1 className="brand-title">D3 STORY LAB</h1>
              <div className="brand-subtitle">EMERGENT NARRATIVE ENGINE</div>
            </div>
          </div>

          {/* Center Forensic Navigation */}
          <TopNav activeView={activeView} onSelectView={onSelectView} />

          {/* Right Toolbar / Project Switcher */}
          <ProjectSwitcher
            currentProject={currentProject}
            projects={projects}
            providerName={providerName}
            onSelectProject={onSelectProject}
            onOpenNewProject={onOpenNewProject}
            onDeleteProject={onDeleteProject}
            onRunSimulation={onRunSimulation}
            loading={loading}
          />
        </div>

        {/* Pipeline Progress Indicator */}
        {currentProject && (
          <div className="header-pipeline-bar" aria-label="Pipeline Progress">
            <div className="pipeline-steps">
              <span className="pipeline-step complete">WORLD</span>
              <span className="pipeline-sep" aria-hidden="true">➔</span>
              <span
                className={`pipeline-step ${
                  currentProject.total_events > 0 || currentProject.current_tick > 0
                    ? 'complete'
                    : 'pending'
                }`}
              >
                SIMULATION {currentProject.current_tick > 0 ? `(T${currentProject.current_tick})` : ''}
              </span>
              <span className="pipeline-sep" aria-hidden="true">➔</span>
              <span
                className={`pipeline-step ${
                  currentProject.total_scenes > 0 ? 'complete' : 'pending'
                }`}
              >
                SCREENPLAY {currentProject.total_scenes > 0 ? `(${currentProject.total_scenes} SCENES)` : ''}
              </span>
              <span className="pipeline-sep" aria-hidden="true">➔</span>
              <span
                className={`pipeline-step ${
                  (currentProject.total_panels || 0) > 0 ? 'complete' : 'pending'
                }`}
              >
                SHOT PLAN
              </span>
              <span className="pipeline-sep" aria-hidden="true">➔</span>
              <span
                className={`pipeline-step ${
                  (currentProject.total_panels || 0) > 0 ? 'complete' : 'pending'
                }`}
              >
                STORYBOARD {(currentProject.total_panels || 0) > 0 ? `${currentProject.total_panels}/${currentProject.total_panels}` : '0/0'}
              </span>
              <span className="pipeline-sep" aria-hidden="true">➔</span>
              <span
                className={`pipeline-step ${
                  (currentProject.total_panels || 0) > 0 ? 'active' : 'pending'
                }`}
              >
                EXPORT READY
              </span>
            </div>
          </div>
        )}
      </header>

      {/* Main Dynamic Viewport */}
      <main className="main-viewport" role="main">
        {children}
      </main>
    </div>
  );
};
