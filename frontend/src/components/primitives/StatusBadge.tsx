import React from 'react';

export type StatusBadgeTone = 'neutral' | 'amber' | 'error' | 'subtle';

export interface StatusBadgeProps {
  label: React.ReactNode;
  tone?: StatusBadgeTone;
  dot?: boolean;
  className?: string;
  ariaLive?: 'polite' | 'off' | 'assertive';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  label,
  tone = 'neutral',
  dot = false,
  className = '',
  ariaLive = 'polite',
}) => {
  return (
    <span
      role="status"
      aria-live={ariaLive}
      className={`primitive-status-badge tone-${tone} ${className}`}
    >
      {dot && <span className="status-badge-dot" aria-hidden="true" />}
      <span className="status-badge-label">{label}</span>
    </span>
  );
};
