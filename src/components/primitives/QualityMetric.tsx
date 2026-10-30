import React from 'react';

export type QualityStatus = 'passed' | 'warning' | 'failed' | 'neutral';

export interface QualityMetricProps {
  label: string;
  value: string | number;
  status: QualityStatus;
  detail?: string;
  benchmark?: string;
  className?: string;
}

export const QualityMetric: React.FC<QualityMetricProps> = ({
  label,
  value,
  status,
  detail,
  benchmark,
  className = '',
}) => {
  const statusGlyph = {
    passed: '✓',
    warning: '▲',
    failed: '✕',
    neutral: '•',
  }[status];

  return (
    <div className={`primitive-quality-metric status-${status} ${className}`}>
      <div className="quality-metric-header">
        <span className="quality-metric-status-badge" aria-hidden="true">
          {statusGlyph}
        </span>
        <span className="quality-metric-label">{label}</span>
        <span className="quality-metric-value">{value}</span>
      </div>
      {(detail || benchmark) && (
        <div className="quality-metric-meta">
          {benchmark && <span className="quality-metric-benchmark">Target: {benchmark}</span>}
          {detail && <span className="quality-metric-detail">{detail}</span>}
        </div>
      )}
    </div>
  );
};
