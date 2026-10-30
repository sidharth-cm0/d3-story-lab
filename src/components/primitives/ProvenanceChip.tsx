import React from 'react';

export interface ProvenanceChipProps {
  type: 'EVENT' | 'BLOCK' | 'SHOT' | 'PANEL' | 'SCENE' | 'PROPOSITION' | string;
  id: string;
  label?: string;
  onClick?: (id: string) => void;
  className?: string;
}

export const ProvenanceChip: React.FC<ProvenanceChipProps> = ({
  type,
  id,
  label,
  onClick,
  className = '',
}) => {
  const content = (
    <>
      <span className="provenance-chip-type">{type}</span>
      <span className="provenance-chip-id">{id}</span>
      {label && <span className="provenance-chip-label">({label})</span>}
    </>
  );

  if (onClick) {
    return (
      <button
        type="button"
        className={`primitive-provenance-chip clickable ${className}`}
        onClick={() => onClick(id)}
        title={`Inspect provenance entity ${type}: ${id}`}
        aria-label={`Inspect ${type} ${id}`}
      >
        {content}
      </button>
    );
  }

  return (
    <span
      className={`primitive-provenance-chip ${className}`}
      title={`Provenance entity ${type}: ${id}`}
    >
      {content}
    </span>
  );
};
