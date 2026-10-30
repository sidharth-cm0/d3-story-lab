import React from 'react';

export interface ErrorStateProps {
  title?: string;
  message: string;
  details?: string;
  retryAction?: () => void;
  retryLabel?: string;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Encountered System Anomaly',
  message,
  details,
  retryAction,
  retryLabel = 'Retry Operation',
  className = '',
}) => {
  return (
    <div className={`primitive-error-state ${className}`} role="alert">
      <div className="error-state-badge" aria-hidden="true">
        <span className="error-glyph">⚠</span>
      </div>
      <div className="error-state-content">
        <h3 className="error-state-title">{title}</h3>
        <p className="error-state-message">{message}</p>
        {details && (
          <pre className="error-state-details">
            <code>{details}</code>
          </pre>
        )}
      </div>
      {retryAction && (
        <div className="error-state-actions">
          <button
            type="button"
            className="btn-cinematic-secondary btn-error-retry"
            onClick={retryAction}
          >
            {retryLabel}
          </button>
        </div>
      )}
    </div>
  );
};
