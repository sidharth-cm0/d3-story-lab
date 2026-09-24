import React, { useState } from 'react';
import {
  CharacterProfileDraft,
  CompletenessReport,
  FieldAuthority,
} from '../types';
import * as api from '../api';

interface CharacterWorkstationProps {
  projectId: string;
  onCharacterCreated?: (characterId: string) => void;
  onCancel?: () => void;
}

type IntakeMode = 'quick' | 'guided';
type WorkstationStep = 'input' | 'review';

export const CharacterWorkstation: React.FC<CharacterWorkstationProps> = ({
  projectId,
  onCharacterCreated,
  onCancel,
}) => {
  const [step, setStep] = useState<WorkstationStep>('input');
  const [mode, setMode] = useState<IntakeMode>('quick');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Quick mode state
  const [rawText, setRawText] = useState('');

  // Guided mode state
  const [formName, setFormName] = useState('');
  const [formRole, setFormRole] = useState('');
  const [formGoals, setFormGoals] = useState('');
  const [formSecrets, setFormSecrets] = useState('');
  const [formBeliefs, setFormBeliefs] = useState('');
  const [formTraits, setFormTraits] = useState('');
  const [formClothing, setFormClothing] = useState('');
  const [lockedFields, setLockedFields] = useState<Record<string, boolean>>({
    name: false,
    role: false,
    goals: false,
    secrets: false,
    beliefs: false,
    traits: false,
    clothing: false,
  });

  // Review mode state
  const [draft, setDraft] = useState<CharacterProfileDraft | null>(null);
  const [completeness, setCompleteness] = useState<CompletenessReport | null>(null);

  const toggleFieldLockInForm = (field: string) => {
    setLockedFields((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const handleNormalize = async () => {
    setError(null);
    setLoading(true);
    try {
      let res;
      if (mode === 'quick') {
        if (!rawText.trim()) {
          setError('Please enter a character description.');
          setLoading(false);
          return;
        }
        res = await api.intakeCharacter(projectId, rawText, undefined, false);
      } else {
        if (!formName.trim() && !formRole.trim()) {
          setError('Please provide at least a name or role.');
          setLoading(false);
          return;
        }
        const activeLocks = Object.keys(lockedFields).filter((k) => lockedFields[k]);
        const payload: Record<string, any> = {
          name: formName.trim() || undefined,
          role: formRole.trim() || undefined,
          goals: formGoals.trim() ? formGoals.split('\n').filter(Boolean) : undefined,
          secrets: formSecrets.trim() ? formSecrets.split('\n').filter(Boolean) : undefined,
          beliefs: formBeliefs.trim() ? formBeliefs.split('\n').filter(Boolean) : undefined,
          personality_traits: formTraits.trim() ? formTraits.split(',').map((t) => t.trim()).filter(Boolean) : undefined,
          visual_profile: formClothing.trim() ? { clothing: formClothing.trim() } : undefined,
          locked_fields: activeLocks,
        };
        res = await api.intakeCharacter(projectId, undefined, payload, false);
      }

      setDraft(res.draft);
      setCompleteness(res.completeness);
      setStep('review');
    } catch (err: any) {
      setError(err.message || 'Failed to normalize character');
    } finally {
      setLoading(false);
    }
  };

  const handleEnrich = async () => {
    if (!draft) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.enrichCharacterDraft(projectId, draft.id);
      setDraft(res.draft);
      setCompleteness(res.completeness);
    } catch (err: any) {
      setError(err.message || 'Failed to enrich character');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleLockInReview = async (fieldName: string) => {
    if (!draft) return;
    setError(null);
    try {
      const isCurrentlyLocked = draft.provenance[fieldName]?.authority === 'USER_LOCKED';
      if (isCurrentlyLocked) {
        const res = await api.unlockCharacterField(projectId, draft.id, fieldName);
        setDraft(res.draft);
      } else {
        const res = await api.lockCharacterField(projectId, draft.id, fieldName);
        setDraft(res.draft);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to toggle lock');
    }
  };

  const handleAccept = async () => {
    if (!draft) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.acceptCharacterDraft(projectId, draft.id);
      if (onCharacterCreated) {
        onCharacterCreated(res.character_id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to accept character');
    } finally {
      setLoading(false);
    }
  };

  const renderAuthorityBadge = (authority?: FieldAuthority) => {
    switch (authority) {
      case 'USER_LOCKED':
        return <span className="auth-badge badge-locked" title="User Locked: Immune to enrichment">🔒 LOCKED</span>;
      case 'USER_PREFERRED':
        return <span className="auth-badge badge-user" title="User Provided: Won't be replaced">👤 USER</span>;
      case 'SYSTEM_INFERRED':
        return <span className="auth-badge badge-inferred" title="System Inferred from context">⚡ INFERRED</span>;
      case 'SYSTEM_GENERATED':
        return <span className="auth-badge badge-generated" title="System Generated default">⚙️ GENERATED</span>;
      default:
        return <span className="auth-badge badge-empty">MISSING</span>;
    }
  };

  return (
    <div className="character-workstation-container">
      {/* Header */}
      <div className="workstation-header">
        <div>
          <span className="pane-kicker">DESIGN-TIME AUTHORIZATION</span>
          <h2 className="pane-title">CHARACTER WORKSTATION</h2>
        </div>
        <div className="workstation-header-actions">
          {onCancel && (
            <button className="btn-cancel" onClick={onCancel} disabled={loading}>
              ✕ Cancel
            </button>
          )}
        </div>
      </div>

      {error && <div className="workstation-error-banner">{error}</div>}

      {/* STEP 1: INPUT MODE */}
      {step === 'input' && (
        <div className="workstation-input-step">
          {/* Mode Switcher */}
          <div className="workstation-mode-tabs">
            <button
              className={`mode-tab ${mode === 'quick' ? 'active' : ''}`}
              onClick={() => setMode('quick')}
            >
              ✍️ Quick Description (NL)
            </button>
            <button
              className={`mode-tab ${mode === 'guided' ? 'active' : ''}`}
              onClick={() => setMode('guided')}
            >
              📋 Guided Profile (Form)
            </button>
          </div>

          {/* Quick Description Mode */}
          {mode === 'quick' && (
            <div className="workstation-mode-content">
              <label className="input-label">
                Natural-Language Character Narrative:
              </label>
              <textarea
                className="workstation-textarea"
                rows={6}
                placeholder="e.g. Detective Marcus Vance, a cynical 42-year-old homicide investigator with a dark trench coat. He wants to solve the waterfront murder case. Secretly, he was at the docks the night of the crime. Cautious, observant, and distrusting."
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
              />

              <div className="quick-templates-box">
                <span className="templates-label">Quick Starter Examples:</span>
                <div className="template-chips">
                  <button
                    type="button"
                    className="template-chip"
                    onClick={() =>
                      setRawText(
                        'Detective Marcus Vance, a cynical 42-year-old homicide investigator with a dark wool trench coat. He wants to solve the waterfront murder case. Secretly, he was at the docks the night of the crime. He believes his partner is hiding evidence. Cautious, observant, and distrusting.'
                      )
                    }
                  >
                    🔍 Homicide Detective
                  </button>
                  <button
                    type="button"
                    className="template-chip"
                    onClick={() =>
                      setRawText(
                        'Elena Rostova: Cyber security analyst. Goal: Expose the corporation\'s data breach. Fear/Secret: Her brother wrote the exploit code. Belief: Corporate security is tracking her phone. Personality: Analytical, guarded, relentless.'
                      )
                    }
                  >
                    💻 Security Analyst
                  </button>
                  <button
                    type="button"
                    className="template-chip"
                    onClick={() =>
                      setRawText(
                        'Courier Jax: Fast and street-smart runner in reinforced leather jacket. Goal: Deliver the mysterious locked canister before midnight. Secret: The canister contains illegal biotech samples. Personality: Agile, alert, secretive.'
                      )
                    }
                  >
                    📦 High-Stakes Courier
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Guided Profile Mode */}
          {mode === 'guided' && (
            <div className="workstation-mode-content guided-grid">
              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Character Name *</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.name}
                      onChange={() => toggleFieldLockInForm('name')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <input
                  type="text"
                  className="workstation-input"
                  placeholder="e.g. Marcus Vance"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
              </div>

              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Role / Profession *</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.role}
                      onChange={() => toggleFieldLockInForm('role')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <input
                  type="text"
                  className="workstation-input"
                  placeholder="e.g. Forensic Investigator"
                  value={formRole}
                  onChange={(e) => setFormRole(e.target.value)}
                />
              </div>

              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Primary Goals (one per line)</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.goals}
                      onChange={() => toggleFieldLockInForm('goals')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <textarea
                  className="workstation-textarea-small"
                  rows={2}
                  placeholder="e.g. Recover the classified files&#10;Verify courier identity"
                  value={formGoals}
                  onChange={(e) => setFormGoals(e.target.value)}
                />
              </div>

              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Secret / Fear (private knowledge)</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.secrets}
                      onChange={() => toggleFieldLockInForm('secrets')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <textarea
                  className="workstation-textarea-small"
                  rows={2}
                  placeholder="e.g. Was present at the warehouse before police arrived"
                  value={formSecrets}
                  onChange={(e) => setFormSecrets(e.target.value)}
                />
              </div>

              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Subjective Beliefs</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.beliefs}
                      onChange={() => toggleFieldLockInForm('beliefs')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <textarea
                  className="workstation-textarea-small"
                  rows={2}
                  placeholder="e.g. The department has an informant"
                  value={formBeliefs}
                  onChange={(e) => setFormBeliefs(e.target.value)}
                />
              </div>

              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Personality Traits (comma-separated)</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.traits}
                      onChange={() => toggleFieldLockInForm('traits')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <input
                  type="text"
                  className="workstation-input"
                  placeholder="e.g. Cautious, observant, distrusting"
                  value={formTraits}
                  onChange={(e) => setFormTraits(e.target.value)}
                />
              </div>

              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Visual Identity / Attire</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.clothing}
                      onChange={() => toggleFieldLockInForm('clothing')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <input
                  type="text"
                  className="workstation-input"
                  placeholder="e.g. Charcoal trench coat over dark collared shirt"
                  value={formClothing}
                  onChange={(e) => setFormClothing(e.target.value)}
                />
              </div>
            </div>
          )}

          {/* Input Actions Footer */}
          <div className="workstation-footer">
            <button
              className="btn-primary"
              onClick={handleNormalize}
              disabled={loading}
            >
              {loading ? 'Normalizing...' : '⚡ Normalize & Review Profile'}
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: REVIEW PANEL WITH FIELD-LEVEL AUTHORITY */}
      {step === 'review' && draft && (
        <div className="workstation-review-step">
          {/* Completeness Meter Card */}
          <div className="completeness-card">
            <div className="completeness-header-row">
              <div>
                <span className="completeness-label">PROFILE COMPLETENESS</span>
                <div className="completeness-score-display">
                  <span className="score-num">{completeness?.score ?? 0}%</span>
                  <span className={`score-badge ${completeness?.is_complete ? 'badge-complete' : 'badge-partial'}`}>
                    {completeness?.is_complete ? 'READY FOR CAST' : 'PARTIAL DRAFT'}
                  </span>
                </div>
              </div>
              <button
                className="btn-enrich"
                onClick={handleEnrich}
                disabled={loading}
                title="Deterministically populate missing and unlocked fields based on role & premise"
              >
                {loading ? 'Enriching...' : '✨ Enrich Missing Fields'}
              </button>
            </div>

            {/* Visual Bar */}
            <div className="completeness-bar-track">
              <div
                className="completeness-bar-fill"
                style={{ width: `${completeness?.score ?? 0}%` }}
              />
            </div>

            {/* Missing Fields List */}
            {completeness && completeness.missing_fields.length > 0 && (
              <div className="missing-fields-box">
                <span className="missing-title">Missing Fields:</span>
                {completeness.missing_fields.map((mf) => (
                  <span key={mf} className="missing-tag">
                    {mf}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Fields Review Table / List */}
          <div className="review-fields-card">
            <div className="review-fields-header">
              <h3>FIELD-LEVEL AUTHORITY BREAKDOWN</h3>
              <span className="review-subtitle">
                User-defined fields are protected. Locked fields will never be overwritten.
              </span>
            </div>

            <div className="review-items-list">
              {/* Name */}
              <div className="review-item-row">
                <div className="review-item-main">
                  <span className="review-field-name">Name</span>
                  <div className="review-field-value">{draft.name || <em className="text-muted">None</em>}</div>
                  {draft.provenance.name?.source_snippet && (
                    <div className="review-field-snippet">Source: &quot;{draft.provenance.name.source_snippet}&quot;</div>
                  )}
                </div>
                <div className="review-item-controls">
                  {renderAuthorityBadge(draft.provenance.name?.authority)}
                  <button
                    className="btn-lock-toggle"
                    onClick={() => handleToggleLockInReview('name')}
                    title={draft.provenance.name?.authority === 'USER_LOCKED' ? 'Unlock field' : 'Lock field'}
                  >
                    {draft.provenance.name?.authority === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                  </button>
                </div>
              </div>

              {/* Role */}
              <div className="review-item-row">
                <div className="review-item-main">
                  <span className="review-field-name">Role / Profession</span>
                  <div className="review-field-value">{draft.role || <em className="text-muted">None</em>}</div>
                  {draft.provenance.role?.source_snippet && (
                    <div className="review-field-snippet">Source: &quot;{draft.provenance.role.source_snippet}&quot;</div>
                  )}
                </div>
                <div className="review-item-controls">
                  {renderAuthorityBadge(draft.provenance.role?.authority)}
                  <button
                    className="btn-lock-toggle"
                    onClick={() => handleToggleLockInReview('role')}
                  >
                    {draft.provenance.role?.authority === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                  </button>
                </div>
              </div>

              {/* Goals */}
              <div className="review-item-row">
                <div className="review-item-main">
                  <span className="review-field-name">Goals</span>
                  <div className="review-field-value">
                    {draft.goals && draft.goals.length > 0 ? (
                      <ul className="review-sublist">
                        {draft.goals.map((g, i) => (
                          <li key={i}>{g}</li>
                        ))}
                      </ul>
                    ) : (
                      <em className="text-muted">No goals specified</em>
                    )}
                  </div>
                  {draft.provenance.goals?.inference_rule && (
                    <div className="review-field-snippet">Rule: {draft.provenance.goals.inference_rule}</div>
                  )}
                </div>
                <div className="review-item-controls">
                  {renderAuthorityBadge(draft.provenance.goals?.authority)}
                  <button
                    className="btn-lock-toggle"
                    onClick={() => handleToggleLockInReview('goals')}
                  >
                    {draft.provenance.goals?.authority === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                  </button>
                </div>
              </div>

              {/* Secrets */}
              <div className="review-item-row">
                <div className="review-item-main">
                  <span className="review-field-name">Secrets (Private Knowledge)</span>
                  <div className="review-field-value">
                    {draft.secrets && draft.secrets.length > 0 ? (
                      <ul className="review-sublist">
                        {draft.secrets.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    ) : (
                      <em className="text-muted">No secrets specified</em>
                    )}
                  </div>
                  {draft.provenance.secrets?.inference_rule && (
                    <div className="review-field-snippet">Rule: {draft.provenance.secrets.inference_rule}</div>
                  )}
                </div>
                <div className="review-item-controls">
                  {renderAuthorityBadge(draft.provenance.secrets?.authority)}
                  <button
                    className="btn-lock-toggle"
                    onClick={() => handleToggleLockInReview('secrets')}
                  >
                    {draft.provenance.secrets?.authority === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                  </button>
                </div>
              </div>

              {/* Beliefs */}
              <div className="review-item-row">
                <div className="review-item-main">
                  <span className="review-field-name">Subjective Beliefs</span>
                  <div className="review-field-value">
                    {draft.beliefs && draft.beliefs.length > 0 ? (
                      <ul className="review-sublist">
                        {draft.beliefs.map((b, i) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>
                    ) : (
                      <em className="text-muted">No beliefs specified</em>
                    )}
                  </div>
                  {draft.provenance.beliefs?.inference_rule && (
                    <div className="review-field-snippet">Rule: {draft.provenance.beliefs.inference_rule}</div>
                  )}
                </div>
                <div className="review-item-controls">
                  {renderAuthorityBadge(draft.provenance.beliefs?.authority)}
                  <button
                    className="btn-lock-toggle"
                    onClick={() => handleToggleLockInReview('beliefs')}
                  >
                    {draft.provenance.beliefs?.authority === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                  </button>
                </div>
              </div>

              {/* Personality Traits */}
              <div className="review-item-row">
                <div className="review-item-main">
                  <span className="review-field-name">Personality Traits</span>
                  <div className="review-field-value">
                    {draft.personality_traits && Object.keys(draft.personality_traits).length > 0 ? (
                      <div className="trait-pill-cloud">
                        {Object.entries(draft.personality_traits).map(([k, v]) => (
                          <span key={k} className="trait-pill">
                            {k}: {Math.round(v * 100)}%
                          </span>
                        ))}
                      </div>
                    ) : (
                      <em className="text-muted">No traits specified</em>
                    )}
                  </div>
                  {draft.provenance.personality_traits?.inference_rule && (
                    <div className="review-field-snippet">Rule: {draft.provenance.personality_traits.inference_rule}</div>
                  )}
                </div>
                <div className="review-item-controls">
                  {renderAuthorityBadge(draft.provenance.personality_traits?.authority)}
                  <button
                    className="btn-lock-toggle"
                    onClick={() => handleToggleLockInReview('personality_traits')}
                  >
                    {draft.provenance.personality_traits?.authority === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                  </button>
                </div>
              </div>

              {/* Visual Profile */}
              <div className="review-item-row">
                <div className="review-item-main">
                  <span className="review-field-name">Visual Profile / Attire</span>
                  <div className="review-field-value">
                    {draft.visual_profile ? (
                      <div>
                        <div><strong>Attire:</strong> {draft.visual_profile.clothing}</div>
                        <div><strong>Face/Build:</strong> {draft.visual_profile.age}, {draft.visual_profile.face_traits}, {draft.visual_profile.build}</div>
                      </div>
                    ) : (
                      <em className="text-muted">No visual identity specified</em>
                    )}
                  </div>
                  {draft.provenance.visual_profile?.inference_rule && (
                    <div className="review-field-snippet">Rule: {draft.provenance.visual_profile.inference_rule}</div>
                  )}
                </div>
                <div className="review-item-controls">
                  {renderAuthorityBadge(draft.provenance.visual_profile?.authority)}
                  <button
                    className="btn-lock-toggle"
                    onClick={() => handleToggleLockInReview('visual_profile')}
                  >
                    {draft.provenance.visual_profile?.authority === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Action Controls */}
          <div className="review-actions-footer">
            <button
              className="btn-secondary"
              onClick={() => setStep('input')}
              disabled={loading}
            >
              ← Edit Raw Input
            </button>
            <button
              className="btn-primary"
              onClick={handleAccept}
              disabled={loading}
            >
              {loading ? 'Adding to Simulation...' : '✓ Accept & Add to Simulation Cast'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
