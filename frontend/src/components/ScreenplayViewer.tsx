import React, { useState } from 'react';
import { ProjectData } from '../types';
import { getDownloadUrl } from '../api';

interface ScreenplayViewerProps {
  project: ProjectData;
  onGenerate: () => Promise<void>;
  loading: boolean;
}

export const ScreenplayViewer: React.FC<ScreenplayViewerProps> = ({
  project,
  onGenerate,
  loading,
}) => {
  const [activeTab, setActiveTab] = useState<'screenplay' | 'sources' | 'raw'>('screenplay');
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const doc = project.screenplay;
  const beats = project.selection?.filtered_beats || [];
  const fountainText = project.fountain_text || '';
  const events = project.world?.events || {};

  const handleCopy = () => {
    if (fountainText) {
      navigator.clipboard.writeText(fountainText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getActiveBlockSources = () => {
    if (!selectedBlockId || !doc) return [];
    for (const scene of doc.scenes) {
      for (const block of scene.blocks) {
        if (block.id === selectedBlockId) {
          return block.source_event_ids.map((eid) => events[eid]).filter(Boolean);
        }
      }
    }
    return [];
  };

  const activeSources = getActiveBlockSources();

  return (
    <div className="cinematic-screenplay-pane">
      {/* Top Header Controls */}
      <div className="pane-header">
        <div>
          <span className="pane-kicker">SCRIBE CONSOLE</span>
          <h2 className="pane-title">SCREENPLAY</h2>
        </div>

        <div className="screenplay-action-buttons">
          <button
            className="btn-cinematic-secondary"
            onClick={handleCopy}
            disabled={!fountainText}
          >
            {copied ? '✓ COPIED' : 'COPY'}
          </button>
          {fountainText && (
            <a
              href={getDownloadUrl(project.metadata.id)}
              download
              className="btn-cinematic-secondary"
              style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
            >
              DOWNLOAD .FOUNTAIN
            </a>
          )}
          <button
            className="btn-cinematic-primary"
            onClick={onGenerate}
            disabled={loading || Object.keys(events).length === 0}
          >
            {loading ? 'SCRIBING...' : 'REFRESH / TRANSCRIBE'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="screenplay-sub-tabs">
        <button
          className={`sub-tab-btn ${activeTab === 'screenplay' ? 'active' : ''}`}
          onClick={() => setActiveTab('screenplay')}
        >
          SCREENPLAY
        </button>
        <button
          className={`sub-tab-btn ${activeTab === 'sources' ? 'active' : ''}`}
          onClick={() => setActiveTab('sources')}
        >
          EVENT SOURCES ({beats.length})
        </button>
        <button
          className={`sub-tab-btn ${activeTab === 'raw' ? 'active' : ''}`}
          onClick={() => setActiveTab('raw')}
        >
          RAW FOUNTAIN
        </button>
      </div>

      {/* Main View Area */}
      <div className="screenplay-main-scroll">
        {!doc && !fountainText ? (
          <div className="empty-quiet" style={{ marginTop: '60px' }}>
            NO SCREENPLAY GENERATED YET.<br />
            ADVANCE SIMULATION TICKS, THEN CLICK <strong>REFRESH / TRANSCRIBE</strong> TO ACTIVATE SCRIBE.
          </div>
        ) : (
          <>
            {activeTab === 'screenplay' && (
              <div className="screenplay-stage-layout">
                {/* Screenplay Document Sheet */}
                <div className="screenplay-sheet">
                  <div className="sheet-title-block">
                    <h2 className="screenplay-h1">{doc?.title || project.metadata.title}</h2>
                    <div className="screenplay-meta-line">Written by D3 Story Lab Engine</div>
                    <div className="screenplay-meta-line">Based on autonomous simulation history</div>
                  </div>

                  {doc?.scenes.map((scene) => (
                    <div key={scene.scene_number} className="screenplay-scene-section">
                      <div className="screenplay-slugline">{scene.heading}</div>

                      {scene.blocks.map((b) => {
                        const isBlockSelected = selectedBlockId === b.id;
                        if (b.block_type === 'character') {
                          return (
                            <div
                              key={b.id}
                              className={`screenplay-character-cue ${isBlockSelected ? 'block-highlighted' : ''}`}
                              onClick={() => setSelectedBlockId(b.id)}
                            >
                              {b.text}
                            </div>
                          );
                        }
                        if (b.block_type === 'dialogue') {
                          return (
                            <div
                              key={b.id}
                              className={`screenplay-dialogue-line ${isBlockSelected ? 'block-highlighted' : ''}`}
                              onClick={() => setSelectedBlockId(b.id)}
                            >
                              "{b.text}"
                            </div>
                          );
                        }
                        if (b.block_type === 'parenthetical') {
                          return (
                            <div
                              key={b.id}
                              className={`screenplay-parenthetical ${isBlockSelected ? 'block-highlighted' : ''}`}
                              onClick={() => setSelectedBlockId(b.id)}
                            >
                              ({b.text})
                            </div>
                          );
                        }
                        return (
                          <div
                            key={b.id}
                            className={`screenplay-action-para ${isBlockSelected ? 'block-highlighted' : ''}`}
                            onClick={() => setSelectedBlockId(b.id)}
                          >
                            {b.text}
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>

                {/* Source Verification Drawer */}
                <aside className="source-grounding-drawer">
                  <div className="drawer-header">
                    <span>GROUNDED SOURCE VERIFICATION</span>
                  </div>

                  {selectedBlockId && activeSources.length > 0 ? (
                    <div className="grounding-list">
                      <div className="drawer-intro">
                        Verified events behind selected script block:
                      </div>
                      {activeSources.map((ev) => (
                        <div key={ev.id} className="grounding-event-card">
                          <span className="grounding-tick">T{ev.tick}</span>
                          <span className="grounding-type">{ev.event_type}</span>
                          <div className="grounding-desc">{ev.description}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="drawer-empty-hint">
                      Click any dialogue cue or action line to inspect its provable simulation events.
                    </div>
                  )}
                </aside>
              </div>
            )}

            {activeTab === 'sources' && (
              <div className="beats-list-view">
                <div className="beats-arc-summary">
                  <span className="summary-label">DRAMATIC ARC: </span>
                  {project.selection?.dramatic_arc_summary || 'Emergent narrative arc clustered by Observer Agent.'}
                </div>

                {beats.map((beat) => (
                  <div key={beat.id} className="noir-beat-card">
                    <div className="beat-top-bar">
                      <span className="beat-tag">{beat.beat_type}</span>
                      <span className="beat-tension-score">TENSION {Math.round(beat.dramatic_score * 100)}%</span>
                    </div>
                    <p className="beat-summary-text">{beat.summary}</p>
                    <div className="beat-provenance">
                      TICKS {beat.start_tick}–{beat.end_tick} | PROVENANCE: {beat.source_event_ids.join(', ')}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'raw' && (
              <div className="raw-fountain-view">
                <pre className="fountain-paper-console">{fountainText}</pre>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
