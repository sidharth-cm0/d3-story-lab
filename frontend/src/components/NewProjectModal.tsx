import React, { useState, useEffect } from 'react';
import { StoryInputType } from '../types';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (seedPrompt: string, title?: string, inputType?: StoryInputType, targetDuration?: number) => Promise<void>;
}

const PRESETS: Array<{ title: string; prompt: string; type: StoryInputType; duration: number }> = [
  {
    title: 'The Infiltration',
    prompt: 'A man enters an abandoned building carrying only an encrypted transceiver.',
    type: 'beginning',
    duration: 20,
  },
  {
    title: 'The Partner Betrayal',
    prompt: 'A detective discovers her partner is lying about the evidence in the locker.',
    type: 'midpoint',
    duration: 20,
  },
  {
    title: 'The Burning Escape',
    prompt: 'The hero escapes the burning warehouse into the rain but loses the evidence in the fire.',
    type: 'ending',
    duration: 20,
  },
  {
    title: 'Hotel Intrigue',
    prompt: 'In a rain-slicked luxury penthouse, investigative journalist Maya Lin confronts diplomat Arjun Mehta regarding a confidential offshore ledger before unknown forces intervene.',
    type: 'full_concept',
    duration: 20,
  },
];

const QUICK_SEEDS = [
  'A journalist disappears after receiving a sealed file.',
  'Three strangers are trapped inside an embassy.',
  'A detective discovers that the witness is lying.',
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
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState(PRESETS[0].prompt);
  const [inputType, setInputType] = useState<StoryInputType>('beginning');
  const [duration, setDuration] = useState<number>(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      await onCreate(prompt.trim(), title.trim() || undefined, inputType, duration);
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
