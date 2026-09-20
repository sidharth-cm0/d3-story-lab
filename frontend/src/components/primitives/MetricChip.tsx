import React from 'react';

export interface MetricChipProps {
  label: string;
  value: string | number;
  delta?: string | number;
  trend?: 'up' | 'down' | 'neutral';
  tone?: 'default' | 'amber' | 'error';
  className?: string;
}

export const MetricChip: React.FC<MetricChipProps> = ({
  label,
  value,
  delta,
  trend,
  tone = 'default',
  className = '',
}) => {
  return (
    <div className={`primitive-metric-chip tone-${tone} ${className}`}>
      <span className="metric-chip-label">{label}</span>
      <span className="metric-chip-value">{value}</span>
      {delta !== undefined && (
        <span className={`metric-chip-delta trend-${trend || 'neutral'}`}>
          {trend === 'up' ? '▲ ' : trend === 'down' ? '▼ ' : ''}
          {delta}
        </span>
      )}
    </div>
  );
};
