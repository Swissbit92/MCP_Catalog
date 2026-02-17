import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

interface LoreFragment {
  title: string
  content: string
  rarity: string
}

interface LoreRevealOverlayProps {
  fragment: LoreFragment
  personaName: string
  onDismiss: () => void
}

/** Map rarity to border/glow color */
const rarityColors: Record<string, { border: string; glow: string; text: string }> = {
  common: {
    border: 'border-blue-400/50',
    glow: 'rgba(96, 165, 250, 0.3)',
    text: 'text-blue-300',
  },
  rare: {
    border: 'border-cyan-400/50',
    glow: 'rgba(6, 182, 212, 0.3)',
    text: 'text-cyan-300',
  },
  epic: {
    border: 'border-purple-400/50',
    glow: 'rgba(167, 139, 250, 0.3)',
    text: 'text-purple-300',
  },
  legendary: {
    border: 'border-yellow-400/50',
    glow: 'rgba(251, 191, 36, 0.3)',
    text: 'text-yellow-300',
  },
}

/** Typing animation hook */
const useTypingAnimation = (text: string, speed: number = 30) => {
  const [displayed, setDisplayed] = useState('')
  const [isComplete, setIsComplete] = useState(false)

  useEffect(() => {
    setDisplayed('')
    setIsComplete(false)
    let index = 0
    const interval = setInterval(() => {
      if (index < text.length) {
        setDisplayed(text.slice(0, index + 1))
        index++
      } else {
        setIsComplete(true)
        clearInterval(interval)
      }
    }, speed)

    return () => clearInterval(interval)
  }, [text, speed])

  return { displayed, isComplete }
}

export const LoreRevealOverlay: React.FC<LoreRevealOverlayProps> = ({
  fragment,
  personaName,
  onDismiss,
}) => {
  const colors = rarityColors[fragment.rarity] || rarityColors.common
  const { displayed, isComplete } = useTypingAnimation(fragment.content, 25)

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDismiss()
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onDismiss])

  return (
      <motion.div
        className="fixed inset-0 z-[100] flex items-center justify-center p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* Backdrop */}
        <motion.div
          className="absolute inset-0 bg-black/90 backdrop-blur-xl"
          onClick={onDismiss}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        />

        {/* Card */}
        <motion.div
          className={`relative max-w-lg w-full bg-white/[0.05] backdrop-blur-xl border ${colors.border} rounded-xl shadow-[0_8px_32px_0_rgba(0,0,0,0.36)] overflow-hidden`}
          style={{ boxShadow: `0 0 60px ${colors.glow}, 0 8px 32px rgba(0,0,0,0.36)` }}
          initial={{ scale: 0.8, opacity: 0, y: 30 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.8, opacity: 0, y: 30 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25, delay: 0.1 }}
        >
          {/* Top accent bar */}
          <div className="h-1 bg-gradient-to-r from-transparent via-cyan-500/60 to-transparent" />

          <div className="p-6 md:p-8">
            {/* Header */}
            <div className="text-center mb-6">
              <motion.p
                className="text-xs uppercase tracking-[0.3em] text-white/60 mb-2"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                Lore Fragment Unlocked
              </motion.p>
              <motion.h2
                className={`text-xl md:text-2xl font-nephilim ${colors.text}`}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                {fragment.title}
              </motion.h2>
              <motion.p
                className="text-sm text-gray-400 mt-1"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                Revealed by {personaName}
              </motion.p>
            </div>

            {/* Divider */}
            <div className="h-px bg-gradient-to-r from-transparent via-white/20 to-transparent mb-6" />

            {/* Content with typing animation */}
            <motion.div
              className="text-gray-200 text-sm md:text-base leading-relaxed min-h-[80px] max-h-[300px] overflow-y-auto"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
            >
              {displayed}
              {!isComplete && (
                <motion.span
                  className="inline-block w-0.5 h-4 bg-cyan-400 ml-0.5 align-text-bottom"
                  animate={{ opacity: [1, 0, 1] }}
                  transition={{ duration: 0.8, repeat: Infinity }}
                />
              )}
            </motion.div>

            {/* Rarity badge */}
            <div className="flex justify-center mt-6 mb-4">
              <span className={`text-xs uppercase tracking-widest px-3 py-1 rounded-full border ${colors.border} ${colors.text} bg-white/[0.05]`}>
                {fragment.rarity}
              </span>
            </div>

            {/* Dismiss button */}
            <motion.button
              onClick={onDismiss}
              className="w-full py-3 bg-white/[0.08] hover:bg-white/[0.12] border border-white/[0.1] rounded-lg text-gray-300 text-sm transition-colors"
              initial={{ opacity: 0 }}
              animate={{ opacity: isComplete ? 1 : 0.3 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              Continue
            </motion.button>
          </div>
        </motion.div>
      </motion.div>
  )
}
