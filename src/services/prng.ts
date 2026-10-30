/**
 * D3 Story Lab — Deterministic Pseudo-Random Number Generator (PRNG)
 *
 * Implements the Mulberry32 deterministic generator with independent subsystem
 * streams. Guarantees bit-exact reproducibility across runs with identical seeds.
 */

export class Mulberry32 {
  private state: number;

  constructor(seed: number | string) {
    this.state = typeof seed === 'string' ? Mulberry32.hashString(seed) : seed >>> 0;
  }

  /**
   * Hashes an arbitrary string into a 32-bit unsigned integer using FNV-1a.
   */
  public static hashString(str: string): number {
    let hash = 2166136261;
    for (let i = 0; i < str.length; i++) {
      hash ^= str.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  /**
   * Returns a deterministic pseudo-random float in [0, 1).
   */
  public nextFloat(): number {
    let t = (this.state += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  /**
   * Returns a deterministic integer in [min, max] inclusive.
   */
  public nextInt(min: number, max: number): number {
    return Math.floor(this.nextFloat() * (max - min + 1)) + min;
  }

  /**
   * Picks a random element from an array.
   */
  public pick<T>(arr: T[]): T {
    if (arr.length === 0) throw new Error('Cannot pick from empty array');
    return arr[this.nextInt(0, arr.length - 1)];
  }

  /**
   * Shuffles an array deterministically in place.
   */
  public shuffle<T>(arr: T[]): T[] {
    const copy = [...arr];
    for (let i = copy.length - 1; i > 0; i--) {
      const j = this.nextInt(0, i);
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  /**
   * Exports the internal state for snapshotting/checkpointing.
   */
  public getState(): number {
    return this.state;
  }

  /**
   * Restores internal state.
   */
  public setState(state: number) {
    this.state = state >>> 0;
  }
}

/**
 * Subsystem PRNG Streams derived from a single root master seed.
 * Guarantees that actions in one subsystem do not displace random sequences in another.
 */
export interface SimulationPrngStreams {
  masterSeed: number;
  worldGen: Mulberry32;
  characterInit: Mulberry32;
  decisionPolicy: Mulberry32;
  director: Mulberry32;
}

export function createSimulationStreams(seed: number | string): SimulationPrngStreams {
  const masterSeed = typeof seed === 'string' ? Mulberry32.hashString(seed) : seed >>> 0;
  return {
    masterSeed,
    worldGen: new Mulberry32(masterSeed ^ 0x1a2b3c4d),
    characterInit: new Mulberry32(masterSeed ^ 0x5e6f7a8b),
    decisionPolicy: new Mulberry32(masterSeed ^ 0x9c0d1e2f),
    director: new Mulberry32(masterSeed ^ 0x3b4a5968),
  };
}
