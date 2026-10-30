/**
 * GranularThreeScene.ts
 *
 * Direct Three.js Controller for D3 Story Lab (Phase 9 — Persistent Cinematic Shell).
 * Manages the single persistent global WebGL point-cloud environment across all 8 workspaces.
 *
 * Features:
 * - 8 distinct visual workspace motifs interpolated 100% on the GPU:
 *   hero | world | actors | arcs | simulation | script | storyboard | export
 * - Smooth GPU morphing via uMotifFrom -> uMotifTo and uMotifProgress (~750–900ms).
 * - Per-workspace legibility governor (opacity, turbulence, pointScale, central clearing for script).
 * - Hardware Optimization: Capped DPR (1.5x), ~26,000–52,000 points on GPU.
 * - Zero JS position mutation in requestAnimationFrame loop (all motion driven by uTime on GPU).
 * - Visibility listener to pause rendering when backgrounded.
 * - Clean disposal with zero memory leaks when application actually unmounts.
 */

import * as THREE from 'three';
import { QualityBudget, getQualityBudget, QualityTier } from './qualityTiers';
import { granularVertexShader, granularFragmentShader } from './pointShaders';
import { generate3DPointCloud, PointCloudBuffers } from './pointGenerators3D';

export type GranularMotif =
  | 'hero'
  | 'world'
  | 'actors'
  | 'arcs'
  | 'simulation'
  | 'script'
  | 'storyboard'
  | 'export';

export function motifToId(motif: GranularMotif): number {
  switch (motif) {
    case 'hero': return 0.0;
    case 'world': return 1.0;
    case 'actors': return 2.0;
    case 'arcs': return 3.0;
    case 'simulation': return 4.0;
    case 'script': return 5.0;
    case 'storyboard': return 6.0;
    case 'export': return 7.0;
    default: return 0.0;
  }
}

interface MotifConfig {
  camZ: number;
  camY: number;
  opacity: number;
  turbulence: number;
  centerClear: number;
  pointScale: number;
  accentStrength: number;
}

const MOTIF_CONFIGS: Record<GranularMotif, MotifConfig> = {
  hero: {
    camZ: 10.5,
    camY: 0.0,
    opacity: 0.95,
    turbulence: 1.0,
    centerClear: 0.0,
    pointScale: 1.05,
    accentStrength: 0.90,
  },
  world: {
    camZ: 13.0,
    camY: 1.4,
    opacity: 0.70,
    turbulence: 0.50,
    centerClear: 0.0,
    pointScale: 0.90,
    accentStrength: 0.40,
  },
  actors: {
    camZ: 10.0,
    camY: 0.35,
    opacity: 0.65,
    turbulence: 0.60,
    centerClear: 0.0,
    pointScale: 1.0,
    accentStrength: 0.55,
  },
  arcs: {
    camZ: 11.2,
    camY: 0.0,
    opacity: 0.60,
    turbulence: 0.70,
    centerClear: 0.0,
    pointScale: 0.95,
    accentStrength: 0.65,
  },
  simulation: {
    camZ: 10.8,
    camY: 0.0,
    opacity: 0.65,
    turbulence: 1.15,
    centerClear: 0.0,
    pointScale: 1.10,
    accentStrength: 0.85,
  },
  script: {
    camZ: 11.5,
    camY: 0.0,
    opacity: 0.24, // Low opacity & high center clearing for screenplay legibility (§14)
    turbulence: 0.20,
    centerClear: 1.0,
    pointScale: 0.75,
    accentStrength: 0.20,
  },
  storyboard: {
    camZ: 11.0,
    camY: 0.0,
    opacity: 0.45,
    turbulence: 0.40,
    centerClear: 0.0,
    pointScale: 0.90,
    accentStrength: 0.45,
  },
  export: {
    camZ: 11.5,
    camY: 0.0,
    opacity: 0.20,
    turbulence: 0.15,
    centerClear: 0.0,
    pointScale: 0.70,
    accentStrength: 0.15,
  },
};

export interface SceneOptions {
  tier?: QualityTier;
  seed?: number;
  motif?: GranularMotif;
  onSettled?: () => void;
}

export class GranularThreeScene {
  private canvas: HTMLCanvasElement;
  private renderer: THREE.WebGLRenderer | null = null;
  private camera: THREE.PerspectiveCamera | null = null;
  private scene: THREE.Scene | null = null;
  private geometry: THREE.BufferGeometry | null = null;
  private material: THREE.ShaderMaterial | null = null;
  private pointsMesh: THREE.Points | null = null;

