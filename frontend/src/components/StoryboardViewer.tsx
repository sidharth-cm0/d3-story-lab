import React, { useState, useEffect } from 'react';
import { ProjectData, StoryboardResponse } from '../types';
import { fetchStoryboard } from '../api';
import { formatDisplayValue, safeExtractSvg } from '../utils/format';

interface StoryboardViewerProps {
  project: ProjectData;
  loading?: boolean;
}

export const StoryboardViewer: React.FC<StoryboardViewerProps> = ({ project }) => {
  const [storyboardData, setStoryboardData] = useState<StoryboardResponse | null>(null);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (project.storyboard) {
      setStoryboardData(project.storyboard);
    }
  }, [project.storyboard]);

  const handleFetchStoryboard = async () => {
    if (!project.screenplay) {
      setError('Screenplay must be generated first. Go to SCRIPT tab to transcribe simulation.');
      return;
    }
    setFetching(true);
    setError(null);
    try {
      const data = await fetchStoryboard(project.metadata.id);
      setStoryboardData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to prepare storyboard shots');
    } finally {
      setFetching(false);
    }
  };

  const panels = storyboardData?.shot_plan?.panels || [];
  const renderedPanels = storyboardData?.rendered_panels || [];

  return (
    <div className="cinematic-storyboard-pane">
      <div className="pane-header">
        <div>
          <span className="pane-kicker">CINEMATIC PREPARATION</span>
          <h2 className="pane-title">STORYBOARD</h2>
        </div>

        <div className="pane-actions">
          <button
            className="btn-cinematic-primary"
            onClick={handleFetchStoryboard}
            disabled={fetching}
          >
            {fetching ? 'PLANNING FRAMES...' : 'PREPARE SHOT PLAN'}
          </button>
        </div>
      </div>

      {error && (
        <div className="modal-error-box" style={{ margin: '16px 24px' }}>
          {error}
        </div>
      )}

      <div className="storyboard-content-scroll">
        {panels.length === 0 ? (
          <div className="empty-quiet" style={{ marginTop: '60px' }}>
            NO SHOT PLAN PREPARED YET.<br />
            {project.screenplay ? (
              <span>CLICK <strong>PREPARE SHOT PLAN</strong> TO GENERATE CINEMATIC FRAMES.</span>
            ) : (
              <span>GENERATE A SCREENPLAY UNDER <strong>SCRIPT</strong> BEFORE PLANNING FRAMES.</span>
            )}
          </div>
        ) : (
          <div className="storyboard-panels-grid">
            {panels.map((panel, idx) => {
              const svgContent = safeExtractSvg(renderedPanels[idx]);
              const shotNum = panel.shot_number ?? panel.panel_number ?? (idx + 1);
              const shotType = (panel.shot_type || 'medium').replace(/_/g, ' ').toUpperCase();
              const cameraAngle = (panel.camera_angle || 'eye_level').replace(/_/g, ' ').toUpperCase();

              const locName = formatDisplayValue(
                panel.location_name ||
                project.world?.locations?.[panel.location_id]?.name ||
                panel.location_id ||
                'Unknown Location'
              );

              let actorNames = '';
              if (panel.character_names && Array.isArray(panel.character_names) && panel.character_names.length > 0) {
                actorNames = formatDisplayValue(panel.character_names);
              } else if (panel.characters_present && Array.isArray(panel.characters_present) && panel.characters_present.length > 0) {
                actorNames = panel.characters_present
                  .map((cid) => formatDisplayValue(project.world?.characters?.[cid]?.name || cid))
                  .filter((s) => s !== '—')
                  .join(', ');
              }

              const actionText = formatDisplayValue(panel.action || panel.action_description || 'Scene unfolds');
              const visualText = formatDisplayValue(
                panel.visual_description ||
                (panel.lighting && panel.mood ? `${panel.lighting} • ${panel.mood}` : '')
              );
              const dialogueText = panel.dialogue_excerpt ? formatDisplayValue(panel.dialogue_excerpt) : null;
              const promptText = formatDisplayValue(panel.prompt || panel.visual_prompt || '');
              const sourceBlocks = panel.source_screenplay_block_ids || [];

              return (
                <div key={panel.id || `panel-${idx}`} className="noir-storyboard-panel">
                  <div className="storyboard-frame-container">
                    {svgContent ? (
                      <div
                        className="storyboard-svg-wrapper"
                        dangerouslySetInnerHTML={{ __html: svgContent }}
                      />
                    ) : (
                      <div className="storyboard-placeholder-sketch">
                        <span className="sketch-crosshair">✛</span>
                        <span className="sketch-label">FRAME {String(shotNum).padStart(2, '0')}</span>
                      </div>
                    )}
                    <span className="frame-number-badge">
                      SHOT {String(shotNum).padStart(2, '0')}
                    </span>
                  </div>

                  <div className="storyboard-panel-info">
                    <div className="panel-tags-row">
                      <span className="panel-badge text-amber">{shotType}</span>
                      <span className="panel-badge">{cameraAngle}</span>
                      <span className="panel-location-tag">📍 {locName}</span>
                    </div>

                    {actorNames ? (
                      <div className="panel-chars-line">
                        <span className="text-muted">ACTORS: </span>
                        <span>{actorNames}</span>
                      </div>
                    ) : null}

                    <p className="panel-action-desc">
                      <span className="text-muted">ACTION: </span>
                      <span>{actionText}</span>
                    </p>

                    {visualText && visualText !== '—' ? (
                      <div className="panel-visual-desc">
                        <span className="text-muted">VISUAL: </span>
                        <span>{visualText}</span>
                      </div>
                    ) : null}

                    {dialogueText && (
                      <div className="panel-dialogue-excerpt">
                        "{dialogueText}"
                      </div>
                    )}

                    {/* Collapsible Prompt & Details */}
                    <details className="panel-prompt-details">
                      <summary className="panel-prompt-summary">PROMPT &amp; DETAILS</summary>
                      <div className="panel-prompt-mono">
                        <div className="mono-kicker">PROMPT</div>
                        <div>{promptText}</div>
                        {sourceBlocks.length > 0 && (
                          <div style={{ marginTop: '4px', opacity: 0.75 }}>
                            <span className="mono-kicker">SCENE BLOCKS: </span>
                            <span>{sourceBlocks.join(', ')}</span>
                          </div>
                        )}
                      </div>
                    </details>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
