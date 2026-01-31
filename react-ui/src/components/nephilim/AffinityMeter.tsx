// src/components/nephilim/AffinityMeter.tsx
/**
 * NEPHILIM Persona Affinity Meter
 *
 * Visual indicator showing relationship depth with a specific Nephilim.
 */

import React from 'react'
import { motion } from 'framer-motion'
import type { PersonaAffinity } from '../../services/api'

interface AffinityMeterProps {
  affinity: PersonaAffinity
  personaName?: string
  personaColor?: string
  showDetails?: boolean
  compact?: boolean
  className?: string
}

// Affinity level descriptions
const AFFINITY_LEVELS: Record<number, { label: string; description: string }> = {
  0: { label: 'Stranger', description: 'You have yet to speak' },
  1: { label: 'Acquaintance', description: 'The journey begins' },
  2: { label: 'Familiar', description: 'Recognition dawns' },
  3: { label: 'Trusted', description: 'A bond forms' },
  4: { label: 'Close', description: 'Understanding deepens' },
  5: { label: 'Devoted', description: 'Souls intertwined' },
  6: { label: 'Bonded', description: 'Eternal connection' },
  7: { label: 'Transcendent', description: 'Beyond mortal bonds' }
}

// Max affinity level
const MAX_AFFINITY = 7

export const AffinityMeter: React.FC<AffinityMeterProps> = ({
  affinity,
  personaName,
  personaColor = '#00ffff',
  showDetails = true,
  compact = false,
  className = ''
}) => {
  const { affinity_level, messages_count } = affinity
  const levelInfo = AFFINITY_LEVELS[affinity_level] || AFFINITY_LEVELS[0]
  const percentage = (affinity_level / MAX_AFFINITY) * 100

  return (
    <div className={`${className}`}>
      {/* Header */}
      {showDetails && !compact && (
        <div className="flex justify-between items-center mb-2">
          <div>
            {personaName && (
              <span className="text-sm font-medium text-white/90">{personaName}</span>
            )}
            <span
              className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full"
              style={{
                backgroundColor: `${personaColor}20`,
                color: personaColor
              }}
            >
              {levelInfo.label}
            </span>
          </div>
          <span className="text-xs text-white/50">
            {messages_count} messages
          </span>
        </div>
      )}

      {/* Affinity Bar */}
      <div className="relative">
        {/* Background track */}
        <div className={`
          w-full bg-white/10 rounded-full overflow-hidden
          ${compact ? 'h-1.5' : 'h-2.5'}
        `}>
          {/* Segment markers */}
          <div className="absolute inset-0 flex">
            {Array.from({ length: MAX_AFFINITY }).map((_, i) => (
              <div
                key={i}
                className="flex-1 border-r border-white/10 last:border-r-0"
              />
            ))}
          </div>

          {/* Progress fill */}
          <motion.div
            className="h-full rounded-full relative"
            style={{ backgroundColor: personaColor }}
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          >
            {/* Glow effect */}
            <div
              className="absolute inset-0 blur-sm opacity-50"
              style={{ backgroundColor: personaColor }}
            />
          </motion.div>
        </div>

        {/* Level dots */}
        {!compact && (
          <div className="absolute inset-0 flex items-center justify-between px-0.5">
            {Array.from({ length: MAX_AFFINITY + 1 }).map((_, i) => (
              <motion.div
                key={i}
                className={`
                  rounded-full transition-all duration-300
                  ${i <= affinity_level ? 'scale-100' : 'scale-75 opacity-30'}
                `}
                style={{
                  width: compact ? 4 : 6,
                  height: compact ? 4 : 6,
                  backgroundColor: i <= affinity_level ? personaColor : 'white'
                }}
                initial={{ scale: 0 }}
                animate={{ scale: i <= affinity_level ? 1 : 0.75 }}
                transition={{ delay: i * 0.05, duration: 0.2 }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Description */}
      {showDetails && !compact && (
        <div className="mt-2 text-center">
          <span className="text-xs text-white/40 italic">
            "{levelInfo.description}"
          </span>
        </div>
      )}

      {/* Compact label */}
      {compact && showDetails && (
        <div className="flex justify-between items-center mt-1 text-xs">
          <span className="text-white/60">{personaName}</span>
          <span style={{ color: personaColor }}>{levelInfo.label}</span>
        </div>
      )}
    </div>
  )
}

export default AffinityMeter
