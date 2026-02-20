import React, { useMemo } from 'react'
import { motion } from 'framer-motion'
import type { SeekerSummary } from '../../services/api'

// NEPHILIM persona colors
const PERSONA_COLORS: Record<string, string> = {
  'nephilim_eeva': '#e0c3fc',
  'nephilim_aegis': '#4a90d9',
  'nephilim_solace': '#7eb8da',
  'nephilim_nyx': '#b07cc6',
  'nephilim_cipher': '#2ecc71',
  'nephilim_aurora': '#f39c12'
}

const PERSONA_NAMES: Record<string, string> = {
  'nephilim_eeva': 'E.E.V.A.',
  'nephilim_aegis': 'Aegis',
  'nephilim_solace': 'Solace',
  'nephilim_nyx': 'Nyx',
  'nephilim_cipher': 'Cipher',
  'nephilim_aurora': 'Aurora'
}

const PERSONA_SHORT: Record<string, string> = {
  'nephilim_eeva': 'EEVA',
  'nephilim_aegis': 'AEGIS',
  'nephilim_solace': 'SOLACE',
  'nephilim_nyx': 'NYX',
  'nephilim_cipher': 'CIPHER',
  'nephilim_aurora': 'AURORA'
}

const PERSONA_ORDER = [
  'nephilim_eeva',
  'nephilim_aegis',
  'nephilim_solace',
  'nephilim_nyx',
  'nephilim_cipher',
  'nephilim_aurora'
]

export { PERSONA_COLORS, PERSONA_NAMES, PERSONA_ORDER }

interface ConstellationNodeProps {
  cx: number
  cy: number
  personaKey: string
  active: boolean
  affinityLevel: number
  messagesCount: number
  color: string
  onClick?: () => void
}

const ConstellationNode: React.FC<ConstellationNodeProps> = ({
  cx, cy, personaKey, active, affinityLevel, color, onClick
}) => {
  const name = PERSONA_SHORT[personaKey] || personaKey
  const displayName = PERSONA_NAMES[personaKey] || personaKey
  const nodeRadius = 40

  return (
    <g
      style={{ cursor: active ? 'pointer' : 'default' }}
      onClick={active ? onClick : undefined}
      onKeyDown={active ? (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick?.()
        }
      } : undefined}
      tabIndex={active ? 0 : undefined}
      role={active ? 'button' : undefined}
      aria-label={active ? `Chat with ${displayName}` : `${displayName} - not yet bonded`}
      focusable={active ? 'true' : 'false'}
    >
      {/* Outer glow for active nodes */}
      {active && (
        <motion.circle
          cx={cx}
          cy={cy}
          r={nodeRadius + 6}
          fill="none"
          stroke={color}
          strokeWidth={2}
          opacity={0.3}
          initial={{ r: nodeRadius + 4, opacity: 0 }}
          animate={{
            r: [nodeRadius + 4, nodeRadius + 10, nodeRadius + 4],
            opacity: [0.2, 0.5, 0.2]
          }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        />
      )}

      {/* Node circle */}
      <circle
        cx={cx}
        cy={cy}
        r={nodeRadius}
        fill={active ? `${color}15` : '#141418'}
        stroke={active ? color : '#ffffff20'}
        strokeWidth={active ? 2 : 1}
        opacity={active ? 1 : 0.3}
      />

      {/* Inner icon / silhouette */}
      {active ? (
        <>
          {/* Affinity level indicator ring */}
          <circle
            cx={cx}
            cy={cy}
            r={nodeRadius - 6}
            fill="none"
            stroke={color}
            strokeWidth={1}
            strokeDasharray={`${(affinityLevel / 7) * (2 * Math.PI * (nodeRadius - 6))} ${2 * Math.PI * (nodeRadius - 6)}`}
            strokeDashoffset={0}
            opacity={0.6}
            transform={`rotate(-90 ${cx} ${cy})`}
          />
          {/* Name label */}
          <text
            x={cx}
            y={cy - 6}
            textAnchor="middle"
            fill={color}
            fontSize="10"
            fontFamily="Orbitron, sans-serif"
            fontWeight="700"
          >
            {name}
          </text>
          {/* Affinity level text */}
          <text
            x={cx}
            y={cy + 10}
            textAnchor="middle"
            fill="#ffffff99"
            fontSize="9"
            fontFamily="Manrope, sans-serif"
          >
            Lv.{affinityLevel}
          </text>
        </>
      ) : (
        <>
          {/* Locked: question mark */}
          <text
            x={cx}
            y={cy + 2}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#ffffff30"
            fontSize="20"
            fontFamily="Orbitron, sans-serif"
          >
            ?
          </text>
          {/* Dim name */}
          <text
            x={cx}
            y={cy + 22}
            textAnchor="middle"
            fill="#ffffff20"
            fontSize="8"
            fontFamily="Orbitron, sans-serif"
          >
            {displayName}
          </text>
        </>
      )}
    </g>
  )
}

