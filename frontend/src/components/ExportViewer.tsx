import React, { useState } from 'react';
import { ProjectData } from '../types';
import { getExportUrl } from '../api';

interface ExportViewerProps {
  project: ProjectData;
}

export const ExportViewer: React.FC<ExportViewerProps> = ({ project }) => {
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  const hasScreenplay = Boolean(project.fountain_text || project.screenplay);
  const hasSynopsis = Boolean(project.synopsis || project.story_outline);
  const hasShotPlan = Boolean(project.shot_plan && project.shot_plan.panels.length > 0);

  const copyToClipboard = (text: string, section: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSection(section);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  return (
    <div className="cinematic-export-pane">
      <div className="pane-header">
        <div>
          <span className="pane-kicker">PRODUCTION ARTIFACT EXPORT CONSOLE</span>
          <h2 className="pane-title">EXPORT PRODUCTION BUNDLE</h2>
        </div>
      </div>

      <div className="export-grid-container">
        {/* 1. SCREENPLAY EXPORT */}
        <div className="export-card">
          <div className="export-card-header">
            <span className="export-tag">SCREENPLAY</span>
            <span className={`status-pill ${hasScreenplay ? 'status-ready' : 'status-pending'}`}>
              {hasScreenplay ? 'READY' : 'NOT GENERATED'}
            </span>
          </div>

          <h3 className="export-card-title">Fountain Screenplay</h3>
          <p className="export-card-desc">
            Industry standard .fountain screenplay with sluglines, action paragraphs, character cues, and dialogue.
          </p>

          <div className="export-actions-row">
            {hasScreenplay ? (
              <>
                <a
                  href={getExportUrl(project.metadata.id, 'screenplay')}
                  download
                  className="btn-cinematic-primary"
                  style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
                >
                  DOWNLOAD .FOUNTAIN
                </a>
                <button
                  className="btn-cinematic-secondary"
                  onClick={() => copyToClipboard(project.fountain_text || '', 'screenplay')}
                >
                  {copiedSection === 'screenplay' ? '✓ COPIED' : 'COPY SCRIPT'}
                </button>
              </>
            ) : (
              <span className="text-muted text-sm">Transcribe screenplay under SCRIPT tab first.</span>
            )}
          </div>
        </div>

        {/* 2. SYNOPSIS EXPORT */}
        <div className="export-card">
          <div className="export-card-header">
            <span className="export-tag">NARRATIVE</span>
            <span className={`status-pill ${hasSynopsis ? 'status-ready' : 'status-pending'}`}>
              {hasSynopsis ? 'READY' : 'NOT GENERATED'}
            </span>
          </div>

          <h3 className="export-card-title">Story Synopsis &amp; Arc</h3>
          <p className="export-card-desc">
            Complete three-tier synopsis including one-line logline, paragraph summary, 3-act beats, and full episode breakdown.
          </p>

          <div className="export-actions-row">
            {hasSynopsis ? (
              <a
                href={getExportUrl(project.metadata.id, 'synopsis')}
                download
                className="btn-cinematic-primary"
                style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
              >
                DOWNLOAD SYNOPSIS (.MD)
              </a>
            ) : (
              <span className="text-muted text-sm">Create an episode outline first.</span>
            )}
          </div>
        </div>

        {/* 3. SHOT LIST EXPORT */}
        <div className="export-card">
          <div className="export-card-header">
            <span className="export-tag">CINEMATOGRAPHY</span>
            <span className={`status-pill ${hasShotPlan ? 'status-ready' : 'status-pending'}`}>
              {hasShotPlan ? 'READY' : 'NOT GENERATED'}
            </span>
          </div>

          <h3 className="export-card-title">Cinematic Shot Plan</h3>
          <p className="export-card-desc">
            Complete breakdown of scene shots, camera framings (wide, medium, close-up), angles, lighting, and props.
          </p>

          <div className="export-actions-row">
            {hasShotPlan ? (
              <>
                <a
                  href={getExportUrl(project.metadata.id, 'shots_csv')}
                  download
                  className="btn-cinematic-primary"
                  style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
                >
                  DOWNLOAD CSV
                </a>
                <a
                  href={getExportUrl(project.metadata.id, 'shots_json')}
                  download
                  className="btn-cinematic-secondary"
                  style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
                >
                  DOWNLOAD JSON
                </a>
              </>
            ) : (
              <span className="text-muted text-sm">Prepare shot plan under STORYBOARD tab first.</span>
            )}
          </div>
        </div>

        {/* 4. STORYBOARD BUNDLE EXPORT */}
        <div className="export-card">
          <div className="export-card-header">
            <span className="export-tag">COMPLETE PACKAGE</span>
            <span className={`status-pill ${hasShotPlan ? 'status-ready' : 'status-pending'}`}>
              {hasShotPlan ? 'READY' : 'NOT GENERATED'}
            </span>
          </div>

          <h3 className="export-card-title">Storyboard &amp; World Bundle</h3>
          <p className="export-card-desc">
            Comprehensive JSON archive containing world state, actor visual identity profiles, rendered comic SVGs, and continuity notes.
          </p>

          <div className="export-actions-row">
            <a
              href={getExportUrl(project.metadata.id, 'bundle')}
              download
              className="btn-cinematic-primary"
              style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
            >
              DOWNLOAD COMPLETE BUNDLE (.JSON)
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
