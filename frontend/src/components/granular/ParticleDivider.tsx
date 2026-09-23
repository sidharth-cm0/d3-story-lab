/**
 * ParticleDivider.tsx
 *
 * Granular Section Divider for D3 Story Lab (Phase 9.2.5).
 *
 * Characteristics:
 * - Subtle horizontal scatter of micro-dots replacing or accenting solid lines.
 * - Point density concentrated at the center and gracefully tapering towards edges.
 * - Deterministic coordinates via Mulberry32 PRNG.
 * - Accessible, presentation-only, pointer-events: none.
 */

import React, { useMemo } from 'react';
import { generateDividerPoints, GranularPoint } from './prng';

export interface ParticleDividerProps {
  count?: number;
  seed?: number;
  width?: number | string;
  height?: number | string;
  viewBoxWidth?: number;
  viewBoxHeight?: number;
  className?: string;
  style?: React.CSSProperties;
  color?: string;
  accentColor?: string;
  showCenterGuide?: boolean;
  'data-testid'?: string;
}

export const ParticleDivider: React.FC<ParticleDividerProps> = ({
  count = 42,
  seed = 555,
  width = '100%',
  height = 20,
  viewBoxWidth = 800,
  viewBoxHeight = 20,
  className = '',
  style,
  color = 'rgba(235, 235, 235, 0.45)',
  accentColor = 'var(--accent-amber, #d89c38)',
  showCenterGuide = true,
  'data-testid': testId = 'particle-divider',
}) => {
  const points: GranularPoint[] = useMemo(() => {
    return generateDividerPoints(count, seed, viewBoxWidth, viewBoxHeight / 2);
  }, [count, seed, viewBoxWidth, viewBoxHeight]);

  const gradId = `div-grad-${seed}`;

  return (
    <svg
      className={`particle-divider-svg ${className}`}
      width={width}
      height={height}
      viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      role="presentation"
      data-testid={testId}
      style={{
        display: 'block',
        pointerEvents: 'none',
        overflow: 'hidden',
        margin: '16px auto',
        ...style,
      }}
    >
      <defs>
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={color} stopOpacity="0" />
          <stop offset="20%" stopColor={color} stopOpacity="0.1" />
          <stop offset="50%" stopColor={accentColor} stopOpacity="0.4" />
          <stop offset="80%" stopColor={color} stopOpacity="0.1" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>

      {showCenterGuide && (
        <line
          x1={viewBoxWidth * 0.15}
          y1={viewBoxHeight / 2}
          x2={viewBoxWidth * 0.85}
          y2={viewBoxHeight / 2}
          stroke={`url(#${gradId})`}
          strokeWidth="0.75"
        />
      )}

      <g className="particle-divider-points">
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