  private budget: QualityBudget;
  private animationFrameId: number | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private visibilityHandler: (() => void) | null = null;

  private startTime: number = 0;
  private lastFrameTime: number = 0;
  private isDisposed: boolean = false;
  private isPaused: boolean = false;
  private isThrottled: boolean = false;
  private throttleFps: number = 30;
  private lastRenderTime: number = 0;
  private isHovered: boolean = false;
  private hoverProgress: number = 0; // 0.0 to 1.0

  private resolveProgress: number = 0; // 0.0 to 1.0
  private currentOpacity: number = 0.0;
  private currentTurbulence: number = 1.0;
  private currentPointScale: number = 1.0;
  private currentCenterClear: number = 0.0;
  private currentAccentStrength: number = 0.9;

  // Active & Morphing Motifs
  private motif: GranularMotif = 'hero';
  private motifFrom: GranularMotif = 'hero';
  private motifTo: GranularMotif = 'hero';
  private motifTransitionStartTime: number = 0;
  private motifTransitionDuration: number = 800; // 800ms smooth GPU interpolation (§6)

  // Camera framing coordinates
  private targetCamZ: number = 10.5;
  private targetCamY: number = 0.0;
  private currentCamZ: number = 11.8;
  private currentCamY: number = 0.0;

  private onSettled?: () => void;
  private hasNotifiedSettled: boolean = false;

  constructor(canvas: HTMLCanvasElement, options: SceneOptions = {}) {
    this.canvas = canvas;
    this.budget = getQualityBudget(options.tier || 'HIGH');
    this.motif = options.motif || 'hero';
    this.motifFrom = this.motif;
    this.motifTo = this.motif;
    this.onSettled = options.onSettled;

    const initialCfg = MOTIF_CONFIGS[this.motif] || MOTIF_CONFIGS.hero;
    this.targetCamZ = initialCfg.camZ;
    this.targetCamY = initialCfg.camY;
    this.currentTurbulence = initialCfg.turbulence;
    this.currentPointScale = initialCfg.pointScale;
    this.currentCenterClear = initialCfg.centerClear;
    this.currentAccentStrength = initialCfg.accentStrength;

    this.init(options.seed || 927);
  }

