import React, { useState, useEffect } from 'react';
import { WorldState, ArchetypeTrajectory, ConflictGraph, CharacterHistorySeries } from '../types';
import { formatDisplayValue } from '../utils/format';
import { ParticleHalo } from './granular';
import { CharacterWorkstation } from './CharacterWorkstation';
import * as api from '../api';

interface CharacterCardsProps {
  world: WorldState;
  projectId?: string;
  onCharacterCreated?: () => void;
}

export const CharacterCards: React.FC<CharacterCardsProps> = ({
  world,
  projectId,
  onCharacterCreated,
}) => {
  const [debugActive, setDebugActive] = useState<Record<string, boolean>>({});
  const [selectedCharId, setSelectedCharId] = useState<string | null>(null);
  const [showWorkstation, setShowWorkstation] = useState(false);
  const [trajectories, setTrajectories] = useState<Record<string, ArchetypeTrajectory>>({});
  const [loadingTraj, setLoadingTraj] = useState<Record<string, boolean>>({});
  const [conflictGraph, setConflictGraph] = useState<ConflictGraph | null>(null);
  const [loadingConflicts, setLoadingConflicts] = useState(false);
  const [expandedConflicts, setExpandedConflicts] = useState<Record<string, boolean>>({});
  const [expandedRelHistory, setExpandedRelHistory] = useState<Record<string, boolean>>({});
  const [relHistoryData, setRelHistoryData] = useState<Record<string, CharacterHistorySeries>>({});
  const [loadingRelHistory, setLoadingRelHistory] = useState<Record<string, boolean>>({});

  const characters = Object.values(world.characters || {});
  const locations = world.locations || {};
  const secrets = world.secrets || {};
  const beliefs = world.beliefs || {};
  const goals = world.goals || {};
  const relationships = world.relationships || {};

  useEffect(() => {
    const pid = projectId || world.id;
    if (pid) {
      api.getProjectConflicts(pid)
        .then((cg) => setConflictGraph(cg))
        .catch(() => {});
    }
  }, [projectId, world.id]);

  const handleDeriveConflicts = async () => {
    const pid = projectId || world.id;
    if (!pid) return;
    setLoadingConflicts(true);
    try {
      const cg = await api.deriveProjectConflicts(pid);
      setConflictGraph(cg);
    } catch (err) {
      console.error('Failed to derive conflicts:', err);
    } finally {
      setLoadingConflicts(false);
    }
  };

  const toggleDebug = (charId: string) => {
    setDebugActive((prev) => ({ ...prev, [charId]: !prev[charId] }));
  };

  const toggleArchetypeTrajectory = async (e: React.MouseEvent, charId: string) => {
    e.stopPropagation();
    if (trajectories[charId]) {
      setTrajectories((prev) => {
        const next = { ...prev };
        delete next[charId];
        return next;
      });
      return;
    }
    setLoadingTraj((prev) => ({ ...prev, [charId]: true }));
    try {
      const traj = await api.getCharacterArchetypeTrajectory(projectId || world.id, charId);
      setTrajectories((prev) => ({ ...prev, [charId]: traj }));
    } catch (err) {
      console.error('Failed to load archetype trajectory:', err);
    } finally {
      setLoadingTraj((prev) => ({ ...prev, [charId]: false }));
    }
  };

  const toggleRelHistory = async (e: React.MouseEvent, charAId: string, charBId: string, relId: string, dimension: string = 'trust') => {
    e.stopPropagation();
    const key = `${charAId}_${relId}_${dimension}`;
    if (expandedRelHistory[key]) {
      setExpandedRelHistory((prev) => ({ ...prev, [key]: false }));
      return;
    }
    setExpandedRelHistory((prev) => ({ ...prev, [key]: true }));
    if (relHistoryData[key]) return;
    setLoadingRelHistory((prev) => ({ ...prev, [key]: true }));
    try {
      const pid = projectId || world.id;
      const series = await api.getRelationshipDimensionHistory(pid, charAId, charBId, dimension, true);
      setRelHistoryData((prev) => ({ ...prev, [key]: series as CharacterHistorySeries }));
    } catch (err) {
      console.error('Failed to load relationship history:', err);
    } finally {
      setLoadingRelHistory((prev) => ({ ...prev, [key]: false }));
    }
  };

  const calculateStateWord = (fear: number, anger: number, trust: number) => {
    if (fear > 0.4) return 'Vigilant';
    if (anger > 0.3) return 'Hostile';
    if (trust > 0.4) return 'Cooperative';
    return 'Uneasy';
  };

  const renderGauge = (label: string, value: number, color: string) => {
    // Normalize -1.0 to 1.0 -> 0 to 100%
    const pct = Math.max(0, Math.min(100, Math.round(((value + 1) / 2) * 100)));
    return (
      <div className="emotion-row" key={label}>
        <span className="emotion-label">{label}</span>
        <div className="emotion-track">
          <div
            className="emotion-fill"
            style={{ width: `${pct}%`, background: color }}
          />
        </div>
        <span className="emotion-val">
          {pct}%
        </span>
      </div>
    );
  };

  return (
    <div className="actors-pane">
      <div className="pane-header">
        <div>
          <span className="pane-kicker">AUTONOMOUS AGENTS</span>
          <h2 className="pane-title">ACTORS</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="badge badge-subtle">{characters.length} ACTIVE</span>
          <button
            className="btn-secondary"
            onClick={handleDeriveConflicts}
            disabled={loadingConflicts}
            style={{ fontSize: '11px', padding: '6px 12px' }}
            title="Derive deterministic interpersonal conflict graph"
          >
            {loadingConflicts ? '⚡ Analyzing...' : '⚡ Analyze Conflicts'}
          </button>
          <button
            className={`btn-primary ${showWorkstation ? 'active' : ''}`}
            onClick={() => setShowWorkstation(!showWorkstation)}
            style={{ fontSize: '11px', padding: '6px 14px' }}
          >
            {showWorkstation ? '✕ Close Workstation' : '＋ Create Character'}
          </button>
        </div>
      </div>

      {showWorkstation && (
        <div style={{ marginBottom: '24px' }}>
          <CharacterWorkstation
            projectId={projectId || world.id}
            onCharacterCreated={() => {
              setShowWorkstation(false);
              onCharacterCreated?.();
            }}
            onCancel={() => setShowWorkstation(false)}
          />
        </div>
      )}
        {characters.map((char) => {
          const loc = locations[char.location_id];
          const isDebug = !!debugActive[char.id];
          const isSelected = selectedCharId === char.id;
          const emo = char.emotional_state || { happiness: 0, fear: 0, anger: 0, trust: 0, curiosity: 0.5 };
          const stateWord = calculateStateWord(emo.fear ?? 0, emo.anger ?? 0, emo.trust ?? 0);
          const charRelationships = Object.values(relationships).filter(
            (rel) => rel.character_a_id === char.id || rel.character_b_id === char.id
          );
          const charConflicts = (conflictGraph?.edges || []).filter(
            (edge) => edge.source_character_id === char.id || edge.target_character_id === char.id
          );

          return (
            <div
              className={`noir-actor-card ${isSelected ? 'selected-shot-granular-frame' : ''}`}
              key={char.id}
              onClick={() => setSelectedCharId(isSelected ? null : char.id)}
              style={{ position: 'relative', cursor: 'pointer' }}
              title="Click to focus character dossier"
            >
              <ParticleHalo
                active={isSelected}
                seed={char.id.charCodeAt(0) * 19}
                rx={130}
                ry={100}
                count={32}
              />
              <div className="actor-card-header" style={{ position: 'relative', zIndex: 1 }}>
                <div>
                  <h3 className="actor-name">{formatDisplayValue(char.name)}</h3>
                  <div className="actor-role">{formatDisplayValue(char.role)}</div>
                  {char.dynamics?.primary_archetype && (
                    <div className="actor-archetype-strip">
                      <span className="archetype-pill primary" title="Primary Archetype">
                        🏛️ {char.dynamics.primary_archetype}
                      </span>
                      {char.dynamics.secondary_archetype && (
                        <span className="archetype-pill secondary" title="Secondary Archetype">
                          ⚖️ {char.dynamics.secondary_archetype}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <div className="actor-status-tags">
                  <span className="actor-location-badge">
                    {formatDisplayValue(loc?.name || char.location_id)}
                  </span>
                  <span className="actor-state-indicator">
                    STATE: {stateWord.toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Emotional Gauges */}
              <div className="actor-emotions-box">
                {renderGauge('TRUST', emo.trust ?? 0, '#778899')}
                {renderGauge('FEAR', emo.fear ?? 0, '#fb7185')}
                {renderGauge('ANGER', emo.anger ?? 0, '#f97316')}
                {renderGauge('CURIOSITY', emo.curiosity ?? 0.5, '#D89C38')}
              </div>

              {/* Visual Identity & Continuity Profile */}
              {char.visual_profile && (
                <div className="actor-visual-profile-box">
                  <div className="profile-box-title">VISUAL IDENTITY PROFILE</div>
                  <div className="profile-detail-row">
                    <span className="profile-detail-label">ATTIRE:</span>
                    <span className="profile-detail-val">{formatDisplayValue(char.visual_profile.clothing)}</span>
                  </div>
                  <div className="profile-detail-row">
                    <span className="profile-detail-label">LOOKS:</span>
                    <span className="profile-detail-val">
                      {formatDisplayValue(`${char.visual_profile.age} • ${char.visual_profile.face_traits} • ${char.visual_profile.hairstyle}`)}
                    </span>
                  </div>
                  {char.visual_profile.signature_items && char.visual_profile.signature_items.length > 0 && (
                    <div className="profile-detail-row">
                      <span className="profile-detail-label">SIGNATURE:</span>
                      <span className="profile-detail-val text-amber">
                        {char.visual_profile.signature_items.join(', ')}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Goals */}
              <div className="actor-field-group">

                <span className="field-group-title">GOAL</span>
                <div className="actor-goal-list">
                  {(char.goals || []).map((gid) => {
                    const g = goals[gid];
                    return (
                      <div key={gid} className="actor-goal-item">
                        <span className="goal-bullet">▸</span>
                        <span>{formatDisplayValue(g?.description || g || gid)}</span>
                        {g?.progress !== undefined && (
                          <span className="goal-progress-badge">
                            {Math.round(g.progress * 100)}%
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Multidimensional Relationships (Phase D) */}
              {charRelationships.length > 0 && (
                <div className="actor-field-group">
                  <span className="field-group-title">RELATIONSHIPS</span>
                  <div className="actor-relationships-list">
                    {charRelationships.map((rel) => {
                      const otherId = rel.character_a_id === char.id ? rel.character_b_id : rel.character_a_id;
                      const otherChar = world.characters?.[otherId];
                      const otherName = otherChar?.name || otherId;

                      return (
                        <div key={rel.id} className="actor-relationship-card">
                          <div className="relationship-card-header">
                            <span className="relationship-peer-name">▸ {otherName}</span>
                            {rel.last_event_id && (
                              <span className="relationship-event-tag" title={`Updated by event: ${rel.last_event_id}`}>
                                evt: {rel.last_event_id.slice(-6)}
                              </span>
                            )}
                          </div>
                          {rel.history && (
                            <div className="relationship-history-snippet">{rel.history}</div>
                          )}
                          <div className="relationship-dimensions-grid">
                            <span className={`dim-pill ${rel.trust >= 0 ? 'pos' : 'neg'}`}>
                              Trust: {rel.trust > 0 ? `+${rel.trust.toFixed(2)}` : rel.trust.toFixed(2)}
                            </span>
                            <span className={`dim-pill ${rel.affinity >= 0 ? 'pos' : 'neg'}`}>
                              Affinity: {rel.affinity > 0 ? `+${rel.affinity.toFixed(2)}` : rel.affinity.toFixed(2)}
                            </span>
                            {rel.affection !== undefined && rel.affection !== 0 && (
                              <span className={`dim-pill ${rel.affection >= 0 ? 'pos' : 'neg'}`}>
                                Affection: {rel.affection > 0 ? `+${rel.affection.toFixed(2)}` : rel.affection.toFixed(2)}
                              </span>
                            )}
                            {rel.fear !== undefined && rel.fear !== 0 && (
                              <span className="dim-pill neg">
                                Fear: {rel.fear > 0 ? `+${rel.fear.toFixed(2)}` : rel.fear.toFixed(2)}
                              </span>
                            )}
                            {rel.respect !== undefined && rel.respect !== 0 && (
                              <span className={`dim-pill ${rel.respect >= 0 ? 'pos' : 'neg'}`}>
                                Respect: {rel.respect > 0 ? `+${rel.respect.toFixed(2)}` : rel.respect.toFixed(2)}
                              </span>
                            )}
                            {rel.resentment !== undefined && rel.resentment !== 0 && (
                              <span className="dim-pill neg">
                                Resentment: {rel.resentment > 0 ? `+${rel.resentment.toFixed(2)}` : rel.resentment.toFixed(2)}
                              </span>
                            )}
                            {rel.suspicion !== undefined && rel.suspicion !== 0 && (
                              <span className="dim-pill neg">
                                Suspicion: {rel.suspicion > 0 ? `+${rel.suspicion.toFixed(2)}` : rel.suspicion.toFixed(2)}
                              </span>
                            )}
                            {rel.dependency !== undefined && rel.dependency !== 0 && (
                              <span className="dim-pill neutral">
                                Dependency: {rel.dependency > 0 ? `+${rel.dependency.toFixed(2)}` : rel.dependency.toFixed(2)}
                              </span>
                            )}
                            {rel.power_imbalance !== undefined && rel.power_imbalance !== 0 && (
                              <span className="dim-pill neutral">
                                Power: {rel.power_imbalance > 0 ? `+${rel.power_imbalance.toFixed(2)}` : rel.power_imbalance.toFixed(2)}
                              </span>
                            )}
                          </div>
                          <div className="relationship-timeline-control" style={{ marginTop: '8px' }}>
                            <button
                              type="button"
                              className="btn-history-toggle"
                              style={{
                                fontSize: '0.72rem',
                                padding: '2px 8px',
                                background: 'rgba(255,255,255,0.06)',
                                border: '1px solid rgba(255,255,255,0.15)',
                                borderRadius: '4px',
                                color: '#aaa',
                                cursor: 'pointer',
                              }}
                              onClick={(e) => toggleRelHistory(e, char.id, otherId, rel.id, 'trust')}
                              title="View reconstructed trust timeline with event provenance"
                            >
                              {expandedRelHistory[`${char.id}_${rel.id}_trust`] ? '▾ Hide History' : '▸ Trust History'}
                            </button>
                            {expandedRelHistory[`${char.id}_${rel.id}_trust`] && (
                              <div
                                className="rel-history-timeline"
                                style={{
                                  marginTop: '6px',
                                  padding: '6px 8px',
                                  background: 'rgba(0,0,0,0.25)',
                                  borderRadius: '4px',
                                  borderLeft: '2px solid #58a6ff',
                                  fontSize: '0.75rem',
                                }}
                              >
                                {loadingRelHistory[`${char.id}_${rel.id}_trust`] ? (
                                  <span className="text-muted">Reconstructing history...</span>
                                ) : relHistoryData[`${char.id}_${rel.id}_trust`]?.points ? (
                                  <div className="history-points-list">
                                    {relHistoryData[`${char.id}_${rel.id}_trust`].points.map((pt, pIdx) => (
                                      <div
                                        key={pIdx}
                                        className="history-point-row"
                                        style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}
                                      >
                                        <span className="history-tick font-mono" style={{ color: '#888', minWidth: '42px' }}>
                                          {`T+${pt.tick}`}
                                        </span>
                                        <span
                                          className={`history-value font-mono ${pt.value >= 0 ? 'text-green' : 'text-red'}`}
                                          style={{ fontWeight: 600, minWidth: '45px' }}
                                        >
                                          {pt.value > 0 ? `+${pt.value.toFixed(2)}` : pt.value.toFixed(2)}
                                        </span>
                                        {pt.event_ids && pt.event_ids.length > 0 && (
                                          <span
                                            className="history-event-badge"
                                            style={{
                                              padding: '1px 4px',
                                              borderRadius: '3px',
                                              background: 'rgba(88,166,255,0.15)',
                                              color: '#58a6ff',
                                              fontSize: '0.7rem',
                                            }}
                                            title={pt.label || undefined}
                                          >
                                            {`evt:${pt.event_ids.map((id) => (id.length > 8 ? id.slice(-6) : id)).join(',')}`}
                                          </span>
                                        )}
                                        {pt.label && (
                                          <span
                                            className="history-label text-muted"
                                            style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                                            title={pt.label}
                                          >
                                            {pt.label}
                                          </span>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <span className="text-muted">No change points</span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* High-level Conflict Summary / Pairwise Intensity (Phase D) */}
              {charConflicts.length > 0 && (
                <div className="actor-field-group conflict-field-group">
                  <div className="conflict-section-header">
                    <span className="field-group-title text-amber">DRAMATIC CONFLICT (ANALYSIS)</span>
                    <span className="conflict-count-badge">
                      {charConflicts.length} EDGE{charConflicts.length > 1 ? 'S' : ''}
                      {conflictGraph?.derived_at_tick !== undefined && conflictGraph?.derived_at_tick !== null && (
                        <span className="conflict-tick-badge" style={{ marginLeft: '6px' }}>
                          (TICK {conflictGraph.derived_at_tick})
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="actor-conflict-list">
                    {charConflicts.map((edge, idx) => {
                      const otherId = edge.source_character_id === char.id ? edge.target_character_id : edge.source_character_id;
                      const otherChar = world.characters?.[otherId];
                      const otherName = otherChar?.name || otherId;
                      const edgeKey = `${char.id}_${otherId}_${idx}`;
                      const isExpanded = !!expandedConflicts[edgeKey];
                      const pct = Math.round(edge.aggregate_intensity * 100);
                      const intensityClass = pct >= 70 ? 'high' : pct >= 40 ? 'medium' : 'low';

                      return (
                        <div key={edgeKey} className="actor-conflict-card">
                          <div
                            className="conflict-card-row"
                            onClick={() => setExpandedConflicts((prev) => ({ ...prev, [edgeKey]: !prev[edgeKey] }))}
                            style={{ cursor: 'pointer' }}
                          >
                            <div className="conflict-card-target">
                              <span className="conflict-target-bullet">⚡</span>
                              <span className="conflict-target-name">vs {otherName}</span>
                            </div>
                            <div className="conflict-card-badges">
                              {edge.is_locked && (
                                <span
                                  className="conflict-lock-pill"
                                  title="User-locked design premise preserved"
                                  style={{
                                    fontSize: '0.7em',
                                    background: '#332a1e',
                                    color: '#ffb74d',
                                    padding: '1px 5px',
                                    borderRadius: '3px',
                                    marginRight: '4px',
                                  }}
                                >
                                  LOCKED
                                </span>
                              )}
                              <span className={`conflict-intensity-pill ${intensityClass}`}>
                                {intensityClass.toUpperCase()} ({pct}%)
                              </span>
                              <span className="conflict-expand-icon">{isExpanded ? '▲' : '▼'}</span>
                            </div>
                          </div>
                          <div className="conflict-dimension-tags">
                            {Object.entries(edge.dimensions || {}).map(([dim, score]) => (
                              <span key={dim} className="conflict-dim-tag" title={`Score: ${score}`}>
                                {dim.replace(/_/g, ' ').toUpperCase()}
                              </span>
                            ))}
                          </div>
                          {isExpanded && edge.evidence && edge.evidence.length > 0 && (
                            <div className="conflict-evidence-panel">
                              <div className="conflict-evidence-title">TRACEABLE CONFLICT EVIDENCE</div>
                              <ul className="conflict-evidence-list">
                                {edge.evidence.map((ev, evIdx) => (
                                  <li key={evIdx} className="conflict-evidence-item">
                                    <span className="evidence-dim-badge">{ev.dimension.replace(/_/g, ' ')}</span>
                                    {ev.is_user_authored && (
                                      <span
                                        className="evidence-author-badge"
                                        style={{ fontSize: '0.7em', color: '#ffb74d', marginRight: '4px' }}
                                      >
                                        [USER DESIGN]
                                      </span>
                                    )}
                                    <span className="evidence-desc">{ev.description}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Private State Boundary Toggle */}
              <button
                className="btn-private-toggle"
                onClick={() => toggleDebug(char.id)}
                aria-expanded={isDebug}
              >
                {isDebug ? '▼ PRIVATE: Hide Boundaries' : '▶ PRIVATE (Inspect Private Boundaries: Secrets & Beliefs)'}
              </button>

              {/* Private State Details */}
              {isDebug && (
                <div className="actor-private-enclave">
                  <div className="private-kicker">STRICT KNOWLEDGE BOUNDARY — ISOLATED FROM PEERS</div>

                  <div className="private-block">
                    <span className="private-label text-amber">SECRETS</span>
                    <ul className="private-list">
                      {(char.secrets || []).map((sid) => {
                        const s = secrets[sid];
                        return (
                          <li key={sid}>
                            {formatDisplayValue(s?.statement || s || sid)}
                          </li>
                        );
                      })}
                    </ul>
                  </div>

                  <div className="private-block">
                    <span className="private-label text-technical">BELIEFS (SUBJECTIVE)</span>
                    <ul className="private-list">
                      {(char.beliefs || []).map((bid) => {
                        const b = beliefs[bid];
                        return (
                          <li key={bid}>
                            {formatDisplayValue(b?.statement || b || bid)}
                            {b && <span className="belief-conf"> ({Math.round(b.confidence * 100)}% confidence)</span>}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                </div>
              )}

              {/* Observational Archetype Trajectory Toggle */}
              <button
                className="btn-private-toggle"
                onClick={(e) => toggleArchetypeTrajectory(e, char.id)}
                aria-expanded={!!trajectories[char.id]}
                style={{ marginTop: '6px' }}
              >
                {loadingTraj[char.id]
                  ? '⌛ Loading Trajectory...'
                  : trajectories[char.id]
                  ? '▼ ARCHETYPE TRAJECTORY (Hide)'
                  : '▶ ARCHETYPE TRAJECTORY (Observational Alignment & Drift)'}
              </button>

              {/* Trajectory Details */}
              {trajectories[char.id] && (
                <div className="trajectory-container">
                  <div className="trajectory-header">
                    <span className="trajectory-title">
                      OBSERVED: {trajectories[char.id].current_dominant_archetype || trajectories[char.id].initial_archetype || 'NEUTRAL'}
                    </span>
                    <span className="trajectory-stability">
                      Stability: {Math.round(trajectories[char.id].stability_score * 100)}%
                    </span>
                  </div>
                  <div className="trajectory-summary-text">
                    {trajectories[char.id].trajectory_summary}
                  </div>
                  {trajectories[char.id].shift_points && trajectories[char.id].shift_points.length > 0 ? (
                    <div className="shift-points-list">
                      {trajectories[char.id].shift_points.map((sp, idx) => (
                        <div key={idx} className="shift-point-item">
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
                      No archetype shifts observed across current event history.
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
