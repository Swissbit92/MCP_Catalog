import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import type { RankCeremony } from '../services/api/types'
import { RANK_CONFIG } from './nephilim/SeekerRankBadge'

interface RankCeremonyOverlayProps {
  ceremony: RankCeremony
  onDismiss: () => void
}

/** Typing animation hook (duplicated from LoreRevealOverlay — extraction is a follow-up) */
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

/** Rank badge used in the progression row */
const RankBadge: React.FC<{ rank: string; glowing?: boolean }> = ({ rank, glowing = false }) => {
  const config = RANK_CONFIG[rank] || RANK_CONFIG['Initiate']
  return (
    <div
      className={`
        inline-flex items-center gap-1.5 px-3 py-1.5
        rounded-full bg-gradient-to-r ${config.color}
        ${glowing ? `${config.glow} shadow-lg` : ''}
        font-semibold text-white text-sm
      `}
    >
      <span className="opacity-80">{config.icon}</span>
      <span>{rank}</span>
    </div>
  )
}

export const RankCeremonyOverlay: React.FC<RankCeremonyOverlayProps> = ({
  ceremony,
  onDismiss,
}) => {
  const { displayed, isComplete } = useTypingAnimation(ceremony.monologue, 25)

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
        className="relative max-w-lg w-full bg-white/[0.05] backdrop-blur-xl border border-amber-400/30 rounded-xl shadow-[0_8px_32px_0_rgba(0,0,0,0.36)] overflow-hidden"
        style={{ boxShadow: '0 0 60px rgba(251, 191, 36, 0.2), 0 8px 32px rgba(0,0,0,0.36)' }}
        initial={{ scale: 0.8, opacity: 0, y: 30 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.8, opacity: 0, y: 30 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25, delay: 0.1 }}
      >
        {/* Top accent bar — animated gradient shimmer */}
        <div
          className="h-1.5"
          style={{
            background: 'linear-gradient(90deg, transparent, #fbbf24, #f59e0b, #fbbf24, transparent)',
            backgroundSize: '200% 100%',
            animation: 'ceremony-shimmer 2s ease-in-out infinite',
          }}
        />

        <div className="p-6 md:p-8">
          {/* Header */}
          <div className="text-center mb-6">
            <motion.p
              className="text-xs uppercase tracking-[0.3em] text-amber-400/70 mb-2"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              Rank Ceremony
            </motion.p>
            <motion.h2
              className="text-xl md:text-2xl font-nephilim text-amber-300"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              {ceremony.title}
            </motion.h2>
          </div>

          {/* Divider */}
          <div className="h-px bg-gradient-to-r from-transparent via-amber-400/30 to-transparent mb-6" />

          {/* Rank progression row */}
          <motion.div
            className="flex items-center justify-center gap-4 mb-6"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5 }}
          >
            <RankBadge rank={ceremony.previous_rank} />
            <motion.span
              className="text-white/60 text-lg"
              animate={{ x: [0, 4, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
            >
              &rarr;
            </motion.span>
            <motion.div
              animate={{
                boxShadow: [
                  '0 0 0px rgba(251, 191, 36, 0)',
                  '0 0 20px rgba(251, 191, 36, 0.4)',
                  '0 0 0px rgba(251, 191, 36, 0)',
                ]
              }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
              className="rounded-full"
            >
              <RankBadge rank={ceremony.new_rank} glowing />
            </motion.div>
          </motion.div>

          {/* Divider */}
          <div className="h-px bg-gradient-to-r from-transparent via-white/20 to-transparent mb-6" />

          {/* E.E.V.A. monologue */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            <p className="text-xs uppercase tracking-widest text-purple-300/70 mb-3">
              {ceremony.speaker} speaks:
            </p>
            <div className="text-gray-200 text-sm md:text-base leading-relaxed min-h-[80px] max-h-[300px] overflow-y-auto italic">
              {displayed}
              {!isComplete && (
                <motion.span
                  className="inline-block w-0.5 h-4 bg-amber-400 ml-0.5 align-text-bottom"
                  animate={{ opacity: [1, 0, 1] }}
                  transition={{ duration: 0.8, repeat: Infinity }}
                />
              )}
            </div>
          </motion.div>

          {/* Dismiss button */}
          <motion.button
            onClick={onDismiss}
            className="w-full mt-6 py-3 bg-white/[0.08] hover:bg-white/[0.12] border border-amber-400/20 rounded-lg text-gray-300 text-sm transition-colors"
            initial={{ opacity: 0 }}
            animate={{ opacity: isComplete ? 1 : 0.3 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Continue
          </motion.button>
        </div>
      </motion.div>

      {/* Shimmer keyframe (injected via style tag — scoped to this overlay) */}
      <style>{`
        @keyframes ceremony-shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
      `}</style>
    </motion.div>
  )
}
