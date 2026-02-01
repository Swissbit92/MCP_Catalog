// src/components/PersonaFilterToggle.tsx
/**
 * Persona Filter Toggle
 *
 * Toggle component for switching between NEPHILIM, legacy, or all personas.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { PersonaFilterMode } from '../utils/personaFilter';

interface PersonaFilterToggleProps {
  mode: PersonaFilterMode;
  onChange: (mode: PersonaFilterMode) => void;
  counts?: { nephilim: number; legacy: number; total: number };
  className?: string;
}

const FILTER_OPTIONS: { value: PersonaFilterMode; label: string; icon: string }[] = [
  { value: 'all', label: 'All', icon: '✦' },
  { value: 'nephilim', label: 'NEPHILIM', icon: '⬡' },
  { value: 'legacy', label: 'Legacy', icon: '◇' },
];

export const PersonaFilterToggle: React.FC<PersonaFilterToggleProps> = ({
  mode,
  onChange,
  counts,
  className = ''
}) => {
  return (
    <div className={`inline-flex items-center gap-1 p-1 rounded-lg bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 ${className}`}>
      {FILTER_OPTIONS.map((option) => {
        const isActive = mode === option.value;
        const count = counts
          ? option.value === 'all'
            ? counts.total
            : option.value === 'nephilim'
            ? counts.nephilim
            : counts.legacy
          : null;

        return (
          <motion.button
            key={option.value}
            onClick={() => onChange(option.value)}
            className={`
              relative px-3 py-1.5 rounded-md text-sm font-medium
              transition-colors duration-200
              ${isActive
                ? 'text-white'
                : 'text-slate-400 hover:text-slate-200'}
            `}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {/* Active indicator background */}
            {isActive && (
              <motion.div
                layoutId="activeFilter"
                className={`
                  absolute inset-0 rounded-md
                  ${option.value === 'nephilim'
                    ? 'bg-gradient-to-r from-cyan-500/30 to-purple-500/30 border border-cyan-500/50'
                    : option.value === 'legacy'
                    ? 'bg-slate-600/50 border border-slate-500/50'
                    : 'bg-blue-500/20 border border-blue-500/40'}
                `}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              />
            )}

            {/* Content */}
            <span className="relative flex items-center gap-1.5">
              <span className={option.value === 'nephilim' ? 'text-cyan-400' : ''}>
                {option.icon}
              </span>
              <span>{option.label}</span>
              {count !== null && (
                <span className="text-xs opacity-60">({count})</span>
              )}
            </span>
          </motion.button>
        );
      })}
    </div>
  );
};

export default PersonaFilterToggle;
