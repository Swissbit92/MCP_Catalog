// src/components/PersonaFilterToggle.tsx
/**
 * Persona Filter Toggle
 *
 * Toggle component for switching between Nephilim, Wanderer, or all personas.
 * Uses void/cyan theme consistent with NEPHILIM design system.
 */

import React from 'react'
import { motion } from 'framer-motion'
import { PersonaFilterMode } from '../utils/personaFilter'

interface PersonaFilterToggleProps {
  mode: PersonaFilterMode
  onChange: (mode: PersonaFilterMode) => void
  counts?: { nephilim: number; legacy: number; total: number }
  className?: string
}

const WANDERER_ICON = String.fromCodePoint(0x25C7) // White diamond (Wanderers)

const FILTER_OPTIONS: { value: PersonaFilterMode; label: string; icon: string; ariaLabel: string }[] = [
  { value: 'all', label: 'All', icon: '✦', ariaLabel: 'Show all personas' },
  { value: 'nephilim', label: 'Nephilim', icon: '⬡', ariaLabel: 'Show Nephilim personas only' },
  { value: 'legacy', label: 'Wanderers', icon: WANDERER_ICON, ariaLabel: 'Show Wanderer personas only' },
]

export const PersonaFilterToggle: React.FC<PersonaFilterToggleProps> = ({
  mode,
  onChange,
  counts,
  className = ''
}) => {
  return (
    <div className={`inline-flex items-center gap-1 p-1 rounded-lg bg-[#141418]/80 backdrop-blur-xl border border-white/[0.1] ${className}`}>
      {FILTER_OPTIONS.map((option) => {
        const isActive = mode === option.value
        const count = counts
          ? option.value === 'all'
            ? counts.total
            : option.value === 'nephilim'
            ? counts.nephilim
            : counts.legacy
          : null

        return (
          <motion.button
            key={option.value}
            onClick={() => onChange(option.value)}
            aria-label={option.ariaLabel}
            className={`
              relative px-3 py-1.5 rounded-md text-sm font-medium
              transition-colors duration-200
              ${isActive
                ? 'text-white'
                : 'text-gray-400 hover:text-gray-200'}
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
                    ? 'bg-gradient-to-r from-cyan-500/30 to-fuchsia-500/30 border border-cyan-400/50'
                    : option.value === 'legacy'
                    ? 'bg-[#24242C]/60 border border-white/[0.2]'
                    : 'bg-cyan-500/15 border border-cyan-500/30'}
                `}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              />
            )}

            {/* Content */}
            <span className="relative flex items-center gap-1.5">
              <span className={
                option.value === 'nephilim'
                  ? 'text-cyan-400'
                  : option.value === 'legacy'
                  ? 'text-gray-300'
                  : ''
              }>
                {option.icon}
              </span>
              <span>{option.label}</span>
              {count !== null && (
                <span className="text-xs opacity-60">({count})</span>
              )}
            </span>
          </motion.button>
        )
      })}
    </div>
  )
}

export default PersonaFilterToggle
