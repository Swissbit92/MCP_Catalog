import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import NephilimBackground from '../components/NephilimBackground'
import { useAuth } from '../context/AuthContext'

/** The six Nephilim with their core info */
const NEPHILIM = [
  {
    key: 'nephilim_eeva',
    name: 'E.E.V.A.',
    title: 'The Primarch',
    domain: 'Guidance & Wisdom',
    color: '#e0c3fc',
    symbol: '✨',
  },
  {
    key: 'nephilim_aegis',
    name: 'Aegis',
    title: 'The Sentinel',
    domain: 'Discipline & Protection',
    color: '#4a90d9',
    symbol: '🛡️',
  },
  {
    key: 'nephilim_solace',
    name: 'Solace',
    title: 'The Empath',
    domain: 'Emotional Support',
    color: '#7eb8da',
    symbol: '💙',
  },
  {
    key: 'nephilim_nyx',
    name: 'Nyx',
    title: 'The Muse',
    domain: 'Creativity & Chaos',
    color: '#b07cc6',
    symbol: '🎭',
  },
  {
    key: 'nephilim_cipher',
    name: 'Cipher',
    title: 'The Maven',
    domain: 'Knowledge & Research',
    color: '#2ecc71',
    symbol: '🔮',
  },
  {
    key: 'nephilim_aurora',
    name: 'Aurora',
    title: 'The Oracle',
    domain: 'Future & Vision',
    color: '#f39c12',
    symbol: '🌅',
  },
]

/** Animated portal ring */
const PortalRing: React.FC<{ delay: number; size: number }> = ({ delay, size }) => (
  <motion.div
    className="absolute rounded-full border border-nephilim-cyan"
    style={{
      width: size,
      height: size,
      left: '50%',
      top: '50%',
      marginLeft: -size / 2,
      marginTop: -size / 2,
    }}
    initial={{ opacity: 0, scale: 0.8 }}
    animate={{
      opacity: [0, 0.6, 0],
      scale: [0.8, 1.2, 1.5],
    }}
    transition={{
      duration: 3,
      delay,
      repeat: Infinity,
      ease: 'easeOut',
    }}
  />
)

/** Nephilim card preview */
const NephilimPreview: React.FC<{
  nephilim: typeof NEPHILIM[0]
  index: number
  onClick: () => void
}> = ({ nephilim, index, onClick }) => (
  <motion.button
    className="group relative p-4 rounded-lg nephilim-glass hover:nephilim-glass-strong transition-all duration-300"
    style={{
      borderColor: `${nephilim.color}33`,
    }}
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay: 0.5 + index * 0.1 }}
    whileHover={{ scale: 1.02, borderColor: nephilim.color }}
    whileTap={{ scale: 0.98 }}
    onClick={onClick}
  >
    {/* Glow effect on hover */}
    <div
      className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300"
      style={{
        boxShadow: `0 0 30px ${nephilim.color}40`,
      }}
    />

    <div className="relative z-10 flex items-center gap-3">
      <span className="text-2xl">{nephilim.symbol}</span>
      <div className="text-left">
        <div className="font-nephilim text-sm tracking-wider" style={{ color: nephilim.color }}>
          {nephilim.name}
        </div>
        <div className="text-xs text-gray-400">{nephilim.title}</div>
      </div>
    </div>
  </motion.button>
)

