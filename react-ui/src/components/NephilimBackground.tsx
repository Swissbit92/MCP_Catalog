import React, { useMemo } from 'react'
import { motion } from 'framer-motion'

interface NephilimBackgroundProps {
  /** Active persona key for color theming */
  persona?: 'eeva' | 'aegis' | 'solace' | 'nyx' | 'cipher' | 'aurora' | null
  /** Show animated particles */
  particles?: boolean
  /** Show city skyline silhouette */
  skyline?: boolean
  /** Intensity of glow effects (0-1) */
  intensity?: number
  /** Children to render on top */
  children?: React.ReactNode
}

/** Floating particle component */
const Particle: React.FC<{
  delay: number
  duration: number
  size: number
  left: string
  color: string
}> = ({ delay, duration, size, left, color }) => (
  <motion.div
    className="absolute rounded-full"
    style={{
      width: size,
      height: size,
      left,
      bottom: '-10px',
      background: `radial-gradient(circle, ${color} 0%, transparent 70%)`,
      filter: 'blur(1px)',
    }}
    initial={{ y: 0, opacity: 0 }}
    animate={{
      y: [0, -window.innerHeight - 100],
      opacity: [0, 0.8, 0.8, 0],
    }}
    transition={{
      duration,
      delay,
      repeat: Infinity,
      ease: 'linear',
    }}
  />
)

/** City skyline silhouette */
const Skyline: React.FC = () => (
  <div className="absolute bottom-0 left-0 right-0 h-48 pointer-events-none">
    <svg
      viewBox="0 0 1200 200"
      preserveAspectRatio="xMidYMax slice"
      className="w-full h-full"
      style={{ filter: 'drop-shadow(0 0 10px rgba(0, 255, 255, 0.3))' }}
    >
      <defs>
        <linearGradient id="skylineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="rgba(0, 255, 255, 0.1)" />
          <stop offset="100%" stopColor="rgba(0, 0, 0, 0.8)" />
        </linearGradient>
        <linearGradient id="windowGlow" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="rgba(0, 255, 255, 0.8)" />
          <stop offset="100%" stopColor="rgba(255, 0, 255, 0.4)" />
        </linearGradient>
      </defs>
      {/* Building silhouettes */}
      <path
        d="M0,200 L0,160 L30,160 L30,140 L60,140 L60,120 L80,120 L80,100 L100,100 L100,80 L120,80 L120,60 L150,60 L150,80 L180,80 L180,100 L200,100 L200,120 L220,120 L220,140 L240,140 L240,160 L260,160 L260,140 L280,140 L280,100 L300,100 L300,60 L320,60 L320,40 L350,40 L350,20 L380,20 L380,40 L400,40 L400,60 L420,60 L420,80 L450,80 L450,100 L480,100 L480,120 L500,120 L500,140 L520,140 L520,160 L540,160 L540,140 L560,140 L560,100 L580,100 L580,80 L600,80 L600,50 L620,50 L620,30 L650,30 L650,50 L680,50 L680,70 L700,70 L700,90 L720,90 L720,110 L740,110 L740,130 L760,130 L760,150 L780,150 L780,130 L800,130 L800,100 L820,100 L820,70 L840,70 L840,50 L870,50 L870,70 L900,70 L900,90 L920,90 L920,110 L940,110 L940,130 L960,130 L960,150 L980,150 L980,170 L1000,170 L1000,150 L1020,150 L1020,120 L1040,120 L1040,90 L1060,90 L1060,110 L1080,110 L1080,130 L1100,130 L1100,150 L1120,150 L1120,170 L1140,170 L1140,180 L1160,180 L1160,190 L1200,190 L1200,200 Z"
        fill="url(#skylineGradient)"
      />
      {/* Animated window lights */}
      {[
        { x: 85, y: 90, w: 3, h: 5 },
        { x: 110, y: 70, w: 3, h: 5 },
        { x: 135, y: 55, w: 3, h: 5 },
        { x: 335, y: 30, w: 3, h: 5 },
        { x: 365, y: 30, w: 3, h: 5 },
        { x: 605, y: 60, w: 3, h: 5 },
        { x: 635, y: 40, w: 3, h: 5 },
        { x: 855, y: 60, w: 3, h: 5 },
        { x: 1045, y: 100, w: 3, h: 5 },
      ].map((win, i) => (
        <motion.rect
          key={i}
          x={win.x}
          y={win.y}
          width={win.w}
          height={win.h}
          fill="url(#windowGlow)"
          initial={{ opacity: 0.3 }}
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{
            duration: 2 + Math.random() * 3,
            delay: Math.random() * 2,
            repeat: Infinity,
          }}
        />
      ))}
    </svg>
  </div>
)

