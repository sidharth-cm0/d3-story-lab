/**
 * ShotCard.tsx
 *
 * Clean, artwork-first storyboard panel card component for D3 Studio.
 * Stripped of heavy metadata borders to emphasize visual composition.
 *
 * Default/Canonical mode is 100% offline Hand-Drawn storyboard sketch.
 * External AI rendering is optional and explicitly triggered by the user via
 * backend endpoint (POST /api/projects/{id}/storyboard/panels/{panel_id}/external-render).
 */

import React, { useState } from 'react';
import { StoryboardPanel, VisualBible } from '../types';
import { requestExternalPanelRender, PRICING_DISCLAIMER } from '../services/HuggingFaceService';
import { formatDisplayValue, safeExtractSvg } from '../utils/format';

export interface ShotCardProps {
  panel: StoryboardPanel;
  projectId?: string;
  visualBible?: VisualBible | null;
  onSelect?: (panel: StoryboardPanel) => void;
  onRegenerate?: (panelId: string) => void;
  onPanelUpdated?: (updatedPanel: StoryboardPanel) => void;
  className?: string;
  isSelected?: boolean;
}

export const ShotCard: React.FC<ShotCardProps> = ({
  panel,
  projectId,
  onSelect,
  onRegenerate,
  onPanelUpdated,
  className = '',
  isSelected = false,
}) => {
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const effectiveProjectId = projectId || panel.project_id || '';

  const handleExternalRender = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isGenerating) return;
    if (!effectiveProjectId) {
      setErrorMessage('Project ID required for external render.');
      return;
    }

    setIsGenerating(true);
    setErrorMessage(null);
    setStatusMessage('Requesting server-side external AI render...');

    try {
      const result = await requestExternalPanelRender(effectiveProjectId, panel.id);
      onPanelUpdated?.(result.panel);
    } catch (err: any) {
      console.error('External storyboard render failed:', err);
      setErrorMessage(err.message || 'Open-model rendering failed. Previs guide retained.');
    } finally {
      setIsGenerating(false);
      setStatusMessage(null);
    }
  };

  // State for toggling previs guide when unrendered
  const [showPrevisGuide, setShowPrevisGuide] = useState<boolean>(false);

  // Derive display values
  const shotNum = panel.shot_number ?? panel.panel_number ?? 1;
  const shotType = (panel.shot_type || 'medium').replace(/_/g, ' ').toUpperCase();
  const cameraAngle = (panel.camera_angle || 'eye_level').replace(/_/g, ' ').toUpperCase();
  const actionText = formatDisplayValue(
    panel.action || panel.action_description || panel.visual_description || 'Scene unfolds'
  );
  const dialogueText = panel.dialogue_excerpt ? formatDisplayValue(panel.dialogue_excerpt) : null;
  const locationName = formatDisplayValue(panel.location_name || panel.location_id || 'Scene');

  // Active artwork source
  const existingImageUrl = panel.image_url || panel.rendered_image_url;
  const hasRasterImage = Boolean(existingImageUrl && !existingImageUrl.endsWith('.svg'));
  const previsSvg = panel.previs_svg || panel.rendered_svg || safeExtractSvg(panel);

  // Provenance checks
  const provenanceLabel = hasRasterImage ? 'OPEN-MODEL STORYBOARD' : 'PREVIS GUIDE';
  const provenanceBadgeClass = hasRasterImage ? 'badge-ai-image' : 'badge-previs-guide';

  return (
    <div
      className={`shot-card-clean ${isSelected ? 'selected-shot-granular-frame' : ''} ${className}`}
      onClick={() => onSelect?.(panel)}
      title="Click to view panel inspector and visual details"
      data-testid={`shot-card-${panel.id}`}
    >
      {/* 1. Minimal Header Bar */}
      <div className="shot-card-header">
        <div className="shot-identity-badge">
          <span className="shot-num-tag">SHOT {String(shotNum).padStart(2, '0')}</span>
          <span className="shot-separator">•</span>
          <span className="shot-framing-tag">{shotType}</span>
          {cameraAngle && <span className="shot-angle-tag">/ {cameraAngle}</span>}
          {panel.is_keyframe && <span className="badge-keyframe">KEYFRAME</span>}
        </div>

        <div className="shot-header-actions">
          {/* Provenance Badge */}
          <span className={`badge-pill ${provenanceBadgeClass}`}>
            {provenanceLabel}
          </span>

          {/* User Action: Render Panel with Open-Model */}
          {effectiveProjectId && (
            <button
              type="button"
              className="btn-shot-action"
              onClick={handleExternalRender}
              disabled={isGenerating}
              title={`Render this panel externally via open-model generation runtime\n${PRICING_DISCLAIMER}`}
            >
              {isGenerating ? '⌛' : '⚡'}
            </button>
          )}

          {/* Regeneration */}
          <button
            type="button"
            className="btn-shot-action"
            onClick={(e) => {
              e.stopPropagation();
              onRegenerate?.(panel.id);
            }}
            disabled={isGenerating}
            title="Regenerate storyboard artwork"
          >
            ↻
          </button>
        </div>
      </div>

      {/* 2. Main 16:9 Cinematic Artwork Frame Container */}
      <div className="shot-image-container">
        {isGenerating ? (
          /* CSS Pulsing Skeleton Loader */
          <div className="shot-skeleton-loader" data-testid="shot-skeleton-loader">
            <div className="shot-wireframe-placeholder">
              <div className="wireframe-crosshair-center">✛</div>
              <div className="wireframe-grid-line wireframe-h" />
              <div className="wireframe-grid-line wireframe-v" />
              <div className="wireframe-corner wireframe-tl" />
              <div className="wireframe-corner wireframe-tr" />
              <div className="wireframe-corner wireframe-bl" />
              <div className="wireframe-corner wireframe-br" />
            </div>

            <div className="shot-loader-shimmer" />

            <div className="shot-generating-status">
              <div className="status-spinner" />
              <div className="status-text-primary">RENDERING STORYBOARD PANEL</div>
              <div className="status-text-sub">
                {statusMessage || 'Processing open-model image render...'}
              </div>
            </div>
          </div>
        ) : hasRasterImage ? (
          /* Final Raster Artwork */
          <img
            src={existingImageUrl!}
            alt={actionText}
            className="shot-image-seamless"
            loading="lazy"
          />
        ) : showPrevisGuide && previsSvg ? (
          /* Previs Guide Overlay (User explicitly toggled on) */
          <div
            className="shot-svg-seamless previs-overlay"
            dangerouslySetInnerHTML={{ __html: previsSvg }}
          />
        ) : (
          /* Ungenerated State: Do NOT show procedural SVG as final artwork */
          <div className="shot-unrendered-container" data-testid="shot-unrendered-state">
            <div className="unrendered-icon">🎬</div>
            <div className="unrendered-title">Open-model storyboard runtime not connected.</div>
            <div className="unrendered-sub">
              <span>Storyboard render unavailable</span>. Connect a GPU generation runtime for final artwork.
            </div>
            <div className="unrendered-actions">
              {previsSvg && (
                <button
                  type="button"
                  className="btn-previs-toggle"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowPrevisGuide(!showPrevisGuide);
                  }}
                >
                  {showPrevisGuide ? 'Hide Previs Guide' : 'Previs guide available'}
                </button>
              )}
            </div>
          </div>

        )}

        {/* Error Notification Pill */}
        {errorMessage && !isGenerating && (
          <div className="shot-error-pill" title={errorMessage}>
            ⚠ {errorMessage}
          </div>
        )}
      </div>

      {/* 3. Clean Artwork-First Action & Dialogue Details */}
      <div className="shot-info-clean">
        <p className="shot-action-text">{actionText}</p>

        {dialogueText && (
          <div className="shot-dialogue-box">
            <span className="dialogue-quote-mark">“</span>
            <span className="dialogue-content">{dialogueText}</span>
          </div>
        )}

        <div className="shot-footer-meta">
          <span className="shot-meta-location">📍 {locationName}</span>
          {panel.character_names && panel.character_names.length > 0 && (
            <span className="shot-meta-characters">
              👤 {panel.character_names.join(', ')}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
