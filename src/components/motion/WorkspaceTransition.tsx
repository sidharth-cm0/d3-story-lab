/**
 * WorkspaceTransition.tsx
 *
 * Reusable Foreground Workspace Transition Component (Phase 9 §10).
 * Coordinates smooth cross-fades and vertical editorial reveals between active workspaces.
 *
 * Characteristics:
 * - Outgoing: opacity 1 -> 0, translateY 0 -> -6px (~160ms)
 * - Incoming: opacity 0 -> 1, translateY 10px -> 0 (~260ms)
 * - Reduced-Motion Safe: Instantaneous cut without translation or bounce
 * - Pointer-Events: auto for all foreground controls
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePrefersReducedMotion, workspaceTransitionVariants } from '../../hooks/usePrefersReducedMotion';

export interface WorkspaceTransitionProps {
  viewKey: string;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export const WorkspaceTransition: React.FC<WorkspaceTransitionProps> = ({
  viewKey,
  children,
  className = 'workspace-transition-container',
  style,
}) => {
  const prefersReduced = usePrefersReducedMotion();

  return (
    <AnimatePresence mode="popLayout" initial={false}>
      <motion.div
        key={viewKey}
        custom={prefersReduced}
        variants={workspaceTransitionVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        className={className}
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          pointerEvents: 'auto',
          ...style,
        }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
};
