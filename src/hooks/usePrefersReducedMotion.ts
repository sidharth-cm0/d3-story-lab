import { useState, useEffect } from 'react';
import {
  MOTION_TIMING,
  MOTION_EASING,
  getMotionTransition,
} from '../tokens/motion';

export * from '../tokens/motion';

/**
 * Backward-compatible aliases for Phase 9.1 consumers
 */
export const MOTION_EASE = {
  editorialOut: MOTION_EASING.easeOut,
  editorialInOut: MOTION_EASING.easeInOut,
};

export const MOTION_DURATION = {
  fast: MOTION_TIMING.fast,
  normal: MOTION_TIMING.normal,
  slow: MOTION_TIMING.slow,
};

/**
 * Hook to detect and respond to the user's OS or browser reduced-motion preference.
 * Defaults to false if window.matchMedia is not available (e.g. in test or SSR).
 */
export function usePrefersReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return false;
    }
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }

    const mediaQueryList = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotionPreference = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };

    // Set initial value
    setPrefersReducedMotion(mediaQueryList.matches);

    // Modern browsers use addEventListener; fallback to addListener for older runtimes
    if (mediaQueryList.addEventListener) {
      mediaQueryList.addEventListener('change', updateMotionPreference);
      return () => mediaQueryList.removeEventListener('change', updateMotionPreference);
    } else if ((mediaQueryList as any).addListener) {
      (mediaQueryList as any).addListener(updateMotionPreference);
      return () => (mediaQueryList as any).removeListener(updateMotionPreference);
    }
  }, []);

  return prefersReducedMotion;
}

export { getMotionTransition };
