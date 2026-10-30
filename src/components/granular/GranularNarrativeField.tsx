/**
 * GranularNarrativeField.tsx
 *
 * Dense Full-Width Point-Cloud Landscape and Agent Interaction Motif (Phase 9.2.6).
 *
 * Visual Target:
 * - Continuous flowing narrative terrain (Background / Midground / Foreground layers).
 * - Two recognizable abstract agent silhouettes made from particle clouds.
 * - Causal transference stream connecting the reaching hands of the agents.
 * - High density (~2,400 points desktop, ~1,500 laptop, ~800 mobile).
 * - Rendered using batched SVG <path> elements for reference-fidelity 60fps performance.
 * - 5-stage overlapping ease-out resolve transition (800–1200ms) and graceful dissolve.
 * - Under prefers-reduced-motion: immediate static finished form.
 */

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { generateDenseNarrativeLandscape, LandscapeLayers } from './landscapeModel';

export interface GranularNarrativeFieldProps {
  seed?: number;
  width?: number | string;
  height?: number | string;
  className?: string;
  style?: React.CSSProperties;
  densityScale?: number;
  isHovered?: boolean;
  'data-testid'?: string;
}

export const GranularNarrativeField: React.FC<GranularNarrativeFieldProps> = ({
  seed = 926,
  width = '100%',
  height = '100%',
  className = '',
  style,
  densityScale = 1.0,
  isHovered = false,
  'data-testid': testId = 'granular-narrative-field',
}) => {
  const prefersReduced = usePrefersReducedMotion();

  // Precompute deterministic point clouds and batched path geometry once
  const landscape: LandscapeLayers = useMemo(() => {
    return generateDenseNarrativeLandscape({ seed, width: 1200, height: 380, densityScale });
  }, [seed, densityScale]);

  // Color constants adhering strictly to D3 dark forensic identity (§13)
  const colorBgStrata = 'rgba(165, 165, 165, 0.28)';
  const colorMidTerrain = 'rgba(215, 215, 210, 0.52)';
  const colorFgRidge = 'rgba(242, 240, 235, 0.88)';
  const colorAmber = 'var(--accent-amber, #d89c38)';
  const colorAgentSilhouette = 'rgba(238, 236, 230, 0.82)';

  // Static render for reduced motion or SSR
  if (prefersReduced) {
    return (
      <div
        className={`granular-narrative-field-wrapper ${className}`}
        style={{ width, height, position: 'relative', pointerEvents: 'none', ...style }}
        aria-hidden="true"
        role="presentation"
        data-testid={testId}
      >
        <svg
          className="granular-narrative-svg"
          viewBox="0 0 1200 380"
          preserveAspectRatio="xMidYMid meet"
          width="100%"
          height="100%"
          aria-hidden="true"
          role="presentation"
        >
          {/* Depth Layer 1: Background Strata */}
          <path d={landscape.bgPathD} fill={colorBgStrata} className="layer-bg-strata" />

          {/* Depth Layer 2: Midground Rolling Narrative Terrain */}
          <path d={landscape.midPathD} fill={colorMidTerrain} className="layer-mid-terrain" />

          {/* Depth Layer 3: Foreground Topological Ridges & Crests */}
          <path d={landscape.fgPathD} fill={colorFgRidge} className="layer-fg-ridge" />
          <path d={landscape.fgAmberPathD} fill={colorAmber} className="layer-fg-amber" />

          {/* Silhouettes: Agent A (Initiator) & Agent B (Receptor) */}
          <g className="layer-agents">
            <path d={landscape.agentLeftPathD} fill={colorAgentSilhouette} className="agent-silhouette-left" />
            <path d={landscape.agentRightPathD} fill={colorAgentSilhouette} className="agent-silhouette-right" />
          </g>

          {/* Causal Transference Stream & Convergence Locus */}
          <g className="layer-causal-stream">
            <path d={landscape.causalPathD} fill={colorFgRidge} className="causal-stream-white" />
            <path d={landscape.causalAmberPathD} fill={colorAmber} className="causal-stream-amber" />
          </g>
        </svg>
      </div>
    );
  }

  // Cinematic 5-Stage Overlapping Resolve Sequence (§9)
  // Stage 1 (0-300ms): Background strata fades in
  // Stage 2 (200-650ms): Midground terrain resolves
  // Stage 3 (450-900ms): Foreground crests & amber nodes brighten
  // Stage 4 (600-1050ms): Agent silhouettes emerge from particles
  // Stage 5 (800-1200ms): Causal transference arc illuminates and settles
  const easeOut = [0.16, 1, 0.3, 1] as const;

  return (
    <div
      className={`granular-narrative-field-wrapper ${className}`}
      style={{
        width,
        height,
        position: 'relative',
        pointerEvents: 'none',
        transition: 'opacity 280ms cubic-bezier(0.16, 1, 0.3, 1)',
        opacity: isHovered ? 1.0 : 0.94,
        ...style,
      }}
      aria-hidden="true"
      role="presentation"
      data-testid={testId}
    >
      <svg
        className="granular-narrative-svg"
        viewBox="0 0 1200 380"
        preserveAspectRatio="xMidYMid meet"
        width="100%"
        height="100%"
        aria-hidden="true"
        role="presentation"
        style={{ overflow: 'visible' }}
      >
        {/* Depth Layer 1: Background Strata (Stage 1) */}
        <motion.path
          d={landscape.bgPathD}
          fill={colorBgStrata}
          className="layer-bg-strata"
          initial={{ opacity: 0.05, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.65, ease: easeOut, delay: 0.05 }}
        />

        {/* Depth Layer 2: Midground Rolling Narrative Terrain (Stage 2) */}
        <motion.path
          d={landscape.midPathD}
          fill={colorMidTerrain}
          className="layer-mid-terrain"
          initial={{ opacity: 0.08, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.75, ease: easeOut, delay: 0.18 }}
        />

        {/* Depth Layer 3: Foreground Topological Ridges (Stage 3) */}
        <motion.g
          className="layer-fg-group"
          initial={{ opacity: 0.1, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.8, ease: easeOut, delay: 0.35 }}
        >
          <path d={landscape.fgPathD} fill={colorFgRidge} className="layer-fg-ridge" />
          <path d={landscape.fgAmberPathD} fill={colorAmber} className="layer-fg-amber" />
        </motion.g>

        {/* Silhouettes: Agent A & Agent B Particle Clouds (Stage 4) */}
        <motion.g
          className="layer-agents"
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98 }}
          transition={{ duration: 0.85, ease: easeOut, delay: 0.5 }}
          style={{ transformOrigin: '600px 190px' }}
        >
          <path
            d={landscape.agentLeftPathD}
            fill={colorAgentSilhouette}
            className="agent-silhouette-left"
          />
          <path
            d={landscape.agentRightPathD}
            fill={colorAgentSilhouette}
            className="agent-silhouette-right"
          />
        </motion.g>

        {/* Causal Transference Stream & Convergence Locus (Stage 5) */}
        <motion.g
          className="layer-causal-stream"
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.8, ease: easeOut, delay: 0.68 }}
        >
          <path d={landscape.causalPathD} fill={colorFgRidge} className="causal-stream-white" />
          <path d={landscape.causalAmberPathD} fill={colorAmber} className="causal-stream-amber" />
        </motion.g>
      </svg>
    </div>
  );
};
