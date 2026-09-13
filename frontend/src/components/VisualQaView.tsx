import React, { useState } from 'react';
import { StoryboardPanel } from '../types';
import { safeExtractSvg, formatDisplayValue } from '../utils/format';

export interface VisualQaViewProps {
  panels: StoryboardPanel[];
  projectId?: string;
  capabilities?: {
    provider?: string;
    model?: string;
    available?: boolean;
    status?: string;
    status_message?: string;
  } | null;
  onRefreshCapabilities?: () => void;
}

interface QaChecklistState {
  characterConsistency: boolean;
  propConsistency: boolean;
  cameraAdherence: boolean;
  styleConsistency: boolean;
  notes: string;
}

export const VisualQaView: React.FC<VisualQaViewProps> = ({
  panels,
  capabilities,
  onRefreshCapabilities,
}) => {
  // Target keyframe numbers: 1, 4, 5, 8
  const targetShotNumbers = [1, 4, 5, 8];

  // Map to find shot by shot_number, panel_number, or fallback index
  const selectedShots: { targetNum: number; panel: StoryboardPanel | null }[] = targetShotNumbers.map(
    (targetNum) => {
      // 1. Match by shot_number
      let match = panels.find((p) => (p.shot_number ?? p.panel_number) === targetNum);
      // 2. Fallback to 0-based index if shot_number not matched
      if (!match && panels.length >= targetNum) {
        match = panels[targetNum - 1];
      }
      return { targetNum, panel: match || null };
    }
  );

  // Local inspection checklist state keyed by shot number
  const [qaState, setQaState] = useState<Record<number, QaChecklistState>>({
    1: { characterConsistency: false, propConsistency: false, cameraAdherence: false, styleConsistency: false, notes: '' },
    4: { characterConsistency: false, propConsistency: false, cameraAdherence: false, styleConsistency: false, notes: '' },
    5: { characterConsistency: false, propConsistency: false, cameraAdherence: false, styleConsistency: false, notes: '' },
    8: { characterConsistency: false, propConsistency: false, cameraAdherence: false, styleConsistency: false, notes: '' },
  });

  // Track debug previs guide toggles when no real raster exists
  const [showPrevisMap, setShowPrevisMap] = useState<Record<number, boolean>>({});

  const togglePrevis = (shotNum: number) => {
    setShowPrevisMap((prev) => ({ ...prev, [shotNum]: !prev[shotNum] }));
  };

  const handleCheckboxChange = (shotNum: number, field: keyof Omit<QaChecklistState, 'notes'>) => {
    setQaState((prev) => ({
      ...prev,
      [shotNum]: {
        ...prev[shotNum],
        [field]: !prev[shotNum]?.[field],
      },
    }));
  };

  const handleNotesChange = (shotNum: number, notes: string) => {
    setQaState((prev) => ({
      ...prev,
      [shotNum]: {
        ...prev[shotNum],
        notes,
      },
    }));
  };

  const runtimeAvailable = Boolean(capabilities?.available);
  const runtimeStatus = capabilities?.status || (runtimeAvailable ? 'RUNTIME_READY' : 'RUNTIME_UNREACHABLE');
  const activeProvider = capabilities?.provider || 'comfyui';
  const activeModel = capabilities?.model || 'sdxl_storyboard_graphite_v1';

  return (
    <div className="visual-qa-view" data-testid="visual-qa-view" style={{ padding: '1.5rem', color: '#e2e8f0' }}>
      {/* 1. Header & Diagnostics */}
      <div
        className="qa-header-card"
        style={{
          background: '#0f172a',
          border: '1px solid #334155',
          borderRadius: '8px',
          padding: '1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, letterSpacing: '0.05em' }}>
              VISUAL QA — KEYFRAME VERIFICATION (SHOTS 1, 4, 5, 8)
            </h2>
            <span
              style={{
                fontSize: '0.75rem',
                padding: '0.2rem 0.6rem',
                borderRadius: '9999px',
                fontWeight: 600,
                background: runtimeAvailable ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                color: runtimeAvailable ? '#4ade80' : '#f87171',
                border: `1px solid ${runtimeAvailable ? '#22c55e' : '#ef4444'}`,
              }}
              data-testid="qa-runtime-status-badge"
            >
              STATUS: {runtimeStatus}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '0.875rem', color: '#94a3b8' }}>
            Inspect open-model raster outputs for continuity, silhouette, prop retention, and camera adherence.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ fontSize: '0.8rem', color: '#cbd5e1', textAlign: 'right' }}>
            <div><strong>Provider:</strong> {activeProvider}</div>
            <div><strong>Model:</strong> {activeModel || '(unconfigured)'}</div>
          </div>
          {onRefreshCapabilities && (
            <button
              onClick={onRefreshCapabilities}
              style={{
                background: '#1e293b',
                color: '#f8fafc',
                border: '1px solid #475569',
                borderRadius: '6px',
                padding: '0.5rem 0.85rem',
                fontSize: '0.8rem',
                cursor: 'pointer',
              }}
            >
              Re-check Runtime
            </button>
          )}
        </div>
      </div>

      {/* 2. Keyframe Cards (Grid: Shots 1, 4, 5, 8) */}
      <div
        className="qa-keyframe-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1.25rem',
        }}
      >
        {selectedShots.map(({ targetNum, panel }) => {
          const shotState = qaState[targetNum] || {
            characterConsistency: false,
            propConsistency: false,
            cameraAdherence: false,
            styleConsistency: false,
            notes: '',
          };

          const actionText = panel
            ? formatDisplayValue(panel.action || panel.action_description || panel.visual_description || 'Action beat')
            : `Shot ${targetNum} (unplanned)`;

          const existingImageUrl = panel ? panel.image_url || panel.rendered_image_url : null;
          const hasRaster = Boolean(existingImageUrl && !existingImageUrl.endsWith('.svg'));
          const previsSvg = panel ? panel.previs_svg || panel.rendered_svg || safeExtractSvg(panel) : null;
          const isPrevisOpen = Boolean(showPrevisMap[targetNum]);

          return (
            <div
              key={targetNum}
              className="qa-shot-card"
              data-testid={`qa-card-shot-${targetNum}`}
              style={{
                background: '#0b1120',
                border: '1px solid #1e293b',
                borderRadius: '8px',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              {/* Card Header */}
              <div
                style={{
                  background: '#1e293b',
                  padding: '0.6rem 0.85rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span style={{ fontWeight: 700, fontSize: '0.9rem', color: '#38bdf8' }}>
                  SHOT {String(targetNum).padStart(2, '0')}
                </span>
                <span
                  style={{
                    fontSize: '0.7rem',
                    padding: '0.15rem 0.45rem',
                    borderRadius: '4px',
                    background: hasRaster ? '#166534' : '#334155',
                    color: '#f8fafc',
                    fontWeight: 600,
                  }}
                >
                  {hasRaster ? 'RASTER IMAGE' : 'UNCONNECTED'}
                </span>
              </div>

              {/* Artwork / Unconnected Frame */}
              <div
                style={{
                  position: 'relative',
                  width: '100%',
                  aspectRatio: '16/9',
                  background: '#020617',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderBottom: '1px solid #1e293b',
                  overflow: 'hidden',
                }}
              >
                {hasRaster ? (
                  <img
                    src={existingImageUrl!}
                    alt={`Shot ${targetNum} artwork`}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    data-testid={`qa-image-shot-${targetNum}`}
                  />
                ) : isPrevisOpen && previsSvg ? (
                  <div
                    style={{ width: '100%', height: '100%', opacity: 0.85 }}
                    dangerouslySetInnerHTML={{ __html: previsSvg }}
                    data-testid={`qa-previs-shot-${targetNum}`}
                  />
                ) : (
                  <div
                    style={{
                      textAlign: 'center',
                      padding: '1rem',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '0.5rem',
                    }}
                    data-testid={`qa-unconnected-shot-${targetNum}`}
                  >
                    <div style={{ fontSize: '1.5rem' }}>🎬</div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f87171' }}>
                      Open-model storyboard runtime not connected.
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      Runtime unavailable. Connect GPU inference runtime.
                    </div>
                    {previsSvg && (
                      <button
                        type="button"
                        onClick={() => togglePrevis(targetNum)}
                        style={{
                          marginTop: '0.25rem',
                          background: '#1e293b',
                          color: '#38bdf8',
                          border: '1px solid #38bdf8',
                          borderRadius: '4px',
                          padding: '0.25rem 0.6rem',
                          fontSize: '0.7rem',
                          cursor: 'pointer',
                        }}
                      >
                        {isPrevisOpen ? 'Hide Previs Guide' : 'Previs guide available'}
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Action Description */}
              <div style={{ padding: '0.75rem', borderBottom: '1px solid #1e293b', flex: '1 0 auto' }}>
                <p style={{ margin: 0, fontSize: '0.8rem', lineHeight: '1.35', color: '#cbd5e1' }}>
                  {actionText}
                </p>
                <div style={{ marginTop: '0.5rem', fontSize: '0.7rem', color: '#64748b' }}>
                  <span><strong>Provider:</strong> {activeProvider}</span> &bull;{' '}
                  <span><strong>Model:</strong> {activeModel}</span>
                </div>
              </div>

              {/* Manual QA Checklist */}
              <div style={{ padding: '0.75rem', background: '#090e1a' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.4rem' }}>
                  MANUAL INSPECTION:
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.75rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={shotState.characterConsistency}
                      onChange={() => handleCheckboxChange(targetNum, 'characterConsistency')}
                      data-testid={`qa-check-character-${targetNum}`}
                    />
                    <span>CHARACTER CONSISTENCY</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={shotState.propConsistency}
                      onChange={() => handleCheckboxChange(targetNum, 'propConsistency')}
                      data-testid={`qa-check-prop-${targetNum}`}
                    />
                    <span>PROP CONSISTENCY</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={shotState.cameraAdherence}
                      onChange={() => handleCheckboxChange(targetNum, 'cameraAdherence')}
                      data-testid={`qa-check-camera-${targetNum}`}
                    />
                    <span>CAMERA ADHERENCE</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={shotState.styleConsistency}
                      onChange={() => handleCheckboxChange(targetNum, 'styleConsistency')}
                      data-testid={`qa-check-style-${targetNum}`}
                    />
                    <span>STYLE CONSISTENCY</span>
                  </label>
                </div>

                <div style={{ marginTop: '0.5rem' }}>
                  <textarea
                    placeholder="Inspection notes (silhouette, lighting, edge quality)..."
                    value={shotState.notes}
                    onChange={(e) => handleNotesChange(targetNum, e.target.value)}
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      background: '#111827',
                      border: '1px solid #374151',
                      borderRadius: '4px',
                      color: '#f3f4f6',
                      fontSize: '0.7rem',
                      padding: '0.35rem',
                      resize: 'vertical',
                      minHeight: '42px',
                    }}
                    data-testid={`qa-notes-${targetNum}`}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
export default VisualQaView;
