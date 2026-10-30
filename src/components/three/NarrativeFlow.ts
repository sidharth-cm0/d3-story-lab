/**
 * NarrativeFlow.ts
 *
 * Causal transference streams, story structure nodes, and event clusters:
 * - CAUSALITY: Flowing particle stream bridging Agent A and Agent B
 * - EVENTS: Dense point clusters representing simulation occurrences
 * - STORY STRUCTURE: Pressure ridges and narrative turning points
 * - D3 Amber / Gold highlights on active causal lines
 */

import { mulberry32 } from '../granular/prng';

export interface FlowPointData {
  positions: Float32Array;
  targets: Float32Array;
  colors: Float32Array;
  sizes: Float32Array;
  phases: Float32Array;
  layerIds: Float32Array;
}

export function generateFlowPoints(count: number, seed: number = 929): FlowPointData {
  const rng = mulberry32(seed);

  const positions = new Float32Array(count * 3);
  const targets = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  const phases = new Float32Array(count);
  const layerIds = new Float32Array(count);

  for (let i = 0; i < count; i++) {
    const i3 = i * 3;

    // Parameter t from 0 (Agent A hand, -4.2) to 1 (Agent B reception, +5.2)
    const t = rng();
    const x = -4.2 + t * 9.4;

    // Hyperbolic catenary arc connecting the two agents
    const arcHeight = Math.sin(t * Math.PI) * 1.35;
    const baseY = 1.6 + arcHeight + (rng() - 0.5) * 0.45;
    const baseZ = Math.sin(t * Math.PI * 2.0) * 0.4 + (rng() - 0.5) * 0.35;

    // Dispersed start (particles gathering from the field)
    positions[i3] = x + (rng() - 0.5) * 4.0;
    positions[i3 + 1] = baseY - 1.2 + (rng() - 0.5) * 2.0;
    positions[i3 + 2] = baseZ + (rng() - 0.5) * 3.0;

    // Target stream trajectory
    targets[i3] = x;
    targets[i3 + 1] = baseY;
    targets[i3 + 2] = baseZ;

    // Palette: Causal stream is accented with D3 Amber / Gold (#D4AF37)
    const isAmberCore = rng() > 0.35;
    if (isAmberCore) {
      colors[i3] = 0.83;     // R
      colors[i3 + 1] = 0.68; // G
      colors[i3 + 2] = 0.22; // B
      sizes[i] = 1.4 + rng() * 0.8;
    } else {
      colors[i3] = 0.95;
      colors[i3 + 1] = 0.94;
      colors[i3 + 2] = 0.90;
      sizes[i] = 0.9 + rng() * 0.5;
    }

    phases[i] = t * Math.PI * 4.0 + rng() * 0.5; // Flow phase along arc
    layerIds[i] = 3.0; // Flow & Causal Layer ID
  }

  return { positions, targets, colors, sizes, phases, layerIds };
}
