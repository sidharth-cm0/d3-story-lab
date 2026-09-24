import React, { useState } from 'react';
import { WorldState } from '../types';
import { formatDisplayValue } from '../utils/format';
import { ParticleHalo } from './granular';
import { CharacterWorkstation } from './CharacterWorkstation';

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

  const characters = Object.values(world.characters || {});
  const locations = world.locations || {};
  const secrets = world.secrets || {};
  const beliefs = world.beliefs || {};
  const goals = world.goals || {};

  const toggleDebug = (charId: string) => {
    setDebugActive((prev) => ({ ...prev, [charId]: !prev[charId] }));
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
            </div>
          );
        })}
      </div>
    </div>
  );
};
