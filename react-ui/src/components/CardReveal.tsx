import React from 'react'
import { motion } from 'framer-motion'
import CharacterCard from './CharacterCard'
import { getDisplayOrder } from '../utils/celestialOrder'

const ORDER_COLORS: Record<string, string> = {
  wanderer: '#C0C0C0',
  sage: '#00BFFF',
  warden: '#DA70D6',
  archon: '#FFD700',
}

interface Persona {
  key: string
  display_name: string
  style: string
  image: string
  rarity: string
  celestial_order?: string
  voice?: {
    greeting: string
  }
}

interface CardRevealProps {
  persona: Persona
  onSelect: (key: string) => void
  isRevealing: boolean
  onRevealComplete: () => void
}

const CardReveal: React.FC<CardRevealProps> = ({
  persona,
  onSelect,
  isRevealing,
  onRevealComplete
}) => {
  const order = getDisplayOrder(persona)
  const rarityColor = ORDER_COLORS[order] || ORDER_COLORS.wanderer

  return (
    <div className="card-reveal-container relative">
      <motion.div
        className="card-reveal-card relative"
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{
          scale: isRevealing ? 1 : 0.8,
          opacity: isRevealing ? 1 : 0,
        }}
        transition={{
          duration: 0.6,
          ease: 'easeOut',
          delay: isRevealing ? 0.2 : 0,
        }}
        onAnimationComplete={() => {
          if (isRevealing) {
            onRevealComplete()
          }
        }}
      >
        {/* Silhouette layer (dark version of the image) */}
        <motion.div
          className="absolute inset-0 z-10 pointer-events-none"
          initial={{ opacity: 1 }}
          animate={{ opacity: isRevealing ? 0 : 1 }}
          transition={{ duration: 1, delay: isRevealing ? 0.3 : 0, ease: 'easeInOut' }}
        >
          <div
            className="w-full h-full rounded-xl overflow-hidden"
            style={{
              filter: 'brightness(0)',
              boxShadow: `0 0 30px ${rarityColor}22`,
            }}
          >
            <img
              src={`/images/${persona.image}`}
              alt=""
              className="w-full h-full object-cover"
              aria-hidden="true"
            />
          </div>
        </motion.div>

        {/* Light sweep overlay (moves left to right during reveal) */}
        {isRevealing && (
          <motion.div
            className="absolute inset-0 z-20 pointer-events-none rounded-xl overflow-hidden"
            initial={{ opacity: 1 }}
            animate={{ opacity: [1, 1, 0] }}
            transition={{ duration: 1.2, times: [0, 0.8, 1] }}
          >
            <motion.div
              className="absolute inset-0"
              style={{
                background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 45%, rgba(255,255,255,0.6) 50%, rgba(255,255,255,0.4) 55%, transparent 100%)',
                mixBlendMode: 'overlay',
              }}
              initial={{ x: '-100%' }}
              animate={{ x: '100%' }}
              transition={{ duration: 1, ease: 'easeInOut', delay: 0.3 }}
            />
          </motion.div>
        )}

        {/* Actual card content (revealed underneath the silhouette) */}
        <CharacterCard
          personaKey={persona.key}
          name={persona.display_name}
          style={persona.style}
          image={`/images/${persona.image}`}
          rarity={persona.rarity}
          celestial_order={persona.celestial_order}
          onSelect={onSelect}
          isSelected={false}
        />
      </motion.div>
    </div>
  )
}

export default CardReveal