/**
 * qualityTiers.ts
 *
 * Adaptive GPU quality tiers and point count budgeting (Phase 9.2.7 §20).
 * Dynamically scales particle density and caps DPR to ensure 60fps on integrated GPUs.
 */

export type QualityTier = 'HIGH' | 'MEDIUM' | 'LOW' | 'FALLBACK';

export interface QualityBudget {
  tier: QualityTier;
  pointCount: number;
  dpr: number;
  enableMorph: boolean;
  enableDisplacement: boolean;
}

export function getPointCountForTier(tier: QualityTier): number {
  switch (tier) {
    case 'HIGH':
      return 52000; // Reference density for powerful desktop
    case 'MEDIUM':
      return 26000; // Balanced density for laptops / ultrabooks
    case 'LOW':
      return 8500;  // Lightweight density for tablets / low-power devices
    case 'FALLBACK':
      return 0;     // SVG / CSS static fallback
  }
}

export function detectQualityTier(options?: {
  prefersReducedMotion?: boolean;
  forceTier?: QualityTier;
}): QualityTier {
  if (options?.forceTier) {
    return options.forceTier;
  }

  if (typeof window === 'undefined') {
    return 'FALLBACK';
  }

  // Reduced motion preference triggers static fallback
  if (
    options?.prefersReducedMotion ||
    window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
  ) {
    return 'FALLBACK';
  }

  const width = window.innerWidth || 1200;
  const isMobile = width < 640;
  const isTablet = width >= 640 && width < 1024;
  const isLaptop = width >= 1024 && width < 1440;

  // Mobile viewports default to LOW or FALLBACK for battery & memory efficiency
  if (isMobile) {
    return 'LOW';
  }

  if (isTablet) {
    return 'LOW';
  }

  // Device memory and hardware concurrency checks when available
  const nav = typeof navigator !== 'undefined' ? (navigator as any) : null;
  const hardwareConcurrency = nav?.hardwareConcurrency || 4;
  const deviceMemory = nav?.deviceMemory || 4;

  if (hardwareConcurrency <= 2 || deviceMemory < 4) {
    return 'LOW';
  }

  if (isLaptop || hardwareConcurrency <= 4) {
    return 'MEDIUM';
  }

  return 'HIGH';
}

export function getQualityBudget(tier: QualityTier): QualityBudget {
  const baseDpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;
  const cappedDpr = Math.min(baseDpr, 1.5); // Cap DPR at 1.5 (§20)

  return {
    tier,
    pointCount: getPointCountForTier(tier),
    dpr: cappedDpr,
    enableMorph: tier === 'HIGH' || tier === 'MEDIUM',
    enableDisplacement: tier !== 'FALLBACK',
  };
}
