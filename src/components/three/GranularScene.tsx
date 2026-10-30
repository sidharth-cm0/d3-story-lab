/**
 * GranularScene.tsx
 *
 * Unified Three.js Granular Scene Component for D3 Story Lab:
 * - Fluid, undulating granular landscape and narrative probability fields
 * - Abstract humanoid agent silhouettes emerging from particles
 * - Causal transference streams and story structure nodes
 * - Workspace-specific motifs (home, world, actors, arcs, simulation, script, storyboard, export)
 * - Adaptive GPU quality tiers (HIGH, MEDIUM, LOW) with DPR capped at 1.5
 * - Zero click interception (pointer-events: none, aria-hidden="true")
 * - Safe WebGL detection with instant deterministic SVG fallback
 * - Reduced-motion safety with zero-animation static render
 */

import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { isWebGLAvailable } from '../granular/three/webglDetector';
import { detectQualityTier, getQualityBudget, QualityTier } from '../granular/three/qualityTiers';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { GranularNarrativeField } from '../granular/GranularNarrativeField';
import { createParticleMaterial } from './ParticleMaterial';
import { generateTerrainPoints } from './ParticleTerrain';
import { generateAgentPoints } from './AgentPointCloud';
import { generateFlowPoints } from './NarrativeFlow';

export type WorkspaceGranularMotif =
  | 'home'
  | 'world'
  | 'actors'
  | 'arcs'
  | 'simulation'
  | 'script'
  | 'storyboard'
  | 'export';

export interface GranularSceneProps {
  motif?: WorkspaceGranularMotif;
  isHovered?: boolean;
  tier?: QualityTier;
  seed?: number;
  className?: string;
  style?: React.CSSProperties;
  onSettled?: () => void;
}

