import React from 'react';
import { MaskedHeading } from '../motion/MaskedHeading';

export interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  action?: React.ReactNode;
  className?: string;
  delay?: number;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  title,
  subtitle,
  eyebrow,
  action,
  className = '',
  delay = 0,
}) => {
  return (
    <div className={`primitive-section-header ${className}`}>
      <div className="section-header-text">
        {eyebrow && <span className="section-header-eyebrow">{eyebrow}</span>}
        <MaskedHeading as="h2" className="section-header-title" delay={delay}>
          {title}
        </MaskedHeading>
        {subtitle && <p className="section-header-subtitle">{subtitle}</p>}
      </div>
      {action && <div className="section-header-action">{action}</div>}
    </div>
  );
};
