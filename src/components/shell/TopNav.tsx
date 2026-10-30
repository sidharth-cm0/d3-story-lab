import React from 'react';
import { motion } from 'framer-motion';
import { ActiveView } from '../../types';
import {
  usePrefersReducedMotion,
  getMotionTransition,
  MOTION_TIMING,
  MOTION_EASING,
} from '../../hooks/usePrefersReducedMotion';

export interface TopNavProps {
  activeView: ActiveView;
  onSelectView: (view: ActiveView) => void;
  className?: string;
}

export const NAV_ITEMS: { key: ActiveView; label: string; number: string }[] = [
  { key: 'home', label: 'HOME', number: '01' },
  { key: 'world', label: 'WORLD', number: '02' },
  { key: 'actors', label: 'ACTORS', number: '03' },
  { key: 'arcs', label: 'ARCS & STRUCTURE', number: '04' },
  { key: 'simulation', label: 'SIMULATION', number: '05' },
  { key: 'script', label: 'SCRIPT', number: '06' },
  { key: 'storyboard', label: 'STORYBOARD', number: '07' },
  { key: 'export', label: 'EXPORT', number: '08' },
];

export const TopNav: React.FC<TopNavProps> = ({
  activeView,
  onSelectView,
  className = '',
}) => {
  const prefersReduced = usePrefersReducedMotion();

  return (
    <nav className={`shell-top-nav ${className}`} aria-label="Main Navigation">
      <div className="nav-items-list" role="tablist">
        {NAV_ITEMS.map((item) => {
          const isActive = activeView === item.key;
          return (
            <button
              key={item.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              tabIndex={0}
              className={`nav-tab-btn ${isActive ? 'active' : ''}`}
              onClick={() => onSelectView(item.key)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectView(item.key);
                }
              }}
            >
              <span className="nav-tab-index" aria-hidden="true">{item.number}</span>
              <span className="nav-tab-label">{item.label}</span>
              {isActive && (
                <motion.span
                  layoutId="topNavActiveIndicator"
                  className="nav-tab-indicator"
                  aria-hidden="true"
                  transition={getMotionTransition(
                    prefersReduced,
                    MOTION_TIMING.normal,
                    MOTION_EASING.easeOut
                  )}
                />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
};
