import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  usePrefersReducedMotion,
  drawerBackdropVariants,
  drawerPanelVariants,
} from '../../hooks/usePrefersReducedMotion';

export interface InspectorDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  width?: string;
  className?: string;
}

/**
 * Editorial Inspector Drawer (§9)
 * - Backdrop: low-opacity overlay fade
 * - Drawer: translateX(32px) -> 0, opacity 0 -> 1 (260ms), exit (180ms)
 * - Focus preservation and Escape key dismiss
 */
export const InspectorDrawer: React.FC<InspectorDrawerProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  width = '420px',
  className = '',
}) => {
  const prefersReduced = usePrefersReducedMotion();
  const drawerRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedElementRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    previouslyFocusedElementRef.current = document.activeElement as HTMLElement | null;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      previouslyFocusedElementRef.current?.focus?.();
    };
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="primitive-drawer-root" role="dialog" aria-modal="true" aria-label={title}>
          {/* Backdrop (Low-opacity overlay) */}
          <motion.div
            className="drawer-backdrop"
            onClick={onClose}
            custom={prefersReduced}
            variants={drawerBackdropVariants}
            initial="initial"
            animate="animate"
            exit="exit"
          />

          {/* Drawer Content: translateX(32px) -> 0, opacity 0 -> 1 */}
          <motion.aside
            ref={drawerRef}
            className={`primitive-inspector-drawer ${className}`}
            style={{ width }}
            custom={prefersReduced}
            variants={drawerPanelVariants}
            initial="initial"
            animate="animate"
            exit="exit"
          >
            <header className="drawer-header">
              <div className="drawer-titles">
                <h3 className="drawer-title">{title}</h3>
                {subtitle && <p className="drawer-subtitle">{subtitle}</p>}
              </div>
              <button
                type="button"
                className="drawer-close-btn"
                onClick={onClose}
                aria-label="Close Inspector Drawer"
              >
                ✕
              </button>
            </header>
            <div className="drawer-body">{children}</div>
          </motion.aside>
        </div>
      )}
    </AnimatePresence>
  );
};
