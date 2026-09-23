/**
 * useGranularTransition.ts
 *
 * Coordinates DOM transitions (Framer Motion) with Three.js granular motifs (Phase 9 — Persistent Cinematic Shell).
 * Maps all 8 application views to their dedicated Three.js motifs.
 */

import { useState, useCallback } from 'react';
import { GranularMotif } from './GranularThreeScene';
import { ActiveView } from '../../../types';

export function viewToMotif(view: ActiveView): GranularMotif {
  switch (view) {
    case 'home':
      return 'hero';
    case 'world':
      return 'world';
    case 'actors':
      return 'actors';
    case 'arcs':
      return 'arcs';
    case 'simulation':
      return 'simulation';
    case 'script':
      return 'script';
    case 'storyboard':
      return 'storyboard';
    case 'export':
      return 'export';
    default:
      return 'hero';
  }
}

export function useGranularTransition(initialView: ActiveView = 'home') {
  const [activeMotif, setActiveMotif] = useState<GranularMotif>(viewToMotif(initialView));
  const [isTransitioning, setIsTransitioning] = useState<boolean>(false);

  const transitionTo = useCallback((nextView: ActiveView, onHalfway?: () => void) => {
    setIsTransitioning(true);
    // Smooth transition window coordinated with WebGL morph
    setTimeout(() => {
      setActiveMotif(viewToMotif(nextView));
      onHalfway?.();
      setTimeout(() => {
        setIsTransitioning(false);
      }, 180);
    }, 280);
  }, []);

  return {
    activeMotif,
    isTransitioning,
    transitionTo,
  };
}
