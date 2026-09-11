import React, { useState } from 'react';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (seedPrompt: string, title?: string) => Promise<void>;
}

const PRESETS = [
  {
    title: 'Hotel Intrigue',
    prompt: 'In a rain-slicked luxury penthouse, investigative journalist Maya Lin confronts diplomat Arjun Mehta regarding a confidential offshore ledger before unknown forces intervene.',
  },
  {
    title: 'The Forged Masterpiece',
    prompt: 'Two rival art gallery curators find themselves locked inside the restoration vault at midnight, both suspecting the other of replacing the Renaissance centerpiece with a forgery.',
  },
  {
    title: 'Embassy Lockdown',
    prompt: 'During a sudden diplomatic code-red lockdown, a defecting codebreaker and an embassy security attache must determine whether to destroy a decrypted cipher drive.',
  },
];

const QUICK_SEEDS = [
  'A journalist disappears after receiving a sealed file.',
  'Three strangers are trapped inside an embassy.',
  'A detective discovers that the witness is lying.',
];

export const NewProjectModal: React.FC<NewProjectModalProps> = ({ isOpen, onClose, onCreate }) => {
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState(PRESETS[0].prompt);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await onCreate(prompt.trim(), title.trim() || undefined);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to initialize project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card cinematic-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-kicker">SANDBOX INITIALIZATION</div>
          <h2 className="modal-title">START WITH A SPARK.</h2>
          <p className="modal-subtitle">
            Paste an idea, clipping, incident, or premise. The system synthesizes sovereign actors, private secrets, and physics.
          </p>
        </div>

        {error && (
          <div className="modal-error-box">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label className="form-label">PRESETS</label>
            <select
              className="form-select"
              onChange={(e) => {
                const selected = PRESETS.find((p) => p.title === e.target.value);
                if (selected) {
                  setTitle(selected.title);
                  setPrompt(selected.prompt);
                }
              }}
              defaultValue={PRESETS[0].title}
            >
              {PRESETS.map((p) => (
                <option key={p.title} value={p.title}>
                  {p.title}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">TITLE (OPTIONAL)</label>
            <input
              type="text"
              className="form-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Penthouse Intrigue"
            />
          </div>

          <div className="form-group">
            <label className="form-label">IDEA / INCIDENT / SCENARIO</label>
            <textarea
              className="form-textarea cinematic-textarea"
              rows={5}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Paste an idea, clipping, incident, or scenario..."
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

          <div className="modal-actions">
            <button type="button" className="btn-cinematic-secondary" onClick={onClose} disabled={loading}>
              CANCEL
            </button>
            <button type="submit" className="btn-cinematic-primary" disabled={loading || !prompt.trim()}>
              {loading ? 'SYNTHESIZING WORLD...' : 'BUILD WORLD'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
