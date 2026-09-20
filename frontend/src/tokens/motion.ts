import type { Transition, Variants } from 'framer-motion';

/**
 * Global Motion Tokens for D3 Story Lab (Phase 9.2)
 *
 * Timings:
 * - INSTANT: 100–120ms (button press, micro-interactions)
 * - FAST: 150–180ms (tab/panel exit, modal close, drawer close)
 * - NORMAL: 220–280ms (incoming page, card reveals, modal open, drawer open)
 * - SLOW: 320–420ms (masked heading reveals, deliberate editorial entrances)
 * - STAGGER: 40–70ms (between list/card items)
 */
export const MOTION_TIMING = {
  instantMs: 110,
  fastMs: 160,
  normalMs: 240,
  slowMs: 360,
  staggerMs: 50,

  // Seconds for Framer Motion transitions
  instant: 0.11,
  fast: 0.16,
  normal: 0.24,
  slow: 0.36,
  stagger: 0.05,
} as const;

/**
 * Editorial Easings (No overshoot, smooth deceleration)
 */
export const MOTION_EASING = {
  easeOut: [0.16, 1, 0.3, 1] as const,
  easeInOut: [0.65, 0, 0.35, 1] as const,
  subtleEase: [0.22, 1, 0.36, 1] as const,

  css: {
    easeOut: 'cubic-bezier(0.16, 1, 0.3, 1)',
    easeInOut: 'cubic-bezier(0.65, 0, 0.35, 1)',
    subtleEase: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },
} as const;

/**
 * Returns a Framer Motion Transition object respecting user reduced motion preferences.
 */
export function getMotionTransition(
  prefersReduced: boolean,
  duration: number = MOTION_TIMING.normal,
  ease: readonly number[] = MOTION_EASING.easeOut,
  delay: number = 0
): Transition {
  if (prefersReduced) {
    return { duration: 0.001, ease: 'linear', delay: 0 };
  }
  return {
    duration,
    ease: ease as [number, number, number, number],
    delay,
  };
}

/**
 * Page / Workspace Transition Variants (§3)
 * Outgoing: opacity 1 -> 0, translateY 0 -> -4px (~160ms)
 * Incoming: opacity 0 -> 1, translateY 12px -> 0 (~240ms)
 */
export const pageTransitionVariants: Variants = {
  initial: (prefersReduced: boolean) => ({
    opacity: 0,
    y: prefersReduced ? 0 : 12,
  }),
  animate: (prefersReduced: boolean) => ({
    opacity: 1,
    y: 0,
    transition: getMotionTransition(prefersReduced, MOTION_TIMING.normal, MOTION_EASING.easeOut),
  }),
  exit: (prefersReduced: boolean) => ({
    opacity: 0,
    y: prefersReduced ? 0 : -4,
    transition: getMotionTransition(prefersReduced, MOTION_TIMING.fast, MOTION_EASING.easeInOut),
  }),
};

/**
 * Masked Heading Reveal Variants (§4)
 * Container: overflow: hidden
 * Heading: translateY(100%) -> translateY(0) (~360ms)
 */
export const maskedHeadingVariants: Variants = {
  initial: (prefersReduced: boolean) => ({
    y: prefersReduced ? 0 : '100%',
    opacity: prefersReduced ? 0 : 1,
  }),
  animate: (prefersReduced: boolean) => ({
    y: 0,
    opacity: 1,
    transition: getMotionTransition(prefersReduced, MOTION_TIMING.slow, MOTION_EASING.easeOut),
  }),
};

/**
 * Stagger Container Variants (§5)
 * Small stagger (50ms) between items.
 */
export const staggerContainerVariants: Variants = {
  hidden: { opacity: 1 },
  visible: (prefersReduced: boolean) => ({
    opacity: 1,
    transition: {
      staggerChildren: prefersReduced ? 0 : MOTION_TIMING.stagger,
      delayChildren: prefersReduced ? 0 : 0.02,
    },
  }),
};

/**
 * Stagger Item Variants (§5)
 */
export const staggerItemVariants: Variants = {
  hidden: (prefersReduced: boolean) => ({
    opacity: 0,
    y: prefersReduced ? 0 : 8,
  }),
  visible: (prefersReduced: boolean) => ({
    opacity: 1,
    y: 0,
    transition: getMotionTransition(prefersReduced, MOTION_TIMING.normal, MOTION_EASING.easeOut),
  }),
};

/**
 * Modal Transition Variants (§16)
 * Backdrop: fade in
 * Panel: opacity 0 -> 1, scale 0.98 -> 1 (~240ms), exit (~180ms)
 */
export const modalBackdropVariants: Variants = {
  initial: { opacity: 0 },
  animate: (prefersReduced: boolean) => ({
    opacity: 1,
    transition: getMotionTransition(prefersReduced, MOTION_TIMING.normal, MOTION_EASING.easeOut),
  }),
  exit: (prefersReduced: boolean) => ({
    opacity: 0,
    transition: getMotionTransition(prefersReduced, MOTION_TIMING.fast, MOTION_EASING.easeInOut),
  }),
};

export const modalPanelVariants: Variants = {
  initial: (prefersReduced: boolean) => ({
    opacity: 0,
    scale: prefersReduced ? 1 : 0.98,
  }),
  animate: (prefersReduced: boolean) => ({
    opacity: 1,
    scale: 1,
    transition: getMotionTransition(prefersReduced, MOTION_TIMING.normal, MOTION_EASING.easeOut),
  }),
  exit: (prefersReduced: boolean) => ({
    opacity: 0,
    scale: prefersReduced ? 1 : 0.98,
    transition: getMotionTransition(prefersReduced, MOTION_TIMING.fast, MOTION_EASING.easeInOut),
  }),
};

/**
 * Inspector Drawer Transition Variants (§9)
 * Backdrop: fade in (low-opacity overlay)
 * Drawer: translateX(32px) -> 0, opacity 0 -> 1 (260ms), exit translateX(24px) (180ms)
 */
export const drawerBackdropVariants: Variants = {
  initial: { opacity: 0 },
  animate: (prefersReduced: boolean) => ({
    opacity: 1,
    transition: getMotionTransition(prefersReduced, MOTION_TIMING.normal, MOTION_EASING.easeOut),
  }),
  exit: (prefersReduced: boolean) => ({
    opacity: 0,
    transition: getMotionTransition(prefersReduced, MOTION_TIMING.fast, MOTION_EASING.easeInOut),
  }),
};

export const drawerPanelVariants: Variants = {
  initial: (prefersReduced: boolean) => ({
    x: prefersReduced ? 0 : 32,
    opacity: 0,
  }),
  animate: (prefersReduced: boolean) => ({
    x: 0,
    opacity: 1,
    transition: getMotionTransition(prefersReduced, 0.26, MOTION_EASING.easeOut),
  }),
  exit: (prefersReduced: boolean) => ({
    x: prefersReduced ? 0 : 24,
    opacity: 0,
    transition: getMotionTransition(prefersReduced, MOTION_TIMING.fast, MOTION_EASING.easeInOut),
  }),
};
