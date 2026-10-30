import React from 'react';

export interface PanelCardProps {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  headerAction?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'accent' | 'error' | 'muted';
}

export const PanelCard: React.FC<PanelCardProps> = ({
  title,
  subtitle,
  headerAction,
  footer,
  children,
  className = '',
  variant = 'default',
}) => {
  const hasHeader = title || subtitle || headerAction;

  return (
    <article className={`primitive-panel-card variant-${variant} ${className}`}>
      {hasHeader && (
        <header className="panel-card-header">
          <div className="panel-card-titles">
            {title && <h3 className="panel-card-title">{title}</h3>}
            {subtitle && <div className="panel-card-subtitle">{subtitle}</div>}
          </div>
          {headerAction && <div className="panel-card-header-action">{headerAction}</div>}
        </header>
      )}
      <div className="panel-card-body">{children}</div>
      {footer && <footer className="panel-card-footer">{footer}</footer>}
    </article>
  );
};
