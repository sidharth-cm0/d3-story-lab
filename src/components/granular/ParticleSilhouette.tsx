/**
 * ParticleSilhouette.tsx
 *
 * Abstract Dual-Agent Particle Silhouette Motif for D3 Story Lab (Phase 9.2.5).
 *
 * Metaphor:
 * Two granular human-like agent silhouettes facing each other and passing
 * narrative causality / consequence between them across an emergent particle stream.
 *
 * Characteristics:
 * - Abstract, minimalist, non-photorealistic point-cloud forms.
 * - Left & right agent clouds with head/shoulder/torso density contours.
 * - Arching transference bridge representing character-to-character causality.
 * - Warm amber highlights on the causal exchange path.
 * - SVG-based, deterministic, zero layout shift, pointer-events: none.
 */

import React, { useMemo } from 'react';
import { generateSilhouettePoints } from './prng';

export interface ParticleSilhouetteProps {
  seed?: number;
  width?: number | string;
  height?: number | string;
  viewBoxWidth?: number;
  viewBoxHeight?: number;
  className?: string;
  style?: React.CSSProperties;
  color?: string;
  accentColor?: string;
  showTransferenceArc?: boolean;
  'data-testid'?: string;
}

export const ParticleSilhouette: React.FC<ParticleSilhouetteProps> = ({
  seed = 777,
  width = '100%',
  height = 240,
  viewBoxWidth = 800,
  viewBoxHeight = 240,
  className = '',
  style,
  color = 'rgba(235, 235, 235, 0.65)',
  accentColor = 'var(--accent-amber, #d89c38)',
  showTransferenceArc = true,
  'data-testid': testId = 'particle-silhouette',
}) => {
  const { leftAgentPoints, rightAgentPoints, bridgePoints } = useMemo(() => {
    return generateSilhouettePoints(seed, viewBoxWidth, viewBoxHeight);
  }, [seed, viewBoxWidth, viewBoxHeight]);

  const bridgeGradId = `transference-grad-${seed}`;

  return (
    <svg
      className={`particle-silhouette-svg ${className}`}
      width={width}
      height={height}
      viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
      role="presentation"
      data-testid={testId}
      style={{
        pointerEvents: 'none',
        overflow: 'hidden',
        ...style,
      }}
    >
      <defs>
        <linearGradient id={bridgeGradId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={accentColor} stopOpacity="0.2" />
          <stop offset="50%" stopColor={accentColor} stopOpacity="0.6" />
          <stop offset="100%" stopColor={accentColor} stopOpacity="0.2" />
        </linearGradient>
      </defs>

      {/* Left Agent Silhouette Point Cloud */}
      <g className="agent-cloud agent-left" aria-label="Left Agent Point Cloud">
        {leftAgentPoints.map((pt) => (
          <circle
            key={pt.id}
            cx={pt.x}
            cy={pt.y}
            r={pt.r}
            fill={pt.isAmber ? accentColor : color}
            fillOpacity={pt.opacity}
          />
        ))}
      </g>

      {/* Right Agent Silhouette Point Cloud */}
      <g className="agent-cloud agent-right" aria-label="Right Agent Point Cloud">
        {rightAgentPoints.map((pt) => (
          <circle
            key={pt.id}
            cx={pt.x}
            cy={pt.y}
            r={pt.r}
            fill={pt.isAmber ? accentColor : color}
            fillOpacity={pt.opacity}
          />
        ))}
      </g>

      {/* Causal Narrative Transference Stream */}
      {showTransferenceArc && (
        <g className="agent-transference-stream" aria-label="Causal Transference Stream">
          {bridgePoints.map((pt) => (
            <circle
              key={pt.id}
              cx={pt.x}
              cy={pt.y}
              r={pt.r}
              fill={pt.isAmber ? accentColor : color}
              fillOpacity={pt.opacity}
            />
          ))}
        </g>
      )}
    </svg>
  );
};
