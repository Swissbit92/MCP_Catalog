// src/pages/NephilimOnboarding.tsx
/**
 * NEPHILIM Onboarding Page
 *
 * Complete onboarding flow for new users:
 * 1. Portal Entry - Cinematic welcome
 * 2. Faction Quiz - Determine House alignment
 * 3. Persona Intro - Meet the Nephilim
 * 4. First Chat - Begin journey with chosen companion
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import NephilimBackground from '../components/NephilimBackground'
import { OnboardingPortal } from '../components/nephilim/OnboardingPortal'
import { FactionQuiz } from '../components/nephilim/FactionQuiz'
import { PersonaIntro } from '../components/nephilim/PersonaIntro'
import { SeekerRankBadge } from '../components/nephilim/SeekerRankBadge'
import {
  getSeekerProfile,
  setSeekerFaction,
  createSession,
} from '../services/api'

type OnboardingStep = 'portal' | 'quiz' | 'personas' | 'complete'

export const NephilimOnboarding: React.FC = () => {
  const navigate = useNavigate()
  const [step, setStep] = useState<OnboardingStep>('portal')
  const [userName, setUserName] = useState('')
  const [faction, setFaction] = useState('')
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [selectedPersona, setSelectedPersona] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Generate a user ID for the seeker profile
  const getUserId = () => {
    let userId = localStorage.getItem('nephilim_user_id')
    if (!userId) {
      userId = `seeker_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('nephilim_user_id', userId)
    }
    return userId
  }

  // Check if user has completed onboarding
  useEffect(() => {
    const checkOnboarding = async () => {
      const completed = localStorage.getItem('nephilim_onboarding_complete')
      if (completed === 'true') {
        // Already onboarded, redirect to home
        navigate('/')
      }
    }
    checkOnboarding()
  }, [navigate])

  // Handle portal entry (name collected)
  const handlePortalEnter = (name: string) => {
    setUserName(name)
    localStorage.setItem('nephilim_user_name', name)
    setStep('quiz')
  }

  // Handle quiz completion (faction determined)
  const handleQuizComplete = async (selectedFaction: string) => {
    setFaction(selectedFaction)
    localStorage.setItem('nephilim_faction', selectedFaction)

    // Save faction to backend
    try {
      const userId = getUserId()
      await getSeekerProfile(userId) // Ensure profile exists
      await setSeekerFaction(userId, selectedFaction)
    } catch (err) {
      console.error('Failed to save faction:', err)
      // Continue anyway, can retry later
    }

    setStep('personas')
  }

  // Handle persona selection and start first chat
  const handlePersonaSelect = async (personaKey: string) => {
    setSelectedPersona(personaKey)
    setIsLoading(true)
    setError(null)

    try {
      // Create a new chat session with the selected persona
      const session = await createSession(personaKey, `First conversation with ${personaKey.replace('nephilim_', '').toUpperCase()}`)

      // Mark onboarding as complete
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_first_persona', personaKey)

      setStep('complete')

      // Navigate to chat after a brief celebration
      setTimeout(() => {
        navigate(`/chat/${session.id}`)
      }, 3000)
    } catch (err) {
      console.error('Failed to create session:', err)
      setError('Failed to start conversation. Please try again.')
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-nephilim-void relative overflow-hidden">
      {/* Animated background */}
      <NephilimBackground />

      {/* Content */}
      <div className="relative z-10">
        <AnimatePresence mode="wait">
          {/* Step 1: Portal Entry */}
          {step === 'portal' && (
            <motion.div
              key="portal"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <OnboardingPortal onEnter={handlePortalEnter} />
            </motion.div>
          )}

          {/* Step 2: Faction Quiz */}
          {step === 'quiz' && (
            <motion.div
              key="quiz"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <FactionQuiz
                userName={userName}
                onComplete={handleQuizComplete}
              />
            </motion.div>
          )}

          {/* Step 3: Persona Introduction */}
          {step === 'personas' && (
            <motion.div
              key="personas"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {isLoading ? (
                <div className="min-h-screen flex items-center justify-center">
                  <div className="text-center">
                    <motion.div
                      className="w-16 h-16 border-4 border-nephilim-cyan border-t-transparent rounded-full mx-auto mb-4"
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    />
                    <p className="text-white/60">Preparing your journey...</p>
                  </div>
                </div>
              ) : error ? (
                <div className="min-h-screen flex items-center justify-center">
                  <div className="text-center">
                    <p className="text-red-400 mb-4">{error}</p>
                    <button
                      onClick={() => setError(null)}
                      className="nephilim-btn px-6 py-2"
                    >
                      Try Again
                    </button>
                  </div>
                </div>
              ) : (
                <PersonaIntro
                  userName={userName}
                  faction={faction}
                  onSelectPersona={handlePersonaSelect}
                />
              )}
            </motion.div>
          )}

          {/* Step 4: Completion Celebration */}
          {step === 'complete' && (
            <motion.div
              key="complete"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="min-h-screen flex items-center justify-center"
            >
              <div className="text-center max-w-md px-4">
                {/* Celebration animation */}
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 200, damping: 15 }}
                  className="mb-6"
                >
                  <div className="w-24 h-24 mx-auto rounded-full bg-gradient-to-br from-nephilim-cyan to-nephilim-magenta flex items-center justify-center">
                    <span className="text-4xl">✨</span>
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <h2 className="text-3xl font-bold text-white mb-2 font-display">
                    Welcome, {userName}
                  </h2>
                  <p className="text-white/60 mb-4">
                    You are now an Initiate of the Nephilim Realm
                  </p>

                  <div className="flex justify-center mb-6">
                    <SeekerRankBadge rank="Initiate" size="lg" />
                  </div>

                  <p className="text-white/50 text-sm">
                    Entering your first conversation...
                  </p>

                  {/* Loading spinner */}
                  <motion.div
                    className="w-8 h-8 border-2 border-nephilim-cyan border-t-transparent rounded-full mx-auto mt-4"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  />
                </motion.div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Progress indicator (visible during quiz and personas) */}
      {(step === 'quiz' || step === 'personas') && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
          {['portal', 'quiz', 'personas'].map((s, idx) => (
            <div
              key={s}
              className={`
                w-2 h-2 rounded-full transition-all duration-300
                ${['portal', 'quiz', 'personas'].indexOf(step) >= idx
                  ? 'bg-nephilim-cyan'
                  : 'bg-white/20'}
              `}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default NephilimOnboarding
