/**
 * ParticleTerrain.ts
 *
 * Mathematical coordinate generator for D3 Story Lab's granular landscape:
 * - Continuous undulating wave terrain spanning X in [-22, 22], Z in [-12, 12]
 * - Represents deterministic World State and narrative probability fields
 * - Generates positions, target morph destinations, colors, phases, and sizes
 */

import { mulberry32 } from '../granular/prng';

export interface TerrainPointData {
  positions: Float32Array;
  targets: Float32Array;
  colors: Float32Array;
  sizes: Float32Array;
  phases: Float32Array;
  layerIds: Float32Array;
}

export function generateTerrainPoints(count: number, seed: number = 927): TerrainPointData {
  const rng = mulberry32(seed);

  const positions = new Float32Array(count * 3);
  const targets = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  const phases = new Float32Array(count);
  const layerIds = new Float32Array(count);

  for (let i = 0; i < count; i++) {
    const i3 = i * 3;

    // Distribute across landscape coordinates
    const u = rng();
    const v = rng();
    const x = (u - 0.5) * 44; // -22 to +22
    const z = (v - 0.5) * 24; // -12 to +12

    // Topological height profile: composite harmonic ridges
    const ridge1 = Math.sin(x * 0.18 + 0.4) * Math.cos(z * 0.22) * 1.8;
    const ridge2 = Math.sin(x * 0.42 - z * 0.35) * 0.9;
    const valley = -Math.exp(-(x * x) / 36) * 1.2; // Central forensic inquiry trough
    const baseY = ridge1 + ridge2 + valley - 1.2;

    // Initial dispersed position (before resolve entrance)
    positions[i3] = x + (rng() - 0.5) * 2.5;
    positions[i3 + 1] = baseY + (rng() - 0.5) * 3.0 - 1.5;
    positions[i3 + 2] = z + (rng() - 0.5) * 2.5;

    // Target coherent position (after resolve)
    targets[i3] = x;
    targets[i3 + 1] = baseY;
    targets[i3 + 2] = z;

    // Palette: Warm off-white (#F5F3EF), muted gray (#A8A196), with rare amber highlights on ridge crests
    const isCrest = baseY > 0.4;
    const isAccent = isCrest && rng() > 0.88;

    if (isAccent) {
      // D3 Amber / Gold
      colors[i3] = 0.83;     // R
      colors[i3 + 1] = 0.68; // G
      colors[i3 + 2] = 0.22; // B
      sizes[i] = 1.3 + rng() * 0.6;
    } else {
      // Filmic graphite / warm off-white gradient
      const brightness = 0.62 + rng() * 0.36;
      colors[i3] = brightness * 0.96;
      colors[i3 + 1] = brightness * 0.95;
      colors[i3 + 2] = brightness * 0.93;
      sizes[i] = 0.75 + rng() * 0.7;
    }

    phases[i] = rng() * Math.PI * 2;
    layerIds[i] = 1.0; // Terrain Layer ID
  }

  return { positions, targets, colors, sizes, phases, layerIds };
}
