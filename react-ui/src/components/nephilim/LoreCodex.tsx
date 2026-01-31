// src/components/nephilim/LoreCodex.tsx
/**
 * NEPHILIM Lore Codex
 *
 * Displays unlocked and locked lore fragments for a persona,
 * creating a collectible narrative experience.
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { LoreFragment } from '../../services/api'

interface LoreCodexProps {
  fragments: LoreFragment[]
  personaName: string
  personaColor?: string
  currentMessages?: number
  className?: string
}

// Rarity styling
const RARITY_STYLES: Record<string, { border: string; bg: string; glow: string }> = {
  'common': {
    border: 'border-blue-500/50',
    bg: 'bg-blue-500/10',
    glow: 'shadow-blue-500/20'
  },
  'rare': {
    border: 'border-cyan-400/50',
    bg: 'bg-cyan-400/10',
    glow: 'shadow-cyan-400/20'
  },
  'epic': {
    border: 'border-purple-500/50',
    bg: 'bg-purple-500/10',
    glow: 'shadow-purple-500/20'
  },
  'legendary': {
    border: 'border-amber-400/50',
    bg: 'bg-amber-400/10',
    glow: 'shadow-amber-400/30'
  }
}

export const LoreCodex: React.FC<LoreCodexProps> = ({
  fragments,
  personaName,
  personaColor = '#00ffff',
  currentMessages = 0,
  className = ''
}) => {
  const [selectedFragment, setSelectedFragment] = useState<LoreFragment | null>(null)

  const unlockedCount = fragments.filter(f => f.unlocked).length
  const totalCount = fragments.length

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <span style={{ color: personaColor }}>📜</span>
          {personaName}'s Lore
        </h3>
        <span className="text-sm text-white/60">
          {unlockedCount} / {totalCount} unlocked
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-white/10 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: personaColor }}
          initial={{ width: 0 }}
          animate={{ width: `${(unlockedCount / totalCount) * 100}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>

      {/* Fragment Grid */}
      <div className="grid gap-3">
        {fragments.map((fragment, index) => {
          const rarity = RARITY_STYLES[fragment.rarity] || RARITY_STYLES['common']
          const progressToUnlock = Math.min(100, (currentMessages / fragment.messages_required) * 100)

          return (
            <motion.div
              key={fragment.fragment_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`
                relative rounded-lg border p-4 cursor-pointer
                transition-all duration-300
                ${rarity.border} ${rarity.bg}
                ${fragment.unlocked ? `shadow-lg ${rarity.glow}` : 'opacity-60'}
                hover:opacity-100 hover:scale-[1.02]
              `}
              onClick={() => fragment.unlocked && setSelectedFragment(fragment)}
            >
              {/* Locked overlay */}
              {!fragment.unlocked && (
                <div className="absolute inset-0 bg-black/50 rounded-lg flex items-center justify-center backdrop-blur-sm">
                  <div className="text-center">
                    <span className="text-2xl">🔒</span>
                    <p className="text-xs text-white/60 mt-1">
                      {fragment.messages_required - currentMessages} messages to unlock
                    </p>
                    {/* Mini progress bar */}
                    <div className="w-24 h-1 bg-white/10 rounded-full mt-2 mx-auto overflow-hidden">
                      <div
                        className="h-full bg-white/40 rounded-full"
                        style={{ width: `${progressToUnlock}%` }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Fragment header */}
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h4 className="font-semibold text-white text-sm">
                    {fragment.fragment_title}
                  </h4>
                  <span className={`
                    text-xs px-1.5 py-0.5 rounded capitalize
                    ${fragment.rarity === 'legendary' ? 'text-amber-400 bg-amber-400/20' :
                      fragment.rarity === 'epic' ? 'text-purple-400 bg-purple-400/20' :
                      fragment.rarity === 'rare' ? 'text-cyan-400 bg-cyan-400/20' :
                      'text-blue-400 bg-blue-400/20'}
                  `}>
                    {fragment.rarity}
                  </span>
                </div>
                {fragment.unlocked && (
                  <span className="text-green-400 text-sm">✓</span>
                )}
              </div>

              {/* Preview text */}
              {fragment.unlocked && (
                <p className="text-xs text-white/70 line-clamp-2">
                  {fragment.fragment.slice(0, 100)}...
                </p>
              )}

              {/* Unlock date */}
              {fragment.unlocked && fragment.unlocked_at && (
                <p className="text-xs text-white/40 mt-2">
                  Unlocked {new Date(fragment.unlocked_at).toLocaleDateString()}
                </p>
              )}
            </motion.div>
          )
        })}
      </div>

      {/* Detail Modal */}
      <AnimatePresence>
        {selectedFragment && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
            onClick={() => setSelectedFragment(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className={`
                max-w-lg w-full rounded-xl border-2 p-6
                ${RARITY_STYLES[selectedFragment.rarity]?.border}
                bg-gradient-to-br from-gray-900/95 to-black/95
                shadow-2xl
              `}
              onClick={e => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold text-white">
                    {selectedFragment.fragment_title}
                  </h3>
                  <span className={`
                    text-xs px-2 py-1 rounded capitalize mt-1 inline-block
                    ${selectedFragment.rarity === 'legendary' ? 'text-amber-400 bg-amber-400/20' :
                      selectedFragment.rarity === 'epic' ? 'text-purple-400 bg-purple-400/20' :
                      selectedFragment.rarity === 'rare' ? 'text-cyan-400 bg-cyan-400/20' :
                      'text-blue-400 bg-blue-400/20'}
                  `}>
                    {selectedFragment.rarity}
                  </span>
                </div>
                <button
                  onClick={() => setSelectedFragment(null)}
                  className="text-white/60 hover:text-white text-xl"
                >
                  ✕
                </button>
              </div>

              {/* Content */}
              <div className="prose prose-invert prose-sm max-w-none">
                <p className="text-white/90 leading-relaxed whitespace-pre-wrap">
                  {selectedFragment.fragment}
                </p>
              </div>

              {/* Footer */}
              <div className="mt-6 pt-4 border-t border-white/10 flex justify-between items-center text-xs text-white/50">
                <span>Required {selectedFragment.messages_required} messages</span>
                {selectedFragment.unlocked_at && (
                  <span>Unlocked {new Date(selectedFragment.unlocked_at).toLocaleDateString()}</span>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default LoreCodex
