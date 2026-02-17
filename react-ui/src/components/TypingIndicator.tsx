import React from 'react'
import { motion } from 'framer-motion'

interface TypingIndicatorProps {
  className?: string
  personaName?: string
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ className = '', personaName }) => {
  const label = personaName ? `${personaName} is channeling...` : 'Assistant is typing...'

  return (
    <motion.div
      className={`flex items-center gap-3 px-4 py-3 bg-white/[0.08] backdrop-blur-lg rounded-2xl border border-white/[0.1] shadow-sm max-w-fit ${className}`}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
    >
      <div className="flex items-center gap-1">
        <motion.div
          className="w-2.5 h-2.5 bg-gradient-to-r from-cyan-400 to-fuchsia-400 rounded-full shadow-sm"
          animate={{
            y: [0, -10, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        <motion.div
          className="w-2.5 h-2.5 bg-gradient-to-r from-cyan-400 to-fuchsia-400 rounded-full shadow-sm"
          animate={{
            y: [0, -10, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 0.2,
          }}
        />
        <motion.div
          className="w-2.5 h-2.5 bg-gradient-to-r from-cyan-400 to-fuchsia-400 rounded-full shadow-sm"
          animate={{
            y: [0, -10, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 0.4,
          }}
        />
      </div>
      <span className="text-sm text-gray-400 font-medium">{label}</span>
    </motion.div>
  )
}
