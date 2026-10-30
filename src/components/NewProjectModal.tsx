import React, { useState, useEffect } from 'react';
import { StoryInputType } from '../types';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (
    seedPrompt: string,
    title?: string,
    inputType?: StoryInputType,
    targetDuration?: number,
    structureMode?: string,
    structureType?: string,
    secondaryStructure?: string,
    presentationStrategy?: string,
    seed?: number | string,
    lifecycleMode?: string
  ) => Promise<void>;
}

const PRESETS: Array<{ title: string; prompt: string; type: StoryInputType; duration: number }> = [
  {
    title: 'Europa Protocol (Sci-Fi)',
    prompt: 'At Europa Sub-Surface Outpost 4, astrobiologist Dr. Sarah Vance detects an unauthorized override on the airlock security locks while security chief Miller monitors incoming life-support telemetry.',
    type: 'beginning',
    duration: 20,
  },
  {
    title: 'Blackwood Sanatorium (Gothic Mystery)',
    prompt: 'Inside the snowbound archives of Blackwood Sanatorium, Dr. Alistair Finch discovers an unredacted patient ledger implicating Head Administrator Thorne before the generator failure.',
    type: 'midpoint',
    duration: 30,
  },
  {
    title: 'High Noon at Dusty Creek (Western)',
    prompt: 'U.S. Marshal Silas Thorne enters the Dusty Creek saloon with an unserved federal warrant, confronting cattle baron Vance Morgan in front of the town deputy.',
    type: 'beginning',
    duration: 20,
  },
  {
    title: 'Triage Unit 4 (Medical Drama)',
    prompt: 'During an emergency containment lockdown at Metro General Hospital, Chief Surgeon Elena Alvarez discovers the experimental antiviral vial missing from the cold storage safe.',
    type: 'beginning',
    duration: 20,
  },
  {
    title: 'The Missing Dossier (Espionage Noir Demo)',
    prompt: 'In a rain-slicked diplomatic vault, operative Marcus Reed attempts to retrieve an encrypted microfilm canister before counter-intelligence agent Cross triggers lockdown.',
    type: 'beginning',
    duration: 20,
  },
  {
    title: 'The Sovereign Ledger (Cyberpunk)',
    prompt: 'Within the neon-drenched server farm of OmniCorp Tower, data courier Jax Ren confronts corporate auditor Vane over an unencrypted black-budget neural imprint.',
    type: 'full_concept',
    duration: 20,
  },
];

const QUICK_SEEDS = [
  'Deep beneath the Arctic ice sheet, two rival drillers uncover a sealed titanium capsule.',
  'During a diplomatic summit, an ambassador discovers poison in the official banquet decanter.',
  'At a remote desert radar station, a technician detects an unlogged hypersonic telemetry track.',
];

const INPUT_TYPE_HINTS: Record<StoryInputType, { label: string; desc: string }> = {
  beginning: {
    label: 'BEGINNING',
    desc: 'You provide the opening inciting incident. The engine infers the middle escalation and ending resolution.',
  },
  midpoint: {
    label: 'MIDPOINT',
    desc: 'You provide the dramatic twist / discovered deception. The engine infers the preceding setup and eventual climax.',
  },
  ending: {
    label: 'ENDING',
    desc: 'You provide the final outcome / escape. The engine reverse-engineers the setup and confrontation that caused it.',
  },
  full_concept: {
    label: 'FULL CONCEPT',
    desc: 'You provide a multi-sentence premise. The engine structures a balanced 3-act episode around it.',
  },
};

