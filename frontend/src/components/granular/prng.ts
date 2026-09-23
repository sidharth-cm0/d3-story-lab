/**
 * prng.ts
 *
 * Deterministic pseudo-random number generator (Mulberry32) and
 * precomputed point-cloud geometry utilities for D3 Story Lab (Phase 9.2.5).
 *
 * Guarantees:
 * 1. Byte-identical output given the same seed (no visual layout shift across re-renders).
 * 2. Zero runtime physics engine or continuous rAF computation.
 * 3. Pure mathematical coordinate generation for SVG / CSS rendering.
 */

export interface GranularPoint {
  id: string;
  x: number;
  y: number;
  r: number;
  opacity: number;
  isAmber?: boolean;
}

/**
 * Fast 32-bit deterministic PRNG (Mulberry32 algorithm)
 * Produces pseudo-random floats uniformly distributed in [0, 1).
 */
export function mulberry32(seed: number): () => number {
  let s = seed >>> 0;
  return function () {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface FieldOptions {
  minR?: number;
  maxR?: number;
  minOpacity?: number;
  maxOpacity?: number;
  amberRatio?: number;
  densityBiasY?: 'uniform' | 'bottom' | 'top' | 'center';
}

/**
 * Generates deterministic scattered points across a bounding rectangle
 */
export function generatePointField(
  count: number,
  seed: number = 42,
  width: number = 1000,
  height: number = 400,
  options: FieldOptions = {}
): GranularPoint[] {
  const {
    minR = 0.75,
    maxR = 2.0,
    minOpacity = 0.15,
    maxOpacity = 0.7,
    amberRatio = 0.06,
    densityBiasY = 'uniform',
  } = options;

  const rand = mulberry32(seed);
  const points: GranularPoint[] = new Array(count);

  for (let i = 0; i < count; i++) {
    const rawX = rand();
    let rawY = rand();

    if (densityBiasY === 'bottom') {
      // Skew towards bottom (y near 1.0)
      rawY = Math.pow(rawY, 0.65);
    } else if (densityBiasY === 'top') {
      // Skew towards top (y near 0.0)
      rawY = Math.pow(rawY, 1.5);
    } else if (densityBiasY === 'center') {
      // Triangular distribution centered around 0.5
      rawY = (rawY + rand()) / 2;
    }

    const x = Math.round(rawX * width * 10) / 10;
    const y = Math.round(rawY * height * 10) / 10;
    const r = Math.round((minR + rand() * (maxR - minR)) * 100) / 100;
    const opacity = Math.round((minOpacity + rand() * (maxOpacity - minOpacity)) * 100) / 100;
    const isAmber = rand() < amberRatio;

    points[i] = {
      id: `pt-${seed}-${i}`,
      x,
      y,
      r,
      opacity,
      isAmber,
    };
  }

  return points;
}

export interface WaveOptions {
  baseY?: number;
  amplitude?: number;
  frequency?: number;
  layers?: number;
  amberRatio?: number;
}

/**
 * Generates deterministic points tracing 2-3 undulating narrative flow / probability terrain curves
 */
export function generateWavePoints(
  pointsPerLayer: number = 80,
  seed: number = 101,
  width: number = 1000,
  height: number = 300,
  options: WaveOptions = {}
): GranularPoint[] {
  const {
    baseY = height * 0.65,
    amplitude = 42,
    frequency = 0.006,
    layers = 3,
    amberRatio = 0.08,
  } = options;

  const rand = mulberry32(seed);
  const totalPoints = pointsPerLayer * layers;
  const points: GranularPoint[] = new Array(totalPoints);

  let idx = 0;
  for (let l = 0; l < layers; l++) {
    const layerOffset = (l - (layers - 1) / 2) * 28;
    const phase = l * 1.35;
    const freqMult = 1.0 + l * 0.25;

    for (let p = 0; p < pointsPerLayer; p++) {
      const normalizedX = p / (pointsPerLayer - 1);
      const x = Math.round(normalizedX * width * 10) / 10;

      // Harmonic undulating wave function (narrative probability surface)
      const harmonic1 = Math.sin(x * frequency * freqMult + phase) * amplitude;
      const harmonic2 = Math.cos(x * frequency * 1.8 + phase * 1.5) * (amplitude * 0.4);
      const jitterY = (rand() - 0.5) * 22;

      const y = Math.round(Math.max(10, Math.min(height - 10, baseY + layerOffset + harmonic1 + harmonic2 + jitterY)) * 10) / 10;
      const r = Math.round((0.85 + (l * 0.3) + rand() * 0.8) * 100) / 100;
      const opacity = Math.round((0.2 + (l / layers) * 0.45 + rand() * 0.25) * 100) / 100;
      const isAmber = rand() < amberRatio;

      points[idx++] = {
        id: `wave-${seed}-${l}-${p}`,
        x,
        y,
        r,
        opacity,
        isAmber,
      };
    }
  }

  return points;
}

/**
 * Generates an original abstract dual-agent silhouette motif:
 * Two granular human-like silhouettes facing each other and passing narrative state across a causal particle bridge.
 */
export function generateSilhouettePoints(
  seed: number = 777,
  viewWidth: number = 800,
  viewHeight: number = 240
): {
  leftAgentPoints: GranularPoint[];
  rightAgentPoints: GranularPoint[];
  bridgePoints: GranularPoint[];
} {
  const rand = mulberry32(seed);

  // Left agent center (facing right towards x=400)
  const leftCenterX = viewWidth * 0.32;
  const leftCenterY = viewHeight * 0.52;

  // Right agent center (facing left towards x=400)
  const rightCenterX = viewWidth * 0.68;
  const rightCenterY = viewHeight * 0.52;

  const leftPoints: GranularPoint[] = [];
  const rightPoints: GranularPoint[] = [];
  const bridgePoints: GranularPoint[] = [];

  // Helper to generate abstract humanoid particle cloud (head, shoulders, torso silhouette)
  const createAgentCloud = (cx: number, cy: number, prefix: string, targetArray: GranularPoint[], facingRight: boolean) => {
    // 1. Head (dense oval) ~ 40 points
    for (let i = 0; i < 40; i++) {
      const angle = rand() * Math.PI * 2;
      const dist = Math.sqrt(rand());
      const hx = cx + Math.cos(angle) * dist * 16 + (facingRight ? 3 : -3);
      const hy = (cy - 52) + Math.sin(angle) * dist * 22;
      const r = 0.8 + rand() * 1.2;
      const opacity = 0.35 + rand() * 0.55;
      targetArray.push({
        id: `${prefix}-head-${i}`,
        x: Math.round(hx * 10) / 10,
        y: Math.round(hy * 10) / 10,
        r: Math.round(r * 100) / 100,
        opacity: Math.round(opacity * 100) / 100,
        isAmber: rand() < 0.04,
      });
    }

    // 2. Neck & Shoulders ~ 55 points
    for (let i = 0; i < 55; i++) {
      const shoulderSpread = (rand() - 0.5) * 72;
      const shoulderY = (cy - 24) + (rand() - 0.5) * 16 + Math.abs(shoulderSpread) * 0.15;
      const r = 0.8 + rand() * 1.4;
      const opacity = 0.3 + rand() * 0.5;
      targetArray.push({
        id: `${prefix}-sh-${i}`,
        x: Math.round((cx + shoulderSpread) * 10) / 10,
        y: Math.round(shoulderY * 10) / 10,
        r: Math.round(r * 100) / 100,
        opacity: Math.round(opacity * 100) / 100,
        isAmber: rand() < 0.05,
      });
    }

    // 3. Torso / Gestural Core ~ 65 points
    for (let i = 0; i < 65; i++) {
      const tY = (cy - 12) + rand() * 64;
      // Taper down as Y increases
      const taperWidth = 56 * (1 - ((tY - (cy - 12)) / 75) * 0.35);
      const tX = cx + (rand() - 0.5) * taperWidth;
      const r = 0.75 + rand() * 1.3;
      const opacity = 0.25 + rand() * 0.45;
      targetArray.push({
        id: `${prefix}-torso-${i}`,
        x: Math.round(tX * 10) / 10,
        y: Math.round(tY * 10) / 10,
        r: Math.round(r * 100) / 100,
        opacity: Math.round(opacity * 100) / 100,
        isAmber: rand() < 0.05,
      });
    }
  };

  createAgentCloud(leftCenterX, leftCenterY, 'left-agent', leftPoints, true);
  createAgentCloud(rightCenterX, rightCenterY, 'right-agent', rightPoints, false);

  // 4. Narrative transference / causal bridge particles between the two silhouettes (~50 points)
  for (let i = 0; i < 50; i++) {
    const t = i / 49;
    // Cubic bezier curve from left chest (t=0) arching upwards then connecting to right chest (t=1)
    const p0x = leftCenterX + 24;
    const p0y = leftCenterY - 14;
    const p1x = viewWidth * 0.42;
    const p1y = viewHeight * 0.26;
    const p2x = viewWidth * 0.58;
    const p2y = viewHeight * 0.26;
    const p3x = rightCenterX - 24;
    const p3y = rightCenterY - 14;

    const oneMinusT = 1 - t;
    const bx =
      Math.pow(oneMinusT, 3) * p0x +
      3 * Math.pow(oneMinusT, 2) * t * p1x +
      3 * oneMinusT * Math.pow(t, 2) * p2x +
      Math.pow(t, 3) * p3x;
    const by =
      Math.pow(oneMinusT, 3) * p0y +
      3 * Math.pow(oneMinusT, 2) * t * p1y +
      3 * oneMinusT * Math.pow(t, 2) * p2y +
      Math.pow(t, 3) * p3y;

    const jitterX = (rand() - 0.5) * 14;
    const jitterY = (rand() - 0.5) * 14;
    const r = 0.9 + rand() * 1.5;
    const opacity = 0.35 + rand() * 0.55;
    // Higher amber ratio on the causal bridge
    const isAmber = rand() < 0.28;

    bridgePoints.push({
      id: `bridge-${i}`,
      x: Math.round((bx + jitterX) * 10) / 10,
      y: Math.round((by + jitterY) * 10) / 10,
      r: Math.round(r * 100) / 100,
      opacity: Math.round(opacity * 100) / 100,
      isAmber,
    });
  }

  return {
    leftAgentPoints: leftPoints,
    rightAgentPoints: rightPoints,
    bridgePoints,
  };
}

/**
 * Generates an elliptical halo of granular particles around an active card / dossier / node
 */
export function generateHaloPoints(
  count: number = 48,
  seed: number = 333,
  cx: number = 100,
  cy: number = 100,
  rx: number = 90,
  ry: number = 90,
  jitter: number = 8
): GranularPoint[] {
  const rand = mulberry32(seed);
  const points: GranularPoint[] = new Array(count);

  for (let i = 0; i < count; i++) {
    const angle = (i / count) * Math.PI * 2 + (rand() - 0.5) * 0.15;
    const radialJitter = (rand() - 0.5) * jitter * 2;
    const curRx = rx + radialJitter;
    const curRy = ry + radialJitter;

    const x = Math.round((cx + Math.cos(angle) * curRx) * 10) / 10;
    const y = Math.round((cy + Math.sin(angle) * curRy) * 10) / 10;
    const r = Math.round((0.75 + rand() * 1.25) * 100) / 100;
    const opacity = Math.round((0.25 + rand() * 0.5) * 100) / 100;
    const isAmber = rand() < 0.12;

    points[i] = {
      id: `halo-${seed}-${i}`,
      x,
      y,
      r,
      opacity,
      isAmber,
    };
  }

  return points;
}

/**
 * Generates a horizontal granular divider with density concentrated at the center
 */
export function generateDividerPoints(
  count: number = 50,
  seed: number = 555,
  width: number = 800,
  cy: number = 12
): GranularPoint[] {
  const rand = mulberry32(seed);
  const points: GranularPoint[] = new Array(count);

  for (let i = 0; i < count; i++) {
    // Triangular distribution centered at width / 2
    const u = (rand() + rand()) / 2;
    const x = Math.round(u * width * 10) / 10;
    const distFromCenter = Math.abs(u - 0.5) * 2; // 0 at center, 1 at edge
    const y = Math.round((cy + (rand() - 0.5) * 8) * 10) / 10;
    const r = Math.round((0.7 + (1 - distFromCenter) * 0.9) * 100) / 100;
    const opacity = Math.round((0.15 + (1 - distFromCenter) * 0.55) * 100) / 100;
    const isAmber = rand() < (0.15 * (1 - distFromCenter));

    points[i] = {
      id: `div-${seed}-${i}`,
      x,
      y,
      r,
      opacity,
      isAmber,
    };
  }

  return points;
}
