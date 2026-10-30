import React, { useRef } from 'react';
import { motion } from 'framer-motion';
import { usePrefersReducedMotion, getMotionTransition } from '../../hooks/usePrefersReducedMotion';

export interface SegmentedControlOption<T extends string = string> {
  value: T;
  label: React.ReactNode;
  disabled?: boolean;
}

export interface SegmentedControlProps<T extends string = string> {
  options: SegmentedControlOption<T>[];
  value: T;
  onChange: (value: T) => void;
  name?: string;
  ariaLabel?: string;
  className?: string;
}

export function SegmentedControl<T extends string = string>({
  options,
  value,
  onChange,
  name = 'segmented-control',
  ariaLabel = 'Select option',
  className = '',
}: SegmentedControlProps<T>) {
  const prefersReduced = usePrefersReducedMotion();
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, currentIndex: number) => {
    let nextIndex = -1;

    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      nextIndex = (currentIndex + 1) % options.length;
      while (options[nextIndex]?.disabled && nextIndex !== currentIndex) {
        nextIndex = (nextIndex + 1) % options.length;
      }
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      nextIndex = (currentIndex - 1 + options.length) % options.length;
      while (options[nextIndex]?.disabled && nextIndex !== currentIndex) {
        nextIndex = (nextIndex - 1 + options.length) % options.length;
      }
    } else if (e.key === 'Home') {
      e.preventDefault();
      nextIndex = 0;
      while (options[nextIndex]?.disabled && nextIndex < options.length - 1) {
        nextIndex++;
      }
    } else if (e.key === 'End') {
      e.preventDefault();
      nextIndex = options.length - 1;
      while (options[nextIndex]?.disabled && nextIndex > 0) {
        nextIndex--;
      }
    }

    if (nextIndex !== -1 && !options[nextIndex]?.disabled) {
      const nextOption = options[nextIndex];
      onChange(nextOption.value);
      buttonRefs.current[nextIndex]?.focus();
    }
  };

  const transition = getMotionTransition(prefersReduced, 0.16);

  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={`primitive-segmented-control ${className}`}
    >
      {options.map((option, index) => {
        const isSelected = option.value === value;
        return (
          <button
            key={option.value}
            ref={(el) => {
              buttonRefs.current[index] = el;
            }}
            type="button"
            role="radio"
            aria-checked={isSelected}
            disabled={option.disabled}
            tabIndex={isSelected ? 0 : -1}
            onClick={() => onChange(option.value)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            className={`segmented-control-item ${isSelected ? 'selected' : ''}`}
          >
            {isSelected && (
              <motion.span
                layoutId={`segmented-indicator-${name}`}
                className="segmented-control-indicator"
                transition={transition}
                aria-hidden="true"
              />
            )}
            <span className="segmented-control-label">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
