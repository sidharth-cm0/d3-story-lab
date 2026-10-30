import React from 'react';
import { ProjectMetadata } from '../../types';

export interface ProjectSwitcherProps {
  currentProject: ProjectMetadata | null;
  projects: ProjectMetadata[];
  providerName: string;
  onSelectProject: (id: string) => void;
  onOpenNewProject: () => void;
  onDeleteProject: (id: string) => void;
  onRunSimulation?: (ticks: number) => void;
  loading?: boolean;
  className?: string;
}

export const ProjectSwitcher: React.FC<ProjectSwitcherProps> = ({
  currentProject,
  projects,
  providerName,
  onSelectProject,
  onOpenNewProject,
  onDeleteProject,
  onRunSimulation,
  loading = false,
  className = '',
}) => {
  return (
    <div className={`shell-project-switcher ${className}`} role="toolbar" aria-label="Project Controls">
      {/* Engine Status Badge */}
      <span className="badge badge-provider" role="status">
        Engine: {providerName}
      </span>

      {/* Project Selector */}
      {projects.length > 0 && (
        <div className="project-select-wrapper">
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
        </div>
      )}

      {/* Run 5 Ticks Button */}
      {currentProject && onRunSimulation && (
        <button
          type="button"
          className="btn-pill-secondary btn-cinematic-run"
          onClick={() => onRunSimulation(5)}
          disabled={loading}
          title="Run 5 Simulation Ticks"
          aria-label="Run 5 Simulation Ticks"
        >
          {loading ? '...' : '▶ RUN'}
        </button>
      )}

      {/* Delete Project Button */}
      {currentProject && (
        <button
          type="button"
          className="btn-pill-danger btn-cinematic-danger"
          onClick={() => {
            if (window.confirm(`Delete project "${currentProject.title}"?`)) {
              onDeleteProject(currentProject.id);
            }
          }}
          title="Delete Project"
          aria-label={`Delete project ${currentProject.title}`}
        >
          DEL
        </button>
      )}

      {/* New Project Button */}
      <button
        type="button"
        className="btn-pill-primary btn-cinematic-primary"
        onClick={onOpenNewProject}
        aria-label="Create New Project"
      >
        + NEW
      </button>
    </div>
  );
};
