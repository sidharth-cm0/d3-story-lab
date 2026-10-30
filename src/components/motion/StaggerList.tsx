import React from 'react';
import { motion } from 'framer-motion';
import {
  usePrefersReducedMotion,
  staggerContainerVariants,
  staggerItemVariants,
} from '../../hooks/usePrefersReducedMotion';

export interface StaggerListProps {
  children: React.ReactNode;
  className?: string;
  as?: 'div' | 'ul' | 'section';
}

export const StaggerList: React.FC<StaggerListProps> = ({
  children,
  className = '',
  as = 'div',
}) => {
  const prefersReduced = usePrefersReducedMotion();
  const Component = motion[as];

  return (
    <Component
      className={className}
      custom={prefersReduced}
      variants={staggerContainerVariants}
      initial="hidden"
      animate="visible"
    >
      {children}
    </Component>
  );
};

export interface StaggerItemProps {
  children: React.ReactNode;
  className?: string;
  as?: 'div' | 'li' | 'article';
}

export const StaggerItem: React.FC<StaggerItemProps> = ({
  children,
  className = '',
  as = 'div',
}) => {
  const prefersReduced = usePrefersReducedMotion();
  const Component = motion[as];

  return (
    <Component
      className={className}
      custom={prefersReduced}
      variants={staggerItemVariants}
    >
      {children}
    </Component>
  );
};
