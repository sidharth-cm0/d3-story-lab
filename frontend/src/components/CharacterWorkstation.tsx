import React, { useState } from 'react';
import {
  CharacterProfileDraft,
  CompletenessReport,
  FieldAuthority,
  ArchetypeType,
} from '../types';
import * as api from '../api';

const ARCHETYPES: ArchetypeType[] = [
  'HERO',
  'RULER',
  'CAREGIVER',
  'CREATOR',
  'INNOCENT',
  'SAGE',
  'EXPLORER',
  'OUTLAW',
  'MAGICIAN',
  'LOVER',
  'JESTER',
  'EVERYMAN',
];

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
  const [formConsciousWant, setFormConsciousWant] = useState('');
  const [formDramaticNeed, setFormDramaticNeed] = useState('');
  const [formCoreValue, setFormCoreValue] = useState('');
  const [formFear, setFormFear] = useState('');
  const [formContradiction, setFormContradiction] = useState('');
  const [formPrimaryArchetype, setFormPrimaryArchetype] = useState<ArchetypeType | ''>('');
  const [formSecondaryArchetype, setFormSecondaryArchetype] = useState<ArchetypeType | ''>('');
  const [lockedFields, setLockedFields] = useState<Record<string, boolean>>({
    name: false,
    role: false,
    goals: false,
    secrets: false,
    beliefs: false,
    traits: false,
    clothing: false,
    conscious_want: false,
    dramatic_need: false,
    core_value: false,
    fear: false,
    contradiction: false,
    primary_archetype: false,
    secondary_archetype: false,
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
          conscious_want: formConsciousWant.trim() || undefined,
          dramatic_need: formDramaticNeed.trim() || undefined,
          core_value: formCoreValue.trim() || undefined,
          fear: formFear.trim() || undefined,
          contradiction: formContradiction.trim() || undefined,
          primary_archetype: formPrimaryArchetype || undefined,
          secondary_archetype: formSecondaryArchetype || undefined,
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

  const getFieldAuthority = (fieldName: string): FieldAuthority | undefined => {
    return draft?.provenance[fieldName]?.authority || draft?.dynamics?.provenance?.[fieldName]?.authority;
  };

  const handleToggleLockInReview = async (fieldName: string) => {
    if (!draft) return;
    setError(null);
    try {
      const isCurrentlyLocked = getFieldAuthority(fieldName) === 'USER_LOCKED';
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

  const handleProjectWant = async () => {
    if (!draft) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.projectDraftConsciousWant(projectId, draft.id);
      setDraft(res.draft);
      setCompleteness(res.completeness);
    } catch (err: any) {
      setError(err.message || 'Failed to project conscious want to goals');
    } finally {
      setLoading(false);
    }
  };

  const handleInferArchetypes = async () => {
    if (!draft) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.inferDraftArchetype(projectId, draft.id);
      setDraft(res.draft);
      setCompleteness(res.completeness);
    } catch (err: any) {
      setError(err.message || 'Failed to infer archetypes');
    } finally {
      setLoading(false);
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

              {/* Guided Mode Character Dynamics Fields */}
              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Conscious Want (Projects to Active Goal)</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.conscious_want}
                      onChange={() => toggleFieldLockInForm('conscious_want')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <input
                  type="text"
                  className="workstation-input"
                  placeholder="e.g. Expose the classified transaction ledger"
                  value={formConsciousWant}
                  onChange={(e) => setFormConsciousWant(e.target.value)}
                />
              </div>

              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Dramatic Need (Analytical Only — Not Simulation Goal)</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.dramatic_need}
                      onChange={() => toggleFieldLockInForm('dramatic_need')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <input
                  type="text"
                  className="workstation-input"
                  placeholder="e.g. Learn to accept vulnerability and trust allies"
                  value={formDramaticNeed}
                  onChange={(e) => setFormDramaticNeed(e.target.value)}
                />
              </div>

              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Core Value</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.core_value}
                      onChange={() => toggleFieldLockInForm('core_value')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <input
                  type="text"
                  className="workstation-input"
                  placeholder="e.g. Truth and accountability"
                  value={formCoreValue}
                  onChange={(e) => setFormCoreValue(e.target.value)}
                />
              </div>

              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Deepest Fear</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.fear}
                      onChange={() => toggleFieldLockInForm('fear')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <input
                  type="text"
                  className="workstation-input"
                  placeholder="e.g. Unwitting complicity in institutional crimes"
                  value={formFear}
                  onChange={(e) => setFormFear(e.target.value)}
                />
              </div>

              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Core Contradiction</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.contradiction}
                      onChange={() => toggleFieldLockInForm('contradiction')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <input
                  type="text"
                  className="workstation-input"
                  placeholder="e.g. Demands total transparency while concealing personal history"
                  value={formContradiction}
                  onChange={(e) => setFormContradiction(e.target.value)}
                />
              </div>

              {/* Phase C: Archetype Selection */}
              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Primary Archetype</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.primary_archetype}
                      onChange={() => toggleFieldLockInForm('primary_archetype')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <select
                  className="workstation-select"
                  value={formPrimaryArchetype}
                  onChange={(e) => setFormPrimaryArchetype(e.target.value as ArchetypeType | '')}
                >
                  <option value="">-- None / Auto-Infer --</option>
                  {ARCHETYPES.map((arch) => (
                    <option key={arch} value={arch}>{arch}</option>
                  ))}
                </select>
              </div>

              <div className="form-field-row">
                <div className="form-field-header">
                  <label>Secondary Archetype</label>
                  <label className="lock-checkbox-label">
                    <input
                      type="checkbox"
                      checked={lockedFields.secondary_archetype}
                      onChange={() => toggleFieldLockInForm('secondary_archetype')}
                    />
                    <span>🔒 Lock Value</span>
                  </label>
                </div>
                <select
                  className="workstation-select"
                  value={formSecondaryArchetype}
                  onChange={(e) => setFormSecondaryArchetype(e.target.value as ArchetypeType | '')}
                >
                  <option value="">-- None / Optional --</option>
                  {ARCHETYPES.map((arch) => (
                    <option key={arch} value={arch}>{arch}</option>
                  ))}
                </select>
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

              {/* PHASE B: CHARACTER DYNAMICS & DRAMATIC CONTEXT */}
              <div className="review-dynamics-section">
                <div className="review-dynamics-header">
                  <span className="dynamics-section-kicker">PHASE B DESIGN METADATA</span>
                  <h4 className="dynamics-section-title">🎭 CHARACTER DYNAMICS &amp; DRAMATIC CONTEXT</h4>
                  <p className="dynamics-section-note">
                    Design-time profile for dramatic starting conditions. <strong>Conscious Want</strong> can project into the active simulation Goal model. <strong>Dramatic Need</strong> remains <em>strictly analytical</em> and never influences character action selection or decision policies.
                  </p>
                </div>

                {/* Conscious Want */}
                <div className="review-item-row dynamics-row">
                  <div className="review-item-main">
                    <div className="dynamics-title-line">
                      <span className="review-field-name">Conscious Want</span>
                      <span className="dynamics-tag tag-want">🎯 Projects to Simulation Goal</span>
                    </div>
                    <div className="review-field-value">
                      {draft.dynamics?.conscious_want || <em className="text-muted">No conscious want specified</em>}
                    </div>
                    {draft.dynamics?.conscious_want && (!draft.goals || !draft.goals.includes(draft.dynamics.conscious_want)) && (
                      <button
                        className="btn-project-want"
                        onClick={handleProjectWant}
                        disabled={loading}
                        title="Explicitly add conscious want to active simulation goals"
                      >
                        ⚡ Project Want → Goal
                      </button>
                    )}
                    {(draft.provenance.conscious_want?.source_snippet || draft.provenance.conscious_want?.inference_rule) && (
                      <div className="review-field-snippet">
                        {draft.provenance.conscious_want.source_snippet
                          ? `Source: "${draft.provenance.conscious_want.source_snippet}"`
                          : `Rule: ${draft.provenance.conscious_want.inference_rule}`}
                      </div>
                    )}
                  </div>
                  <div className="review-item-controls">
                    {renderAuthorityBadge(getFieldAuthority('conscious_want'))}
                    <button
                      className="btn-lock-toggle"
                      onClick={() => handleToggleLockInReview('conscious_want')}
                    >
                      {getFieldAuthority('conscious_want') === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                    </button>
                  </div>
                </div>

                {/* Dramatic Need */}
                <div className="review-item-row dynamics-row">
                  <div className="review-item-main">
                    <div className="dynamics-title-line">
                      <span className="review-field-name">Dramatic Need</span>
                      <span className="dynamics-tag tag-need">🧠 Analytical Only (Inactive in Simulation)</span>
                    </div>
                    <div className="review-field-value">
                      {draft.dynamics?.dramatic_need || <em className="text-muted">No dramatic need specified</em>}
                    </div>
                    <div className="dramatic-need-notice">
                      ⚠️ Analytical invariant: Dramatic Need is never converted to a Goal and never directly drives ActionProposal or DecisionPolicy.
                    </div>
                    {(draft.provenance.dramatic_need?.source_snippet || draft.provenance.dramatic_need?.inference_rule) && (
                      <div className="review-field-snippet">
                        {draft.provenance.dramatic_need.source_snippet
                          ? `Source: "${draft.provenance.dramatic_need.source_snippet}"`
                          : `Rule: ${draft.provenance.dramatic_need.inference_rule}`}
                      </div>
                    )}
                  </div>
                  <div className="review-item-controls">
                    {renderAuthorityBadge(getFieldAuthority('dramatic_need'))}
                    <button
                      className="btn-lock-toggle"
                      onClick={() => handleToggleLockInReview('dramatic_need')}
                    >
                      {getFieldAuthority('dramatic_need') === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                    </button>
                  </div>
                </div>

                {/* Core Value & Shadow Value */}
                <div className="review-item-row dynamics-row">
                  <div className="review-item-main">
                    <span className="review-field-name">Core Value &amp; Shadow Value</span>
                    <div className="review-field-value">
                      {draft.dynamics?.core_value ? (
                        <div>
                          <div><strong>Core Value:</strong> {draft.dynamics.core_value}</div>
                          {draft.dynamics.shadow_value && (
                            <div><strong>Shadow Value:</strong> {draft.dynamics.shadow_value}</div>
                          )}
                        </div>
                      ) : (
                        <em className="text-muted">No values specified</em>
                      )}
                    </div>
                    {(draft.provenance.core_value?.source_snippet || draft.provenance.core_value?.inference_rule) && (
                      <div className="review-field-snippet">
                        {draft.provenance.core_value.source_snippet
                          ? `Source: "${draft.provenance.core_value.source_snippet}"`
                          : `Rule: ${draft.provenance.core_value.inference_rule}`}
                      </div>
                    )}
                  </div>
                  <div className="review-item-controls">
                    {renderAuthorityBadge(getFieldAuthority('core_value'))}
                    <button
                      className="btn-lock-toggle"
                      onClick={() => handleToggleLockInReview('core_value')}
                    >
                      {getFieldAuthority('core_value') === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                    </button>
                  </div>
                </div>

                {/* Fear */}
                <div className="review-item-row dynamics-row">
                  <div className="review-item-main">
                    <span className="review-field-name">Deepest Fear</span>
                    <div className="review-field-value">
                      {draft.dynamics?.fear || <em className="text-muted">No fear specified</em>}
                    </div>
                    {(draft.provenance.fear?.source_snippet || draft.provenance.fear?.inference_rule) && (
                      <div className="review-field-snippet">
                        {draft.provenance.fear.source_snippet
                          ? `Source: "${draft.provenance.fear.source_snippet}"`
                          : `Rule: ${draft.provenance.fear.inference_rule}`}
                      </div>
                    )}
                  </div>
                  <div className="review-item-controls">
                    {renderAuthorityBadge(getFieldAuthority('fear'))}
                    <button
                      className="btn-lock-toggle"
                      onClick={() => handleToggleLockInReview('fear')}
                    >
                      {getFieldAuthority('fear') === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                    </button>
                  </div>
                </div>

                {/* Contradiction */}
                <div className="review-item-row dynamics-row">
                  <div className="review-item-main">
                    <span className="review-field-name">Core Contradiction</span>
                    <div className="review-field-value">
                      {draft.dynamics?.contradiction || <em className="text-muted">No contradiction specified</em>}
                    </div>
                    {(draft.provenance.contradiction?.source_snippet || draft.provenance.contradiction?.inference_rule) && (
                      <div className="review-field-snippet">
                        {draft.provenance.contradiction.source_snippet
                          ? `Source: "${draft.provenance.contradiction.source_snippet}"`
                          : `Rule: ${draft.provenance.contradiction.inference_rule}`}
                      </div>
                    )}
                  </div>
                  <div className="review-item-controls">
                    {renderAuthorityBadge(getFieldAuthority('contradiction'))}
                    <button
                      className="btn-lock-toggle"
                      onClick={() => handleToggleLockInReview('contradiction')}
                    >
                      {getFieldAuthority('contradiction') === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                    </button>
                  </div>
                </div>

                {/* Moral Boundary */}
                <div className="review-item-row dynamics-row">
                  <div className="review-item-main">
                    <span className="review-field-name">Moral Boundary</span>
                    <div className="review-field-value">
                      {draft.dynamics?.moral_boundary || <em className="text-muted">No boundary specified</em>}
                    </div>
                  </div>
                  <div className="review-item-controls">
                    {renderAuthorityBadge(getFieldAuthority('moral_boundary'))}
                    <button
                      className="btn-lock-toggle"
                      onClick={() => handleToggleLockInReview('moral_boundary')}
                    >
                      {getFieldAuthority('moral_boundary') === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                    </button>
                  </div>
                </div>

                {/* Habits & Mannerisms */}
                <div className="review-item-row dynamics-row">
                  <div className="review-item-main">
                    <span className="review-field-name">Habits &amp; Mannerisms</span>
                    <div className="review-field-value">
                      {draft.dynamics?.habits && draft.dynamics.habits.length > 0 && (
                        <div style={{ marginBottom: 4 }}>
                          <strong>Habits:</strong> {draft.dynamics.habits.join(', ')}
                        </div>
                      )}
                      {draft.dynamics?.mannerisms && draft.dynamics.mannerisms.length > 0 && (
                        <div>
                          <strong>Mannerisms:</strong> {draft.dynamics.mannerisms.join(', ')}
                        </div>
                      )}
                      {(!draft.dynamics?.habits || draft.dynamics.habits.length === 0) &&
                       (!draft.dynamics?.mannerisms || draft.dynamics.mannerisms.length === 0) && (
                        <em className="text-muted">No behavioral signatures specified</em>
                      )}
                    </div>
                  </div>
                  <div className="review-item-controls">
                    {renderAuthorityBadge(getFieldAuthority('habits'))}
                    <button
                      className="btn-lock-toggle"
                      onClick={() => handleToggleLockInReview('habits')}
                    >
                      {getFieldAuthority('habits') === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                    </button>
                  </div>
                </div>

                {/* Speech Style & Lifestyle */}
                <div className="review-item-row dynamics-row">
                  <div className="review-item-main">
                    <span className="review-field-name">Speech Style &amp; Lifestyle</span>
                    <div className="review-field-value">
                      {draft.dynamics?.speech_style && (
                        <div style={{ marginBottom: 4 }}>
                          <strong>Speech Style:</strong> {draft.dynamics.speech_style}
                        </div>
                      )}
                      {draft.dynamics?.lifestyle && (
                        <div>
                          <strong>Lifestyle:</strong> {draft.dynamics.lifestyle}
                        </div>
                      )}
                      {!draft.dynamics?.speech_style && !draft.dynamics?.lifestyle && (
                        <em className="text-muted">None specified</em>
                      )}
                    </div>
                  </div>
                  <div className="review-item-controls">
                    {renderAuthorityBadge(getFieldAuthority('speech_style'))}
                    <button
                      className="btn-lock-toggle"
                      onClick={() => handleToggleLockInReview('speech_style')}
                    >
                      {getFieldAuthority('speech_style') === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                    </button>
                  </div>
                </div>

                {/* Conflict Strategy */}
                <div className="review-item-row dynamics-row">
                  <div className="review-item-main">
                    <span className="review-field-name">Conflict / Pressure Strategy</span>
                    <div className="review-field-value">
                      {draft.dynamics?.conflict_strategy || <em className="text-muted">None specified</em>}
                    </div>
                  </div>
                  <div className="review-item-controls">
                    {renderAuthorityBadge(getFieldAuthority('conflict_strategy'))}
                    <button
                      className="btn-lock-toggle"
                      onClick={() => handleToggleLockInReview('conflict_strategy')}
                    >
                      {getFieldAuthority('conflict_strategy') === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                    </button>
                  </div>
                </div>

                {/* PHASE C: ARCHETYPE ORIENTATION & OBSERVATIONAL TRAJECTORY */}
                <div className="review-archetype-header">
                  <div>
                    <span className="dynamics-section-kicker">PHASE C DESIGN METADATA</span>
                    <h4 className="dynamics-section-title">🏛️ ARCHETYPE ORIENTATION &amp; OBSERVATIONAL TRAJECTORY</h4>
                    <p className="dynamics-section-note">
                      Thematic design-time orientation and derived post-hoc analytics. Strictly non-coercive: zero direct influence on action selection, DecisionPolicy, or simulation rules. Never forces actions or invents goals.
                    </p>
                  </div>
                  <button
                    className="btn-enrich"
                    onClick={handleInferArchetypes}
                    disabled={loading}
                    title="Deterministically infer archetypes from traits, role, and premise"
                  >
                    {loading ? 'Inferring...' : '✨ Infer Archetypes'}
                  </button>
                </div>

                {/* Primary Archetype */}
                <div className="review-item-row dynamics-row archetype-row">
                  <div className="review-item-main">
                    <div className="dynamics-title-line">
                      <span className="review-field-name">Primary Archetype</span>
                      <span className="dynamics-tag tag-archetype">Dominant Orientation</span>
                    </div>
                    <div className="review-field-value">
                      {draft.dynamics?.primary_archetype ? (
                        <span className="archetype-badge primary">
                          🏛️ {draft.dynamics.primary_archetype}
                        </span>
                      ) : (
                        <em className="text-muted">None specified</em>
                      )}
                    </div>
                    {(draft.provenance.primary_archetype?.source_snippet || draft.provenance.primary_archetype?.inference_rule) && (
                      <div className="review-field-snippet">
                        {draft.provenance.primary_archetype.source_snippet
                          ? `Source: "${draft.provenance.primary_archetype.source_snippet}"`
                          : `Rule: ${draft.provenance.primary_archetype.inference_rule}`}
                      </div>
                    )}
                  </div>
                  <div className="review-item-controls">
                    {renderAuthorityBadge(getFieldAuthority('primary_archetype'))}
                    <button
                      className="btn-lock-toggle"
                      onClick={() => handleToggleLockInReview('primary_archetype')}
                    >
                      {getFieldAuthority('primary_archetype') === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                    </button>
                  </div>
                </div>

                {/* Secondary Archetype */}
                <div className="review-item-row dynamics-row archetype-row">
                  <div className="review-item-main">
                    <div className="dynamics-title-line">
                      <span className="review-field-name">Secondary Archetype</span>
                      <span className="dynamics-tag tag-archetype-secondary">Secondary Overlay</span>
                    </div>
                    <div className="review-field-value">
                      {draft.dynamics?.secondary_archetype ? (
                        <span className="archetype-badge secondary">
                          ⚖️ {draft.dynamics.secondary_archetype}
                        </span>
                      ) : (
                        <em className="text-muted">None specified</em>
                      )}
                    </div>
                    {(draft.provenance.secondary_archetype?.source_snippet || draft.provenance.secondary_archetype?.inference_rule) && (
                      <div className="review-field-snippet">
                        {draft.provenance.secondary_archetype.source_snippet
                          ? `Source: "${draft.provenance.secondary_archetype.source_snippet}"`
                          : `Rule: ${draft.provenance.secondary_archetype.inference_rule}`}
                      </div>
                    )}
                  </div>
                  <div className="review-item-controls">
                    {renderAuthorityBadge(getFieldAuthority('secondary_archetype'))}
                    <button
                      className="btn-lock-toggle"
                      onClick={() => handleToggleLockInReview('secondary_archetype')}
                    >
                      {getFieldAuthority('secondary_archetype') === 'USER_LOCKED' ? '🔓 Unlock' : '🔒 Lock'}
                    </button>
                  </div>
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
