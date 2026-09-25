import React, { useRef, useEffect, useState } from 'react';
import { WorldState, Event, EventCausality } from '../types';
import { formatDisplayValue } from '../utils/format';
import { ParticleDivider } from './granular';

interface SimulationTickerProps {
  world: WorldState;
  events: Event[];
  onStep: (ticks: number) => Promise<void>;
  onRun: (numTicks: number) => Promise<void>;
  loading: boolean;
  onReset?: () => void;
}

export const SimulationTicker: React.FC<SimulationTickerProps> = ({
  world,
  events,
  onStep,
  onRun,
  loading,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  // Auto-select latest event if none selected
  useEffect(() => {
    if (events.length > 0 && !selectedEventId) {
      setSelectedEventId(events[events.length - 1].id);
    }
  }, [events, selectedEventId]);

  useEffect(() => {
    if (typeof bottomRef.current?.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events.length]);

  const selectedEvent = events.find((e) => e.id === selectedEventId) || (events.length > 0 ? events[events.length - 1] : null);

  const getEventCausality = (ev: Event | null): EventCausality | null => {
    if (!ev) return null;

    const isDirector = !!ev.metadata?.incident_type || ev.event_type === 'environment_incident' || ev.source === 'DIRECTOR';
    if (isDirector) {
      const inc = ev.metadata?.incident_type || ev.metadata?.director_intervention || 'INCIDENT';
      const trigger = ev.metadata?.trigger_signal;
      let goalDesc = 'Inject dramatic tension and eliminate conversational stagnation';
      let beliefStmt = 'Sandbox stagnation detected without recent state change';
      let delta = 'Ambient pressure applied; actor physical affordances disrupted';

      if (trigger === 'unresolved_conflict' || trigger === 'unresolved_conflict_separated') {
        const src = ev.metadata?.conflict_source ? formatDisplayValue(ev.metadata.conflict_source) : 'Actor A';
        const tgt = ev.metadata?.conflict_target ? formatDisplayValue(ev.metadata.conflict_target) : 'Actor B';
        const intensity = ev.metadata?.conflict_intensity !== undefined ? `${Math.round(Number(ev.metadata.conflict_intensity) * 100)}%` : 'elevated';
        goalDesc = `Apply environmental catalyst for unresolved conflict between ${src} and ${tgt}`;
        beliefStmt = `Unresolved interpersonal conflict detected (intensity: ${intensity})`;
        delta = `Environmental pressure injected: ${ev.metadata?.director_intervention || inc}; actors must adapt to new world constraint`;
      } else if (trigger === 'stalled_relationship') {
        const dim = ev.metadata?.tension_dimension || 'suspicion';
        goalDesc = 'Disrupt stalled confrontation and catalyze active dialogue';
        beliefStmt = `Actors co-located with high latent ${dim} without recent movement`;
        delta = 'Auditory / spatial jolt injected to force character situational response';
      } else if (trigger === 'dramatic_need_opportunity') {
        const theme = ev.metadata?.theme || 'moral choice';
        goalDesc = `Present environmental opportunity aligned with character dramatic need (${theme})`;
        beliefStmt = 'Character thematic growth opportunity surfaced in environment';
        delta = 'New clue or information affordance introduced into scene';
      }

      return {
        eventId: ev.id,
        actorName: 'DIRECTOR AGENT',
        actorRole: 'Environmental Pacing Engine',
        goalDescription: goalDesc,
        beliefStatement: beliefStmt,
        memoryExcerpt: trigger ? `Dramatic trigger: ${formatDisplayValue(trigger)}` : 'Pacing evaluation triggered environmental intervention',
        emotionalSummary: `Pacing Urgency: ${ev.metadata?.urgency ? formatDisplayValue(ev.metadata.urgency).toUpperCase() : 'HIGH'}`,
        actionSummary: `Injected environmental intervention: ${inc}`,
        resultSummary: ev.description,
        stateDelta: delta,
      };
    }

    const actorId = ev.actor_ids[0];
    const actor = actorId ? world.characters[actorId] : null;
    const actorName = actor ? formatDisplayValue(actor.name || actor) : 'Unknown Actor';
    const actorRole = actor ? formatDisplayValue(actor.role) : 'Observer';

    const goalId = actor?.goals?.[0];
    const goal = goalId ? world.goals[goalId] : null;
    const goalDesc = goal ? formatDisplayValue(goal.description || goal) : 'Advance survival and investigate situation';

    const beliefId = actor?.beliefs?.[0];
    const belief = beliefId ? world.beliefs[beliefId] : null;
    const beliefStmt = belief ? formatDisplayValue(belief.statement || belief) : 'Assessing peer motives and environmental clues';

    const emo = actor?.emotional_state;
    const emoStr = emo
      ? `Trust: ${Math.round(((emo.trust + 1) / 2) * 100)}% | Fear: ${Math.round(((emo.fear + 1) / 2) * 100)}% | Anger: ${Math.round(((emo.anger + 1) / 2) * 100)}%`
      : 'Measured alertness';

    const speechAct = ev.metadata?.speech_act;
    let stateDelta = 'Action verified and appended to immutable event log';
    if (speechAct === 'accuse') stateDelta = 'Trust -15%, Tension escalated';
    else if (speechAct === 'reveal') stateDelta = 'Secret exposed; Goal progress +35%';
    else if (speechAct === 'cooperate') stateDelta = 'Alliance formed; Trust +25%';
    else if (speechAct === 'deny') stateDelta = 'Evasion registered; Suspicion +10%';
    else if (ev.event_type.includes('picked_up')) stateDelta = 'Object moved into actor inventory';
    else if (ev.event_type.includes('moved')) stateDelta = 'Spatial position updated in topology';

    const locName = world.locations[ev.location_id || '']?.name || 'sandbox';

    return {
      eventId: ev.id,
      actorName,
      actorRole,
      goalDescription: goalDesc,
      beliefStatement: beliefStmt,
      memoryExcerpt: `Perceived co-located entities in ${formatDisplayValue(locName)}`,
      emotionalSummary: emoStr,
      actionSummary: formatDisplayValue(ev.description),
      resultSummary: speechAct ? `Expressed intent [${speechAct.toUpperCase()}]: ${formatDisplayValue(ev.description)}` : formatDisplayValue(ev.description),
      stateDelta,
    };
  };

  const causality = getEventCausality(selectedEvent);

  const getEventBadgeClass = (ev: Event) => {
    if (ev.metadata?.trigger_signal || ev.metadata?.incident_type || ev.event_type === 'environment_incident' || ev.source === 'DIRECTOR') return 'badge-director-amber';
    if (ev.event_type === 'character_spoke') return 'badge-spoke-dim';
    if (ev.event_type === 'character_moved') return 'badge-moved-dim';
    if (ev.event_type.includes('object') || ev.event_type === 'character_observed') return 'badge-object-dim';
    return 'badge-other-dim';
  };

  const getEventTag = (ev: Event) => {
    if (ev.metadata?.trigger_signal === 'unresolved_conflict') return 'DIRECTOR: CONFLICT CATALYST';
    if (ev.metadata?.trigger_signal === 'stalled_relationship') return 'DIRECTOR: TENSION JOLT';
    if (ev.metadata?.trigger_signal === 'dramatic_need_opportunity') return 'DIRECTOR: NEED CATALYST';
    if (ev.metadata?.incident_type) return `DIRECTOR: ${ev.metadata.incident_type}`;
    if (ev.metadata?.speech_act) return `SPEAK: ${ev.metadata.speech_act}`;
    return ev.event_type.replace(/_/g, ' ');
  };

  return (
    <div className="cinematic-sim-view">
      {/* Simulation Top Toolbar */}
      <div className="sim-console-toolbar">
        <div className="toolbar-stats-group">
          <div className="stat-pill">
            <span className="pill-lbl">TICK</span>
            <strong className="pill-num">T{world.current_tick}</strong>
          </div>
          <div className="stat-pill">
            <span className="pill-lbl">EVENTS</span>
            <strong className="pill-num">{events.length}</strong>
          </div>
          <div className="stat-pill">
            <span className="pill-lbl">ACTORS</span>
            <strong className="pill-num">{Object.keys(world.characters || {}).length}</strong>
          </div>
          {events.some((e) => e.metadata?.trigger_signal) && (
            <div className="stat-pill text-amber" title="Director dramatic interventions logged">
              <span className="pill-lbl">DRAMA INJECTIONS</span>
              <strong className="pill-num">{events.filter((e) => e.metadata?.trigger_signal).length}</strong>
            </div>
          )}
        </div>

        <div className="toolbar-actions-group">
          <button
            className="btn-cinematic-secondary"
            onClick={() => onStep(1)}
            disabled={loading}
          >
            Step 1 Tick
          </button>
          <button
            className="btn-cinematic-secondary"
            onClick={() => onStep(5)}
            disabled={loading}
          >
            Step 5 Ticks
          </button>
          <button
            className="btn-cinematic-accent"
            onClick={() => onRun(10)}
            disabled={loading}
          >
            Run 10 Ticks
          </button>
        </div>
      </div>

      {/* 3-Column Workstation Grid */}
      <div className="sim-three-col-grid">
        {/* COLUMN 1: Actor Quick Status */}
        <aside className="sim-actor-col">
          <div className="col-header-bar">
            <span>ACTORS</span>
            <span className="text-muted">{Object.keys(world.characters || {}).length}</span>
          </div>

          <div className="actor-mini-list">
            {Object.values(world.characters || {}).map((char) => {
              const loc = world.locations[char.location_id];
              const goal = char.goals[0] ? world.goals[char.goals[0]] : null;
              return (
                <div key={char.id} className="actor-mini-card">
                  <div className="mini-card-top">
                    <strong className="mini-name">{formatDisplayValue(char.name)}</strong>
                    <span className="mini-role">{formatDisplayValue(char.role)}</span>
                  </div>
                  <div className="mini-loc">📍 {formatDisplayValue(loc?.name || char.location_id)}</div>
                  {goal && (
                    <div className="mini-goal">
                      <span className="text-muted">GOAL: </span>
                      {formatDisplayValue(goal.description || goal)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </aside>

        {/* COLUMN 2: Minimal Event Stream */}
        <section className="sim-event-col">
          <div className="col-header-bar">
            <span>EVENT STREAM</span>
            <span className="text-muted">IMMUTABLE LOG</span>
          </div>

          <div className="sim-events-scroll">
            {events.length === 0 ? (
              <div className="empty-stream-notice">
                <div className="stream-crosshair">❖</div>
                <p>SIMULATION STANDBY</p>
                <span>Trigger Step or Run to begin autonomous agent loop.</span>
              </div>
            ) : (
              events.map((ev) => {
                const isSelected = selectedEvent?.id === ev.id;
                const isDirector = !!ev.metadata?.incident_type || ev.event_type === 'environment_incident';

                return (
                  <div
                    key={ev.id}
                    className={`stream-event-item ${isSelected ? 'selected' : ''} ${isDirector ? 'director-highlight' : ''}`}
                    onClick={() => setSelectedEventId(ev.id)}
                    role="button"
                    tabIndex={0}
                  >
                    <span className="event-tick-badge">T{ev.tick}</span>
                    <span className={`event-type-badge ${getEventBadgeClass(ev)}`}>
                      {getEventTag(ev)}
                    </span>
                    <div className="event-text">
                      {formatDisplayValue(ev.description)}
                    </div>
                  </div>
                );
              })
            )}
            <div ref={bottomRef} />
          </div>
        </section>

        {/* COLUMN 3: Causality Inspector */}
        <aside className="sim-causality-col">
          <div className="col-header-bar">
            <span>CAUSALITY INSPECTOR</span>
            <span className="text-amber">WHY DID THIS HAPPEN?</span>
          </div>

          {causality ? (
            <div className="causality-card">
              <div className="causality-header">
                <div>
                  <div className="causality-actor">{formatDisplayValue(causality.actorName)}</div>
                  <div className="causality-role">{formatDisplayValue(causality.actorRole)}</div>
                </div>
                <span className="causality-tick-id">{formatDisplayValue(causality.eventId)}</span>
              </div>

              <div className="causal-step-block">
                <span className="causal-label text-amber">GOAL</span>
                <div className="causal-content">{formatDisplayValue(causality.goalDescription)}</div>
              </div>

              <ParticleDivider seed={101} count={20} height={12} width="100%" />

              <div className="causal-step-block">
                <span className="causal-label text-technical">BELIEF</span>
                <div className="causal-content">{formatDisplayValue(causality.beliefStatement)}</div>
              </div>

              <ParticleDivider seed={102} count={20} height={12} width="100%" />

              <div className="causal-step-block">
                <span className="causal-label">MEMORY</span>
                <div className="causal-content text-muted">{formatDisplayValue(causality.memoryExcerpt)}</div>
              </div>

              <div className="causal-step-block">
                <span className="causal-label">EMOTION</span>
                <div className="causal-content">{formatDisplayValue(causality.emotionalSummary)}</div>
              </div>

              <ParticleDivider seed={103} count={20} height={12} width="100%" />

              <div className="causal-step-block">
                <span className="causal-label text-white">ACTION / RESULT</span>
                <div className="causal-content font-bold">Outcome: {formatDisplayValue(causality.resultSummary)}</div>
              </div>

              <div className="causal-step-block state-delta-block">
                <span className="causal-label text-amber">STATE CHANGE</span>
                <div className="causal-content">{formatDisplayValue(causality.stateDelta)}</div>
              </div>
            </div>
          ) : (
            <div className="empty-causality-notice">
              <span>Select an event from the stream to inspect underlying causal factors.</span>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
};
