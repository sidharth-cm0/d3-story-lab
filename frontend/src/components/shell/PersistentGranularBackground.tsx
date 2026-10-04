/**
 * PersistentGranularBackground.tsx
 *
 * Single persistent global Three.js WebGL granular background for D3 Story Lab (Phase 9).
 * Sits at AppShell level behind all 8 workstations and coordinates GPU motif transitions
 * without ever unmounting or restarting across workspace navigation.
 */

import React, { memo } from 'react';
import { ActiveView } from '../../types';
import { GranularThreeCanvas, viewToMotif } from '../granular';

export interface PersistentGranularBackgroundProps {
  activeView: ActiveView;
  isPaused?: boolean;
  isThrottled?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export const PersistentGranularBackground: React.FC<PersistentGranularBackgroundProps> = memo(({
  activeView,
  isPaused = false,
  isThrottled = false,
  className = '',
  style,
}) => {
  const motif = viewToMotif(activeView);
  // Heavy analytics views auto-throttle Three.js rendering to maintain 60fps UI responsiveness
  const shouldThrottle = isThrottled || activeView === 'actors' || activeView === 'arcs';

  return (
    <div
      className={`app-persistent-granular-background ${className}`}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 0,
        overflow: 'hidden',
        ...style,
      }}
      data-testid="persistent-granular-background"
      aria-hidden="true"
      role="presentation"
    >
      <GranularThreeCanvas
        motif={motif}
        width="100%"
        height="100%"
        isPaused={isPaused}
        isThrottled={shouldThrottle}
        throttleFps={30}
        data-testid="persistent-granular-canvas"
      />
    </div>
  );
});

PersistentGranularBackground.displayName = 'PersistentGranularBackground';
