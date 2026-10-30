/**
 * GranularField.tsx
 *
 * Subtle reusable particle field for D3 Story Lab (Phase 9.2.5).
 *
 * Characteristics:
 * - Sparse white/off-white micro-dots on black/graphite void.
 * - Random but strictly deterministic placement using Mulberry32 PRNG.
 * - Opacity & radius variations.
 * - Layered with pointer-events: none and full accessibility attributes.
 * - Precomputed once via useMemo; does NOT re-randomize across re-renders.
 */

import React, { useMemo } from 'react';
import { generatePointField, GranularPoint, FieldOptions } from './prng';

export interface GranularFieldProps {
  pointCount?: number;
  seed?: number;
  width?: number | string;
  height?: number | string;
  viewBoxWidth?: number;
  viewBoxHeight?: number;
  className?: string;
  style?: React.CSSProperties;
  color?: string;
  accentColor?: string;
  options?: FieldOptions;
  'data-testid'?: string;
}

export const GranularField: React.FC<GranularFieldProps> = ({
  pointCount = 90,
  seed = 42,
  width = '100%',
  height = '100%',
  viewBoxWidth = 1000,
  viewBoxHeight = 400,
  className = '',
  style,
  color = 'rgba(235, 235, 235, 0.55)',
  accentColor = 'var(--accent-amber, #d89c38)',
  options,
  'data-testid': testId = 'granular-field',
}) => {
  // Precompute deterministic points once per seed/count/dimension combination
  const points: GranularPoint[] = useMemo(() => {
    return generatePointField(pointCount, seed, viewBoxWidth, viewBoxHeight, options);
  }, [pointCount, seed, viewBoxWidth, viewBoxHeight, options]);

  return (
    <svg
      className={`granular-field-svg ${className}`}
      width={width}
      height={height}
      viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      role="presentation"
      data-testid={testId}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
        ...style,
      }}
    >
      <g className="granular-field-points">
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