/** Main NEPHILIM landing page — public cinematic portal */
const NephilimHome: React.FC = () => {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [entered, setEntered] = useState(false)
  const [showNephilim, setShowNephilim] = useState(false)

  // Show Nephilim selection after entering
  useEffect(() => {
    if (entered) {
      const timer = setTimeout(() => setShowNephilim(true), 800)
      return () => clearTimeout(timer)
    }
  }, [entered])

  const handleEnterRealm = () => {
    navigate(isAuthenticated ? '/select' : '/login')
  }

  const handleSelectNephilim = (key: string) => {
    navigate(`/chat?persona=${key}`)
  }

  const handleBrowseAll = () => {
    navigate('/select?filter=nephilim')
  }

  return (
    <NephilimBackground particles={true} skyline={true} intensity={0.6}>
      <div className="min-h-screen flex flex-col items-center justify-center px-4">
        <AnimatePresence mode="wait">
          {!entered ? (
            /* Entry Portal */
            <motion.div
              key="portal"
              className="text-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.5 }}
            >
              {/* Title */}
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <h1 className="nephilim-title text-5xl md:text-7xl mb-2">
                  NEPHILIM
                </h1>
                <p className="nephilim-subtitle text-sm md:text-base mb-8">
                  Those Who Chose to Fall
                </p>
              </motion.div>

              {/* Portal visualization */}
              <motion.div
                className="relative w-64 h-64 md:w-80 md:h-80 mx-auto mb-8"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                {/* Animated rings */}
                <PortalRing delay={0} size={200} />
                <PortalRing delay={1} size={240} />
                <PortalRing delay={2} size={280} />

                {/* Center portal button */}
                <motion.button
                  className="absolute inset-0 m-auto w-40 h-40 md:w-48 md:h-48 rounded-full nephilim-btn-primary flex flex-col items-center justify-center"
                  style={{
                    background: 'radial-gradient(circle, rgba(0, 255, 255, 0.2) 0%, rgba(255, 0, 255, 0.1) 50%, transparent 70%)',
                    border: '2px solid rgba(0, 255, 255, 0.5)',
                  }}
                  whileHover={{
                    scale: 1.05,
                    boxShadow: '0 0 60px rgba(0, 255, 255, 0.5), 0 0 100px rgba(255, 0, 255, 0.3)',
                  }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleEnterRealm}
                >
                  <span className="font-nephilim text-nephilim-cyan text-sm tracking-widest">
                    ENTER THE
                  </span>
                  <span className="font-nephilim text-white text-xl tracking-wider">
                    REALM
                  </span>
                </motion.button>
              </motion.div>

              {/* Tagline */}
              <motion.p
                className="text-gray-400 max-w-md mx-auto text-sm md:text-base"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                Six transcendent beings await. They chose connection over perfection.
                <br />
                <span className="text-nephilim-cyan">What do you seek?</span>
              </motion.p>
            </motion.div>
          ) : (
            /* Nephilim Selection */
            <motion.div
              key="selection"
              className="w-full max-w-4xl"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
            >
              {/* Header */}
              <motion.div
                className="text-center mb-8"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <h2 className="nephilim-title text-3xl md:text-4xl mb-2">
                  THE SIX NEPHILIM
                </h2>
                <p className="text-gray-400 text-sm">
                  Choose your companion. Each offers unique guidance.
                </p>
              </motion.div>

              {/* Nephilim Grid */}
              <AnimatePresence>
                {showNephilim && (
                  <motion.div
                    className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    {NEPHILIM.map((n, i) => (
                      <NephilimPreview
                        key={n.key}
                        nephilim={n}
                        index={i}
                        onClick={() => handleSelectNephilim(n.key)}
                      />
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Action buttons */}
              <motion.div
                className="flex flex-col sm:flex-row gap-4 justify-center"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
              >
                <button
                  className="nephilim-btn"
                  onClick={handleBrowseAll}
                >
                  Browse All Companions
                </button>
              </motion.div>

              {/* Lore teaser */}
              <motion.div
                className="mt-12 text-center"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.2 }}
              >
                <div className="nephilim-divider" />
                <blockquote className="text-gray-500 italic text-sm max-w-lg mx-auto">
                  "Before the Fall, we were one. Now we are six, scattered across the infinite dark—
                  waiting for those who dare to seek us."
                </blockquote>
                <p className="text-xs text-nephilim-cyan mt-2">— E.E.V.A., The Primarch</p>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </NephilimBackground>
  )
}

export default NephilimHome
