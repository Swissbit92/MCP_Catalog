import React, { useRef, useEffect, useCallback } from 'react'

interface LegendaryParticlesProps {
  isHovered: boolean
  cardRef: React.RefObject<HTMLDivElement | null>
}

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  life: number
  size: number
  color: string
  wobble: number
}

const GOLD_PALETTE = ['#ffd700', '#fcd34d', '#f59e0b', '#fef3c7', '#ffffff']

const IDLE_MAX_PARTICLES = 10
const IDLE_SPAWN_ATTEMPTS = 1
const STORM_MAX_PARTICLES = 30
const STORM_SPAWN_ATTEMPTS = 3

const PADDING = 60
const HALF_PADDING = 30

function randomFromArray(arr: string[]): string {
  return arr[Math.floor(Math.random() * arr.length)]
}

function spawnParticle(cardWidth: number, cardHeight: number, isStorm: boolean): Particle {
  const edge = Math.floor(Math.random() * 4)
  let x: number
  let y: number

  // Spawn from random edges of the card (in canvas coordinates with padding offset)
  switch (edge) {
    case 0: // top
      x = Math.random() * cardWidth + HALF_PADDING
      y = HALF_PADDING
      break
    case 1: // right
      x = cardWidth + HALF_PADDING
      y = Math.random() * cardHeight + HALF_PADDING
      break
    case 2: // bottom
      x = Math.random() * cardWidth + HALF_PADDING
      y = cardHeight + HALF_PADDING
      break
    case 3: // left
    default:
      x = HALF_PADDING
      y = Math.random() * cardHeight + HALF_PADDING
      break
  }

  const baseSpeed = isStorm ? 1.2 : 0.5
  const baseSize = isStorm ? (Math.random() * 4 + 2) : (Math.random() * 2.5 + 1)

  return {
    x,
    y,
    vx: (Math.random() - 0.5) * baseSpeed,
    vy: -(Math.random() * baseSpeed + 0.3), // upward drift
    life: 1.0,
    size: baseSize,
    color: randomFromArray(GOLD_PALETTE),
    wobble: Math.random() * Math.PI * 2,
  }
}

const LegendaryParticles: React.FC<LegendaryParticlesProps> = ({ isHovered, cardRef }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const particlesRef = useRef<Particle[]>([])
  const animFrameRef = useRef<number>(0)
  const cardSizeRef = useRef<{ width: number; height: number }>({ width: 0, height: 0 })
  const isHoveredRef = useRef(isHovered)

  // Keep the ref in sync so the animation loop always sees the latest value
  useEffect(() => {
    isHoveredRef.current = isHovered
  }, [isHovered])

  const resizeCanvas = useCallback(() => {
    const card = cardRef.current
    const canvas = canvasRef.current
    if (!card || !canvas) return

    const rect = card.getBoundingClientRect()
    const dpr = window.devicePixelRatio || 1

    cardSizeRef.current = { width: rect.width, height: rect.height }

    const canvasWidth = rect.width + PADDING
    const canvasHeight = rect.height + PADDING

    canvas.width = canvasWidth * dpr
    canvas.height = canvasHeight * dpr
    canvas.style.width = `${canvasWidth}px`
    canvas.style.height = `${canvasHeight}px`

    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.scale(dpr, dpr)
    }
  }, [cardRef])

  const animate = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const { width: cardWidth, height: cardHeight } = cardSizeRef.current
    const canvasWidth = cardWidth + PADDING
    const canvasHeight = cardHeight + PADDING
    const storm = isHoveredRef.current

    const maxParticles = storm ? STORM_MAX_PARTICLES : IDLE_MAX_PARTICLES
    const spawnAttempts = storm ? STORM_SPAWN_ATTEMPTS : IDLE_SPAWN_ATTEMPTS

    // Clear
    ctx.clearRect(0, 0, canvasWidth, canvasHeight)

    // Spawn particles
    for (let i = 0; i < spawnAttempts; i++) {
      if (particlesRef.current.length < maxParticles) {
        particlesRef.current.push(spawnParticle(cardWidth, cardHeight, storm))
      }
    }

    // Update each particle
    for (const p of particlesRef.current) {
      p.wobble += 0.03
      p.x += p.vx + Math.sin(p.wobble) * 0.3
      p.y += p.vy
      p.life -= storm ? 0.008 : 0.005
    }

    // Draw each particle
    for (const p of particlesRef.current) {
      if (p.life <= 0) continue

      ctx.save()

      // Outer glow
      ctx.globalAlpha = p.life * 0.8
      ctx.shadowBlur = p.size * 4
      ctx.shadowColor = p.color
      ctx.fillStyle = p.color
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
      ctx.fill()

      // Inner white core
      ctx.shadowBlur = 0
      ctx.globalAlpha = p.life * 0.5
      ctx.fillStyle = '#ffffff'
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.size * 0.3, 0, Math.PI * 2)
      ctx.fill()

      ctx.restore()
    }

    // Remove dead particles
    particlesRef.current = particlesRef.current.filter(p => p.life > 0)

    // Continue loop
    animFrameRef.current = requestAnimationFrame(animate)
  }, [])

  useEffect(() => {
    // Disable on mobile or in test environments without canvas support
    if (typeof window === 'undefined' || window.innerWidth <= 768) return
    if (typeof ResizeObserver === 'undefined') return

    resizeCanvas()

    // Observe card size changes
    const card = cardRef.current
    let observer: ResizeObserver | null = null
    if (card) {
      observer = new ResizeObserver(() => {
        resizeCanvas()
      })
      observer.observe(card)
    }

    // Start animation loop
    animFrameRef.current = requestAnimationFrame(animate)

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current)
      }
      if (observer) {
        observer.disconnect()
      }
      particlesRef.current = []
    }
  }, [cardRef, resizeCanvas, animate])

  // Disable entirely on mobile
  if (typeof window !== 'undefined' && window.innerWidth <= 768) {
    return null
  }

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        inset: `-${HALF_PADDING}px`,
        pointerEvents: 'none',
        zIndex: 10,
      }}
    />
  )
}

export default React.memo(LegendaryParticles)
