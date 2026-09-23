/**
 * landscapeModel.ts
 *
 * Dense Point-Cloud Landscape and Abstract Agent Model for D3 Story Lab (Phase 9.2.6).
 *
 * Characteristics:
 * 1. Full-width continuous narrative terrain (Background, Midground, Foreground depth layers).
 * 2. Two recognizable abstract agent silhouettes made from particles (initiator & receptor).
 * 3. Causal transference particle stream bridging between agents and descending into the landscape.
 * 4. Ultra-high performance path batching: ~2,500 points rendered across just 8 SVG <path> elements.
 * 5. Deterministic Mulberry32 PRNG ensures zero visual layout shift.
 */

import { mulberry32, GranularPoint } from './prng';

export interface LandscapeLayers {
  // Depth Layer 1: Background Strata (tiny, soft, low-opacity)
  bgPoints: GranularPoint[];
  bgPathD: string;

  // Depth Layer 2: Midground Rolling Narrative Terrain (dense probability waves)
  midPoints: GranularPoint[];
  midPathD: string;

  // Depth Layer 3: Foreground Topological Ridges (luminous crests + amber nodes)
  fgPoints: GranularPoint[];
  fgPathD: string;
  fgAmberPoints: GranularPoint[];
  fgAmberPathD: string;

  // Silhouette: Left Agent (Initiator with reaching right arm)
  agentLeftPoints: GranularPoint[];
  agentLeftPathD: string;

  // Silhouette: Right Agent (Receptor with raised receptive arm)
  agentRightPoints: GranularPoint[];
  agentRightPathD: string;

  // Causal Transference Stream & Convergence Locus
  causalPoints: GranularPoint[];
  causalPathD: string;
  causalAmberPoints: GranularPoint[];
  causalAmberPathD: string;

  // Total point count across all layers
  totalPoints: number;
}

/**
 * Converts an array of GranularPoints into a single batched SVG path `d` string.
 * Uses optimized subpath arc syntax (M x-r y a r r 0 1 0 2r 0 a r r 0 1 0 -2r 0).
 */
export function pointsToSvgPath(points: GranularPoint[]): string {
  if (!points || points.length === 0) return '';
  const parts: string[] = new Array(points.length);

  for (let i = 0; i < points.length; i++) {
    const pt = points[i];
    const x = pt.x;
    const y = pt.y;
    const r = pt.r;
    const twoR = Math.round(r * 2 * 100) / 100;
    const negTwoR = -twoR;
    const startX = Math.round((x - r) * 10) / 10;

    parts[i] = `M${startX} ${y}a${r} ${r} 0 1 0 ${twoR} 0a${r} ${r} 0 1 0 ${negTwoR} 0`;
  }

  return parts.join('');
}

export interface LandscapeOptions {
  seed?: number;
  width?: number;
  height?: number;
  densityScale?: number; // 1.0 = desktop (~2400 pts), 0.65 = tablet (~1600 pts), 0.35 = mobile (~850 pts)
}

/**
 * Generates the full-width continuous granular narrative landscape and dual-agent forms.
 */
