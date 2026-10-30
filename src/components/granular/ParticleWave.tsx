/**
 * ParticleWave.tsx
 *
 * 2D Granular Particle-Wave Motif for D3 Story Lab (Phase 9.2.5).
 *
 * Represents the D3-specific visual metaphor:
 * "Story Possibility Space / Emergent Narrative Field"
 *
 * Characteristics:
 * - Undulating harmonic curves composed of discrete micro-points.
 * - Layered opacities and subtle amber narrative probability accents.
 * - Pure SVG, zero WebGL/Canvas overhead.
 * - Deterministic coordinates precomputed via Mulberry32 PRNG.
 */

import React, { useMemo } from 'react';
import { generateWavePoints, GranularPoint, WaveOptions } from './prng';

export interface ParticleWaveProps {
  pointsPerLayer?: number;
  seed?: number;
  width?: number | string;
  height?: number | string;
  viewBoxWidth?: number;
  viewBoxHeight?: number;
  className?: string;
  style?: React.CSSProperties;
  color?: string;
  accentColor?: string;
  options?: WaveOptions;
  showBaselineGuide?: boolean;
  'data-testid'?: string;
}

export const ParticleWave: React.FC<ParticleWaveProps> = ({
  pointsPerLayer = 70,
  seed = 101,
  width = '100%',
  height = '100%',
  viewBoxWidth = 1000,
  viewBoxHeight = 240,
  className = '',
  style,
  color = 'rgba(235, 235, 235, 0.65)',
  accentColor = 'var(--accent-amber, #d89c38)',
  options,
  showBaselineGuide = true,
  'data-testid': testId = 'particle-wave',
}) => {
  const points: GranularPoint[] = useMemo(() => {
    return generateWavePoints(pointsPerLayer, seed, viewBoxWidth, viewBoxHeight, options);
  }, [pointsPerLayer, seed, viewBoxWidth, viewBoxHeight, options]);

  // SVG gradient identifier scoped to seed to avoid collisions
  const gradId = `wave-grad-${seed}`;

  return (
    <svg
      className={`particle-wave-svg ${className}`}
      width={width}
      height={height}
      viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
      preserveAspectRatio="none"
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
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={color} stopOpacity="0.05" />
          <stop offset="25%" stopColor={color} stopOpacity="0.25" />
          <stop offset="50%" stopColor={accentColor} stopOpacity="0.35" />
          <stop offset="75%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0.05" />
        </linearGradient>
      </defs>

      {/* Subtle baseline narrative probability horizon */}
      {showBaselineGuide && (
        <line
          x1={viewBoxWidth * 0.05}
          y1={viewBoxHeight * 0.72}
          x2={viewBoxWidth * 0.95}
          y2={viewBoxHeight * 0.72}
          stroke={`url(#${gradId})`}
          strokeWidth="1"
          strokeDasharray="3 6"
        />
      )}

      {/* Undulating granular point clusters */}
      <g className="particle-wave-points">
        {points.map((pt) => (
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
    </svg>
  );
};
