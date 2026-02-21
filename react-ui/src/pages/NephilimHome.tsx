import React from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import NephilimBackground from '../components/NephilimBackground'
import { useAuth } from '../context/AuthContext'

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

/** Main NEPHILIM landing page — public cinematic portal */
const NephilimHome: React.FC = () => {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const handleEnterRealm = () => {
    navigate(isAuthenticated ? '/select' : '/login')
  }

  return (
    <NephilimBackground particles={true} skyline={true} intensity={0.6}>
      <div className="min-h-screen flex flex-col items-center justify-center px-4">
        <motion.div
            className="text-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
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
      </div>
    </NephilimBackground>
  )
}

export default NephilimHome
