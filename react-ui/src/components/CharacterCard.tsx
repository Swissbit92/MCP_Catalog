import React, { useRef, useState, useCallback } from 'react'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import styles from './CharacterCard.module.css'
import LegendaryParticles from './LegendaryParticles'
import { getDisplayOrder, formatOrderLabel } from '../utils/celestialOrder'

interface CharacterCardProps {
  name: string
  style: string
  image: string
  celestial_order: string
  onSelect: (key: string) => void
  onChoose?: (key: string) => void
  isSelected: boolean
  personaKey: string
  index?: number
}

const CharacterCard: React.FC<CharacterCardProps> = ({ name, style, image, celestial_order, onSelect, onChoose, isSelected, personaKey, index = 0 }) => {
  // Resolve order for display and CSS classes
  const order = getDisplayOrder({ celestial_order })
  const orderClass = styles[`order-${order}`]
  const selectedClass = isSelected ? styles['selected'] : ''
  const cardRef = useRef<HTMLDivElement>(null)
  const [isHovered, setIsHovered] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [spotlightPos, setSpotlightPos] = useState({ x: 50, y: 50 })

  // Detect mobile for disabling canvas particles
  React.useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  // Motion values for mouse tracking
  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)

  // Spring physics for smooth 3D tilt (+-8 degrees)
  const rotateX = useSpring(useTransform(mouseY, [-0.5, 0.5], [8, -8]), {
    stiffness: 300,
    damping: 30
  })
  const rotateY = useSpring(useTransform(mouseX, [-0.5, 0.5], [-8, 8]), {
    stiffness: 300,
    damping: 30
  })

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return
    const rect = cardRef.current.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    const x = (e.clientX - centerX) / (rect.width / 2)
    const y = (e.clientY - centerY) / (rect.height / 2)
    mouseX.set(x)
    mouseY.set(y)
    // Update spotlight position as percentage (state-driven for reactive rendering)
    setSpotlightPos({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    })
    // Set CSS custom properties for rarity effects
    if (cardRef.current) {
      const percentX = ((e.clientX - rect.left) / rect.width) * 100
      const percentY = ((e.clientY - rect.top) / rect.height) * 100
      cardRef.current.style.setProperty('--mouse-x', `${percentX}%`)
      cardRef.current.style.setProperty('--mouse-y', `${percentY}%`)
    }
  }, [mouseX, mouseY])

  const handleMouseEnter = useCallback(() => setIsHovered(true), [])

  const handleMouseLeave = useCallback(() => {
    setIsHovered(false)
    mouseX.set(0)
    mouseY.set(0)
    setSpotlightPos({ x: 50, y: 50 })
    if (cardRef.current) {
      cardRef.current.style.removeProperty('--mouse-x')
      cardRef.current.style.removeProperty('--mouse-y')
    }
  }, [mouseX, mouseY])

  const handleChooseClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (onChoose) {
      onChoose(personaKey)
    } else {
      onSelect(personaKey)
    }
  }

  const handleCardClick = () => {
    onSelect(personaKey)
  }

  return (
    <div style={{ perspective: '1000px' }}>
      <motion.div
        ref={cardRef}
        className={`${styles['card-outer']} ${orderClass} ${selectedClass}`}
        onClick={handleCardClick}
        style={{
          cursor: 'pointer',
          rotateX: isHovered ? rotateX : 0,
          rotateY: isHovered ? rotateY : 0,
          transformStyle: 'preserve-3d',
          transformOrigin: 'center center',
          overflow: order === 'archon' ? 'visible' : undefined,
        }}
        initial={{ opacity: 0, y: 20, scale: 0.9 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{
          opacity: { duration: 0.6, delay: index * 0.1 },
          y: { type: 'spring', stiffness: 300, damping: 20, delay: index * 0.1 },
          default: { duration: 0.15, ease: [0.4, 0, 0.2, 1] }
        }}
        whileHover={{
          scale: 1.05,
          transition: { duration: 0.15, ease: [0.4, 0, 0.2, 1] }
        }}
        whileTap={{ scale: 0.96 }}
        onMouseMove={handleMouseMove}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <div className={styles['card-frame']}></div>
        <div className={styles['card-foil']}></div>
        <div className={styles['card-glint']}></div>
        {/* Radial gradient spotlight following cursor */}
        {isHovered && (
          <div
            className={styles['card-spotlight']}
            style={{
              background: `radial-gradient(circle at ${spotlightPos.x}% ${spotlightPos.y}%, rgba(255,255,255,0.15) 0%, transparent 60%)`,
            }}
          />
        )}
        {/* Spinning border for Sage/Warden/Archon */}
        {(order === 'sage' || order === 'warden' || order === 'archon') && (
          <div className={styles['border-spin']} />
        )}

        {/* Wanderer: breathing border */}
        {order === 'wanderer' && (
          <div className={styles['wanderer-breathe']} />
        )}

        {/* Cursor glare for Wanderer + Sage */}
        {(order === 'wanderer' || order === 'sage') && (
          <div className={styles['cursor-glare']} />
        )}

        {/* Aurora orbs for Warden + Archon */}
        {(order === 'warden' || order === 'archon') && (
          <>
            <div className={`${styles['aurora-orb']} ${styles['aurora-orb-1']}`} />
            <div className={`${styles['aurora-orb']} ${styles['aurora-orb-2']}`} />
            <div className={`${styles['aurora-orb']} ${styles['aurora-orb-3']}`} />
          </>
        )}

        {/* Holographic foil for Warden */}
        {order === 'warden' && <div className={styles['holo-foil']} />}

        {/* Void Rift foil for Sage (cyan version) */}
        {order === 'sage' && <div className={styles['sage-holo-foil']} />}

        {/* Archon foil + particles */}
        {order === 'archon' && <div className={styles['legendary-foil']} />}
        {order === 'archon' && !isMobile && (
          <LegendaryParticles isHovered={isHovered} cardRef={cardRef} />
        )}
        <div className={styles['card-body']}>
          <img
            src={image}
            alt={name}
            className={styles['card-img']}
          />
          <div className={styles['card-name']}>{name}</div>
          <div className={styles['card-tagline']}>{style}</div>
          <div className={styles['rarity-badge']}>{formatOrderLabel(order)}</div>
          <div className={styles['card-choose']}>
            <motion.button
              className={styles['choose-pill']}
              onClick={handleChooseClick}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            >
              Choose
            </motion.button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default CharacterCard