/**
 * AgentPointCloud.ts
 *
 * Abstract humanoid agent point-cloud generator for D3 Story Lab:
 * - Represents autonomous simulated agents (Actors)
 * - Anonymous, particulate, no facial detail, recognizable humanoid silhouettes
 * - Agent A (Initiator, left): Extended arm dispersing narrative particle stream
 * - Agent B (Receptor, right): Attentive posture receiving causal transference
 */

import { mulberry32 } from '../granular/prng';

export interface AgentPointData {
  positions: Float32Array;
  targets: Float32Array;
  colors: Float32Array;
  sizes: Float32Array;
  phases: Float32Array;
  layerIds: Float32Array;
}

export function generateAgentPoints(count: number, seed: number = 928): AgentPointData {
  const rng = mulberry32(seed);

  const positions = new Float32Array(count * 3);
  const targets = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  const phases = new Float32Array(count);
  const layerIds = new Float32Array(count);

  const halfCount = Math.floor(count / 2);

  for (let i = 0; i < count; i++) {
    const i3 = i * 3;
    const isAgentA = i < halfCount;

    // Center positions for agents
    const centerX = isAgentA ? -6.2 : 6.2;
    const centerZ = isAgentA ? -0.5 : 0.5;

    // Body part distribution: Head (15%), Torso (40%), Limbs (45%)
    const partRoll = rng();
    let lx = 0, ly = 0, lz = 0;

    if (partRoll < 0.15) {
      // Head (ellipsoid at top)
      const theta = rng() * Math.PI * 2;
      const phi = rng() * Math.PI;
      const r = 0.32 * Math.cbrt(rng());
      lx = r * Math.sin(phi) * Math.cos(theta);
      ly = 2.4 + r * Math.cos(phi) * 1.15;
      lz = r * Math.sin(phi) * Math.sin(theta);
    } else if (partRoll < 0.55) {
      // Torso & Shoulders (tapered column)
      const tY = rng(); // 0 (waist) to 1 (shoulders)
      const shoulderWidth = 0.65 - tY * 0.15;
      const uW = (rng() - 0.5) * shoulderWidth * 2;
      const uD = (rng() - 0.5) * 0.32;
      lx = uW;
      ly = 1.0 + tY * 1.25;
      lz = uD;
    } else if (partRoll < 0.80) {
      // Arms
      const armSide = rng() > 0.5 ? 1 : -1;
      const armProgress = rng(); // shoulder down

      if (isAgentA && armSide > 0) {
        // Agent A right arm: extended outward toward Agent B (causal initiator)
        lx = 0.6 + armProgress * 1.35;
        ly = 2.05 - armProgress * 0.45;
        lz = (rng() - 0.5) * 0.25;
      } else if (!isAgentA && armSide < 0) {
        // Agent B left arm: raised receptive posture
        lx = -0.6 - armProgress * 0.95;
        ly = 1.95 + armProgress * 0.25;
        lz = (rng() - 0.5) * 0.25;
      } else {
        // Relaxed resting arm
        lx = armSide * (0.65 + armProgress * 0.15);
        ly = 2.05 - armProgress * 1.0;
        lz = (rng() - 0.5) * 0.22;
      }
    } else {
      // Legs / Base dissolving into the narrative terrain
      const legSide = rng() > 0.5 ? 0.28 : -0.28;
      const legProgress = rng(); // waist down to ground
      lx = legSide + (rng() - 0.5) * 0.25;
      ly = 1.0 - legProgress * 1.4; // descends toward ground
      lz = (rng() - 0.5) * 0.3;
    }

    // Add organic particulate jitter
    const jitter = 0.08;
    lx += (rng() - 0.5) * jitter;
    ly += (rng() - 0.5) * jitter;
    lz += (rng() - 0.5) * jitter;

    // Dispersed starting position (emerges from deep terrain)
    positions[i3] = centerX + (rng() - 0.5) * 5.0;
    positions[i3 + 1] = -1.8 + (rng() - 0.5) * 1.5;
    positions[i3 + 2] = centerZ + (rng() - 0.5) * 4.0;

    // Target coherent silhouette position
    targets[i3] = centerX + lx;
    targets[i3 + 1] = ly;
    targets[i3 + 2] = centerZ + lz;

    // Palette: Crisp high-density warm off-white (#FAF9F6)
    const brightness = 0.85 + rng() * 0.15;
    colors[i3] = brightness;
    colors[i3 + 1] = brightness * 0.98;
    colors[i3 + 2] = brightness * 0.95;

    sizes[i] = 0.9 + rng() * 0.85;
    phases[i] = rng() * Math.PI * 2;
    layerIds[i] = 2.0; // Agent Layer ID
  }

  return { positions, targets, colors, sizes, phases, layerIds };
}