export const GranularScene: React.FC<GranularSceneProps> = ({
  motif = 'home',
  isHovered = false,
  tier: propTier,
  seed = 927,
  className = '',
  style = {},
  onSettled,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const prefersReducedMotion = usePrefersReducedMotion();

  const [webGlSupported] = useState<boolean>(() => isWebGLAvailable());

  useEffect(() => {
    // If WebGL is unavailable or reduced motion is active, do not initialize Three.js
    if (!webGlSupported || prefersReducedMotion || !canvasRef.current) {
      return;
    }

    const canvas = canvasRef.current;
    const activeTier = propTier || detectQualityTier();
    const budget = getQualityBudget(activeTier);

    if (activeTier === 'FALLBACK' || budget.pointCount === 0) {
      return;
    }

    const width = canvas.clientWidth || window.innerWidth || 1200;
    const height = canvas.clientHeight || window.innerHeight || 800;

    // 1. WebGL Renderer
    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        alpha: true,
        antialias: true,
        powerPreference: 'high-performance',
        preserveDrawingBuffer: false,
      });
    } catch {
      return;
    }

    renderer.setSize(width, height, false);
    renderer.setPixelRatio(budget.dpr);
    renderer.setClearColor(0x000000, 0.0);

    // 2. Perspective Camera
    const camera = new THREE.PerspectiveCamera(42, width / Math.max(height, 1), 0.1, 100);
    camera.position.set(0, 0.9, 12.5);
    camera.lookAt(0, 0.15, 0);

    // 3. Scene
    const scene = new THREE.Scene();

    // 4. Geometry Point Distribution across Topological Layers
    // - Terrain: ~65%
    // - Agents: ~24% (Agent A + Agent B)
    // - Causal Stream / Flow: ~11%
    const totalPoints = budget.pointCount;
    const terrainCount = Math.floor(totalPoints * 0.65);
    const agentCount = Math.floor(totalPoints * 0.24);
    const flowCount = totalPoints - terrainCount - agentCount;

    const terrain = generateTerrainPoints(terrainCount, seed);
    const agents = generateAgentPoints(agentCount, seed + 1);
    const flow = generateFlowPoints(flowCount, seed + 2);

    // Combine into single BufferGeometry for single draw-call performance
    const positions = new Float32Array(totalPoints * 3);
    const targets = new Float32Array(totalPoints * 3);
    const colors = new Float32Array(totalPoints * 3);
    const sizes = new Float32Array(totalPoints);
    const phases = new Float32Array(totalPoints);
    const layerIds = new Float32Array(totalPoints);

    // Copy terrain
    positions.set(terrain.positions, 0);
    targets.set(terrain.targets, 0);
    colors.set(terrain.colors, 0);
    sizes.set(terrain.sizes, 0);
    phases.set(terrain.phases, 0);
    layerIds.set(terrain.layerIds, 0);

    // Copy agents
    let offset3 = terrainCount * 3;
    let offset1 = terrainCount;
    positions.set(agents.positions, offset3);
    targets.set(agents.targets, offset3);
    colors.set(agents.colors, offset3);
    sizes.set(agents.sizes, offset1);
    phases.set(agents.phases, offset1);
    layerIds.set(agents.layerIds, offset1);

    // Copy flow
    offset3 += agentCount * 3;
    offset1 += agentCount;
    positions.set(flow.positions, offset3);
    targets.set(flow.targets, offset3);
    colors.set(flow.colors, offset3);
    sizes.set(flow.sizes, offset1);
    phases.set(flow.phases, offset1);
    layerIds.set(flow.layerIds, offset1);

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('aTarget', new THREE.BufferAttribute(targets, 3));
    geometry.setAttribute('aColor', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1));
    geometry.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1));
    geometry.setAttribute('aLayerId', new THREE.BufferAttribute(layerIds, 1));

    // 5. Shader Material
    const material = createParticleMaterial({
      uPointSize: { value: 1.0 },
      uPixelRatio: { value: budget.dpr },
    });

    const pointsMesh = new THREE.Points(geometry, material);
    scene.add(pointsMesh);

    // 6. State & Animation Management
    let animId: number | null = null;
    let startTime = performance.now();
    let lastTime = startTime;
    let isDisposed = false;
    let isPaused = false;

    let resolveProgress = 0.0;
    let morphProgress = 0.0;
    let currentOpacity = 0.0;
    let hoverVal = 0.0;
    let hasNotifiedSettled = false;

    // Motif-based camera targets
    const getCameraTargets = (m: WorkspaceGranularMotif) => {
      switch (m) {
        case 'home':
          return { camY: 0.9, camZ: 12.2, maxOpacity: 0.95, depthFade: 1.0 };
        case 'world':
          return { camY: 2.6, camZ: 14.8, maxOpacity: 0.85, depthFade: 1.1 };
        case 'actors':
          return { camY: 1.2, camZ: 10.4, maxOpacity: 0.90, depthFade: 0.9 };
        case 'arcs':
          return { camY: 0.6, camZ: 11.5, maxOpacity: 0.88, depthFade: 1.0 };
        case 'simulation':
          return { camY: 1.0, camZ: 12.8, maxOpacity: 0.82, depthFade: 1.0 };
        case 'script':
          return { camY: 0.8, camZ: 14.0, maxOpacity: 0.18, depthFade: 1.4 }; // Ultra-calm for reading
        case 'storyboard':
          return { camY: 0.9, camZ: 12.5, maxOpacity: 0.40, depthFade: 1.2 };
        case 'export':
          return { camY: 1.0, camZ: 13.5, maxOpacity: 0.25, depthFade: 1.3 };
        default:
          return { camY: 0.9, camZ: 12.2, maxOpacity: 0.90, depthFade: 1.0 };
      }
    };

    let camTargets = getCameraTargets(motif);
    let curCamY = camTargets.camY + 0.4;
    let curCamZ = camTargets.camZ + 1.2;

    const onVisibilityChange = () => {
      if (document.hidden) {
        isPaused = true;
      } else {
        isPaused = false;
        lastTime = performance.now();
        if (!animId && !isDisposed) {
          animId = requestAnimationFrame(tick);
        }
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);

    const resizeObserver = typeof ResizeObserver !== 'undefined'
      ? new ResizeObserver((entries) => {
          if (entries[0] && renderer && !isDisposed) {
            const { width: w, height: h } = entries[0].contentRect;
            if (w > 0 && h > 0) {
              camera.aspect = w / h;
              camera.updateProjectionMatrix();
              renderer.setSize(w, h, false);
            }
          }
        })
      : null;

    resizeObserver?.observe(canvas);

    // Render loop
    const tick = (timestamp: number) => {
      if (isDisposed) return;
      if (isPaused) {
        animId = null;
        return;
      }

      const elapsed = (timestamp - startTime) / 1000;
      const delta = Math.min((timestamp - lastTime) / 1000, 0.1);
      lastTime = timestamp;

      // Update motif camera targets
      camTargets = getCameraTargets(motif);

      // Staged Resolve Sequence (0.0s to 1.4s)
      currentOpacity = Math.min(camTargets.maxOpacity, currentOpacity + delta * 1.8);
      resolveProgress = Math.min(1.0, resolveProgress + delta * 0.85);

      if (elapsed > 0.35) {
        morphProgress = Math.min(1.0, morphProgress + delta * 0.95);
      }

      // Smooth camera motion
      curCamY += (camTargets.camY - curCamY) * delta * 2.5;
      curCamZ += (camTargets.camZ - curCamZ) * delta * 2.5;

      // Hover response
      const targetHover = isHovered ? 1.0 : 0.0;
      hoverVal += (targetHover - hoverVal) * delta * 5.0;

      // Camera placement with subtle hover parallax
      camera.position.set(0, curCamY, curCamZ - hoverVal * 0.25);
      camera.lookAt(0, 0.15, 0);

      // Uniforms update
      const u = material.uniforms;
      u.uTime.value = elapsed;
      u.uProgress.value = resolveProgress;
      u.uMorph.value = morphProgress;
      u.uOpacity.value = currentOpacity;
      u.uDepthFade.value = camTargets.depthFade;
      u.uAmberBoost.value = hoverVal;

      if (renderer) {
        renderer.render(scene, camera);
      }

      if (elapsed > 1.4 && !hasNotifiedSettled) {
        hasNotifiedSettled = true;
        onSettled?.();
      }

      animId = requestAnimationFrame(tick);
    };

    animId = requestAnimationFrame(tick);

    // Cleanup
    return () => {
      isDisposed = true;
      if (animId) cancelAnimationFrame(animId);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      resizeObserver?.disconnect();

      if (pointsMesh) scene.remove(pointsMesh);
      geometry.dispose();
      material.dispose();
      renderer?.dispose();
      renderer?.forceContextLoss();
      renderer = null;
    };
  }, [webGlSupported, prefersReducedMotion, motif, isHovered, propTier, seed, onSettled]);

  // Fallback for non-WebGL or reduced motion
  if (!webGlSupported || prefersReducedMotion) {
    return (
      <div
        ref={containerRef}
        className={`granular-three-container ${className}`}
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          overflow: 'hidden',
          ...style,
        }}
        aria-hidden="true"
        role="presentation"
      >
        <GranularNarrativeField
          width="100%"
          height="100%"
          isHovered={isHovered}
          seed={seed}
        />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`granular-three-container ${className}`}
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
        ...style,
      }}
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
        }}
      />
    </div>
  );
};
