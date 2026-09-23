/**
 * ParticleReveal.tsx
 *
 * Cinematic Particle Reveal Entrance Component for D3 Story Lab (Phase 9.2.5).
 *
 * Characteristics:
 * - When entering: particles begin sparse/blurred, subtly resolve into clarity and settle.
 * - Smooth ease-out deceleration [0.16, 1, 0.3, 1].
 * - Duration: 600–1200ms (default 850ms).
 * - No explosive scattering or jarring displacement.
 * - Accessibility: under prefers-reduced-motion, renders final static state immediately.
 */

import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';

export interface ParticleRevealProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  className?: string;
  style?: React.CSSProperties;
  'data-testid'?: string;
}

export const ParticleReveal: React.FC<ParticleRevealProps> = ({
  children,
  delay = 0.12,
  duration = 0.85,
  className = '',
  style,
  'data-testid': testId = 'particle-reveal',
  ...rest
}) => {
  const prefersReduced = usePrefersReducedMotion();

  if (prefersReduced) {
    return (
      <div
        className={`particle-reveal-container ${className}`}
        style={{
          opacity: 1,
          pointerEvents: 'none',
          ...style,
        }}
        data-testid={testId}
      >
        {children}
      </div>
    );
  }

  return (
    <motion.div
      className={`particle-reveal-container ${className}`}
      initial={{ opacity: 0.08, y: 6, filter: 'blur(1.5px)' }}
      animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      transition={{
        duration,
        ease: [0.16, 1, 0.3, 1],
        delay,
      }}
      style={{
        pointerEvents: 'none',
        ...style,
      }}
      data-testid={testId}
      {...rest}
    >
      {children}
    </motion.div>
  );
};
