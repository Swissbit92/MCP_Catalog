import React, { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { usePersona } from '../context/PersonaContext'
import { useAudio } from '../context/AudioContext'
import { Persona } from '../types/personas'

type SummoningPhase = 'idle' | 'commitment' | 'anticipation' | 'rarity_gate' | 'identity_reveal' | 'celebration'

interface SummoningRitualProps {
  onCharacterSelect: (personaKey: string) => void
}

const ORDER_WEIGHTS = {
  wanderer: 50,
  sage: 30,
  warden: 15,
  archon: 5,
}

const ORDER_COLORS: Record<string, string> = {
  wanderer: '#C0C0C0',
  sage: '#00BFFF',
  warden: '#DA70D6',
  archon: '#FFD700',
}

const ORDER_LABELS: Record<string, string> = {
  wanderer: 'Wanderer',
  sage: 'Sage',
  warden: 'Warden',
  archon: 'Archon',
}

const SOFT_PITY_THRESHOLD = 5
const HARD_PITY_THRESHOLD = 10

const SummoningRitual: React.FC<SummoningRitualProps> = ({ onCharacterSelect }) => {
  const { personas, addToCollection, addPullRecord, isCollected } = usePersona()
  const {
    playCommitSound,
    playAnticipationSound,
    playRarityRevealSound,
    playIdentityRevealSound,
    playCelebrationSound,
  } = useAudio()

  const [phase, setPhase] = useState<SummoningPhase>('idle')
  const [holdProgress, setHoldProgress] = useState(0)
  const [pulledCharacter, setPulledCharacter] = useState<Persona | null>(null)
  const [isDuplicate, setIsDuplicate] = useState(false)
  const [revealedOrder, setRevealedOrder] = useState<string | null>(null)
  const [nameRevealIndex, setNameRevealIndex] = useState(0)

  // Pity system
  const [pityCounter, setPityCounter] = useState<number>(() => {
    const stored = localStorage.getItem('nephilim_pity_counter')
    return stored ? parseInt(stored, 10) : 0
  })

  const holdTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const holdStartRef = useRef<number>(0)
  const animationFrameRef = useRef<number>(0)
  const isHoldingRef = useRef(false)

  // Save pity counter to localStorage
  useEffect(() => {
    localStorage.setItem('nephilim_pity_counter', String(pityCounter))
  }, [pityCounter])

  // Name reveal animation
  useEffect(() => {
    if (phase === 'identity_reveal' && pulledCharacter) {
      const name = pulledCharacter.display_name
      let idx = 0
      const interval = setInterval(() => {
        idx++
        setNameRevealIndex(idx)
        if (idx >= name.length) {
          clearInterval(interval)
        }
      }, 60)
      return () => clearInterval(interval)
    }
  }, [phase, pulledCharacter])

  const getGuaranteedNewCount = useCallback(() => {
    return HARD_PITY_THRESHOLD - pityCounter
  }, [pityCounter])

  const selectWeightedOrder = useCallback((): string => {
    const weights = { ...ORDER_WEIGHTS }

    // Soft pity: boost rarer weights after threshold
    if (pityCounter >= SOFT_PITY_THRESHOLD) {
      const pityBonus = (pityCounter - SOFT_PITY_THRESHOLD + 1) * 5
      weights.sage += pityBonus
      weights.warden += Math.floor(pityBonus / 2)
      weights.archon += Math.floor(pityBonus / 3)
      weights.wanderer = Math.max(10, weights.wanderer - pityBonus)
    }

    const totalWeight = Object.values(weights).reduce((sum, w) => sum + w, 0)
    let roll = Math.random() * totalWeight

    for (const [order, weight] of Object.entries(weights)) {
      roll -= weight
      if (roll <= 0) return order
    }
    return 'wanderer'
  }, [pityCounter])

  const selectPersona = useCallback((): Persona | null => {
    if (personas.length === 0) return null

    const isHardPity = pityCounter >= HARD_PITY_THRESHOLD - 1
    const selectedOrder = selectWeightedOrder()
    // Filter by celestial_order (prefer it over rarity-based mapping)
    let candidates = personas.filter(p => (p.celestial_order || 'wanderer') === selectedOrder)
    if (candidates.length === 0) {
      candidates = personas
    }

    // Hard pity: guarantee unowned
    if (isHardPity) {
      const unownedCandidates = personas.filter(p => !isCollected(p.key))
      if (unownedCandidates.length > 0) {
        candidates = unownedCandidates
      }
    }
    // Soft pity: prefer unowned
    else if (pityCounter >= SOFT_PITY_THRESHOLD) {
      const unownedInRarity = candidates.filter(p => !isCollected(p.key))
      if (unownedInRarity.length > 0) {
        candidates = unownedInRarity
      }
    }

    const randomIndex = Math.floor(Math.random() * candidates.length)
    return candidates[randomIndex]
  }, [personas, pityCounter, selectWeightedOrder, isCollected])

  const runSummoningSequence = useCallback(async () => {
    const character = selectPersona()
    if (!character) return

    const duplicate = isCollected(character.key)
    setIsDuplicate(duplicate)
    setPulledCharacter(character)

    // Phase 2: Anticipation (2-4s)
    setPhase('anticipation')
    playAnticipationSound()
    const anticipationDuration = 2000 + Math.random() * 2000
    await new Promise(resolve => setTimeout(resolve, anticipationDuration))

    // Phase 3: Rarity Gate (0.8s)
    const order = character.celestial_order || 'wanderer'
    setRevealedOrder(order)
    setPhase('rarity_gate')
    playRarityRevealSound(order)
    await new Promise(resolve => setTimeout(resolve, 800))

    // Phase 4: Identity Reveal (1-2s)
    setPhase('identity_reveal')
    setNameRevealIndex(0)
    playIdentityRevealSound()
    const revealDuration = 1000 + Math.random() * 1000
    await new Promise(resolve => setTimeout(resolve, revealDuration))

    // Phase 5: Celebration (1-3s)
    setPhase('celebration')
    playCelebrationSound(character.celestial_order || 'wanderer')

    // Record the pull
    addPullRecord({
      personaKey: character.key,
      rarity: character.rarity,
      celestial_order: character.celestial_order,
      pullCount: 1,
    })

    // Update pity counter
    if (!duplicate) {
      setPityCounter(0)
    } else {
      setPityCounter(prev => prev + 1)
    }

    // Auto-add to collection
    addToCollection(character.key)
  }, [
    selectPersona, isCollected, addPullRecord, addToCollection,
    playAnticipationSound, playRarityRevealSound, playIdentityRevealSound, playCelebrationSound,
  ])

  const handlePointerDown = useCallback(() => {
    if (phase !== 'idle') return

    isHoldingRef.current = true
    holdStartRef.current = Date.now()
    setHoldProgress(0)

    playCommitSound()

    const updateProgress = () => {
      if (!isHoldingRef.current) return

      const elapsed = Date.now() - holdStartRef.current
      const progress = Math.min(elapsed / 300, 1)
      setHoldProgress(progress)

      if (progress >= 1) {
        // Threshold met: begin summoning
        isHoldingRef.current = false
        setPhase('commitment')
        // Brief commitment phase before sequence
        setTimeout(() => {
          runSummoningSequence()
        }, 500)
        return
      }

      animationFrameRef.current = requestAnimationFrame(updateProgress)
    }

    animationFrameRef.current = requestAnimationFrame(updateProgress)
  }, [phase, playCommitSound, runSummoningSequence])

  const handlePointerUp = useCallback(() => {
    isHoldingRef.current = false
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
    }
    // If not yet committed, reset
    if (phase === 'idle') {
      setHoldProgress(0)
    }
  }, [phase])

  const handleReset = useCallback(() => {
    setPhase('idle')
    setPulledCharacter(null)
    setRevealedOrder(null)
    setIsDuplicate(false)
    setHoldProgress(0)
    setNameRevealIndex(0)
  }, [])

  const handleAcceptBond = useCallback(() => {
    if (pulledCharacter) {
      onCharacterSelect(pulledCharacter.key)
    }
    handleReset()
  }, [pulledCharacter, onCharacterSelect, handleReset])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      const timer = holdTimerRef.current
      if (timer) {
        clearInterval(timer)
      }
    }
  }, [])

  const rarityColor = revealedOrder ? ORDER_COLORS[revealedOrder] : ORDER_COLORS.wanderer
  const circumference = 2 * Math.PI * 58

  return (
    <div className="min-h-screen bg-[#0B0B0D] flex flex-col relative overflow-hidden">
      {/* Summoning circle CSS animations */}
      <style>{`
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes spin-reverse {
          from { transform: rotate(360deg); }
          to { transform: rotate(0deg); }
        }
        @keyframes pulse-glow {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.8; }
        }
        @keyframes energy-stream {
          0% { transform: scale(2); opacity: 0; }
          50% { opacity: 0.6; }
          100% { transform: scale(0.5); opacity: 0; }
        }
        @keyframes streak-launch {
          0% { transform: translateY(0) scaleY(1); opacity: 0; }
          20% { opacity: 1; }
          100% { transform: translateY(-200vh) scaleY(3); opacity: 0; }
        }
        @keyframes sigil-expand {
          0% { transform: scale(0) rotate(0deg); opacity: 0; }
          50% { opacity: 1; }
          100% { transform: scale(1) rotate(180deg); opacity: 0.9; }
        }
        @keyframes sweep-reveal {
          0% { clip-path: inset(0 100% 0 0); filter: brightness(0); }
          100% { clip-path: inset(0 0 0 0); filter: brightness(1); }
        }
        @keyframes particle-burst {
          0% { transform: translate(0, 0) scale(1); opacity: 1; }
          100% { transform: translate(var(--tx), var(--ty)) scale(0); opacity: 0; }
        }
        @keyframes cosmic-ring {
          0% { transform: scale(0); opacity: 0.8; border-width: 4px; }
          100% { transform: scale(4); opacity: 0; border-width: 1px; }
        }
        .summoning-circle {
          animation: spin-slow 8s linear infinite;
        }
        .summoning-circle-inner {
          animation: spin-reverse 6s linear infinite;
        }
        @media (prefers-reduced-motion: reduce) {
          .summoning-circle,
          .summoning-circle-inner { animation: none; }
          * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
          }
        }
      `}</style>

      {/* Dimming overlay for active phases */}
      <AnimatePresence>
        {(phase === 'anticipation' || phase === 'rarity_gate') && (
          <motion.div
            className="absolute inset-0 bg-black/80 z-20"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          />
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="text-center py-8 px-4 relative z-10">
        <h1 className="text-4xl md:text-5xl font-nephilim font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-cyan-400 mb-3">
          Summoning Ritual
        </h1>
        <p className="text-lg text-gray-300 max-w-2xl mx-auto">
          Invoke the ancient bonds and call forth a companion from the void
        </p>
      </div>

      {/* Main Summoning Area */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 pb-8 relative z-30">
        <AnimatePresence mode="wait">
          {/* IDLE / COMMITMENT PHASE */}
          {(phase === 'idle' || phase === 'commitment') && (
            <motion.div
              key="invoke"
              className="text-center space-y-8"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              {/* Summoning Circle */}
              <div className="relative w-64 h-64 mx-auto flex items-center justify-center">
                {/* Outer ring */}
                <svg
                  className="absolute inset-0 w-full h-full summoning-circle"
                  viewBox="0 0 256 256"
                  style={{
                    animationDuration: phase === 'commitment' ? '2s' : '8s'
                  }}
                >
                  <circle
                    cx="128"
                    cy="128"
                    r="120"
                    fill="none"
                    stroke="rgba(0, 255, 255, 0.15)"
                    strokeWidth="1"
                  />
                  <circle
                    cx="128"
                    cy="128"
                    r="110"
                    fill="none"
                    stroke="rgba(0, 255, 255, 0.1)"
                    strokeWidth="0.5"
                    strokeDasharray="8 4"
                  />
                  {/* Runic markers */}
                  {[0, 60, 120, 180, 240, 300].map((angle) => (
                    <circle
                      key={angle}
                      cx={128 + 115 * Math.cos((angle * Math.PI) / 180)}
                      cy={128 + 115 * Math.sin((angle * Math.PI) / 180)}
                      r="3"
                      fill="rgba(0, 255, 255, 0.4)"
                    />
                  ))}
                </svg>

                {/* Inner ring */}
                <svg
                  className="absolute inset-0 w-full h-full summoning-circle-inner"
                  viewBox="0 0 256 256"
                  style={{
                    animationDuration: phase === 'commitment' ? '1.5s' : '6s'
                  }}
                >
                  <polygon
                    points="128,48 198,168 58,168"
                    fill="none"
                    stroke="rgba(255, 0, 255, 0.12)"
                    strokeWidth="1"
                  />
                  <polygon
                    points="128,208 58,88 198,88"
                    fill="none"
                    stroke="rgba(0, 255, 255, 0.12)"
                    strokeWidth="1"
                  />
                </svg>

                {/* Hold-to-invoke button */}
                <div className="relative">
                  <motion.button
                    className="relative w-32 h-32 rounded-full flex items-center justify-center select-none touch-none"
                    style={{
                      background: 'radial-gradient(circle, rgba(0,255,255,0.15) 0%, rgba(0,0,0,0.8) 70%)',
                      boxShadow: holdProgress > 0
                        ? `0 0 ${30 + holdProgress * 40}px rgba(0,255,255,${0.2 + holdProgress * 0.4})`
                        : '0 0 30px rgba(0,255,255,0.2)',
                    }}
                    animate={phase === 'commitment' ? {
                      scale: [1, 1.1, 1.05],
                    } : {}}
                    transition={{ duration: 0.5, repeat: phase === 'commitment' ? Infinity : 0 }}
                    onPointerDown={handlePointerDown}
                    onPointerUp={handlePointerUp}
                    onPointerLeave={handlePointerUp}
                    aria-label="Hold to invoke summoning"
                  >
                    {/* Progress ring */}
                    <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 128 128">
                      {/* Background ring */}
                      <circle
                        cx="64"
                        cy="64"
                        r="58"
                        fill="none"
                        stroke="rgba(0,255,255,0.1)"
                        strokeWidth="3"
                      />
                      {/* Progress ring */}
                      <circle
                        cx="64"
                        cy="64"
                        r="58"
                        fill="none"
                        stroke="rgba(0,255,255,0.8)"
                        strokeWidth="3"
                        strokeDasharray={circumference}
                        strokeDashoffset={circumference * (1 - holdProgress)}
                        strokeLinecap="round"
                        style={{ transition: 'stroke-dashoffset 0.05s linear' }}
                      />
                    </svg>

                    {/* Button content */}
                    <div className="relative z-10 text-center">
                      {phase === 'commitment' ? (
                        <motion.div
                          animate={{ opacity: [0.5, 1, 0.5] }}
                          transition={{ duration: 1, repeat: Infinity }}
                        >
                          <div className="text-cyan-400 font-nephilim text-sm tracking-widest">
                            INVOKING
                          </div>
                        </motion.div>
                      ) : (
                        <>
                          <div className="text-cyan-400 font-nephilim text-lg tracking-wider mb-1">
                            Invoke
                          </div>
                          <div className="text-gray-500 text-xs">
                            Hold to summon
                          </div>
                        </>
                      )}
                    </div>
                  </motion.button>

                  {/* Pulsing glow behind button */}
                  <motion.div
                    className="absolute inset-0 rounded-full pointer-events-none"
                    style={{
                      background: 'radial-gradient(circle, rgba(0,255,255,0.2) 0%, transparent 70%)',
                    }}
                    animate={{ opacity: [0.3, 0.7, 0.3], scale: [1, 1.15, 1] }}
                    transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                  />
                </div>
              </div>

              {/* Pity info */}
              <div className="text-gray-400 text-sm">
                Guaranteed new in: <span className="text-cyan-400 font-semibold">{getGuaranteedNewCount()}</span> more invocations
              </div>
            </motion.div>
          )}

          {/* ANTICIPATION PHASE */}
          {phase === 'anticipation' && (
            <motion.div
              key="anticipation"
              className="relative flex items-center justify-center w-full h-64"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {/* Energy streams */}
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                {[...Array(6)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="absolute w-64 h-64 rounded-full"
                    style={{
                      background: `radial-gradient(circle, rgba(0,255,255,0.15) 0%, transparent 70%)`,
                    }}
                    initial={{ scale: 2.5, opacity: 0 }}
                    animate={{
                      scale: [2.5, 0.5],
                      opacity: [0, 0.4, 0],
                    }}
                    transition={{
                      duration: 2,
                      delay: i * 0.3,
                      repeat: Infinity,
                      ease: 'easeIn',
                    }}
                  />
                ))}
              </div>

              {/* Center convergence point */}
              <motion.div
                className="w-4 h-4 rounded-full bg-cyan-400"
                animate={{
                  scale: [0.5, 1.5, 0.5],
                  opacity: [0.3, 1, 0.3],
                  boxShadow: [
                    '0 0 10px rgba(0,255,255,0.3)',
                    '0 0 40px rgba(0,255,255,0.8)',
                    '0 0 10px rgba(0,255,255,0.3)',
                  ],
                }}
                transition={{ duration: 1, repeat: Infinity }}
              />

              {/* Ascending text */}
              <motion.div
                className="absolute bottom-8 text-gray-400 font-nephilim text-sm tracking-[0.3em]"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                CHANNELING THE VOID
              </motion.div>
            </motion.div>
          )}

          {/* RARITY GATE PHASE */}
          {phase === 'rarity_gate' && revealedOrder && (
            <motion.div
              key="rarity-gate"
              className="relative flex flex-col items-center justify-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {/* Rarity sigil */}
              <motion.div
                className="relative"
                initial={{ scale: 0, rotate: 0 }}
                animate={{ scale: [0, 1.3, 1], rotate: [0, 180] }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              >
                {/* Glow background */}
                <div
                  className="w-40 h-40 rounded-full flex items-center justify-center"
                  style={{
                    background: `radial-gradient(circle, ${rarityColor}33 0%, transparent 70%)`,
                    boxShadow: `0 0 80px ${rarityColor}66`,
                  }}
                >
                  {/* Sigil shape */}
                  <svg width="100" height="100" viewBox="0 0 100 100">
                    <polygon
                      points="50,5 95,27.5 95,72.5 50,95 5,72.5 5,27.5"
                      fill="none"
                      stroke={rarityColor}
                      strokeWidth="2"
                      opacity="0.8"
                    />
                    <polygon
                      points="50,20 80,35 80,65 50,80 20,65 20,35"
                      fill="none"
                      stroke={rarityColor}
                      strokeWidth="1.5"
                      opacity="0.5"
                    />
                    <circle cx="50" cy="50" r="15" fill={rarityColor} opacity="0.3" />
                  </svg>
                </div>
              </motion.div>

              {/* Rarity label */}
              <motion.div
                className="mt-6 font-nephilim text-2xl tracking-[0.4em] uppercase"
                style={{ color: rarityColor }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.4 }}
              >
                {ORDER_LABELS[revealedOrder]}
              </motion.div>
            </motion.div>
          )}

          {/* IDENTITY REVEAL PHASE */}
          {phase === 'identity_reveal' && pulledCharacter && (
            <motion.div
              key="identity-reveal"
              className="relative flex flex-col items-center justify-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {/* Character image with silhouette-to-reveal */}
              <div className="relative w-48 h-64 mb-6 overflow-hidden rounded-xl">
                {/* Silhouette layer */}
                <img
                  src={`/images/${pulledCharacter.image}`}
                  alt=""
                  className="absolute inset-0 w-full h-full object-cover"
                  style={{ filter: 'brightness(0)' }}
                />

                {/* Revealed layer with sweep */}
                <motion.div
                  className="absolute inset-0"
                  initial={{ clipPath: 'inset(0 100% 0 0)' }}
                  animate={{ clipPath: 'inset(0 0% 0 0)' }}
                  transition={{ duration: 1, ease: 'easeInOut' }}
                >
                  <img
                    src={`/images/${pulledCharacter.image}`}
                    alt={pulledCharacter.display_name}
                    className="w-full h-full object-cover"
                  />
                </motion.div>

                {/* Light sweep overlay */}
                <motion.div
                  className="absolute inset-0 pointer-events-none"
                  style={{
                    background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%)',
                    mixBlendMode: 'overlay',
                  }}
                  initial={{ x: '-100%' }}
                  animate={{ x: '100%' }}
                  transition={{ duration: 1, ease: 'easeInOut' }}
                />

                {/* Order border glow */}
                <div
                  className="absolute inset-0 rounded-xl pointer-events-none"
                  style={{
                    border: `2px solid ${rarityColor}`,
                    boxShadow: `inset 0 0 20px ${rarityColor}33, 0 0 20px ${rarityColor}33`,
                  }}
                />
              </div>

              {/* Name with staggered letter reveal */}
              <div className="font-nephilim text-2xl md:text-3xl tracking-wider">
                {pulledCharacter.display_name.split('').map((letter, i) => (
                  <motion.span
                    key={i}
                    style={{ color: rarityColor }}
                    initial={{ opacity: 0, y: 10 }}
                    animate={i < nameRevealIndex ? { opacity: 1, y: 0 } : {}}
                    transition={{ duration: 0.1 }}
                  >
                    {letter}
                  </motion.span>
                ))}
              </div>
            </motion.div>
          )}

          {/* CELEBRATION PHASE */}
          {phase === 'celebration' && pulledCharacter && (
            <motion.div
              key="celebration"
              className="relative flex flex-col items-center justify-center text-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {/* Particle burst */}
              <div className="absolute inset-0 pointer-events-none overflow-hidden">
                {[...Array(revealedOrder === 'archon' ? 30 : revealedOrder === 'warden' ? 20 : 12)].map((_, i) => {
                  const angle = (i / (revealedOrder === 'archon' ? 30 : revealedOrder === 'warden' ? 20 : 12)) * Math.PI * 2
                  const distance = 150 + Math.random() * 200
                  return (
                    <motion.div
                      key={i}
                      className="absolute left-1/2 top-1/2 w-2 h-2 rounded-full"
                      style={{
                        backgroundColor: rarityColor,
                        boxShadow: `0 0 6px ${rarityColor}`,
                      }}
                      initial={{ x: 0, y: 0, scale: 1, opacity: 1 }}
                      animate={{
                        x: Math.cos(angle) * distance,
                        y: Math.sin(angle) * distance,
                        scale: 0,
                        opacity: 0,
                      }}
                      transition={{
                        duration: 1.5 + Math.random(),
                        delay: Math.random() * 0.3,
                        ease: 'easeOut',
                      }}
                    />
                  )
                })}

                {/* Archon cosmic rings */}
                {revealedOrder === 'archon' && (
                  <>
                    {[0, 0.3, 0.6].map((delay, i) => (
                      <motion.div
                        key={`ring-${i}`}
                        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border-2"
                        style={{ borderColor: rarityColor, width: 20, height: 20 }}
                        initial={{ scale: 0, opacity: 0.8 }}
                        animate={{ scale: 6, opacity: 0 }}
                        transition={{ duration: 2, delay, ease: 'easeOut' }}
                      />
                    ))}
                  </>
                )}
              </div>

              {/* Character card area */}
              <motion.div
                className="relative mb-6"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: 'spring', stiffness: 200, damping: 15 }}
              >
                <div className="relative w-48 h-64 rounded-xl overflow-hidden">
                  <img
                    src={`/images/${pulledCharacter.image}`}
                    alt={pulledCharacter.display_name}
                    className="w-full h-full object-cover"
                  />
                  <div
                    className="absolute inset-0 rounded-xl pointer-events-none"
                    style={{
                      border: `2px solid ${rarityColor}`,
                      boxShadow: `inset 0 0 30px ${rarityColor}33, 0 0 30px ${rarityColor}33`,
                    }}
                  />
                </div>
              </motion.div>

              {/* Name */}
              <motion.h2
                className="font-nephilim text-3xl tracking-wider mb-2"
                style={{ color: rarityColor }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                {pulledCharacter.display_name}
              </motion.h2>

              {/* Rarity badge */}
              <motion.div
                className="font-nephilim text-sm tracking-[0.3em] uppercase mb-4"
                style={{ color: rarityColor, opacity: 0.8 }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.8 }}
                transition={{ delay: 0.4 }}
              >
                {revealedOrder ? ORDER_LABELS[revealedOrder] : ORDER_LABELS.wanderer}
              </motion.div>

              {/* Bond status */}
              <motion.div
                className="mb-6"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                {isDuplicate ? (
                  <div className="space-y-2">
                    <div className="text-fuchsia-400 font-nephilim text-xl tracking-wider">
                      Bond Deepened
                    </div>
                    <div className="text-gray-400 text-sm">
                      +10 Resonance — Your bond with {pulledCharacter.display_name} grows stronger
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="text-cyan-400 font-nephilim text-xl tracking-wider">
                      New Bond Forged
                    </div>
                    <div className="text-gray-400 text-sm">
                      A new companion has answered your call
                    </div>
                  </div>
                )}
              </motion.div>

              {/* Action Buttons */}
              <motion.div
                className="flex gap-4"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 }}
              >
                <motion.button
                  onClick={handleAcceptBond}
                  className="px-8 py-3 rounded-full font-nephilim text-sm tracking-wider border border-cyan-400/50 text-cyan-400 bg-cyan-400/10 hover:bg-cyan-400/20 transition-colors"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  Accept Bond
                </motion.button>
                <motion.button
                  onClick={handleReset}
                  className="px-8 py-3 rounded-full font-nephilim text-sm tracking-wider border border-white/10 text-gray-400 bg-white/[0.05] hover:bg-white/10 transition-colors"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  Invoke Again
                </motion.button>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Transparent Odds Display */}
      <div className="relative z-10 max-w-lg mx-auto px-4 pb-8">
        <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-5">
          <h3 className="font-nephilim text-sm tracking-[0.2em] text-gray-300 mb-3">
            Current Invocation Rates
          </h3>
          <div className="flex items-center justify-between text-sm mb-3">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: ORDER_COLORS.wanderer }} />
              <span className="text-gray-400">Wanderer:</span>
              <span className="text-gray-200">{ORDER_WEIGHTS.wanderer}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: ORDER_COLORS.sage }} />
              <span className="text-gray-400">Sage:</span>
              <span className="text-gray-200">{ORDER_WEIGHTS.sage}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: ORDER_COLORS.warden }} />
              <span className="text-gray-400">Warden:</span>
              <span className="text-gray-200">{ORDER_WEIGHTS.warden}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: ORDER_COLORS.archon }} />
              <span className="text-gray-400">Archon:</span>
              <span className="text-gray-200">{ORDER_WEIGHTS.archon}%</span>
            </div>
          </div>
          <div className="text-xs text-gray-500 border-t border-white/[0.05] pt-2">
            Guaranteed new in: <span className="text-cyan-400">{getGuaranteedNewCount()}</span> more invocations
            {pityCounter >= SOFT_PITY_THRESHOLD && (
              <span className="ml-2 text-fuchsia-400">(Soft pity active)</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default SummoningRitual
