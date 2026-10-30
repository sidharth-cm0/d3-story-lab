import React from 'react';
import { motion } from 'framer-motion';
import { usePrefersReducedMotion, maskedHeadingVariants } from '../../hooks/usePrefersReducedMotion';

export interface MaskedHeadingProps {
  children: React.ReactNode;
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'div' | 'span';
  className?: string;
  delay?: number;
}

/**
 * Editorial Masked Heading Entrance (§4)
 *
 * Container:
 * - overflow: hidden
 *
 * Heading:
 * - translateY(100%) -> translateY(0) (360ms easeOut)
 *
 * Reduced Motion:
 * - Immediate appearance without vertical translation
 */
export const MaskedHeading: React.FC<MaskedHeadingProps> = ({
  children,
  as: Component = 'h2',
  className = '',
  delay = 0,
}) => {
  const prefersReduced = usePrefersReducedMotion();

  return (
    <div
      className="masked-heading-mask"
      style={{
        overflow: 'hidden',
        display: 'block',
        lineHeight: 1.15,
      }}
    >
      <motion.div
        custom={prefersReduced}
        variants={maskedHeadingVariants}
        initial="initial"
        animate="animate"
        transition={{ delay }}
      >
        <Component className={className} style={{ margin: 0 }}>
          {children}
        </Component>
      </motion.div>
    </div>
  );
};
