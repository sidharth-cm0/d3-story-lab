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
  const [activeTab, setActiveTab] = useState<'synopsis' | 'screenplay' | 'sources' | 'raw'>('screenplay');
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const doc = project.screenplay;
  const beats = project.selection?.filtered_beats || [];
  const fountainText = project.fountain_text || '';
  const events = project.world?.events || {};
  const synopsis = project.synopsis;
  const outline = project.story_outline;

  const handleCopy = () => {
    if (fountainText) {
      navigator.clipboard.writeText(fountainText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getActiveBlock = () => {
    if (!selectedBlockId || !doc) return null;
    for (const scene of doc.scenes) {
      for (const block of scene.blocks) {
        if (block.id === selectedBlockId) {
          return block;
        }
      }
    }
    return null;
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

  const activeBlock = getActiveBlock();
  const activeSources = getActiveBlockSources();

  return (
    <div className="cinematic-screenplay-pane">
      {/* Top Header Controls */}
      <div className="pane-header">
        <div>
          <span className="pane-kicker">SCRIBE CONSOLE &amp; NARRATIVE ARCHITECTURE</span>
          <h2 className="pane-title">SCREENPLAY &amp; SYNOPSIS</h2>
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
          className={`sub-tab-btn ${activeTab === 'synopsis' ? 'active' : ''}`}
          onClick={() => setActiveTab('synopsis')}
        >
          SYNOPSIS &amp; BEATS
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
        {/* TAB 1: SYNOPSIS */}
        {activeTab === 'synopsis' && (
          <div className="synopsis-container">
            <div className="synopsis-card">
              <span className="synopsis-badge">ONE-LINE LOGLINE</span>
              <p className="synopsis-logline">
                {synopsis?.logline ||
                  `When sovereign actors clash over opposing secrets in ${project.world.name}, mounting crises force a decisive choice between survival and the truth.`}
              </p>
            </div>

            <div className="synopsis-card">
              <span className="synopsis-badge">PARAGRAPH SUMMARY</span>
              <p className="synopsis-summary-text">
                {synopsis?.paragraph_summary ||
                  `In this ${project.metadata.target_duration_minutes || 20}-minute episode, tensions escalate inside ${project.world.name} as conflicting loyalties and concealed objectives erupt into irreversible confrontation.`}
              </p>
            </div>

            <div className="synopsis-card">
              <span className="synopsis-badge">DRAMATIC QUESTION</span>
              <p className="synopsis-question">
                {synopsis?.dramatic_question || outline?.dramatic_question || 'Will truth survive the clash of sovereign actors?'}
              </p>
            </div>

            {/* Act Structure Breakdown */}
            {outline && outline.act_structure && (
              <div className="synopsis-acts-grid">
                <div className="act-card">
                  <span className="act-header-tag">ACT I: SETUP</span>
                  <p className="act-desc">{outline.act_structure.act_1}</p>
                </div>
                <div className="act-card">
                  <span className="act-header-tag">ACT II: CONFRONTATION</span>
                  <p className="act-desc">{outline.act_structure.act_2}</p>
                </div>
                <div className="act-card">
                  <span className="act-header-tag">ACT III: CLIMAX &amp; RESOLUTION</span>
                  <p className="act-desc">{outline.act_structure.act_3}</p>
                </div>
              </div>
            )}

            {/* Full Multi-Paragraph Episode Synopsis */}
            <div className="synopsis-card full-synopsis-box">
              <span className="synopsis-badge">FULL EPISODE SYNOPSIS</span>
              <pre className="full-synopsis-text">
                {synopsis?.full_synopsis ||
                  `EPISODE: ${project.metadata.title}\n\nPREMISE:\n${project.metadata.seed_prompt}\n\nOBSERVED PROGRESSION:\nScreenplay grounded in canonical simulation state.`}
              </pre>
            </div>
          </div>
        )}

        {/* TAB 2: SCREENPLAY */}
        {activeTab === 'screenplay' && (
          !doc && !fountainText ? (
            <div className="empty-quiet" style={{ marginTop: '60px' }}>
              NO SCREENPLAY GENERATED YET.<br />
              ADVANCE SIMULATION TICKS, THEN CLICK <strong>REFRESH / TRANSCRIBE</strong> TO ACTIVATE SCRIBE.
            </div>
          ) : (
            <div className="screenplay-stage-layout">
              {/* Screenplay Document Sheet */}
              <div className="screenplay-sheet">
                <div className="sheet-title-block">
                  <h2 className="screenplay-h1">{doc?.title || project.metadata.title}</h2>
                  <div className="screenplay-byline">Written by D3 Story Lab Simulation Engine</div>
                </div>

                {doc?.scenes.map((scene) => (
                  <section key={`scene-${scene.scene_number}`} className="screenplay-scene-section">
                    <div className="scene-slugline" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                      <div>
                        <span className="scene-num-prefix">{scene.scene_number}.</span>
                        <span>{scene.heading}</span>
                      </div>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        {scene.framing_type && scene.framing_type !== 'chronological' && (
                          <span className="panel-badge text-amber" style={{ fontSize: '10px' }}>
                            FRAMING: {scene.framing_type.replace(/_/g, ' ').toUpperCase()}
                          </span>
                        )}
                        {scene.dramatic_purpose && (
                          <span className="panel-badge" style={{ fontSize: '10px' }}>
                            {scene.dramatic_purpose.replace(/_/g, ' ').toUpperCase()}
                          </span>
                        )}
                      </div>
                    </div>

                    {Boolean(scene.scene_goal || scene.dramatic_question || scene.turning_point || scene.subtext) && (
                      <div className="scene-editorial-summary">
                        {scene.scene_goal && (
                          <div className="scene-editorial-row">
                            <span className="scene-editorial-label">GOAL:</span>
                            <span className="scene-editorial-value">{scene.scene_goal}</span>
                          </div>
                        )}
                        {scene.dramatic_question && (
                          <div className="scene-editorial-row">
                            <span className="scene-editorial-label">QUESTION:</span>
                            <span className="scene-editorial-value">{scene.dramatic_question}</span>
                          </div>
                        )}
                        {scene.turning_point && (
                          <div className="scene-editorial-row">
                            <span className="scene-editorial-label">TURNING POINT:</span>
                            <span className="scene-editorial-value">{scene.turning_point}</span>
                          </div>
                        )}
                        {scene.subtext && (
                          <div className="scene-editorial-row">
                            <span className="scene-editorial-label">SUBTEXT:</span>
                            <span className="scene-editorial-value">{scene.subtext}</span>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="scene-blocks-flow">
                      {scene.blocks.map((block) => {
                        const isSelected = selectedBlockId === block.id;

                        if (block.block_type === 'action') {
                          return (
                            <p
                              key={block.id}
                              className={`screenplay-action ${isSelected ? 'selected' : ''}`}
                              onClick={() => setSelectedBlockId(block.id)}
                            >
                              {block.text}
                            </p>
                          );
                        }

                        if (block.block_type === 'character') {
                          return (
                            <div
                              key={block.id}
                              className={`screenplay-character-cue ${isSelected ? 'selected' : ''}`}
                              onClick={() => setSelectedBlockId(block.id)}
                            >
                              {block.text}
                            </div>
                          );
                        }

                        if (block.block_type === 'parenthetical') {
                          return (
                            <div
                              key={block.id}
                              className={`screenplay-parenthetical ${isSelected ? 'selected' : ''}`}
                              onClick={() => setSelectedBlockId(block.id)}
                              title={block.is_performance_cue ? `Performance Cue (${block.cue_type || 'micro-expression'})` : undefined}
                            >
                              ({block.text})
                              {block.is_performance_cue && (
                                <span className="perf-cue-dot" title={`Grounded behavioral tell: ${block.cue_type}`} style={{ marginLeft: '5px', color: '#f59e0b', fontSize: '10px' }}>
                                  ●
                                </span>
                              )}
                            </div>
                          );
                        }

                        if (block.block_type === 'dialogue') {
                          return (
                            <p
                              key={block.id}
                              className={`screenplay-dialogue ${isSelected ? 'selected' : ''}`}
                              onClick={() => setSelectedBlockId(block.id)}
                            >
                              "{block.text}"
                            </p>
                          );
                        }

                        return (
                          <div key={block.id} className="screenplay-generic">
                            {block.text}
                          </div>
                        );
                      })}
                    </div>
                  </section>
                ))}
              </div>

              {/* Provenance Grounding Drawer */}
              <aside className="provenance-grounding-drawer">
                <div className="drawer-kicker">STRICT PROVENANCE AUDIT</div>
                <h3 className="drawer-title">GROUNDING SOURCE EVENTS</h3>

                {activeSources.length > 0 ? (
                  <div className="grounding-events-list">
                    <div className="grounding-intro">
                      Block mapped to <strong>{activeSources.length}</strong> verified simulation event(s):
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

                {activeBlock && (activeBlock.is_performance_cue || activeBlock.cue_type) && (
                  <div style={{ marginTop: '16px', padding: '10px 12px', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '4px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 800, color: '#f59e0b', letterSpacing: '0.06em' }}>
                      🎭 PERFORMANCE CUE PROVENANCE
                    </div>
                    <div style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '6px' }}>
                      <strong>CUE TYPE:</strong> <span className="panel-badge text-amber" style={{ fontSize: '10px' }}>{activeBlock.cue_type || 'BEHAVIORAL TELL'}</span>
                    </div>
                    <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '6px', lineHeight: 1.4 }}>
                      Deterministically grounded in actor emotional subtext without exposing confidential secrets or internal knowledge.
                    </div>
                  </div>
                )}
              </aside>
            </div>
          )
        )}

        {/* TAB 3: SOURCES */}
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

        {/* TAB 4: RAW FOUNTAIN */}
        {activeTab === 'raw' && (
          <div className="raw-fountain-view">
            <pre className="fountain-paper-console">{fountainText}</pre>
          </div>
        )}
      </div>
    </div>
  );
};
