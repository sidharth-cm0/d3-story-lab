/**
 * GranularThreeCanvas.tsx
 *
 * React wrapper for the Three.js granular point-cloud experience (Phase 9.2.7).
 *
 * Guarantees:
 * 1. Automatic WebGL capability detection with immediate SVG fallback when unsupported.
 * 2. Reduced-motion compliance (renders static finished composition under prefers-reduced-motion).
 * 3. 100% pointer-events transparency (zero obstruction of DOM buttons or typography).
 * 4. Progressive non-blocking mount (DOM is authoritative and immediately interactive).
 * 5. Clean lifecycle unmount with zero memory leaks.
 * 6. Sits at z-index: -1 and pointer-events: none behind editorial typography and controls.
 */

import React, { useEffect, useRef, useState } from 'react';
import { isWebGLAvailable } from './webglDetector';
import { detectQualityTier, QualityTier } from './qualityTiers';
import { GranularThreeScene, GranularMotif } from './GranularThreeScene';
import { GranularNarrativeField } from '../GranularNarrativeField';
import { usePrefersReducedMotion } from '../../../hooks/usePrefersReducedMotion';

export interface GranularThreeCanvasProps {
  seed?: number;
  motif?: GranularMotif;
  isHovered?: boolean;
  isPaused?: boolean;
  isThrottled?: boolean;
  throttleFps?: number;
  forceTier?: QualityTier;
  width?: string | number;
  height?: string | number;
  className?: string;
  style?: React.CSSProperties;
  onSettled?: () => void;
  'data-testid'?: string;
}

export const GranularThreeCanvas: React.FC<GranularThreeCanvasProps> = ({
  seed = 927,
  motif = 'hero',
  isHovered = false,
  isPaused = false,
  isThrottled = false,
  throttleFps = 30,
  forceTier,
  width = '100%',
  height = '100%',
  className = '',
  style,
  onSettled,
  'data-testid': testId = 'granular-three-canvas',
}) => {
  const prefersReduced = usePrefersReducedMotion();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<GranularThreeScene | null>(null);
  const [useFallback, setUseFallback] = useState<boolean>(false);

  // Check WebGL availability and reduced motion
  const webglSupported = isWebGLAvailable();
  const tier = detectQualityTier({ prefersReducedMotion: prefersReduced, forceTier });
  const shouldRenderFallback = !webglSupported || prefersReduced || tier === 'FALLBACK' || useFallback;

  const onSettledRef = useRef(onSettled);
  useEffect(() => {
    onSettledRef.current = onSettled;
  }, [onSettled]);

  useEffect(() => {
    if (shouldRenderFallback) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;

    try {
      const scene = new GranularThreeScene(canvas, {
        tier,
        seed,
        motif,
        onSettled: () => onSettledRef.current?.(),
      });
      sceneRef.current = scene;
    } catch (err) {
      console.warn('[GranularThreeCanvas] WebGL init failed, falling back to SVG:', err);
      setUseFallback(true);
    }

    return () => {
      if (sceneRef.current) {
        sceneRef.current.dispose();
        sceneRef.current = null;
      }
    };
  }, [shouldRenderFallback, tier, seed]);

  // Sync hover reactivity
  useEffect(() => {
    if (sceneRef.current) {
      sceneRef.current.setHovered(isHovered);
    }
  }, [isHovered]);

  // Sync motif
  useEffect(() => {
    if (sceneRef.current) {
      sceneRef.current.setMotif(motif);
    }
  }, [motif]);

  // Sync pause state
  useEffect(() => {
    if (sceneRef.current) {
      if (isPaused) {
        sceneRef.current.pause();
      } else {
        sceneRef.current.resume();
      }
    }
  }, [isPaused]);

  // Sync throttled state
  useEffect(() => {
    if (sceneRef.current) {
      sceneRef.current.setThrottled(Boolean(isThrottled), throttleFps || 30);
    }
  }, [isThrottled, throttleFps]);

  if (shouldRenderFallback) {
    return (
      <div
        className={`granular-three-container fallback-mode ${className}`}
        style={{
          width,
          height,
          position: 'relative',
          pointerEvents: 'none',
          zIndex: -1,
          ...style,
        }}
        data-testid={testId}
        data-fallback="true"
        aria-hidden="true"
        role="presentation"
      >
        <GranularNarrativeField
          seed={seed}
          isHovered={isHovered}
          width="100%"
          height="100%"
        />
      </div>
    );
  }

  return (
    <div
      className={`granular-three-container webgl-mode ${className}`}
      style={{
        width,
        height,
        position: 'relative',
        pointerEvents: 'none',
        zIndex: -1,
        ...style,
      }}
      data-testid={testId}
      data-fallback="false"
      aria-hidden="true"
      role="presentation"
    >
      <canvas
        ref={canvasRef}
        className="granular-three-webgl-canvas"
        style={{
          width: '100%',
          height: '100%',
          display: 'block',
          pointerEvents: 'none',
          position: 'absolute',
          top: 0,
          left: 0,
          zIndex: -1,
        }}
        aria-hidden="true"
      />
    </div>
  );
};
