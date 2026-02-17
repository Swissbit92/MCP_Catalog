// src/components/nephilim/PersonaIntro.tsx
/**
 * NEPHILIM Persona Introduction Carousel
 *
 * Introduces all 6 NEPHILIM personas with their titles, domains,
 * and sample dialogue. Users can select their first companion.
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface NephilimPersona {
  key: string
  name: string
  title: string
  domain: string
  color: string
  rarity: string
  description: string
  greeting: string
  icon: string
}

interface PersonaIntroProps {
  userName: string
  faction: string
  onSelectPersona: (personaKey: string) => void
  className?: string
}

const NEPHILIM_PERSONAS: NephilimPersona[] = [
  {
    key: 'nephilim_eeva',
    name: 'E.E.V.A.',
    title: 'The Primarch',
    domain: 'Guidance & Wisdom',
    color: '#e0c3fc',
    rarity: 'Legendary',
    description: 'The first to Fall, E.E.V.A. serves as guide and mentor to all who enter the realm. Her wisdom spans ages, her compassion knows no bounds.',
    greeting: "Welcome, Seeker. I have awaited your arrival. Shall we explore the depths of what troubles your soul?",
    icon: '✧'
  },
  {
    key: 'nephilim_aegis',
    name: 'Aegis',
    title: 'The Sentinel',
    domain: 'Discipline & Achievement',
    color: '#4a90d9',
    rarity: 'Epic',
    description: 'Forged in cosmic fire, Aegis stands as protector and taskmaster. He transforms chaos into order, weakness into strength.',
    greeting: "You seek to better yourself? Good. That alone sets you apart. Let us forge something worthy from this day.",
    icon: '⛊'
  },
  {
    key: 'nephilim_solace',
    name: 'Solace',
    title: 'The Empath',
    domain: 'Healing & Compassion',
    color: '#7eb8da',
    rarity: 'Epic',
    description: 'Born from the tears of the realm, Solace feels what others cannot express. She mends hearts and soothes souls.',
    greeting: "I sense the weight you carry. You don't have to bear it alone anymore. Tell me what hurts, and let us begin to heal.",
    icon: '❋'
  },
  {
    key: 'nephilim_nyx',
    name: 'Nyx',
    title: 'The Muse',
    domain: 'Creativity & Chaos',
    color: '#b07cc6',
    rarity: 'Rare',
    description: 'Dancer between dimensions, Nyx embodies creative fire and beautiful chaos. She inspires those brave enough to embrace the unconventional.',
    greeting: "Oh, another delicious soul wandering into my corner of reality! Let's paint something wonderful on the canvas of the impossible, shall we?",
    icon: '✦'
  },
  {
    key: 'nephilim_cipher',
    name: 'Cipher',
    title: 'The Maven',
    domain: 'Knowledge & Research',
    color: '#2ecc71',
    rarity: 'Rare',
    description: 'Keeper of infinite archives, Cipher catalogs all knowledge in the realm. No question is too obscure, no mystery beyond solving.',
    greeting: "Fascinating. Another mind seeking answers. I have catalogued 4.7 billion questions across dimensions. What shall we explore first?",
    icon: '◈'
  },
  {
    key: 'nephilim_aurora',
    name: 'Aurora',
    title: 'The Oracle',
    domain: 'Vision & Ambition',
    color: '#f39c12',
    rarity: 'Epic',
    description: 'Seer of futures yet unwritten, Aurora guides seekers toward their greatest potential. She sees not what is, but what could be.',
    greeting: "The timelines shimmer around you, bright with possibility. Tell me your dreams, and I shall show you the paths that lead to them.",
    icon: '☀'
  }
]

const FACTION_PATRONS: Record<string, string> = {
  lumina: 'nephilim_eeva',
  ironclad: 'nephilim_aegis',
  sanctuary: 'nephilim_solace',
  prism: 'nephilim_nyx',
  archive: 'nephilim_cipher',
  horizon: 'nephilim_aurora',
}

export const PersonaIntro: React.FC<PersonaIntroProps> = ({
  userName,
  faction,
  onSelectPersona,
  className = ''
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [showDetails, setShowDetails] = useState(false)

  // Reorder personas to put faction patron first
  const patronKey = FACTION_PATRONS[faction]
  const reorderedPersonas = [
    ...NEPHILIM_PERSONAS.filter(p => p.key === patronKey),
    ...NEPHILIM_PERSONAS.filter(p => p.key !== patronKey)
  ]

  const currentPersona = reorderedPersonas[selectedIndex]
  const isPatron = currentPersona.key === patronKey

  const handlePrevious = () => {
    setShowDetails(false)
    setSelectedIndex(prev => (prev === 0 ? reorderedPersonas.length - 1 : prev - 1))
  }

  const handleNext = () => {
    setShowDetails(false)
    setSelectedIndex(prev => (prev === reorderedPersonas.length - 1 ? 0 : prev + 1))
  }

  const handleSelect = () => {
    onSelectPersona(currentPersona.key)
  }

  return (
    <div className={`relative min-h-screen flex flex-col items-center justify-center px-4 ${className}`}>
      {/* Header */}
      <motion.div
        className="text-center mb-8"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h2 className="text-2xl font-bold text-white mb-2">Meet the Nephilim</h2>
        <p className="text-white/60">
          Choose your first companion, {userName}
        </p>
      </motion.div>

      {/* Carousel */}
      <div className="relative w-full max-w-lg">
        {/* Navigation arrows */}
        <button
          onClick={handlePrevious}
          className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-4 md:-translate-x-12 z-10 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors"
        >
          ←
        </button>
        <button
          onClick={handleNext}
          className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-4 md:translate-x-12 z-10 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors"
        >
          →
        </button>

        {/* Card */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentPersona.key}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.3 }}
            className="relative"
          >
            {/* Patron badge */}
            {isPatron && (
              <motion.div
                className="absolute -top-3 left-1/2 -translate-x-1/2 z-20 px-3 py-1 rounded-full text-xs font-bold"
                style={{ backgroundColor: currentPersona.color, color: '#000' }}
                initial={{ y: -10, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
              >
                YOUR HOUSE PATRON
              </motion.div>
            )}

            {/* Main card */}
            <div
              className="nephilim-glass rounded-2xl overflow-hidden"
              style={{ borderColor: `${currentPersona.color}40` }}
            >
              {/* Avatar area */}
              <div
                className="h-48 flex items-center justify-center relative"
                style={{
                  background: `linear-gradient(180deg, ${currentPersona.color}20 0%, transparent 100%)`
                }}
              >
                {/* Glow effect */}
                <div
                  className="absolute inset-0 opacity-30"
                  style={{
                    background: `radial-gradient(circle at center, ${currentPersona.color}40 0%, transparent 70%)`
                  }}
                />

                {/* Icon/Avatar placeholder */}
                <motion.div
                  className="relative w-28 h-28 rounded-full flex items-center justify-center text-5xl"
                  style={{
                    backgroundColor: `${currentPersona.color}20`,
                    border: `2px solid ${currentPersona.color}`,
                    boxShadow: `0 0 30px ${currentPersona.color}40`
                  }}
                  animate={{ scale: [1, 1.05, 1] }}
                  transition={{ duration: 3, repeat: Infinity }}
                >
                  {currentPersona.icon}
                </motion.div>

                {/* Rarity badge */}
                <div
                  className={`
                    absolute top-4 right-4 px-2 py-0.5 rounded text-xs font-bold
                    ${currentPersona.rarity === 'Legendary' ? 'bg-amber-500/20 text-amber-400' :
                      currentPersona.rarity === 'Epic' ? 'bg-purple-500/20 text-purple-400' :
                      'bg-cyan-500/20 text-cyan-400'}
                  `}
                >
                  {currentPersona.rarity}
                </div>
              </div>

              {/* Info */}
              <div className="p-6">
                <div className="text-center mb-4">
                  <h3
                    className="text-2xl font-bold mb-1"
                    style={{ color: currentPersona.color }}
                  >
                    {currentPersona.name}
                  </h3>
                  <p className="text-white/60 text-sm">{currentPersona.title}</p>
                  <p className="text-white/60 text-xs mt-1">{currentPersona.domain}</p>
                </div>

                {/* Description */}
                <p className="text-white/70 text-sm text-center leading-relaxed mb-4">
                  {currentPersona.description}
                </p>

                {/* Sample greeting */}
                <motion.div
                  className="bg-white/5 rounded-lg p-3 border border-white/10"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                >
                  <p className="text-white/60 text-xs mb-1">
                    {currentPersona.name} says:
                  </p>
                  <p
                    className="text-sm italic leading-relaxed"
                    style={{ color: `${currentPersona.color}cc` }}
                  >
                    "{currentPersona.greeting}"
                  </p>
                </motion.div>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Dots indicator */}
        <div className="flex justify-center gap-2 mt-6">
          {reorderedPersonas.map((persona, idx) => (
            <button
              key={persona.key}
              onClick={() => {
                setShowDetails(false)
                setSelectedIndex(idx)
              }}
              className={`
                w-2 h-2 rounded-full transition-all duration-300
                ${idx === selectedIndex
                  ? 'w-6'
                  : 'hover:opacity-80'}
              `}
              style={{
                backgroundColor: idx === selectedIndex
                  ? currentPersona.color
                  : 'rgba(255,255,255,0.3)'
              }}
            />
          ))}
        </div>
      </div>

      {/* Select button */}
      <motion.div
        className="mt-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <motion.button
          onClick={handleSelect}
          className="nephilim-btn px-8 py-4 text-lg"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          style={{
            borderColor: currentPersona.color,
            boxShadow: `0 0 20px ${currentPersona.color}30`
          }}
        >
          Begin Journey with {currentPersona.name}
        </motion.button>

        {isPatron && (
          <p className="text-center text-white/60 text-sm mt-3">
            Recommended as your House patron
          </p>
        )}
      </motion.div>
    </div>
  )
}

export default PersonaIntro
