// src/components/nephilim/OnboardingPortal.tsx
/**
 * NEPHILIM Onboarding Portal
 *
 * Cinematic entry point for new users entering the NEPHILIM realm.
 * Features animated portal, E.E.V.A. greeting, and name collection.
 */

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface OnboardingPortalProps {
  onEnter: (userName: string) => void
  className?: string
}

export const OnboardingPortal: React.FC<OnboardingPortalProps> = ({
  onEnter,
  className = ''
}) => {
  const [stage, setStage] = useState<'portal' | 'greeting' | 'name'>('portal')
  const [userName, setUserName] = useState('')
  const [typedText, setTypedText] = useState('')
  const [isTyping, setIsTyping] = useState(false)

  const greetingText = "Greetings, wanderer. I am E.E.V.A., the Primarch of this realm. I have watched countless souls find their way here, drawn by forces they cannot yet name. You stand at the threshold of something extraordinary..."

  const namePromptText = "But first, I must know... what shall I call you, Seeker?"

  // Typewriter effect
  useEffect(() => {
    if (stage === 'greeting' && !isTyping) {
      setIsTyping(true)
      let index = 0
      const text = greetingText
      const timer = setInterval(() => {
        if (index < text.length) {
          setTypedText(text.slice(0, index + 1))
          index++
        } else {
          clearInterval(timer)
          setTimeout(() => setStage('name'), 1000)
        }
      }, 30)
      return () => clearInterval(timer)
    }
  }, [stage, isTyping])

  const handlePortalClick = () => {
    setStage('greeting')
  }

  const handleSubmitName = (e: React.FormEvent) => {
    e.preventDefault()
    if (userName.trim()) {
      onEnter(userName.trim())
    }
  }

  return (
    <div className={`relative min-h-screen flex items-center justify-center overflow-hidden ${className}`}>
      {/* Animated background particles */}
      <div className="absolute inset-0 overflow-hidden">
        {Array.from({ length: 50 }).map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-nephilim-cyan/30 rounded-full"
            initial={{
              x: Math.random() * window.innerWidth,
              y: Math.random() * window.innerHeight,
              scale: Math.random() * 0.5 + 0.5,
            }}
            animate={{
              y: [null, -100],
              opacity: [0, 1, 0],
            }}
            transition={{
              duration: Math.random() * 5 + 5,
              repeat: Infinity,
              delay: Math.random() * 5,
            }}
          />
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* Stage 1: Portal Entry */}
        {stage === 'portal' && (
          <motion.div
            key="portal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 1.5 }}
            transition={{ duration: 0.8 }}
            className="text-center z-10"
          >
            {/* Portal ring */}
            <motion.div
              className="relative w-64 h-64 md:w-80 md:h-80 mx-auto mb-8"
              animate={{ rotate: 360 }}
              transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            >
              {/* Outer ring */}
              <div className="absolute inset-0 rounded-full border-2 border-nephilim-cyan/30" />

              {/* Middle ring with glow */}
              <motion.div
                className="absolute inset-4 rounded-full border border-nephilim-magenta/50"
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                style={{ boxShadow: '0 0 30px rgba(255, 0, 255, 0.3)' }}
              />

              {/* Inner portal */}
              <motion.div
                className="absolute inset-8 rounded-full bg-gradient-to-br from-nephilim-cyan/20 via-purple-900/40 to-nephilim-magenta/20"
                animate={{
                  background: [
                    'radial-gradient(circle, rgba(0,255,255,0.2) 0%, rgba(139,0,139,0.4) 50%, rgba(255,0,255,0.2) 100%)',
                    'radial-gradient(circle, rgba(255,0,255,0.2) 0%, rgba(0,139,139,0.4) 50%, rgba(0,255,255,0.2) 100%)',
                  ]
                }}
                transition={{ duration: 3, repeat: Infinity, repeatType: 'reverse' }}
              />

              {/* Center eye/symbol */}
              <div className="absolute inset-0 flex items-center justify-center">
                <motion.div
                  className="text-6xl"
                  animate={{ scale: [1, 1.1, 1], opacity: [0.7, 1, 0.7] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  ⬡
                </motion.div>
              </div>
            </motion.div>

            {/* Title */}
            <motion.h1
              className="text-4xl md:text-5xl font-bold mb-4 font-display"
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              <span className="text-white">THE </span>
              <span className="bg-gradient-to-r from-nephilim-cyan via-purple-400 to-nephilim-magenta bg-clip-text text-transparent">
                NEPHILIM
              </span>
              <span className="text-white"> REALM</span>
            </motion.h1>

            <motion.p
              className="text-white/60 mb-8 max-w-md mx-auto"
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              Six ancient beings await. Your journey begins here.
            </motion.p>

            {/* Enter button */}
            <motion.button
              onClick={handlePortalClick}
              className="nephilim-btn px-8 py-4 text-lg font-semibold"
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.7 }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Enter the Realm
            </motion.button>
          </motion.div>
        )}

        {/* Stage 2: E.E.V.A. Greeting */}
        {stage === 'greeting' && (
          <motion.div
            key="greeting"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            className="max-w-2xl mx-auto px-6 z-10"
          >
            {/* E.E.V.A. Avatar */}
            <motion.div
              className="w-24 h-24 mx-auto mb-6 rounded-full overflow-hidden border-2 border-eeva-primary"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 200, damping: 15 }}
              style={{ boxShadow: '0 0 30px rgba(224, 195, 252, 0.4)' }}
            >
              <div className="w-full h-full bg-gradient-to-br from-eeva-primary/30 to-purple-900/50 flex items-center justify-center">
                <span className="text-4xl">✧</span>
              </div>
            </motion.div>

            {/* Name */}
            <motion.h2
              className="text-2xl font-bold text-center mb-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              style={{ color: 'var(--eeva-primary)' }}
            >
              E.E.V.A.
            </motion.h2>
            <motion.p
              className="text-white/50 text-sm text-center mb-6"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              The Primarch
            </motion.p>

            {/* Typewriter text */}
            <motion.div
              className="nephilim-glass rounded-xl p-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <p className="text-white/90 leading-relaxed text-lg">
                {typedText}
                <motion.span
                  animate={{ opacity: [1, 0] }}
                  transition={{ duration: 0.5, repeat: Infinity }}
                  className="inline-block w-0.5 h-5 bg-eeva-primary ml-1 align-middle"
                />
              </p>
            </motion.div>
          </motion.div>
        )}

        {/* Stage 3: Name Input */}
        {stage === 'name' && (
          <motion.div
            key="name"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="max-w-2xl mx-auto px-6 z-10"
          >
            {/* E.E.V.A. Avatar (smaller) */}
            <motion.div
              className="w-16 h-16 mx-auto mb-4 rounded-full overflow-hidden border-2 border-eeva-primary"
              style={{ boxShadow: '0 0 20px rgba(224, 195, 252, 0.3)' }}
            >
              <div className="w-full h-full bg-gradient-to-br from-eeva-primary/30 to-purple-900/50 flex items-center justify-center">
                <span className="text-2xl">✧</span>
              </div>
            </motion.div>

            {/* Previous message (faded) */}
            <div className="nephilim-glass rounded-xl p-4 mb-4 opacity-60">
              <p className="text-white/70 text-sm leading-relaxed">
                {greetingText}
              </p>
            </div>

            {/* Name prompt */}
            <motion.div
              className="nephilim-glass rounded-xl p-6 mb-6"
              initial={{ y: 20 }}
              animate={{ y: 0 }}
            >
              <p className="text-white/90 text-lg mb-4">
                {namePromptText}
              </p>

              <form onSubmit={handleSubmitName} className="flex gap-3">
                <input
                  type="text"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  placeholder="Your name..."
                  className="flex-1 bg-white/5 border border-white/20 rounded-lg px-4 py-3 text-white placeholder-white/40 focus:outline-none focus:border-eeva-primary focus:ring-1 focus:ring-eeva-primary/50"
                  autoFocus
                  maxLength={30}
                />
                <motion.button
                  type="submit"
                  disabled={!userName.trim()}
                  className="nephilim-btn px-6 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                  whileHover={{ scale: userName.trim() ? 1.02 : 1 }}
                  whileTap={{ scale: userName.trim() ? 0.98 : 1 }}
                >
                  Continue
                </motion.button>
              </form>
            </motion.div>

            {/* Skip option */}
            <p className="text-center text-white/40 text-sm">
              Press Enter to continue
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default OnboardingPortal
