/**
 * pointGenerators3D.ts
 *
 * Deterministic mathematical 3D point-cloud generation for D3 Story Lab's Iris Ring (Phase 9.2.7).
 *
 * Layers:
 * 1. Core Dense Iris Ring (~55%): High-density glowing rim centered behind text.
 * 2. Coronal Strands & Radial Filaments (~25%): Radiating stroma fibers and coronal loops.
 * 3. Inward Horizon Tendrils (~10%): Filaments reaching into the central void.
 * 4. Volatile Luminous Embers (~10%): High-energy amber particles flaring under turbulence.
 */

import { mulberry32 } from '../prng';

export interface PointCloudBuffers {
  positions: Float32Array;      // Initial rest position (vec3)
  targets: Float32Array;        // Target morph position (vec3)
  colors: Float32Array;         // Color (vec3)
  sizes: Float32Array;          // Size (float)
  phases: Float32Array;         // Wave phase offset (float)
  layerIds: Float32Array;       // Layer ID (0=core, 1=filaments, 2=tendrils, 3=embers) (float)
  pointCount: number;
}

export function generate3DPointCloud(totalPoints: number, seed = 927): PointCloudBuffers {
  const prng = mulberry32(seed);

  const count = Math.max(1000, totalPoints);
  const coreCount = Math.floor(count * 0.55);
  const filamentCount = Math.floor(count * 0.25);
  const tendrilCount = Math.floor(count * 0.10);
  const emberCount = count - coreCount - filamentCount - tendrilCount;

  const positions = new Float32Array(count * 3);
  const targets = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  const phases = new Float32Array(count);
  const layerIds = new Float32Array(count);

  let ptr = 0;

  // Colors based on D3 Story Lab Neo-Noir Design Tokens:
  // --text-primary: #F5F3EF -> [0.961, 0.953, 0.937]
  // --text-muted: #B5AEA3 -> [0.710, 0.682, 0.640]
  // --accent: #C9A46B -> [0.788, 0.643, 0.420]
  const colPrimary = [0.961, 0.953, 0.937];
  const colMuted = [0.710, 0.682, 0.640];
  const colAccent = [0.788, 0.643, 0.420];

  // =========================================================================
  // 1. CORE DENSE IRIS RING (Layer 0, ~55%)
  // Tightly clustered circular ring forming the glowing iris rim
  // =========================================================================
  for (let i = 0; i < coreCount; i++) {
    const angle = prng() * Math.PI * 2;
    // Radial distribution peaking around radius 3.5
    const r = 3.2 + (prng() + prng() - 1.0) * 0.75;
    const x = Math.cos(angle) * r;
    const y = Math.sin(angle) * r;
    const z = (prng() - 0.5) * 0.35;

    positions[ptr * 3] = x;
    positions[ptr * 3 + 1] = y;
    positions[ptr * 3 + 2] = z;

    // Target position with slight azimuthal swirl
    const targetAngle = angle + 0.14;
    const targetR = r * 1.04;
    targets[ptr * 3] = Math.cos(targetAngle) * targetR;
    targets[ptr * 3 + 1] = Math.sin(targetAngle) * targetR;
    targets[ptr * 3 + 2] = z * 1.2;

    const isGold = prng() < 0.08;
    const col = isGold ? colAccent : (prng() < 0.75 ? colPrimary : colMuted);
    colors[ptr * 3] = col[0];
    colors[ptr * 3 + 1] = col[1];
    colors[ptr * 3 + 2] = col[2];

    sizes[ptr] = 1.3 + prng() * 1.5;
    phases[ptr] = prng() * Math.PI * 2;
    layerIds[ptr] = 0.0;
    ptr++;
  }

  // =========================================================================
  // 2. CORONAL STRANDS & RADIAL FILAMENTS (Layer 1, ~25%)
  // Radiating outward from 3.6 to 6.0 like solar corona / iris fibers
  // =========================================================================
  for (let i = 0; i < filamentCount; i++) {
    const angle = prng() * Math.PI * 2;
    const r = 3.6 + Math.pow(prng(), 1.4) * 2.2;
    const x = Math.cos(angle) * r;
    const y = Math.sin(angle) * r;
    const z = (prng() - 0.5) * 0.65;

    positions[ptr * 3] = x;
    positions[ptr * 3 + 1] = y;
    positions[ptr * 3 + 2] = z;

    const targetAngle = angle + (prng() - 0.5) * 0.35;
    const targetR = r * 1.15;
    targets[ptr * 3] = Math.cos(targetAngle) * targetR;
    targets[ptr * 3 + 1] = Math.sin(targetAngle) * targetR;
    targets[ptr * 3 + 2] = z * 1.4;

    const isGold = prng() < 0.14;
    const col = isGold ? colAccent : (prng() < 0.60 ? colPrimary : colMuted);
    colors[ptr * 3] = col[0];
    colors[ptr * 3 + 1] = col[1];
    colors[ptr * 3 + 2] = col[2];

    sizes[ptr] = 1.0 + prng() * 1.4;
    phases[ptr] = prng() * Math.PI * 2;
    layerIds[ptr] = 1.0;
    ptr++;
  }

  // =========================================================================
  // 3. INWARD HORIZON TENDRILS (Layer 2, ~10%)
  // Reaching inward from 1.0 to 3.0 toward the dark central void
  // =========================================================================
  for (let i = 0; i < tendrilCount; i++) {
    const angle = prng() * Math.PI * 2;
    const r = 1.0 + Math.pow(prng(), 1.2) * 2.2;
    const x = Math.cos(angle) * r;
    const y = Math.sin(angle) * r;
    const z = (prng() - 0.5) * 0.45;

    positions[ptr * 3] = x;
    positions[ptr * 3 + 1] = y;
    positions[ptr * 3 + 2] = z;

    const targetAngle = angle + 0.25;
    const targetR = r * 0.85;
    targets[ptr * 3] = Math.cos(targetAngle) * targetR;
    targets[ptr * 3 + 1] = Math.sin(targetAngle) * targetR;
    targets[ptr * 3 + 2] = z * 0.9;

    const isGold = prng() < 0.12;
    const col = isGold ? colAccent : (prng() < 0.50 ? colPrimary : colMuted);
    colors[ptr * 3] = col[0];
    colors[ptr * 3 + 1] = col[1];
    colors[ptr * 3 + 2] = col[2];

    sizes[ptr] = 0.9 + prng() * 1.2;
    phases[ptr] = prng() * Math.PI * 2;
    layerIds[ptr] = 2.0;
    ptr++;
  }

  // =========================================================================
  // 4. VOLATILE EMBERS & NARRATIVE ENERGY (Layer 3, ~10%)
  // Wide radial dispersion with high amber concentration
  // =========================================================================
  for (let i = 0; i < emberCount; i++) {
    const angle = prng() * Math.PI * 2;
    const r = 2.4 + prng() * 4.6;
    const x = Math.cos(angle) * r;
    const y = Math.sin(angle) * r;
    const z = (prng() - 0.5) * 0.95;

    positions[ptr * 3] = x;
    positions[ptr * 3 + 1] = y;
    positions[ptr * 3 + 2] = z;

    const targetAngle = angle + (prng() - 0.5) * 0.6;
    const targetR = r * (1.1 + prng() * 0.25);
    targets[ptr * 3] = Math.cos(targetAngle) * targetR;
    targets[ptr * 3 + 1] = Math.sin(targetAngle) * targetR;
    targets[ptr * 3 + 2] = z * 1.5;

    // High amber proportion for dramatic energy flashes
    const isGold = prng() < 0.45;
    const col = isGold ? colAccent : colPrimary;
    colors[ptr * 3] = col[0];
    colors[ptr * 3 + 1] = col[1];
    colors[ptr * 3 + 2] = col[2];

    sizes[ptr] = 1.8 + prng() * 1.8;
    phases[ptr] = prng() * Math.PI * 2;
    layerIds[ptr] = 3.0;
    ptr++;
  }

  return {
    positions,
    targets,
    colors,
    sizes,
    phases,
    layerIds,
    pointCount: count,
  };
}