/** Aurora/nebula gradient overlay */
const AuroraOverlay: React.FC<{ persona?: string; intensity: number }> = ({
  persona,
  intensity,
}) => {
  const colors = useMemo(() => {
    switch (persona) {
      case 'eeva':
        return ['rgba(224, 195, 252, 0.15)', 'rgba(196, 167, 231, 0.10)']
      case 'aegis':
        return ['rgba(74, 144, 217, 0.15)', 'rgba(107, 163, 224, 0.10)']
      case 'solace':
        return ['rgba(126, 184, 218, 0.15)', 'rgba(94, 174, 211, 0.10)']
      case 'nyx':
        return ['rgba(155, 89, 182, 0.20)', 'rgba(255, 0, 255, 0.10)']
      case 'cipher':
        return ['rgba(46, 204, 113, 0.15)', 'rgba(39, 174, 96, 0.10)']
      case 'aurora':
        return ['rgba(243, 156, 18, 0.15)', 'rgba(230, 126, 34, 0.10)']
      default:
        return ['rgba(0, 255, 255, 0.08)', 'rgba(255, 0, 255, 0.05)']
    }
  }, [persona])

  return (
    <motion.div
      className="absolute inset-0 pointer-events-none"
      initial={{ opacity: 0 }}
      animate={{ opacity: intensity }}
      transition={{ duration: 1 }}
    >
      {/* Primary nebula */}
      <div
        className="absolute inset-0"
        style={{
          background: `
            radial-gradient(ellipse at 20% 30%, ${colors[0]}, transparent 60%),
            radial-gradient(ellipse at 80% 70%, ${colors[1]}, transparent 60%),
            radial-gradient(ellipse at 50% 50%, rgba(0, 255, 255, 0.03), transparent 70%)
          `,
        }}
      />
      {/* Animated glow pulse */}
      <motion.div
        className="absolute inset-0"
        style={{
          background: `radial-gradient(ellipse at 50% 30%, ${colors[0]}, transparent 50%)`,
        }}
        animate={{
          opacity: [0.3, 0.6, 0.3],
          scale: [1, 1.1, 1],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
    </motion.div>
  )
}

/** Grid overlay for cyberpunk feel */
const GridOverlay: React.FC = () => (
  <div
    className="absolute inset-0 pointer-events-none opacity-[0.03]"
    style={{
      backgroundImage: `
        linear-gradient(rgba(0, 255, 255, 0.5) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 255, 255, 0.5) 1px, transparent 1px)
      `,
      backgroundSize: '50px 50px',
    }}
  />
)

/** Scan line effect */
const ScanLines: React.FC = () => (
  <div
    className="absolute inset-0 pointer-events-none opacity-[0.02]"
    style={{
      backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 0, 0, 0.3) 2px, rgba(0, 0, 0, 0.3) 4px)',
    }}
  />
)

/**
 * NEPHILIM Background Component
 *
 * Creates an immersive dark cyberpunk atmosphere with:
 * - Animated particle effects
 * - City skyline silhouette
 * - Persona-specific aurora gradients
 * - Subtle grid and scan line overlays
 */
const NephilimBackground: React.FC<NephilimBackgroundProps> = ({
  persona = null,
  particles = true,
  skyline = true,
  intensity = 0.6,
  children,
}) => {
  // Generate random particles
  const particleConfigs = useMemo(() => {
    const configs = []
    const colors = persona
      ? {
          eeva: '#e0c3fc',
          aegis: '#4a90d9',
          solace: '#7eb8da',
          nyx: '#ff00ff',
          cipher: '#2ecc71',
          aurora: '#f39c12',
        }[persona] || '#00ffff'
      : '#00ffff'

    for (let i = 0; i < 20; i++) {
      configs.push({
        delay: Math.random() * 10,
        duration: 15 + Math.random() * 20,
        size: 2 + Math.random() * 4,
        left: `${Math.random() * 100}%`,
        color: Math.random() > 0.5 ? colors : '#ff00ff',
      })
    }
    return configs
  }, [persona])

  return (
    <>
      {/* Fixed decorative background — no content here */}
      <div className="fixed inset-0 overflow-hidden bg-nephilim-void pointer-events-none">
        {/* Base gradient */}
        <div
          className="absolute inset-0"
          style={{
            background: 'linear-gradient(180deg, #0B0B0D 0%, #1a0f2e 50%, #0B0B0D 100%)',
          }}
        />

        {/* Aurora/nebula overlay */}
        <AuroraOverlay persona={persona || undefined} intensity={intensity} />

        {/* Grid overlay */}
        <GridOverlay />

        {/* Scan lines */}
        <ScanLines />

        {/* Floating particles */}
        {particles && (
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            {particleConfigs.map((config, i) => (
              <Particle key={i} {...config} />
            ))}
          </div>
        )}

        {/* City skyline */}
        {skyline && <Skyline />}

        {/* Vignette effect */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: 'radial-gradient(ellipse at center, transparent 0%, rgba(0, 0, 0, 0.4) 100%)',
          }}
        />
      </div>

      {/* Scrollable content layer */}
      <div className="relative z-10 h-full">{children}</div>
    </>
  )
}

export default NephilimBackground