export const NewProjectModal: React.FC<NewProjectModalProps> = ({ isOpen, onClose, onCreate }) => {
  const [title, setTitle] = useState(PRESETS[0].title);
  const [prompt, setPrompt] = useState(PRESETS[0].prompt);
  const [inputType, setInputType] = useState<StoryInputType>('beginning');
  const [duration, setDuration] = useState<number>(20);
  const [structureMode, setStructureMode] = useState<'AUTO' | 'MANUAL'>('AUTO');
  const [structureType, setStructureType] = useState<string>('THREE_ACT');
  const [secondaryStructure, setSecondaryStructure] = useState<string>('NONE');
  const [presentationStrategy, setPresentationStrategy] = useState<string>('CHRONOLOGICAL');
  const [seed, setSeed] = useState<string>(() => Math.floor(Math.random() * 899999 + 100000).toString());
  const [lifecycleMode, setLifecycleMode] = useState<'new_simulation' | 'alternative_run'>('new_simulation');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const randomizeSeed = () => {
    setSeed(Math.floor(Math.random() * 899999 + 100000).toString());
  };

  // Prevent background page scroll while modal is open & listen for Escape key
  useEffect(() => {
    if (!isOpen) return;

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const parsedSeed = seed.trim() !== '' ? (isNaN(Number(seed)) ? seed.trim() : Number(seed.trim())) : undefined;
      await onCreate(
        prompt.trim(),
        title.trim() || undefined,
        inputType,
        duration,
        structureMode,
        structureMode === 'MANUAL' ? structureType : undefined,
        structureMode === 'MANUAL' && secondaryStructure !== 'NONE' ? secondaryStructure : undefined,
        presentationStrategy,
        parsedSeed,
        lifecycleMode
      );
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to initialize project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-spark-title"
    >
      <div className="modal-card cinematic-modal" onClick={(e) => e.stopPropagation()}>
        {/* Pinned / Fixed Header */}
        <div className="modal-header cinematic-modal-header">
          <div className="modal-header-text">
            <div className="modal-kicker">NARRATIVE ENGINE INITIALIZER</div>
            <h2 id="modal-spark-title" className="modal-title">START WITH A SPARK.</h2>
            <p className="modal-subtitle">
              Provide a beginning, midpoint, ending, or full concept. The Director Agent synthesizes sovereign actors, private secrets, and 3-act episodic structure.
            </p>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close modal"
            title="Close (Esc)"
          >
            ✕
          </button>
        </div>

        {/* Modal Form with Scrollable Body & Sticky Action Footer */}
        <form onSubmit={handleSubmit} className="modal-form cinematic-modal-form">
          <div className="modal-body cinematic-modal-body">
            {error && (
              <div className="modal-error-box" role="alert">
                {error}
              </div>
            )}

            {/* Preset Selector */}
            <div className="form-group">
              <label className="form-label" htmlFor="modal-preset-select">PRESETS</label>
              <select
                id="modal-preset-select"
                className="form-select"
                onChange={(e) => {
                  const selected = PRESETS.find((p) => p.title === e.target.value);
                  if (selected) {
                    setTitle(selected.title);
                    setPrompt(selected.prompt);
                    setInputType(selected.type);
                    setDuration(selected.duration);
                  }
                }}
                defaultValue={PRESETS[0].title}
              >
                {PRESETS.map((p) => (
                  <option key={p.title} value={p.title}>
                    {p.title} ({p.type.toUpperCase()})
                  </option>
                ))}
              </select>
            </div>

            {/* 1. Story Input Type Selector */}
            <div className="form-group">
              <label className="form-label">1. STORY INPUT TYPE</label>
              <div className="input-type-pill-grid">
                {(['beginning', 'midpoint', 'ending', 'full_concept'] as StoryInputType[]).map((type) => (
                  <button
                    key={type}
                    type="button"
                    className={`type-pill-btn ${inputType === type ? 'active' : ''}`}
                    onClick={() => setInputType(type)}
                  >
                    <span className="pill-title">{INPUT_TYPE_HINTS[type].label}</span>
                  </button>
                ))}
              </div>
              <div className="input-type-explainer">
                {INPUT_TYPE_HINTS[inputType].desc}
              </div>
            </div>

            {/* 2. Episode Duration */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label className="form-label">2. EPISODE DURATION TARGET</label>
                <span className="text-amber mono-bold">{duration} MINUTES</span>
              </div>
              <div className="duration-pill-row">
                {[10, 20, 30, 45].map((mins) => (
                  <button
                    key={mins}
                    type="button"
                    className={`duration-chip ${duration === mins ? 'active' : ''}`}
                    onClick={() => setDuration(mins)}
                  >
                    {mins} MIN
                  </button>
                ))}
              </div>
            </div>

            {/* 3. Narrative Dramatic Structure */}
            <div className="form-group">
              <label className="form-label">3. STORY STRUCTURE FRAMEWORK</label>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                <button
                  type="button"
                  className={`type-pill-btn ${structureMode === 'AUTO' ? 'active' : ''}`}
                  onClick={() => setStructureMode('AUTO')}
                  style={{ flex: 1 }}
                >
                  <span className="pill-title">AUTO FIT (RECOMMENDED)</span>
                </button>
                <button
                  type="button"
                  className={`type-pill-btn ${structureMode === 'MANUAL' ? 'active' : ''}`}
                  onClick={() => setStructureMode('MANUAL')}
                  style={{ flex: 1 }}
                >
                  <span className="pill-title">MANUAL SELECT</span>
                </button>
              </div>

              {structureMode === 'AUTO' ? (
                <div className="input-type-explainer" style={{ color: 'var(--text-muted)' }}>
                  The engine will heuristically score prompt keywords and narrative archetype to select the optimal framework (e.g. Three-Act, Hero's Journey, Freytag, Save the Cat, Story Circle, or Kishōtenketsu) and synthesize a non-puppeted soft blueprint.
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '8px' }}>
                  <div>
                    <label className="form-label" style={{ fontSize: '11px' }}>PRIMARY STRUCTURE</label>
                    <select
                      className="form-select"
                      value={structureType}
                      onChange={(e) => setStructureType(e.target.value)}
                    >
                      <option value="THREE_ACT">Three-Act (Syd Field)</option>
                      <option value="HERO_JOURNEY">Hero's Journey (Vogler)</option>
                      <option value="FREYTAG">Freytag's Pyramid</option>
                      <option value="SAVE_THE_CAT">Save the Cat! (Snyder)</option>
                      <option value="STORY_CIRCLE">Story Circle (Harmon)</option>
                      <option value="KISHOTENKETSU">Kishōtenketsu (4-Part)</option>
                    </select>
                  </div>
                  <div>
                    <label className="form-label" style={{ fontSize: '11px' }}>SECONDARY OVERLAY</label>
                    <select
                      className="form-select"
                      value={secondaryStructure}
                      onChange={(e) => setSecondaryStructure(e.target.value)}
                    >
                      <option value="NONE">None (Pure Structure)</option>
                      {structureType !== 'THREE_ACT' && <option value="THREE_ACT">Three-Act Overlay</option>}
                      {structureType !== 'HERO_JOURNEY' && <option value="HERO_JOURNEY">Hero's Journey Overlay</option>}
                      {structureType !== 'FREYTAG' && <option value="FREYTAG">Freytag Overlay</option>}
                      {structureType !== 'SAVE_THE_CAT' && <option value="SAVE_THE_CAT">Save the Cat Overlay</option>}
                      {structureType !== 'STORY_CIRCLE' && <option value="STORY_CIRCLE">Story Circle Overlay</option>}
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* Presentation Strategy */}
            <div className="form-group">
              <label className="form-label">4. PRESENTATION STRATEGY</label>
              <select
                className="form-select"
                value={presentationStrategy}
                onChange={(e) => setPresentationStrategy(e.target.value)}
              >
                <option value="CHRONOLOGICAL">Chronological (Linear Real-Time Progression)</option>
                <option value="IN_MEDIA_RES">In Media Res (Opening Crisis / Flashback Core)</option>
                <option value="FLASHBACK_FRAME">Flashback Frame (Interrogation / Retrospective)</option>
                <option value="PARALLEL_TRACKS">Parallel Tracks (Split Temporal Escalation)</option>
              </select>
            </div>

            {/* 5. PRNG Seed & Determinism Control */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label className="form-label">5. SIMULATION SEED & REPRODUCIBILITY</label>
                <span className="text-amber mono-bold" style={{ fontSize: '11px' }}>
                  MULBERRY32 PRNG
                </span>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  className="form-input"
                  style={{ fontFamily: 'monospace' }}
                  value={seed}
                  onChange={(e) => setSeed(e.target.value)}
                  placeholder="e.g. 428190 or custom text seed"
                />
                <button
                  type="button"
                  className="btn-cinematic-secondary"
                  onClick={randomizeSeed}
                  title="Generate a new randomized seed"
                  style={{ whiteSpace: 'nowrap' }}
                >
                  🎲 RANDOMIZE
                </button>
              </div>
              <div className="input-type-explainer" style={{ marginTop: '4px' }}>
                Identical seed + prompt produces a bit-exact identical world state, character dynamic profiles, and causal event sequence.
              </div>
            </div>

            {/* 6. Lifecycle Mode */}
            <div className="form-group">
              <label className="form-label">6. GENERATION MODE</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  className={`type-pill-btn ${lifecycleMode === 'new_simulation' ? 'active' : ''}`}
                  onClick={() => setLifecycleMode('new_simulation')}
                  style={{ flex: 1 }}
                >
                  <span className="pill-title">NEW SIMULATION</span>
                </button>
                <button
                  type="button"
                  className={`type-pill-btn ${lifecycleMode === 'alternative_run' ? 'active' : ''}`}
                  onClick={() => setLifecycleMode('alternative_run')}
                  style={{ flex: 1 }}
                >
                  <span className="pill-title">ALTERNATIVE RUN</span>
                </button>
              </div>
            </div>

            {/* Title (Optional) */}
            <div className="form-group">
              <label className="form-label" htmlFor="modal-episode-title">EPISODE TITLE (OPTIONAL)</label>
              <input
                id="modal-episode-title"
                type="text"
                className="form-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. The Threshold, False Partner, Ashes of Truth..."
              />
            </div>

            {/* 3. Prompt Textarea */}
            <div className="form-group">
              <label className="form-label" htmlFor="modal-prompt-textarea">3. PROMPT / PREMISE / INCIDENT</label>
              <textarea
                id="modal-prompt-textarea"
                className="form-textarea cinematic-textarea"
                rows={3}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. A man enters an abandoned building..."
                required
              />
            </div>

            <div className="quick-seeds-container">
              <span className="quick-seeds-label">EXAMPLES:</span>
              {QUICK_SEEDS.map((seed, i) => (
                <button
                  key={i}
                  type="button"
                  className="seed-chip"
                  onClick={() => {
                    setPrompt(seed);
                    setTitle('');
                  }}
                >
                  "{seed}"
                </button>
              ))}
            </div>
          </div>

          {/* Pinned / Fixed Footer */}
          <div className="modal-actions cinematic-modal-footer">
            <button type="button" className="btn-cinematic-secondary" onClick={onClose} disabled={loading}>
              CANCEL
            </button>
            <button type="submit" className="btn-cinematic-primary" disabled={loading || !prompt.trim()}>
              {loading ? 'BUILDING WORLD...' : 'BUILD WORLD'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
