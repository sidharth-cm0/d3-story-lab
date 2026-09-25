import React, { useState, useEffect, useCallback } from 'react';
import { ProjectData, StoryBlueprint, CharacterArcReport, CausalContinuitySummary, ArchetypeTrajectory } from '../types';
import * as api from '../api';
import { ParticleWave } from './granular';

interface StructureAndArcsViewerProps {
  project: ProjectData | null;
  loading?: boolean;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: (error: Error, reset: () => void) => React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class StructureErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('StructureAndArcsViewer caught error in boundary:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error || new Error('Unknown error'), this.handleReset);
      }
      return (
        <div className="structure-error-container">
          <div className="error-card">
            <span className="error-icon">⚠</span>
            <h3 className="error-title">STRUCTURE & ARCS DIAGNOSTIC ERROR</h3>
            <p className="error-message">
              {this.state.error?.message || 'An unexpected rendering error occurred in structure diagnostics.'}
            </p>
            <button className="btn-retry" onClick={this.handleReset}>
              RETRY DIAGNOSTICS
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const StructureAndArcsViewerContent: React.FC<StructureAndArcsViewerProps> = ({ project, loading = false }) => {
  const [blueprint, setBlueprint] = useState<StoryBlueprint | null>(project?.story_blueprint || null);
  const [arcs, setArcs] = useState<Record<string, CharacterArcReport>>(project?.character_arcs || {});
  const [causalSummary, setCausalSummary] = useState<CausalContinuitySummary | null>(project?.causal_summary || null);
  const [scenes, setScenes] = useState<any[]>(project?.scenes || []);
  const [selectedCharId, setSelectedCharId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'blueprint' | 'arcs' | 'causality'>('blueprint');
  const [archetypeTrajectories, setArchetypeTrajectories] = useState<Record<string, ArchetypeTrajectory>>({});
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync state if project changes
  useEffect(() => {
    if (project) {
      if (project.story_blueprint) setBlueprint(project.story_blueprint);
      if (project.character_arcs && Object.keys(project.character_arcs).length > 0) setArcs(project.character_arcs);
      if (project.causal_summary) setCausalSummary(project.causal_summary);
      if (project.scenes && project.scenes.length > 0) setScenes(project.scenes);
    }
  }, [project]);

  const loadData = useCallback(async () => {
    if (!project?.metadata?.id) return;
    const pid = project.metadata.id;

    setFetching(true);
    setError(null);
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
      if (scenes.length === 0) {
        try {
          const sc = await api.fetchScenes(pid);
          if (sc && sc.length > 0) setScenes(sc);
        } catch {
          // non-fatal
        }
      }
    } catch (err: any) {
      console.error('Failed to load structure or arc diagnostics', err);
      setError(err?.message || 'Failed to load structure diagnostics from server.');
    } finally {
      setFetching(false);
    }
  }, [project?.metadata?.id, blueprint, arcs, causalSummary, scenes.length, selectedCharId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (Object.keys(arcs).length > 0 && (!selectedCharId || !arcs[selectedCharId])) {
      setSelectedCharId(Object.keys(arcs)[0]);
    }
  }, [arcs, selectedCharId]);

  useEffect(() => {
    if (activeTab === 'arcs' && selectedCharId && project?.metadata?.id) {
      if (!archetypeTrajectories[selectedCharId]) {
        api.getCharacterArchetypeTrajectory(project.metadata.id, selectedCharId)
          .then((traj) => {
            setArchetypeTrajectories((prev) => ({ ...prev, [selectedCharId]: traj }));
          })
          .catch(() => {
            // non-fatal in offline/test environment
          });
      }
    }
  }, [activeTab, selectedCharId, project?.metadata?.id, archetypeTrajectories]);

  // Handle initial LOADING state before any data is ready
  if ((loading || fetching) && (!project || (!blueprint && Object.keys(arcs).length === 0 && !causalSummary))) {
    return (
      <div className="structure-loading-container">
        <div className="loading-banner">
          <span>❖ Analyzing narrative structure and observing character trajectories...</span>
        </div>
      </div>
    );
  }

  // Handle NO_DATA state
  if (!project) {
    return (
      <div className="structure-empty-container">
        <div className="empty-standby-screen">
          <span className="empty-logo">❖</span>
          <h2 className="empty-title">NO ACTIVE SIMULATION</h2>
          <p className="empty-desc">
            The narrative framework requires an active simulation project. Create or select a project to view story blueprint, character arcs, and causal continuity.
          </p>
        </div>
      </div>
    );
  }

  // Handle ERROR state when no critical data could be loaded
  if (error && !blueprint && Object.keys(arcs).length === 0 && !causalSummary) {
    return (
      <div className="structure-error-container">
        <div className="error-card">
          <span className="error-icon">⚠</span>
          <h3 className="error-title">FAILED TO LOAD NARRATIVE DATA</h3>
          <p className="error-message">{error}</p>
          <button className="btn-retry" onClick={loadData}>
            RETRY
          </button>
        </div>
      </div>
    );
  }

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

      {error && (
        <div className="structure-error-banner" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', padding: '8px 16px', borderRadius: '4px', fontSize: '12px', color: '#fca5a5' }}>
          <span>⚠ Some narrative diagnostics could not be updated: {error}</span>
          <button className="btn-retry" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={loadData}>RETRY</button>
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
                    {(blueprint.primary_structure || 'THREE_ACT').replace(/_/g, ' ')}
                  </div>
                  <div className="card-meta">
                    Fit Score: <strong className="text-amber">
                      {blueprint.fit_score != null ? blueprint.fit_score : (blueprint.metadata?.fit_score != null ? blueprint.metadata.fit_score : 'N/A')}/100
                    </strong> ({blueprint.selection_mode || blueprint.metadata?.selection_mode || 'AUTO'})
                  </div>
                  <p className="card-desc">
                    {blueprint.fit_rationale || blueprint.metadata?.fit_rationale || 'Deterministic structure framework.'}
                  </p>
                </div>

                <div className="blueprint-card">
                  <span className="card-label">SECONDARY OVERLAY & STRATEGY</span>
                  <div className="card-value">
                    {blueprint.secondary_structure ? String(blueprint.secondary_structure).replace(/_/g, ' ') : 'PURE STRUCTURE'}
                  </div>
                  <div className="card-meta">
                    Presentation: <strong>{blueprint.presentation_strategy || 'CHRONOLOGICAL'}</strong>
                  </div>
                  <p className="card-desc">
                    Target Duration: {blueprint.target_duration_minutes ?? project.metadata?.target_duration_minutes ?? 20} min episode
                  </p>
                </div>

                <div className="blueprint-card">
                  <span className="card-label">THEMATIC CORE & STAKES</span>
                  <div className="card-value text-sm" style={{ fontWeight: 600 }}>
                    "{blueprint.dramatic_question || 'How will the conflict be resolved?'}"
                  </div>
                  <div className="card-meta">
                    Conflict: {blueprint.central_conflict_type || blueprint.theme || blueprint.metadata?.conflict_type || 'Dramatic Friction'}
                  </div>
                  <p className="card-desc">Stakes: {blueprint.stakes || 'Uncertain outcome'}</p>
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
              <div className="beat-timeline-section" style={{ position: 'relative' }}>
                <ParticleWave
                  seed={808}
                  pointsPerLayer={45}
                  className="narrative-flow-bg"
                  width="100%"
                  height={130}
                  color="rgba(235, 235, 235, 0.4)"
                  accentColor="var(--accent-amber, #d89c38)"
                />
                <h3 className="section-title" style={{ position: 'relative', zIndex: 1 }}>TARGET BEAT OUTLINE & PRESSURE SIGNALS</h3>
                {blueprint.expected_beats && blueprint.expected_beats.length > 0 ? (
                  <div className="beat-cards-list" style={{ position: 'relative', zIndex: 1 }}>
                    {blueprint.expected_beats.map((beat, idx) => (
                      <div key={beat.beat_id || idx} className="beat-card">
                        <div className="beat-card-header">
                          <span className="beat-number">BEAT {idx + 1}</span>
                          <span className="beat-act">{beat.act}</span>
                          <span className={`beat-status-badge status-${(beat.status || 'PENDING').toLowerCase()}`}>
                            {beat.status || 'PENDING'}
                          </span>
                          <span className="beat-pos">
                            {beat.target_position_pct != null ? `${(beat.target_position_pct * 100).toFixed(0)}% POSITION` : ''}
                          </span>
                        </div>
                        <h4 className="beat-name">{beat.name}</h4>
                        <p className="beat-func">{beat.expected_dramatic_function}</p>
                        <div className="beat-pressure">
                          <span className="pressure-tag">DIRECTOR PRESSURE SIGNAL:</span> {beat.pressure_signal}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-quiet">NO BEAT EXPECTATIONS LOGGED.</div>
                )}
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
              {Object.keys(characters).length > 0 ? (
                Object.keys(characters).map((cid) => {
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
                        <span className={`arc-trajectory-tag ${(arc.arc_trajectory || 'NO_ARC').toLowerCase()}`}>
                          {arc.arc_trajectory}
                        </span>
                      )}
                    </button>
                  );
                })
              ) : (
                <div className="empty-quiet text-xs">No characters registered.</div>
              )}
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
                        <strong>Role:</strong> {selectedArc.starting_state?.role || 'Actor'}
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
                        <strong>Location:</strong> {selectedArc.ending_state?.current_location_id || selectedArc.starting_state?.initial_location_id || 'Unknown'}
                      </div>
                      <div className="state-row">
                        <strong>Total Decisions:</strong> {selectedArc.ending_state?.total_decisions_made ?? selectedArc.ending_state?.decisions_count ?? selectedArc.major_decisions?.length ?? 0}
                      </div>
                      <div className="state-row">
                        <strong>Dominant Emotion:</strong> {selectedArc.ending_state?.dominant_emotion || 'Balanced'}
                      </div>
                    </div>
                  </div>

                  {/* Major Decisions */}
                  <div className="arc-section">
                    <h4 className="arc-section-title">AUTONOMOUS DECISIONS ({(selectedArc.major_decisions || []).length})</h4>
                    {selectedArc.major_decisions && selectedArc.major_decisions.length > 0 ? (
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
                    <h4 className="arc-section-title">KEY TURNS & SHIFTS ({(selectedArc.key_turns || []).length})</h4>
                    {selectedArc.key_turns && selectedArc.key_turns.length > 0 ? (
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

                  {/* Relationship Deltas (SAFELY handle string or numeric deltas) */}
                  {selectedArc.relationship_deltas && Object.keys(selectedArc.relationship_deltas).length > 0 && (
                    <div className="arc-section">
                      <h4 className="arc-section-title">RELATIONSHIP AFFINITY DELTAS</h4>
                      <div className="relationship-delta-grid">
                        {Object.entries(selectedArc.relationship_deltas).map(([otherId, delta]) => {
                          const otherName = characters[otherId]?.name || otherId;
                          const isNum = typeof delta === 'number';
                          const displayVal = isNum
                            ? (delta >= 0 ? `+${delta.toFixed(2)}` : delta.toFixed(2))
                            : String(delta);
                          const isPos = isNum ? delta >= 0 : (!displayVal.startsWith('-') && !displayVal.includes(':-'));
                          return (
                            <div key={otherId} className="rel-delta-chip">
                              <span className="rel-name">{otherName}:</span>
                              <span className={`rel-value ${isPos ? 'pos' : 'neg'}`}>
                                {displayVal}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Archetype Trajectory (Observational) */}
                  {archetypeTrajectories[selectedCharId] && (
                    <div className="arc-section">
                      <div className="trajectory-header" style={{ marginBottom: '6px' }}>
                        <h4 className="arc-section-title" style={{ margin: 0 }}>
                          ARCHETYPE TRAJECTORY (OBSERVATIONAL)
                        </h4>
                        <span className="trajectory-stability">
                          Stability: {Math.round(archetypeTrajectories[selectedCharId].stability_score * 100)}%
                        </span>
                      </div>
                      <div className="trajectory-summary-text">
                        {archetypeTrajectories[selectedCharId].trajectory_summary}
                      </div>
                      {archetypeTrajectories[selectedCharId].shift_points && archetypeTrajectories[selectedCharId].shift_points.length > 0 ? (
                        <div className="shift-points-list">
                          {archetypeTrajectories[selectedCharId].shift_points.map((sp, i) => (
                            <div key={i} className="shift-point-item">
                              <span className="shift-point-tick">TICK {sp.tick}</span>
                              <span className="archetype-pill primary">{sp.dominant_archetype}</span>
                              <span>{sp.rationale}</span>
                              {sp.evidence_event_ids && sp.evidence_event_ids.length > 0 && (
                                <span className="shift-point-evidence">
                                  {sp.evidence_event_ids.length} events
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-muted text-sm" style={{ margin: 0 }}>
                          Initial archetype remained stable throughout observed history.
                        </p>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-quiet">
                  {Object.keys(arcs).length > 0
                    ? 'SELECT A CHARACTER TO VIEW OBSERVED ARC.'
                    : 'NO CHARACTER ARCS OBSERVED YET. RUN SIMULATION TICKS TO TRACK TRAJECTORIES.'}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: CAUSAL CONTINUITY & SCENES */}
      {activeTab === 'causality' && (
        <div className="causality-container">
          {causalSummary ? (
            <>
              {/* Metrics Header */}
              <div className="causality-metrics-grid">
                <div className="metric-card">
                  <span className="metric-label">CAUSAL CONTINUITY SCORE</span>
                  <div className="metric-value highlight-gold">
                    {typeof causalSummary.overall_causal_score === 'number'
                      ? causalSummary.overall_causal_score.toFixed(0)
                      : '0'}/100
                  </div>
                  <div className="metric-sub">
                    {(causalSummary.overall_causal_score ?? 0) >= 70
                      ? 'Strong Causal Escalation'
                      : 'Episodic Friction'}
                  </div>
                </div>

                <div className="metric-card">
                  <span className="metric-label">THEREFORE / BUT vs AND-THEN</span>
                  <div className="metric-value">
                    <span className="text-amber">{causalSummary.but_therefore_count ?? 0}</span>
                    <span className="text-dim"> / </span>
                    <span className="text-muted">{causalSummary.and_then_count ?? 0}</span>
                  </div>
                  <div className="metric-sub">
                    Ratio: {typeof causalSummary.but_therefore_ratio === 'number'
                      ? (causalSummary.but_therefore_ratio * 100).toFixed(0)
                      : '0'}% Consequential
                  </div>
                </div>

                <div className="metric-card wide">
                  <span className="metric-label">DIRECTOR PACING SIGNAL</span>
                  <p className="pacing-text">{causalSummary.pressure_recommendation || 'Balanced dramatic progression.'}</p>
                </div>
              </div>

              {/* Transition Breakdown */}
              <div className="causal-transitions-section">
                <h3 className="section-title">
                  CONSECUTIVE EVENT TRANSITIONS ({(causalSummary.transitions || []).length})
                </h3>
                {causalSummary.transitions && causalSummary.transitions.length > 0 ? (
                  <div className="transitions-list">
                    {causalSummary.transitions.map((t, idx) => (
                      <div
                        key={idx}
                        className={`transition-row ${t.transition_type === 'BUT_THEREFORE' || t.transition_type === 'THEREFORE' ? 'consequential' : 'episodic'}`}
                      >
                        <div className="trans-type-badge">
                          {t.transition_type === 'BUT_THEREFORE' || t.transition_type === 'THEREFORE'
                            ? 'THEREFORE / BUT'
                            : (t.transition_type ? String(t.transition_type).replace(/_/g, ' ') : 'AND THEN')}
                        </div>
                        <div className="trans-rationale">{t.rationale}</div>
                        <div className="trans-score">
                          {typeof t.score === 'number' ? `${(t.score * 100).toFixed(0)}%` : ''}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-quiet">NO CONSECUTIVE TRANSITIONS LOGGED.</div>
                )}
              </div>

              {/* Scenes Breakdown with Subtext and Performance Cues */}
              {scenes && scenes.length > 0 && (
                <div className="scenes-breakdown-section">
                  <h3 className="section-title">SCENES & DRAMATIC GROUNDING ({scenes.length})</h3>
                  <div className="scenes-cards-list">
                    {scenes.map((scene, idx) => {
                      const obj = scene.objective || scene.core_emotional_objective;
                      return (
                        <div key={scene.scene_id || idx} className="scene-card-item">
                          <div className="scene-card-header">
                            <span className="scene-heading-title">
                              {scene.heading || `SCENE ${idx + 1}`}
                            </span>
                            <span className="scene-purpose-badge">
                              {scene.purpose || scene.scene_purpose || 'DRAMATIC'}
                            </span>
                          </div>

                          {obj && (
                            <div className="scene-objective-box">
                              <div><strong>POV:</strong> {characters[obj.pov_character_id]?.name || obj.pov_character_id}</div>
                              {obj.wants && <div><strong>Wants:</strong> {obj.wants}</div>}
                              {obj.obstacle && <div><strong>Obstacle:</strong> {obj.obstacle}</div>}
                              {obj.outcome && <div><strong>Outcome:</strong> {obj.outcome}</div>}
                            </div>
                          )}

                          {/* Subtext Analyses */}
                          {scene.subtext_analyses && scene.subtext_analyses.length > 0 && (
                            <div className="scene-subtext-box">
                              <span className="subtext-header">DIALOGUE SUBTEXT ({scene.subtext_analyses.length})</span>
                              {scene.subtext_analyses.map((sub: any, sIdx: number) => (
                                <div key={sIdx} className="subtext-item">
                                  <span className="subtext-intent">[{sub.spoken_intent || sub.intent || 'SUBTEXT'}]</span>
                                  <span className="subtext-dialogue">"{sub.spoken_dialogue || sub.dialogue}"</span>
                                  {sub.private_truth && <span className="subtext-truth">Truth: {sub.private_truth}</span>}
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Performance Cues */}
                          {scene.performance_cues && scene.performance_cues.length > 0 && (
                            <div className="scene-cues-box">
                              <span className="cues-header">PERFORMANCE CUES ({scene.performance_cues.length})</span>
                              {scene.performance_cues.map((cue: any, cIdx: number) => (
                                <div key={cIdx} className="cue-item">
                                  <span className="cue-type">{cue.cue_type || cue.type || 'ACTION'}:</span>
                                  <span className="cue-action">{cue.observable_action || cue.action || cue.description}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="empty-quiet">NO CAUSALITY ANALYSIS AVAILABLE YET. RUN SIMULATION TICKS.</div>
          )}
        </div>
      )}
    </div>
  );
};

export const StructureAndArcsViewer: React.FC<StructureAndArcsViewerProps> = (props) => {
  return (
    <StructureErrorBoundary>
      <StructureAndArcsViewerContent {...props} />
    </StructureErrorBoundary>
  );
};
