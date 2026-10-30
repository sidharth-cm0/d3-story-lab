import React from 'react';

export interface PanelToolbarProps {
  left?: React.ReactNode;
  center?: React.ReactNode;
  right?: React.ReactNode;
  className?: string;
  bordered?: boolean;
}

export const PanelToolbar: React.FC<PanelToolbarProps> = ({
  left,
  center,
  right,
  className = '',
  bordered = true,
}) => {
  return (
    <div
      className={`primitive-panel-toolbar ${bordered ? 'bordered' : ''} ${className}`}
      role="toolbar"
      aria-label="Panel controls"
    >
      <div className="toolbar-left">{left}</div>
      {center && <div className="toolbar-center">{center}</div>}
      <div className="toolbar-right">{right}</div>
    </div>
  );
};
