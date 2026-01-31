// src/components/nephilim/ResonanceProgress.tsx
/**
 * NEPHILIM Resonance Progress Bar
 *
 * Displays progress towards the next rank with animated effects.
 */

import React from 'react'
import { motion } from 'framer-motion'
import type { RankProgress } from '../../services/api'

interface ResonanceProgressProps {
  progress: RankProgress
  showLabels?: boolean
  compact?: boolean
  className?: string
}

// Rank colors for the progress bar
const RANK_COLORS: Record<string, string> = {
  'Initiate': 'from-slate-500 to-slate-400',
  'Acolyte': 'from-emerald-500 to-emerald-400',
  'Adept': 'from-cyan-500 to-cyan-400',
  'Ascendant': 'from-purple-500 to-violet-400',
  'Nephilim': 'from-amber-500 to-orange-400'
}

export const ResonanceProgress: React.FC<ResonanceProgressProps> = ({
  progress,
  showLabels = true,
  compact = false,
  className = ''
}) => {
  const {
    current_rank,
    current_resonance,
    next_rank,
    resonance_needed,
    progress_percent
  } = progress

  const barColor = RANK_COLORS[current_rank] || RANK_COLORS['Initiate']
  const isMaxRank = !next_rank || progress_percent >= 100

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Labels */}
      {showLabels && !compact && (
        <div className="flex justify-between items-center text-sm">
          <span className="text-white/80 font-medium">{current_rank}</span>
          {next_rank && (
            <span className="text-white/60">{next_rank}</span>
          )}
        </div>
      )}

      {/* Progress Bar Container */}
      <div className="relative">
        <div className={`
          w-full bg-white/10 rounded-full overflow-hidden
          ${compact ? 'h-2' : 'h-3'}
        `}>
          {/* Background glow */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent" />

          {/* Progress fill */}
          <motion.div
            className={`
              h-full rounded-full
              bg-gradient-to-r ${barColor}
              relative overflow-hidden
            `}
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(progress_percent, 100)}%` }}
            transition={{ duration: 1, ease: 'easeOut' }}
          >
            {/* Shimmer effect */}
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
              initial={{ x: '-100%' }}
              animate={{ x: '200%' }}
              transition={{
                duration: 2,
                repeat: Infinity,
                repeatDelay: 1,
                ease: 'easeInOut'
              }}
            />
          </motion.div>
        </div>

        {/* Resonance count overlay */}
        {!compact && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xs font-bold text-white drop-shadow-lg">
              {isMaxRank ? (
                'MAX RANK'
              ) : (
                `${current_resonance.toLocaleString()} / ${(current_resonance + resonance_needed).toLocaleString()}`
              )}
            </span>
          </div>
        )}
      </div>

      {/* Compact resonance text */}
      {compact && showLabels && (
        <div className="flex justify-between items-center text-xs text-white/60">
          <span>{current_resonance.toLocaleString()} RP</span>
          <span>{progress_percent}%</span>
        </div>
      )}

      {/* Resonance needed text */}
      {showLabels && !compact && !isMaxRank && (
        <div className="text-center text-xs text-white/50">
          {resonance_needed.toLocaleString()} Resonance to {next_rank}
        </div>
      )}
    </div>
  )
}

export default ResonanceProgress