export function generateDenseNarrativeLandscape(options: LandscapeOptions = {}): LandscapeLayers {
  const {
    seed = 926,
    width = 1200,
    height = 380,
    densityScale = 1.0,
  } = options;

  const rand = mulberry32(seed);

  // -------------------------------------------------------------
  // 1. BACKGROUND TERRAIN STRATA (Depth Layer 1)
  // -------------------------------------------------------------
  const bgCount = Math.round(480 * densityScale);
  const bgPoints: GranularPoint[] = new Array(bgCount);

  for (let i = 0; i < bgCount; i++) {
    const normX = i / (bgCount - 1);
    const x = Math.round(normX * width * 10) / 10;
    // Deep harmonic waves flowing across entire width
    const wave1 = Math.sin(normX * Math.PI * 4 + 0.4) * 26;
    const wave2 = Math.cos(normX * Math.PI * 7 + 1.2) * 16;
    const bandOffset = ((i % 5) - 2) * 14;
    const jitterY = (rand() - 0.5) * 18;
    const y = Math.round(Math.max(180, Math.min(height - 15, 270 + wave1 + wave2 + bandOffset + jitterY)) * 10) / 10;

    const r = Math.round((0.65 + rand() * 0.35) * 100) / 100;
    const opacity = Math.round((0.14 + rand() * 0.16) * 100) / 100;

    bgPoints[i] = {
      id: `bg-${i}`,
      x,
      y,
      r,
      opacity,
      isAmber: false,
    };
  }

  // -------------------------------------------------------------
  // 2. MIDGROUND ROLLING NARRATIVE TERRAIN (Depth Layer 2)
  // -------------------------------------------------------------
  const midCount = Math.round(780 * densityScale);
  const midPoints: GranularPoint[] = new Array(midCount);

  for (let i = 0; i < midCount; i++) {
    const normX = i / (midCount - 1);
    const x = Math.round(normX * width * 10) / 10;
    // Multi-frequency probability surface waves
    const waveA = Math.sin(normX * Math.PI * 5 + 0.8) * 38;
    const waveB = Math.cos(normX * Math.PI * 9 + 2.1) * 22;
    const waveC = Math.sin(normX * Math.PI * 14) * 12;
    const layerTier = (i % 6) * 9;
    const jitterX = (rand() - 0.5) * 6;
    const jitterY = (rand() - 0.5) * 24;
    const y = Math.round(Math.max(160, Math.min(height - 10, 280 + waveA + waveB + waveC + layerTier + jitterY)) * 10) / 10;

    const r = Math.round((1.05 + rand() * 0.5) * 100) / 100;
    const opacity = Math.round((0.36 + rand() * 0.28) * 100) / 100;

    midPoints[i] = {
      id: `mid-${i}`,
      x: Math.round((x + jitterX) * 10) / 10,
      y,
      r,
      opacity,
      isAmber: false,
    };
  }

  // -------------------------------------------------------------
  // 3. FOREGROUND TOPOLOGICAL RIDGES & CRESTS (Depth Layer 3)
  // -------------------------------------------------------------
  const fgTotal = Math.round(440 * densityScale);
  const fgPoints: GranularPoint[] = [];
  const fgAmberPoints: GranularPoint[] = [];

  for (let i = 0; i < fgTotal; i++) {
    const normX = i / (fgTotal - 1);
    const x = Math.round(normX * width * 10) / 10;
    // Sharp crest contour tracing the narrative peak
    const crest = Math.sin(normX * Math.PI * 4.2 + 0.3) * 44 + Math.cos(normX * Math.PI * 8.5) * 18;
    const y = Math.round(Math.max(140, Math.min(height - 12, 295 + crest + (rand() - 0.5) * 12)) * 10) / 10;

    const r = Math.round((1.4 + rand() * 0.75) * 100) / 100;
    const opacity = Math.round((0.68 + rand() * 0.28) * 100) / 100;
    const isAmber = rand() < 0.12;

    const pt: GranularPoint = {
      id: `fg-${i}`,
      x,
      y,
      r,
      opacity,
      isAmber,
    };

    if (isAmber) {
      fgAmberPoints.push(pt);
    } else {
      fgPoints.push(pt);
    }
  }

  // -------------------------------------------------------------
  // 4. ABSTRACT AGENT SILHOUETTE: AGENT A (Initiator, Left)
  // -------------------------------------------------------------
  // Centered at X ~ 360, Y ~ 190, reaching right hand toward center
  const agentLeftPoints: GranularPoint[] = [];
  const agentLeftCenter = { x: width * 0.3, y: height * 0.52 };

  // 4.1 Head & Cranium (~85 points)
  for (let i = 0; i < Math.round(85 * densityScale); i++) {
    const angle = rand() * Math.PI * 2;
    const radDist = Math.sqrt(rand());
    const hx = agentLeftCenter.x + Math.cos(angle) * radDist * 17 + 4; // slight right tilt
    const hy = (agentLeftCenter.y - 74) + Math.sin(angle) * radDist * 22;
    agentLeftPoints.push({
      id: `agA-h-${i}`,
      x: Math.round(hx * 10) / 10,
      y: Math.round(hy * 10) / 10,
      r: Math.round((0.85 + rand() * 0.95) * 100) / 100,
      opacity: Math.round((0.45 + rand() * 0.5) * 100) / 100,
    });
  }

  // 4.2 Neck & Shoulders (~110 points)
  for (let i = 0; i < Math.round(110 * densityScale); i++) {
    const spreadX = (rand() - 0.5) * 76;
    const sy = (agentLeftCenter.y - 38) + (rand() - 0.5) * 20 + Math.abs(spreadX) * 0.12;
    agentLeftPoints.push({
      id: `agA-sh-${i}`,
      x: Math.round((agentLeftCenter.x + spreadX) * 10) / 10,
      y: Math.round(sy * 10) / 10,
      r: Math.round((0.95 + rand() * 1.05) * 100) / 100,
      opacity: Math.round((0.4 + rand() * 0.55) * 100) / 100,
    });
  }

  // 4.3 Torso & Grounded Stance (~160 points)
  for (let i = 0; i < Math.round(160 * densityScale); i++) {
    const tY = (agentLeftCenter.y - 20) + rand() * 95;
    const progress = (tY - (agentLeftCenter.y - 20)) / 95; // 0 at chest, 1 at hips/feet
    const widthAtY = progress < 0.6 ? 54 * (1 - progress * 0.3) : 42 + (progress - 0.6) * 38;
    const tX = agentLeftCenter.x + (rand() - 0.5) * widthAtY;
    agentLeftPoints.push({
      id: `agA-torso-${i}`,
      x: Math.round(tX * 10) / 10,
      y: Math.round(tY * 10) / 10,
      r: Math.round((0.85 + rand() * 1.1) * 100) / 100,
      opacity: Math.round((0.35 + rand() * 0.5) * 100) / 100,
    });
  }

  // 4.4 Extended Reaching Right Arm & Hand (~85 points)
  for (let i = 0; i < Math.round(85 * densityScale); i++) {
    const t = rand(); // 0 at shoulder, 1 at fingertips
    const armX = agentLeftCenter.x + 28 + t * 95 + (rand() - 0.5) * 12;
    const armY = (agentLeftCenter.y - 28) + t * 14 + (rand() - 0.5) * 12;
    agentLeftPoints.push({
      id: `agA-arm-${i}`,
      x: Math.round(armX * 10) / 10,
      y: Math.round(armY * 10) / 10,
      r: Math.round((0.9 + rand() * 1.1) * 100) / 100,
      opacity: Math.round((0.5 + rand() * 0.45) * 100) / 100,
    });
  }

  // -------------------------------------------------------------
  // 5. ABSTRACT AGENT SILHOUETTE: AGENT B (Receptor, Right)
  // -------------------------------------------------------------
  // Centered at X ~ 840, Y ~ 190, facing left with receptive arm
  const agentRightPoints: GranularPoint[] = [];
  const agentRightCenter = { x: width * 0.7, y: height * 0.52 };

  // 5.1 Head & Cranium (~85 points)
  for (let i = 0; i < Math.round(85 * densityScale); i++) {
    const angle = rand() * Math.PI * 2;
    const radDist = Math.sqrt(rand());
    const hx = agentRightCenter.x + Math.cos(angle) * radDist * 17 - 4; // slight left tilt
    const hy = (agentRightCenter.y - 74) + Math.sin(angle) * radDist * 22;
    agentRightPoints.push({
      id: `agB-h-${i}`,
      x: Math.round(hx * 10) / 10,
      y: Math.round(hy * 10) / 10,
      r: Math.round((0.85 + rand() * 0.95) * 100) / 100,
      opacity: Math.round((0.45 + rand() * 0.5) * 100) / 100,
    });
  }

  // 5.2 Neck & Shoulders (~110 points)
  for (let i = 0; i < Math.round(110 * densityScale); i++) {
    const spreadX = (rand() - 0.5) * 76;
    const sy = (agentRightCenter.y - 38) + (rand() - 0.5) * 20 + Math.abs(spreadX) * 0.12;
    agentRightPoints.push({
      id: `agB-sh-${i}`,
      x: Math.round((agentRightCenter.x + spreadX) * 10) / 10,
      y: Math.round(sy * 10) / 10,
      r: Math.round((0.95 + rand() * 1.05) * 100) / 100,
      opacity: Math.round((0.4 + rand() * 0.55) * 100) / 100,
    });
  }

  // 5.3 Torso & Grounded Stance (~160 points)
  for (let i = 0; i < Math.round(160 * densityScale); i++) {
    const tY = (agentRightCenter.y - 20) + rand() * 95;
    const progress = (tY - (agentRightCenter.y - 20)) / 95;
    const widthAtY = progress < 0.6 ? 54 * (1 - progress * 0.3) : 42 + (progress - 0.6) * 38;
    const tX = agentRightCenter.x + (rand() - 0.5) * widthAtY;
    agentRightPoints.push({
      id: `agB-torso-${i}`,
      x: Math.round(tX * 10) / 10,
      y: Math.round(tY * 10) / 10,
      r: Math.round((0.85 + rand() * 1.1) * 100) / 100,
      opacity: Math.round((0.35 + rand() * 0.5) * 100) / 100,
    });
  }

  // 5.4 Receptive Left Arm & Hand (~85 points)
  for (let i = 0; i < Math.round(85 * densityScale); i++) {
    const t = rand();
    const armX = agentRightCenter.x - 28 - t * 95 + (rand() - 0.5) * 12;
    const armY = (agentRightCenter.y - 28) + t * 14 + (rand() - 0.5) * 12;
    agentRightPoints.push({
      id: `agB-arm-${i}`,
      x: Math.round(armX * 10) / 10,
      y: Math.round(armY * 10) / 10,
      r: Math.round((0.9 + rand() * 1.1) * 100) / 100,
      opacity: Math.round((0.5 + rand() * 0.45) * 100) / 100,
    });
  }

  // -------------------------------------------------------------
  // 6. CAUSAL TRANSFERENCE STREAM & CONVERGENCE LOCUS
  // -------------------------------------------------------------
  // Connects hand A (x ~ agentLeftCenter.x + 120) to hand B (x ~ agentRightCenter.x - 120)
  const causalPoints: GranularPoint[] = [];
  const causalAmberPoints: GranularPoint[] = [];
  const startHand = { x: agentLeftCenter.x + 118, y: agentLeftCenter.y - 14 };
  const endHand = { x: agentRightCenter.x - 118, y: agentRightCenter.y - 14 };
  const midLocus = { x: width * 0.5, y: agentLeftCenter.y - 28 };

  const streamCount = Math.round(180 * densityScale);
  for (let i = 0; i < streamCount; i++) {
    const t = i / (streamCount - 1);
    // Cubic bezier trajectory
    const p0x = startHand.x;
    const p0y = startHand.y;
    const p1x = midLocus.x - 60;
    const p1y = midLocus.y;
    const p2x = midLocus.x + 60;
    const p2y = midLocus.y;
    const p3x = endHand.x;
    const p3y = endHand.y;

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

    const jitterX = (rand() - 0.5) * 16;
    const jitterY = (rand() - 0.5) * 14;
    const isAmber = rand() < 0.28;

    const pt: GranularPoint = {
      id: `causal-${i}`,
      x: Math.round((bx + jitterX) * 10) / 10,
      y: Math.round((by + jitterY) * 10) / 10,
      r: Math.round((0.95 + rand() * 1.3) * 100) / 100,
      opacity: Math.round((0.45 + rand() * 0.5) * 100) / 100,
      isAmber,
    };

    if (isAmber) {
      causalAmberPoints.push(pt);
    } else {
      causalPoints.push(pt);
    }
  }

  // 6.2 Causal roots descending into the narrative terrain (~60 points)
  for (let i = 0; i < Math.round(60 * densityScale); i++) {
    const t = rand();
    const rootX = midLocus.x + (rand() - 0.5) * 50 * (1 + t);
    const rootY = midLocus.y + 12 + t * 95;
    const isAmber = rand() < 0.35;
    const pt: GranularPoint = {
      id: `causal-root-${i}`,
      x: Math.round(rootX * 10) / 10,
      y: Math.round(rootY * 10) / 10,
      r: Math.round((0.85 + rand() * 1.0) * 100) / 100,
      opacity: Math.round((0.35 + rand() * 0.45) * 100) / 100,
      isAmber,
    };
    if (isAmber) {
      causalAmberPoints.push(pt);
    } else {
      causalPoints.push(pt);
    }
  }

  // -------------------------------------------------------------
  // Precompute Batched Path 'd' Strings
  // -------------------------------------------------------------
  const bgPathD = pointsToSvgPath(bgPoints);
  const midPathD = pointsToSvgPath(midPoints);
  const fgPathD = pointsToSvgPath(fgPoints);
  const fgAmberPathD = pointsToSvgPath(fgAmberPoints);
  const agentLeftPathD = pointsToSvgPath(agentLeftPoints);
  const agentRightPathD = pointsToSvgPath(agentRightPoints);
  const causalPathD = pointsToSvgPath(causalPoints);
  const causalAmberPathD = pointsToSvgPath(causalAmberPoints);

  const totalPoints =
    bgPoints.length +
    midPoints.length +
    fgPoints.length +
    fgAmberPoints.length +
    agentLeftPoints.length +
    agentRightPoints.length +
    causalPoints.length +
    causalAmberPoints.length;

  return {
    bgPoints,
    bgPathD,
    midPoints,
    midPathD,
    fgPoints,
    fgPathD,
    fgAmberPoints,
    fgAmberPathD,
    agentLeftPoints,
    agentLeftPathD,
    agentRightPoints,
    agentRightPathD,
    causalPoints,
    causalPathD,
    causalAmberPoints,
    causalAmberPathD,
    totalPoints,
  };
}
