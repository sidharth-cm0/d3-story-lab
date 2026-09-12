import React from 'react';
import { ProjectMetadata, ActiveView } from '../types';

interface HeaderProps {
  currentProject: ProjectMetadata | null;
  projects: ProjectMetadata[];
  providerName: string;
  activeView?: ActiveView;
  onSelectView?: (view: ActiveView) => void;
  onSelectProject: (id: string) => void;
  onOpenNewProject: () => void;
  onDeleteProject: (id: string) => void;
  onRunSimulation?: (ticks: number) => void;
  loading?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentProject,
  projects,
  providerName,
  activeView = 'home',
  onSelectView,
  onSelectProject,
  onOpenNewProject,
  onDeleteProject,
  onRunSimulation,
  loading = false,
}) => {
  const navItems: { key: ActiveView; label: string }[] = [
    { key: 'home', label: 'HOME' },
    { key: 'world', label: 'WORLD' },
    { key: 'actors', label: 'ACTORS' },
    { key: 'simulation', label: 'SIMULATION' },
    { key: 'script', label: 'SCRIPT' },
    { key: 'storyboard', label: 'STORYBOARD' },
    { key: 'export', label: 'EXPORT' },
  ];


  return (
    <header className="app-header">
      <div className="brand-section" onClick={() => onSelectView?.('home')} style={{ cursor: 'pointer' }}>
        <span className="brand-logo" aria-label="D3 Story Lab icon">❖</span>
        <div>
          <h1 className="brand-title">D3 STORY LAB</h1>
          <div className="brand-subtitle">EMERGENT NARRATIVE ENGINE</div>
        </div>
      </div>

      {/* Center Minimal Navigation */}
      {onSelectView && (
        <nav className="header-nav" aria-label="Main Navigation">
          {navItems.map((item) => (
            <button
              key={item.key}
              className={`nav-link-btn ${activeView === item.key ? 'active' : ''}`}
              onClick={() => onSelectView(item.key)}
            >
              {item.label}
              {activeView === item.key && <span className="nav-link-glow" />}
            </button>
          ))}
        </nav>
      )}

      {/* Right Controls */}
      <div className="header-controls">
        <span className="badge badge-provider">Engine: {providerName}</span>

        {projects.length > 0 && (
          <select
            className="form-select project-select"
            value={currentProject?.id || ''}
            onChange={(e) => onSelectProject(e.target.value)}
            aria-label="Select Simulation Project"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title} (T{p.current_tick})
              </option>
            ))}
          </select>
        )}

        {currentProject && onRunSimulation && (
          <button
            className="btn-cinematic-run"
            onClick={() => onRunSimulation(5)}
            disabled={loading}
            title="Run 5 Simulation Ticks"
          >
            {loading ? '...' : '▶ RUN'}
          </button>
        )}

        {currentProject && (
          <button
            className="btn-cinematic-danger"
            onClick={() => {
              if (confirm(`Delete project "${currentProject.title}"?`)) {
                onDeleteProject(currentProject.id);
              }
            }}
            title="Delete Project"
          >
            DEL
          </button>
        )}

        <button className="btn-cinematic-primary" onClick={onOpenNewProject}>
          + NEW
        </button>
      </div>
    </header>
  );
};