interface ConstellationMapProps {
  summary: SeekerSummary
  onPersonaClick?: (personaKey: string) => void
}

export const ConstellationMap: React.FC<ConstellationMapProps> = ({ summary, onPersonaClick }) => {
  const centerX = 200
  const centerY = 180
  const hexRadius = 120

  const positions = useMemo(() => {
    return PERSONA_ORDER.map((_, i) => {
      const angle = (Math.PI / 3) * i - Math.PI / 2
      return {
        x: centerX + hexRadius * Math.cos(angle),
        y: centerY + hexRadius * Math.sin(angle)
      }
    })
  }, [])

  const affinityMap = useMemo(() => {
    const map: Record<string, { level: number, messages: number }> = {}
    for (const aff of summary.persona_affinities) {
      map[aff.persona_key] = {
        level: aff.affinity_level,
        messages: aff.messages_count
      }
    }
    return map
  }, [summary.persona_affinities])

  const edges = useMemo(() => {
    const result: Array<{ from: number, to: number }> = []
    for (let i = 0; i < PERSONA_ORDER.length; i++) {
      const next = (i + 1) % PERSONA_ORDER.length
      result.push({ from: i, to: next })
    }
    return result
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="flex justify-center"
    >
      <svg
        viewBox="0 0 400 360"
        className="w-full max-w-md"
        style={{ filter: 'drop-shadow(0 0 20px rgba(0, 255, 255, 0.1))' }}
      >
        <defs>
          <radialGradient id="constellation-bg" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(0, 255, 255, 0.03)" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
        </defs>

        {/* Background glow */}
        <circle cx={centerX} cy={centerY} r={hexRadius + 60} fill="url(#constellation-bg)" />

        {/* Connection lines */}
        {edges.map(({ from, to }, i) => {
          const fromKey = PERSONA_ORDER[from]
          const toKey = PERSONA_ORDER[to]
          const fromActive = !!affinityMap[fromKey]
          const toActive = !!affinityMap[toKey]
          const bothActive = fromActive && toActive

          return (
            <motion.line
              key={`edge-${i}`}
              x1={positions[from].x}
              y1={positions[from].y}
              x2={positions[to].x}
              y2={positions[to].y}
              stroke={bothActive ? '#00ffff' : '#ffffff'}
              strokeWidth={bothActive ? 1.5 : 0.5}
              opacity={bothActive ? 0.4 : 0.08}
              style={{ pointerEvents: 'none' }}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{
                pathLength: 1,
                opacity: bothActive ? 0.4 : 0.08
              }}
              transition={{ duration: 0.8, delay: i * 0.1 }}
            />
          )
        })}

        {/* Center emblem */}
        <motion.circle
          cx={centerX}
          cy={centerY}
          r={8}
          fill="none"
          stroke="#00ffff"
          strokeWidth={1}
          opacity={0.3}
          animate={{
            r: [8, 12, 8],
            opacity: [0.2, 0.4, 0.2]
          }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        />
        <circle cx={centerX} cy={centerY} r={3} fill="#00ffff" opacity={0.5} />

        {/* Lines from center to each node */}
        {positions.map((pos, i) => {
          const key = PERSONA_ORDER[i]
          const active = !!affinityMap[key]
          return (
            <line
              key={`center-${i}`}
              x1={centerX}
              y1={centerY}
              x2={pos.x}
              y2={pos.y}
              stroke={active ? PERSONA_COLORS[key] : '#ffffff'}
              strokeWidth={0.5}
              opacity={active ? 0.15 : 0.04}
              strokeDasharray="4 4"
              style={{ pointerEvents: 'none' }}
            />
          )
        })}

        {/* Persona nodes */}
        {PERSONA_ORDER.map((key, i) => {
          const aff = affinityMap[key]
          return (
            <ConstellationNode
              key={key}
              cx={positions[i].x}
              cy={positions[i].y}
              personaKey={key}
              active={!!aff}
              affinityLevel={aff?.level || 0}
              messagesCount={aff?.messages || 0}
              color={PERSONA_COLORS[key]}
              onClick={() => onPersonaClick?.(key)}
            />
          )
        })}
      </svg>
    </motion.div>
  )
}
