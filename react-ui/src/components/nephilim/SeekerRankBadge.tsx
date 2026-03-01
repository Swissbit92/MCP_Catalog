// src/components/nephilim/SeekerRankBadge.tsx
/**
 * NEPHILIM Seeker Rank Badge
 *
 * Displays the user's current rank with appropriate styling
 * and optional progress indicator.
 */

import React from 'react'
import { motion } from 'framer-motion'

interface SeekerRankBadgeProps {
  rank: string
  resonance?: number
  showResonance?: boolean
  size?: 'sm' | 'md' | 'lg'
  animated?: boolean
  className?: string
}

// Rank configuration with colors and icons
export const RANK_CONFIG: Record<string, { color: string; glow: string; icon: string }> = {
  'Initiate': {
    color: 'from-slate-500 to-slate-600',
    glow: 'shadow-slate-500/30',
    icon: '◇'
  },
  'Acolyte': {
    color: 'from-emerald-500 to-emerald-600',
    glow: 'shadow-emerald-500/30',
    icon: '◆'
  },
  'Adept': {
    color: 'from-cyan-400 to-blue-500',
    glow: 'shadow-cyan-500/40',
    icon: '✦'
  },
  'Ascendant': {
    color: 'from-purple-400 to-violet-600',
    glow: 'shadow-purple-500/50',
    icon: '✧'
  },
  'Nephilim': {
    color: 'from-amber-400 to-orange-500',
    glow: 'shadow-amber-500/60',
    icon: '⬡'
  }
}

const SIZE_CLASSES = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
  lg: 'px-4 py-1.5 text-base'
}

export const SeekerRankBadge: React.FC<SeekerRankBadgeProps> = ({
  rank,
  resonance,
  showResonance = false,
  size = 'md',
  animated = true,
  className = ''
}) => {
  const config = RANK_CONFIG[rank] || RANK_CONFIG['Initiate']

  const badge = (
    <div
      className={`
        inline-flex items-center gap-1.5
        rounded-full
        bg-gradient-to-r ${config.color}
        ${config.glow}
        shadow-lg
        font-semibold text-white
        ${SIZE_CLASSES[size]}
        ${className}
      `}
    >
      <span className="opacity-80">{config.icon}</span>
      <span>{rank}</span>
      {showResonance && resonance !== undefined && (
        <span className="opacity-70 ml-1">
          ({resonance.toLocaleString()})
        </span>
      )}
    </div>
  )

  if (!animated) return badge

  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      whileHover={{ scale: 1.05 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
    >
      {badge}
    </motion.div>
  )
}

export default SeekerRankBadge
