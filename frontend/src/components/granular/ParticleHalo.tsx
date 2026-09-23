/**
 * ParticleHalo.tsx
 *
 * Granular Particle Halo Framing Component for D3 Story Lab (Phase 9.2.5).
 *
 * Characteristics:
 * - Subtle elliptical halo of micro-dots surrounding active character dossiers,
 *   cards, or selected nodes.
 * - Gentle opacity decay away from the center.
 * - Strictly deterministic coordinates via Mulberry32 PRNG.
 * - Pointer-events: none, SVG-based, zero layout disturbance.
 */

import React, { useMemo } from 'react';
import { generateHaloPoints, GranularPoint } from './prng';

export interface ParticleHaloProps {
  count?: number;
  seed?: number;
  width?: number | string;
  height?: number | string;
  rx?: number;
  ry?: number;
  className?: string;
  style?: React.CSSProperties;
  color?: string;
  accentColor?: string;
  active?: boolean;
  'data-testid'?: string;
}

export const ParticleHalo: React.FC<ParticleHaloProps> = ({
  count = 36,
  seed = 333,
  width = 160,
  height = 160,
  rx = 70,
  ry = 70,
  className = '',
  style,
  color = 'rgba(235, 235, 235, 0.5)',
  accentColor = 'var(--accent-amber, #d89c38)',
  active = true,
  'data-testid': testId = 'particle-halo',
}) => {
  const points: GranularPoint[] = useMemo(() => {
    return generateHaloPoints(count, seed, 80, 80, rx, ry, 6);
  }, [count, seed, rx, ry]);

  if (!active) return null;

  return (
    <svg
      className={`particle-halo-svg ${className}`}
      width={width}
      height={height}
      viewBox="0 0 160 160"
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
      role="presentation"
      data-testid={testId}
      style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        pointerEvents: 'none',
        overflow: 'visible',
        zIndex: 0,
        ...style,
      }}
    >
      <g className="particle-halo-points">
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
