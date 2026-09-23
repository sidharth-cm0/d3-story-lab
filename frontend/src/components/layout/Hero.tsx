/**
 * Hero.tsx
 *
 * Cinematic Editorial Hero Component for D3 Story Lab:
 * - High-contrast typography in Barlow Condensed & Archivo
 * - Staged entry sequence (0.00s–1.40s) using Framer Motion
 * - Interactive CTA buttons with hover coupling to the granular background
 * - Technical metadata strip with engine invariants and active dossier status
 * - Fully accessible semantic DOM (h1, buttons, aria labels)
 * - Zero interaction blocking during animations
 */

import React from 'react';
import { motion, Transition } from 'framer-motion';
import { ProjectMetadata } from '../../types';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';

export interface HeroProps {
  onStartNew: () => void;
  onOpenProject?: (id: string) => void;
  projects?: ProjectMetadata[];
  onCtaHoverChange?: (hovered: boolean) => void;
}

export const Hero: React.FC<HeroProps> = ({
  onStartNew,
  onOpenProject,
  projects = [],
  onCtaHoverChange,
}) => {
  const prefersReduced = usePrefersReducedMotion();

  // Animation timeline configuration adhering to Section 9:
  // 0.25s eyebrow -> 0.35s heading -> 0.45s statement -> 0.85s CTAs -> 1.00s metadata
  const t = (delay: number): Transition =>
    prefersReduced
      ? { duration: 0 }
      : { duration: 0.55, delay, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] };

  const activeProject = projects.length > 0 ? projects[0] : null;

  return (
    <section className="scrolly-section hero-section" aria-label="D3 Story Lab Hero">
      <div className="hero-central-composition">
        {/* Eyebrow: 0.25s */}
        <motion.div
          className="hero-eyebrow"
          initial={prefersReduced ? {} : { opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={t(0.25)}
        >
          <span className="eyebrow-glyph" aria-hidden="true">❖</span>
          <span className="hero-kicker">AGENTIC PROCEDURAL NARRATIVE ENGINE</span>
        </motion.div>

        {/* Large Editorial Title: 0.35s */}
        <motion.h1
          className="hero-editorial-title"
          initial={prefersReduced ? {} : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={t(0.35)}
        >
          D3 STORY LAB
        </motion.h1>

        {/* Main Statement: 0.45s */}
        <motion.div
          className="hero-statement-container"
          initial={prefersReduced ? {} : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={t(0.45)}
        >
          <div className="statement-line statement-receding">
            THE STORY IS NOT WRITTEN.
          </div>
          <div className="statement-line statement-emerging text-amber">
            IT EMERGES.
          </div>
        </motion.div>

        {/* Supporting Copy */}
        <motion.p
          className="hero-prose"
          initial={prefersReduced ? {} : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={t(0.65)}
        >
          Autonomous characters make decisions inside a deterministic world.
          Narrative arcs, subtext, causality, screenplay, and storyboard emerge from simulation.
        </motion.p>

        {/* Action Buttons: 0.85s */}
        <motion.div
          className="hero-actions"
          initial={prefersReduced ? {} : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={t(0.85)}
        >
          <button
            type="button"
            className="btn-pill-primary btn-cinematic-primary"
            onClick={onStartNew}
            onMouseEnter={() => onCtaHoverChange?.(true)}
            onMouseLeave={() => onCtaHoverChange?.(false)}
          >
            <span>NEW SIMULATION</span>
            <span className="btn-arrow" aria-hidden="true">→</span>
          </button>

          {activeProject && onOpenProject && (
            <button
              type="button"
              className="btn-pill-secondary btn-cinematic-secondary"
              onClick={() => onOpenProject(activeProject.id)}
              onMouseEnter={() => onCtaHoverChange?.(true)}
              onMouseLeave={() => onCtaHoverChange?.(false)}
            >
              <span>OPEN PROJECT ({activeProject.title})</span>
            </button>
          )}
        </motion.div>

        {/* Breathing gap separating CTAs from the metadata strip */}
        <div className="hero-breathing-gap" aria-hidden="true" />

        {/* Technical Metadata Strip: 1.00s */}
        <motion.div
          className="hero-metadata-strip"
          aria-label="System status strip"
          initial={prefersReduced ? {} : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={t(1.0)}
        >
          <div className="metadata-strip-item">
            <span className="strip-label">ENGINE</span>
            <strong className="strip-val">DETERMINISTIC HYBRID</strong>
          </div>
          <span className="strip-sep" aria-hidden="true">/</span>
          <div className="metadata-strip-item">
            <span className="strip-label">EXECUTION</span>
            <strong className="strip-val">LOCAL ZERO-AI FALLBACK</strong>
          </div>
          <span className="strip-sep" aria-hidden="true">/</span>
          <div className="metadata-strip-item">
            <span className="strip-label">FIREWALL</span>
            <strong className="strip-val">SCENE PROJECTION ONLY</strong>
          </div>
          {activeProject && (
            <>
              <span className="strip-sep" aria-hidden="true">/</span>
              <div className="metadata-strip-item">
                <span className="strip-label">ACTIVE DOSSIER</span>
                <strong className="strip-val text-amber">
                  {activeProject.title.toUpperCase()} (T{activeProject.current_tick})
                </strong>
              </div>
            </>
          )}
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <div className="scroll-indicator" aria-hidden="true">
        <span>SCROLL TO EXPLORE ARCHITECTURE</span>
        <div className="scroll-notch" />
      </div>
    </section>
  );
};
