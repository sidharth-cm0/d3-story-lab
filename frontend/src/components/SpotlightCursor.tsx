import React, { useEffect, useState } from 'react';

export const SpotlightCursor: React.FC = () => {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const [visible, setVisible] = useState(false);
  const [isInteractive, setIsInteractive] = useState(false);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isTouch = window.matchMedia('(hover: none), (pointer: coarse)').matches;
    if (prefersReducedMotion || isTouch) return;

    let frameId: number;
    const handleMouseMove = (e: MouseEvent) => {
      cancelAnimationFrame(frameId);
      frameId = requestAnimationFrame(() => {
        setPos({ x: e.clientX, y: e.clientY });
        setVisible(true);

        const target = e.target as HTMLElement | null;
        const interactive = Boolean(
          target &&
          (target.tagName === 'BUTTON' ||
            target.tagName === 'A' ||
            target.tagName === 'SELECT' ||
            target.tagName === 'INPUT' ||
            target.tagName === 'SUMMARY' ||
            target.getAttribute('role') === 'button' ||
            target.closest('button, a, select, input, summary, [role="button"], .comic-panel-box, .artwork-first-card, .portfolio-project-card'))
        );
        setIsInteractive(interactive);
      });
    };

    const handleMouseLeave = () => {
      setVisible(false);
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    document.body.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('mousemove', handleMouseMove);
      document.body.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  if (!visible || !pos) return null;

  return (
    <div
      className={`spotlight-cursor ${isInteractive ? 'spotlight-interactive' : ''}`}
      style={{
        left: `${pos.x}px`,
        top: `${pos.y}px`,
      }}
      aria-hidden="true"
    />
  );
};
