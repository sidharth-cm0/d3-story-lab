import React from 'react';

export interface LoadingStateProps {
  message?: string;
  step?: string;
  progressPercent?: number;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Executing Narrative Step...',
  step,
  progressPercent,
  className = '',
}) => {
  return (
    <div
      className={`primitive-loading-state ${className}`}
      role="status"
      aria-live="polite"
    >
      <div className="loading-meter-container" aria-hidden="true">
        <div
          className="loading-meter-bar"
          style={{
            width: progressPercent !== undefined ? `${Math.min(100, Math.max(0, progressPercent))}%` : '60%',
          }}
        />
      </div>
      <div className="loading-text-group">
        <span className="loading-spinner-glyph" aria-hidden="true">◌</span>
        <span className="loading-message">{message}</span>
        {step && <span className="loading-step">[{step}]</span>}
      </div>
    </div>
  );
};
