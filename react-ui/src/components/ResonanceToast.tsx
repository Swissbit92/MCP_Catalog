import React from 'react'
import { motion } from 'framer-motion'

interface ResonanceToastProps {
  amount: number
  className?: string
}

export const ResonanceToast: React.FC<ResonanceToastProps> = ({ amount, className = '' }) => {
  return (
    <motion.div
      className={`flex flex-col items-center gap-1 py-2 ${className}`}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      {/* Gradient divider line */}
      <div className="w-full h-px bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent" />

      {/* Resonance text */}
      <motion.span
        className="text-white/60 text-xs tracking-wider"
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.4 }}
      >
        +{amount} resonance &#x2727;
      </motion.span>

      {/* Second gradient divider line */}
      <div className="w-full h-px bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent" />
    </motion.div>
  )
}
