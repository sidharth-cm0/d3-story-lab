import React, { useState, useEffect } from 'react';
import { ProjectData, StoryBlueprint, CharacterArcReport, CausalContinuitySummary } from '../types';
import * as api from '../api';

interface StructureAndArcsViewerProps {
  project: ProjectData;
  loading?: boolean;
}

export const StructureAndArcsViewer: React.FC<StructureAndArcsViewerProps> = ({ project, loading = false }) => {
  const [blueprint, setBlueprint] = useState<StoryBlueprint | null>(project.story_blueprint || null);
  const [arcs, setArcs] = useState<Record<string, CharacterArcReport>>(project.character_arcs || {});
  const [causalSummary, setCausalSummary] = useState<CausalContinuitySummary | null>(project.causal_summary || null);
  const [selectedCharId, setSelectedCharId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'blueprint' | 'arcs' | 'causality'>('blueprint');
  const [fetching, setFetching] = useState(false);

  // Load blueprint, arcs, and causality if missing
  useEffect(() => {
    if (!project.metadata?.id) return;
    const pid = project.metadata.id;

    const loadData = async () => {
      setFetching(true);
      try {
        if (!blueprint) {
          const bp = await api.fetchBlueprint(pid);
          setBlueprint(bp);
        }
        if (Object.keys(arcs).length === 0) {
          const arcData = await api.fetchCharacterArcs(pid);
          setArcs(arcData);
          if (Object.keys(arcData).length > 0 && !selectedCharId) {
            setSelectedCharId(Object.keys(arcData)[0]);
          }
        }
        if (!causalSummary) {
          const causal = await api.fetchCausalContinuity(pid);
          setCausalSummary(causal);
        }
      } catch (err) {
        console.error('Failed to load structure or arc diagnostics', err);
      } finally {
        setFetching(false);
      }
    };

    loadData();
  }, [project.metadata?.id]);

  useEffect(() => {
    if (Object.keys(arcs).length > 0 && (!selectedCharId || !arcs[selectedCharId])) {
      setSelectedCharId(Object.keys(arcs)[0]);
    }
  }, [arcs, selectedCharId]);

  const characters = project.world?.characters || {};
  const selectedArc = selectedCharId ? arcs[selectedCharId] : null;

  return (
    <div className="structure-arcs-view">
      {/* Top Banner Navigation */}
      <div className="structure-header-bar">
        <div>
          <div className="view-kicker">NARRATIVE FRAMEWORK & CAUSALITY</div>
          <h2 className="view-title">STRUCTURE, ARCS & CAUSAL CONTINUITY</h2>
        </div>
        <div className="structure-subnav-pills">
          <button
            className={`subnav-pill ${activeTab === 'blueprint' ? 'active' : ''}`}
            onClick={() => setActiveTab('blueprint')}
          >
            STORY BLUEPRINT
          </button>
          <button
            className={`subnav-pill ${activeTab === 'arcs' ? 'active' : ''}`}
            onClick={() => setActiveTab('arcs')}
          >
            CHARACTER ARCS ({Object.keys(arcs).length})
          </button>
          <button
            className={`subnav-pill ${activeTab === 'causality' ? 'active' : ''}`}
            onClick={() => setActiveTab('causality')}
          >
            CAUSAL CONTINUITY
          </button>
        </div>
      </div>

      {(loading || fetching) && (
        <div className="loading-banner">
          <span>❖ Analyzing narrative structure and observing character trajectories...</span>
        </div>
      )}

      {/* TAB 1: STORY BLUEPRINT */}
      {activeTab === 'blueprint' && (
        <div className="blueprint-container">
          {blueprint ? (
            <>
              {/* Structure Overview Cards */}
              <div className="blueprint-meta-grid">
                <div className="blueprint-card">
                  <span className="card-label">PRIMARY STRUCTURE</span>
                  <div className="card-value highlight-gold">
                    {blueprint.primary_structure.replace(/_/g, ' ')}
                  </div>
                  <div className="card-meta">
                    Fit Score: <strong className="text-amber">{blueprint.fit_score}/100</strong> ({blueprint.selection_mode})
                  </div>
                  <p className="card-desc">{blueprint.fit_rationale}</p>
                </div>

                <div className="blueprint-card">
                  <span className="card-label">SECONDARY OVERLAY & STRATEGY</span>
                  <div className="card-value">
                    {blueprint.secondary_structure ? blueprint.secondary_structure.replace(/_/g, ' ') : 'PURE STRUCTURE'}
                  </div>
                  <div className="card-meta">
                    Presentation: <strong>{blueprint.presentation_strategy}</strong>
                  </div>
                  <p className="card-desc">
                    Target Duration: {blueprint.target_duration_minutes} min episode
                  </p>
                </div>

                <div className="blueprint-card">
                  <span className="card-label">THEMATIC CORE & STAKES</span>
                  <div className="card-value text-sm" style={{ fontWeight: 600 }}>
                    "{blueprint.dramatic_question}"
                  </div>
                  <div className="card-meta">Conflict: {blueprint.central_conflict_type}</div>
                  <p className="card-desc">Stakes: {blueprint.stakes}</p>
                </div>
              </div>

              {/* Principle Notice */}
              <div className="structure-notice-box">
                <span className="notice-icon">⚖</span>
                <div>
                  <strong>Structure Without Puppetry:</strong> The blueprint sets target positions and soft pressure signals for the Director agent. Characters make autonomous decisions and are never forced to speak or act against their canonical beliefs.
                </div>
              </div>

              {/* Target Beat Timeline */}
              <div className="beat-timeline-section">
                <h3 className="section-title">TARGET BEAT OUTLINE & PRESSURE SIGNALS</h3>
                <div className="beat-cards-list">
                  {blueprint.expected_beats.map((beat, idx) => (
                    <div key={beat.beat_id || idx} className="beat-card">
                      <div className="beat-card-header">
                        <span className="beat-number">BEAT {idx + 1}</span>
                        <span className="beat-act">{beat.act}</span>
                        <span className="beat-pos">{(beat.target_position_pct * 100).toFixed(0)}% POSITION</span>
                      </div>
                      <h4 className="beat-name">{beat.name}</h4>
                      <p className="beat-func">{beat.expected_dramatic_function}</p>
                      <div className="beat-pressure">
                        <span className="pressure-tag">DIRECTOR PRESSURE SIGNAL:</span> {beat.pressure_signal}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="empty-quiet">NO BLUEPRINT GENERATED YET.</div>
          )}
        </div>
      )}

      {/* TAB 2: OBSERVATIONAL CHARACTER ARCS */}
      {activeTab === 'arcs' && (
        <div className="arcs-container">
          <div className="arcs-layout">
            {/* Left: Character Selector Sidebar */}
            <div className="arcs-sidebar">
              <span className="sidebar-heading">CHARACTERS</span>
              {Object.keys(characters).map((cid) => {
                const char = characters[cid];
                const arc = arcs[cid];
                return (
                  <button
                    key={cid}
                    className={`arc-char-btn ${selectedCharId === cid ? 'active' : ''}`}
                    onClick={() => setSelectedCharId(cid)}
                  >
                    <div className="arc-char-name">{char.name}</div>
                    <div className="arc-char-role">{char.role}</div>
                    {arc && (
                      <span className={`arc-trajectory-tag ${arc.arc_trajectory.toLowerCase()}`}>
                        {arc.arc_trajectory}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Right: Character Arc Details */}
            <div className="arc-details-panel">
              {selectedArc ? (
                <>
                  <div className="arc-details-header">
                    <div>
                      <h3 className="arc-char-title">{selectedArc.character_name}</h3>
                      <div className="arc-char-subtitle">
                        Role: {selectedArc.starting_state?.role || 'Actor'} &nbsp;|&nbsp;
                        Trajectory: <strong className="text-amber">{selectedArc.arc_trajectory}</strong>
                      </div>
                    </div>
                    <div className="provenance-badge">
                      <span className="prov-dot">●</span> OBSERVATIONAL ONLY (NO PUPPETRY)
                    </div>
                  </div>

                  {/* Starting vs Ending State */}
                  <div className="arc-state-comparison">
                    <div className="arc-state-box">
                      <span className="state-box-label">INITIAL OBSERVED STATE</span>
                      <div className="state-row">
                        <strong>Role:</strong> {selectedArc.starting_state?.role}
                      </div>
                      <div className="state-row">
                        <strong>Location:</strong> {selectedArc.starting_state?.initial_location_id || 'Unknown'}
                      </div>
                      {selectedArc.starting_state?.personality_traits && selectedArc.starting_state.personality_traits.length > 0 && (
                        <div className="state-row">
                          <strong>Traits:</strong> {selectedArc.starting_state.personality_traits.join(', ')}
                        </div>
                      )}
                    </div>

                    <div className="arc-arrow">➔</div>

                    <div className="arc-state-box">
                      <span className="state-box-label">FINAL OBSERVED STATE</span>
                      <div className="state-row">
                        <strong>Location:</strong> {selectedArc.ending_state?.current_location_id || 'Unknown'}
                      </div>
                      <div className="state-row">
                        <strong>Total Decisions:</strong> {selectedArc.ending_state?.decisions_count || selectedArc.major_decisions?.length || 0}
                      </div>
                      <div className="state-row">
                        <strong>Dominant Emotion:</strong> {selectedArc.ending_state?.dominant_emotion || 'Balanced'}
                      </div>
                    </div>
                  </div>

                  {/* Major Decisions */}
                  <div className="arc-section">
                    <h4 className="arc-section-title">AUTONOMOUS DECISIONS ({selectedArc.major_decisions.length})</h4>
                    {selectedArc.major_decisions.length > 0 ? (
                      <ul className="arc-decision-list">
                        {selectedArc.major_decisions.map((dec, i) => (
                          <li key={i} className="arc-decision-item">{dec}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-muted text-sm">No independent physical actions logged yet.</p>
                    )}
                  </div>

                  {/* Key Dramatic Turns */}
                  <div className="arc-section">
                    <h4 className="arc-section-title">KEY TURNS & SHIFTS ({selectedArc.key_turns.length})</h4>
                    {selectedArc.key_turns.length > 0 ? (
                      <div className="arc-turns-list">
                        {selectedArc.key_turns.map((turn, i) => (
                          <div key={i} className="arc-turn-item">
                            <span className="turn-tick">TICK {turn.tick}</span>
                            <span className="turn-type">{turn.turn_type}</span>
                            <span className="turn-summary">{turn.summary}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-muted text-sm">Character remained steadfast throughout observed events.</p>
                    )}
                  </div>

                  {/* Relationship Deltas */}
                  {selectedArc.relationship_deltas && Object.keys(selectedArc.relationship_deltas).length > 0 && (
                    <div className="arc-section">
                      <h4 className="arc-section-title">RELATIONSHIP AFFINITY DELTAS</h4>
                      <div className="relationship-delta-grid">
                        {Object.entries(selectedArc.relationship_deltas).map(([otherId, delta]) => {
                          const otherName = characters[otherId]?.name || otherId;
                          return (
                            <div key={otherId} className="rel-delta-chip">
                              <span className="rel-name">{otherName}:</span>
                              <span className={`rel-value ${delta >= 0 ? 'pos' : 'neg'}`}>
                                {delta >= 0 ? `+${delta.toFixed(2)}` : delta.toFixed(2)}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-quiet">SELECT A CHARACTER TO VIEW OBSERVED ARC.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: CAUSAL CONTINUITY */}
      {activeTab === 'causality' && (
        <div className="causality-container">
          {causalSummary ? (
            <>
              {/* Metrics Header */}
              <div className="causality-metrics-grid">
                <div className="metric-card">
                  <span className="metric-label">CAUSAL CONTINUITY SCORE</span>
                  <div className="metric-value highlight-gold">
                    {causalSummary.overall_causal_score.toFixed(0)}/100
                  </div>
                  <div className="metric-sub">
                    {causalSummary.overall_causal_score >= 70 ? 'Strong Causal Escalation' : 'Episodic Friction'}
                  </div>
                </div>

                <div className="metric-card">
                  <span className="metric-label">THEREFORE / BUT vs AND-THEN</span>
                  <div className="metric-value">
                    <span className="text-amber">{causalSummary.but_therefore_count}</span>
                    <span className="text-dim"> / </span>
                    <span className="text-muted">{causalSummary.and_then_count}</span>
                  </div>
                  <div className="metric-sub">
                    Ratio: {(causalSummary.but_therefore_ratio * 100).toFixed(0)}% Consequential
                  </div>
                </div>

                <div className="metric-card wide">
                  <span className="metric-label">DIRECTOR PACING SIGNAL</span>
                  <p className="pacing-text">{causalSummary.pressure_recommendation}</p>
                </div>
              </div>

              {/* Transition Breakdown */}
              <div className="causal-transitions-section">
                <h3 className="section-title">CONSECUTIVE EVENT TRANSITIONS ({causalSummary.transitions.length})</h3>
                <div className="transitions-list">
                  {causalSummary.transitions.map((t, idx) => (
                    <div
                      key={idx}
                      className={`transition-row ${t.transition_type === 'BUT_THEREFORE' ? 'consequential' : 'episodic'}`}
                    >
                      <div className="trans-type-badge">
                        {t.transition_type === 'BUT_THEREFORE' ? 'THEREFORE / BUT' : 'AND THEN'}
                      </div>
                      <div className="trans-rationale">{t.rationale}</div>
                      <div className="trans-score">{(t.score * 100).toFixed(0)}%</div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="empty-quiet">NO CAUSALITY ANALYSIS AVAILABLE YET. RUN SIMULATION TICKS.</div>
          )}
        </div>
      )}
    </div>
  );
};
