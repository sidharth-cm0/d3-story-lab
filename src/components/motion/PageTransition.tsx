import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePrefersReducedMotion, pageTransitionVariants } from '../../hooks/usePrefersReducedMotion';

export interface PageTransitionProps {
  viewKey: string;
  children: React.ReactNode;
  className?: string;
}

/**
 * Editorial Workspace / Page Cross-Dissolve Transition (§3)
 *
 * Outgoing:
 * - opacity 1 -> 0
 * - translateY 0 -> -4px (160ms)
 *
 * Incoming:
 * - opacity 0 -> 1
 * - translateY 12px -> 0 (240ms)
 *
 * When prefers-reduced-motion is active:
 * - Immediate switch without translation or lag
 */
export const PageTransition: React.FC<PageTransitionProps> = ({
  viewKey,
  children,
  className = 'page-transition-container',
}) => {
  const prefersReduced = usePrefersReducedMotion();

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={viewKey}
        custom={prefersReduced}
        variants={pageTransitionVariants}
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
        }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
};