  private init(seed: number): void {
    const width = this.canvas.clientWidth || (typeof window !== 'undefined' ? window.innerWidth : 1200);
    const height = this.canvas.clientHeight || (typeof window !== 'undefined' ? window.innerHeight : 800);

    // 1. WebGL Renderer with capped DPR and alpha transparency
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
      preserveDrawingBuffer: false,
    });
    this.renderer.setSize(width, height, false);
    this.renderer.setPixelRatio(this.budget.dpr);
    this.renderer.setClearColor(0x000000, 0.0);

    // 2. Perspective Camera (centered directly on the granular environment)
    this.camera = new THREE.PerspectiveCamera(42, width / Math.max(height, 1), 0.1, 100);
    this.camera.position.set(0, this.currentCamY, this.currentCamZ);
    this.camera.lookAt(0, 0, 0);

    // 3. Scene
    this.scene = new THREE.Scene();

    // 4. Point Cloud Buffers & Geometry
    const buffers: PointCloudBuffers = generate3DPointCloud(this.budget.pointCount, seed);
    this.geometry = new THREE.BufferGeometry();

    this.geometry.setAttribute('position', new THREE.BufferAttribute(buffers.positions, 3));
    this.geometry.setAttribute('aTarget', new THREE.BufferAttribute(buffers.targets, 3));
    this.geometry.setAttribute('aColor', new THREE.BufferAttribute(buffers.colors, 3));
    this.geometry.setAttribute('aSize', new THREE.BufferAttribute(buffers.sizes, 1));
    this.geometry.setAttribute('aPhase', new THREE.BufferAttribute(buffers.phases, 1));
    this.geometry.setAttribute('aLayerId', new THREE.BufferAttribute(buffers.layerIds, 1));

    // 5. Custom GLSL Shader Material
    this.material = new THREE.ShaderMaterial({
      vertexShader: granularVertexShader,
      fragmentShader: granularFragmentShader,
      uniforms: {
        uTime: { value: 0.0 },
        uProgress: { value: 0.0 },
        uPointSize: { value: 1.0 },
        uDepthFade: { value: 1.0 },
        uAmberBoost: { value: 0.0 },
        uOpacity: { value: 0.0 },
        // Motif Transition Uniforms (§6)
        uMotifFrom: { value: motifToId(this.motifFrom) },
        uMotifTo: { value: motifToId(this.motifTo) },
        uMotifProgress: { value: 1.0 },
        uTurbulence: { value: this.currentTurbulence },
        uPointScale: { value: this.currentPointScale },
        uCenterClear: { value: this.currentCenterClear },
        uAccentStrength: { value: this.currentAccentStrength },
      },
      transparent: true,
      depthWrite: false,
      blending: THREE.NormalBlending,
    });

    this.pointsMesh = new THREE.Points(this.geometry, this.material);
    this.scene.add(this.pointsMesh);

    // 6. Listeners & ResizeObserver
    this.setupListeners();

    // 7. Start render loop
    this.startTime = performance.now();
    this.lastFrameTime = this.startTime;
    this.tick(this.startTime);
  }

  private setupListeners(): void {
    // Visibility listener to pause rendering when backgrounded (power saving §15)
    this.visibilityHandler = () => {
      if (document.hidden) {
        this.isPaused = true;
      } else {
        this.isPaused = false;
        this.lastFrameTime = performance.now();
        if (!this.animationFrameId && !this.isDisposed) {
          this.animationFrameId = requestAnimationFrame(this.tick.bind(this));
        }
      }
    };
    document.addEventListener('visibilitychange', this.visibilityHandler);

    // ResizeObserver for responsive canvas updates
    if (typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver((entries) => {
        if (entries[0] && this.renderer && this.camera && !this.isDisposed) {
          const { width, height } = entries[0].contentRect;
          if (width > 0 && height > 0) {
            this.resize(width, height);
          }
        }
      });
      this.resizeObserver.observe(this.canvas);
    }
  }

  public resize(width: number, height: number): void {
    if (!this.renderer || !this.camera || this.isDisposed) return;
    this.camera.aspect = width / Math.max(height, 1);
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
    this.renderer.setPixelRatio(this.budget.dpr);
  }

  public setHovered(hovered: boolean): void {
    this.isHovered = hovered;
  }

  public setMotif(nextMotif: GranularMotif): void {
    if (nextMotif === this.motif && this.motifFrom === this.motifTo) {
      return;
    }

    this.motifFrom = this.motif;
    this.motifTo = nextMotif;
    this.motif = nextMotif;
    this.motifTransitionStartTime = performance.now();

    const targetCfg = MOTIF_CONFIGS[nextMotif] || MOTIF_CONFIGS.hero;
    this.targetCamZ = targetCfg.camZ;
    this.targetCamY = targetCfg.camY;
  }

  public getMotif(): GranularMotif {
    return this.motif;
  }

  public pause(): void {
    this.isPaused = true;
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  public resume(): void {
    if (!this.isPaused) return;
    this.isPaused = false;
    this.lastFrameTime = performance.now();
    this.lastRenderTime = this.lastFrameTime;
    if (!this.animationFrameId && !this.isDisposed) {
      this.animationFrameId = requestAnimationFrame(this.tick.bind(this));
    }
  }

  public setThrottled(throttled: boolean, fps: number = 30): void {
    this.isThrottled = throttled;
    this.throttleFps = fps;
  }

  private tick(timestamp: number): void {
    if (this.isDisposed) return;

    if (this.isPaused) {
      this.animationFrameId = null;
      return;
    }

    if (this.isThrottled) {
      const minInterval = 1000 / this.throttleFps;
      if (timestamp - this.lastRenderTime < minInterval) {
        this.animationFrameId = requestAnimationFrame(this.tick.bind(this));
        return;
      }
      this.lastRenderTime = timestamp;
    }

    const elapsedTotal = (timestamp - this.startTime) / 1000;
    const delta = Math.min((timestamp - this.lastFrameTime) / 1000, 0.1);
    this.lastFrameTime = timestamp;

    // -------------------------------------------------------------------------
    // Initial 5-Stage Resolve Entrance Sequence (1.2–1.8s)
    // -------------------------------------------------------------------------
    this.resolveProgress = Math.min(1.0, this.resolveProgress + delta * 0.75);

    if (elapsedTotal > 1.8 && !this.hasNotifiedSettled) {
      this.hasNotifiedSettled = true;
      this.onSettled?.();
    }

    // -------------------------------------------------------------------------
    // Smooth Motif Interpolation on the GPU (§5, §6)
    // -------------------------------------------------------------------------
    let motifProgress = 1.0;
    if (this.motifTransitionStartTime > 0) {
      const transitionElapsed = timestamp - this.motifTransitionStartTime;
      const rawProgress = Math.min(1.0, transitionElapsed / this.motifTransitionDuration);
      // Cinematic easing: cubic-bezier(0.16, 1, 0.3, 1) approximation
      motifProgress = rawProgress === 1.0 ? 1.0 : 1.0 - Math.pow(1.0 - rawProgress, 3);

      if (rawProgress >= 1.0) {
        this.motifFrom = this.motifTo;
        this.motifTransitionStartTime = 0;
      }
    }

    // Target parameters from active and target motifs
    const targetCfg = MOTIF_CONFIGS[this.motifTo] || MOTIF_CONFIGS.hero;
    const fromCfg   = MOTIF_CONFIGS[this.motifFrom] || MOTIF_CONFIGS.hero;

    const destOpacity = THREE.MathUtils.lerp(fromCfg.opacity, targetCfg.opacity, motifProgress);
    const destTurbulence = THREE.MathUtils.lerp(fromCfg.turbulence, targetCfg.turbulence, motifProgress);
    const destPointScale = THREE.MathUtils.lerp(fromCfg.pointScale, targetCfg.pointScale, motifProgress);
    const destCenterClear = THREE.MathUtils.lerp(fromCfg.centerClear, targetCfg.centerClear, motifProgress);
    const destAccentStrength = THREE.MathUtils.lerp(fromCfg.accentStrength, targetCfg.accentStrength, motifProgress);

    // Smoothly lerp scene parameters
    this.currentOpacity += (destOpacity - this.currentOpacity) * delta * 4.0;
    this.currentTurbulence += (destTurbulence - this.currentTurbulence) * delta * 4.0;
    this.currentPointScale += (destPointScale - this.currentPointScale) * delta * 4.0;
    this.currentCenterClear += (destCenterClear - this.currentCenterClear) * delta * 4.0;
    this.currentAccentStrength += (destAccentStrength - this.currentAccentStrength) * delta * 4.0;

    // Smoothly lerp camera position
    this.currentCamZ += (this.targetCamZ - this.currentCamZ) * delta * 3.0;
    this.currentCamY += (this.targetCamY - this.currentCamY) * delta * 3.0;

    // Hover smoothing
    const targetHover = this.isHovered ? 1.0 : 0.0;
    this.hoverProgress += (targetHover - this.hoverProgress) * delta * 5.0;

    // Apply Camera Position with subtle hover zoom
    if (this.camera) {
      const camZHover = this.currentCamZ - this.hoverProgress * 0.35;
      this.camera.position.set(0, this.currentCamY, camZHover);
      this.camera.lookAt(0, 0, 0);
    }

    // Update Uniforms on GPU (ZERO JS coordinate calculation in RAF loop!)
    if (this.material) {
      const u = this.material.uniforms;
      u.uTime.value = elapsedTotal;
      u.uProgress.value = this.resolveProgress;
      u.uOpacity.value = this.currentOpacity;
      u.uAmberBoost.value = this.hoverProgress;

      u.uMotifFrom.value = motifToId(this.motifFrom);
      u.uMotifTo.value = motifToId(this.motifTo);
      u.uMotifProgress.value = motifProgress;
      u.uTurbulence.value = this.currentTurbulence;
      u.uPointScale.value = this.currentPointScale;
      u.uCenterClear.value = this.currentCenterClear;
      u.uAccentStrength.value = this.currentAccentStrength;
    }

    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }

    this.animationFrameId = requestAnimationFrame(this.tick.bind(this));
  }

  public dispose(): void {
    if (this.isDisposed) return;
    this.isDisposed = true;

    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }

    if (this.visibilityHandler) {
      document.removeEventListener('visibilitychange', this.visibilityHandler);
      this.visibilityHandler = null;
    }

    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }

    if (this.pointsMesh && this.scene) {
      this.scene.remove(this.pointsMesh);
    }

    if (this.geometry) {
      this.geometry.dispose();
      this.geometry = null;
    }

    if (this.material) {
      this.material.dispose();
      this.material = null;
    }

    if (this.renderer) {
      this.renderer.dispose();
      this.renderer = null;
    }

    this.camera = null;
    this.scene = null;
    this.pointsMesh = null;
  }
}

export { granularVertexShader, granularFragmentShader };
