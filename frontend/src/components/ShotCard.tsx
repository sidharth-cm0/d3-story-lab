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
}

export const ShotCard: React.FC<ShotCardProps> = ({
  panel,
  projectId,
  onSelect,
  onRegenerate,
  onPanelUpdated,
  className = '',
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
      setErrorMessage(err.message || 'External rendering failed. Switched to hand-drawn fallback.');
    } finally {
      setIsGenerating(false);
      setStatusMessage(null);
    }
  };

  // Derive display values
  const shotNum = panel.shot_number ?? panel.panel_number ?? 1;
  const shotType = (panel.shot_type || 'medium').replace(/_/g, ' ').toUpperCase();
  const cameraAngle = (panel.camera_angle || 'eye_level').replace(/_/g, ' ').toUpperCase();
  const actionText = formatDisplayValue(
    panel.action || panel.action_description || panel.visual_description || 'Scene unfolds'
  );
  const dialogueText = panel.dialogue_excerpt ? formatDisplayValue(panel.dialogue_excerpt) : null;
  const locationName = formatDisplayValue(panel.location_name || panel.location_id || 'Scene');

  // Provenance checks
  const isAi =
    panel.mode === 'ai_image' ||
    panel.provider === 'huggingface' ||
    panel.versions?.some((v) => v.is_selected && v.mode === 'ai_image');

  const provenanceLabel = isAi ? 'EXTERNAL AI IMAGE' : 'HAND-DRAWN STORYBOARD';
  const provenanceBadgeClass = isAi ? 'badge-ai-image' : 'badge-hand-drawn';

  // Active artwork source
  const existingSvg = panel.rendered_svg || safeExtractSvg(panel);
  const existingImageUrl = panel.image_url || panel.rendered_image_url;
  const hasRasterImage = Boolean(existingImageUrl && !existingImageUrl.endsWith('.svg'));
  const hasSvg = Boolean(existingSvg);

  return (
    <div
      className={`shot-card-clean ${className}`}
      onClick={() => onSelect?.(panel)}
      title="Click to view panel inspector and visual details"
      data-testid={`shot-card-${panel.id}`}
    >
      {/* 1. Minimal Header Bar (Clean, no heavy borders) */}
      <div className="shot-card-header">
        <div className="shot-identity-badge">
          <span className="shot-num-tag">SHOT {String(shotNum).padStart(2, '0')}</span>
          <span className="shot-separator">•</span>
          <span className="shot-framing-tag">{shotType}</span>
          {cameraAngle && <span className="shot-angle-tag">/ {cameraAngle}</span>}
        </div>

        <div className="shot-header-actions">
          {/* Provenance Badge */}
          <span className={`badge-pill ${provenanceBadgeClass}`}>
            {provenanceLabel}
          </span>

          {/* Explicit User Action: Render Panel Externally */}
          {effectiveProjectId && (
            <button
              type="button"
              className="btn-shot-action"
              onClick={handleExternalRender}
              disabled={isGenerating}
              title={`RENDER THIS PANEL EXTERNALLY (HF SDXL)\n${PRICING_DISCLAIMER}`}
            >
              {isGenerating ? '⌛' : '⚡'}
            </button>
          )}

          {/* Normal Offline Hand-Drawn Regeneration */}
          <button
            type="button"
            className="btn-shot-action"
            onClick={(e) => {
              e.stopPropagation();
              onRegenerate?.(panel.id);
            }}
            disabled={isGenerating}
            title="Regenerate hand-drawn sketch (offline)"
          >
            ↻
          </button>
        </div>
      </div>

      {/* 2. Main 16:9 Cinematic Artwork Frame Container */}
      <div className="shot-image-container">
        {isGenerating ? (
          /* CSS Pulsing Skeleton Loader & Wireframe Placeholder */
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
                {statusMessage || 'Processing external AI model request...'}
              </div>
            </div>
          </div>
        ) : hasRasterImage ? (
          /* Raster Artwork (Persisted backend asset) */
          <img
            src={existingImageUrl!}
            alt={actionText}
            className="shot-image-seamless"
            loading="lazy"
          />
        ) : hasSvg ? (
          /* Offline Deterministic Hand-Drawn SVG */
          <div
            className="shot-svg-seamless"
            dangerouslySetInnerHTML={{ __html: existingSvg! }}
          />
        ) : (
          /* Idle Wireframe Placeholder */
          <div className="shot-wireframe-placeholder idle-placeholder">
            <div className="wireframe-crosshair-center">✛</div>
            <div className="wireframe-label">FRAME {String(shotNum).padStart(2, '0')}</div>
            <span className="idle-instruction">Hand-drawn storyboard ready</span>
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
