// src/components/nephilim/SeekerDashboard.tsx
/**
 * NEPHILIM Seeker Dashboard
 *
 * Comprehensive view of user's progression, affinities,
 * and unlocked lore across all personas.
 *
 * Phase 7F: Tabbed interface with Seeker Profile, Bonds Forged,
 * Lore Codex, and Invocation Chronicle tabs.
 */

import React, { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  getSeekerSummary,
  getFactionInfo,
  getPersonaLoreWithContent,
  type SeekerSummary,
  type Faction,
  type LoreFragment
} from '../../services/api'
import { usePersona } from '../../context/PersonaContext'
import { formatOrderLabel } from '../../utils/celestialOrder'
import { SeekerRankBadge } from './SeekerRankBadge'
import { ResonanceProgress } from './ResonanceProgress'
import { AffinityMeter } from './AffinityMeter'
import { LoreCodex } from './LoreCodex'
import { FactionSelector } from './FactionSelector'

interface SeekerDashboardProps {
  userId: string
  className?: string
}

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

// Short labels for the constellation map
const PERSONA_SHORT: Record<string, string> = {
  'nephilim_eeva': 'EEVA',
  'nephilim_aegis': 'AEGIS',
  'nephilim_solace': 'SOLACE',
  'nephilim_nyx': 'NYX',
  'nephilim_cipher': 'CIPHER',
  'nephilim_aurora': 'AURORA'
}

// Ordered list of persona keys for the hexagonal layout
const PERSONA_ORDER = [
  'nephilim_eeva',
  'nephilim_aegis',
  'nephilim_solace',
  'nephilim_nyx',
  'nephilim_cipher',
  'nephilim_aurora'
]

type TabId = 'profile' | 'bonds' | 'codex' | 'chronicle'

interface TabDef {
  id: TabId
  label: string
  icon: string
  condition?: (summary: SeekerSummary) => boolean
}

const TABS: TabDef[] = [
  { id: 'profile', label: 'Seeker Profile', icon: '\u2726' },
  { id: 'bonds', label: 'Bonds Forged', icon: '\u2B21' },
  {
    id: 'codex',
    label: 'Lore Codex',
    icon: '\u2620',
    condition: (s) => s.unlocked_lore_count > 0
  },
  { id: 'chronicle', label: 'Invocation Chronicle', icon: '\u2604' }
]

// ---------------------------------------------------------------
// Constellation Map SVG Component
// ---------------------------------------------------------------

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

const ConstellationMap: React.FC<ConstellationMapProps> = ({ summary, onPersonaClick }) => {
  // Calculate hexagonal positions
  // Center at (200, 180), radius 120
  const centerX = 200
  const centerY = 180
  const hexRadius = 120

  const positions = useMemo(() => {
    return PERSONA_ORDER.map((_, i) => {
      // Start from top (offset -90 degrees), go clockwise
      const angle = (Math.PI / 3) * i - Math.PI / 2
      return {
        x: centerX + hexRadius * Math.cos(angle),
        y: centerY + hexRadius * Math.sin(angle)
      }
    })
  }, [])

  // Build affinity map
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

  // Edge connections: connect adjacent nodes in hexagon
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

// ---------------------------------------------------------------
// Chronicle Tab Components (inline, using PersonaContext data)
// ---------------------------------------------------------------

const ChronicleStats: React.FC = () => {
  const { pullStats } = usePersona()

  return (
    <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-6">
      <h3 className="text-lg font-semibold text-gray-100 mb-2 font-nephilim tracking-wide">
        Invocation Stats
      </h3>
      <p className="text-sm text-white/60 mb-6">
        Your summoning history across all rituals
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-cyan-400">{pullStats.totalPulls}</div>
          <div className="text-xs text-gray-200/60">Total Invocations</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-yellow-400">{pullStats.archonCount}</div>
          <div className="text-xs text-gray-200/60">Archon</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-400">{pullStats.wardenCount}</div>
          <div className="text-xs text-gray-200/60">Warden</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-cyan-400">{pullStats.sageCount}</div>
          <div className="text-xs text-gray-200/60">Sage</div>
        </div>
      </div>
    </div>
  )
}

const getRecordOrder = (rec: { rarity?: string; celestial_order?: string }): string => {
  if (rec.celestial_order) return rec.celestial_order.toLowerCase()
  const m: Record<string, string> = { legendary: 'archon', epic: 'warden', rare: 'sage', common: 'wanderer' }
  return m[rec.rarity?.toLowerCase() || ''] || 'wanderer'
}

const ChronicleHistory: React.FC = () => {
  const navigate = useNavigate()
  const { pullHistory } = usePersona()

  const RARITY_COLORS: Record<string, string> = {
    common: '#C0C0C0',
    rare: '#00BFFF',
    epic: '#DA70D6',
    legendary: '#FFD700',
  }

  const RARITY_TEXT: Record<string, string> = {
    common: 'text-gray-400',
    rare: 'text-cyan-400',
    epic: 'text-purple-400',
    legendary: 'text-yellow-400',
  }

  const formatTime = (timestamp: number): string => {
    const diff = Date.now() - timestamp
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)
    if (minutes < 1) return 'Moments ago'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    return `${days}d ago`
  }

  if (pullHistory.length === 0) {
    return (
      <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-2 font-nephilim tracking-wide">
          Recent Invocations
        </h3>
        <div className="text-center py-8">
          <div className="text-white/60 mb-2">The chronicle awaits</div>
          <div className="text-sm text-white/60">Perform your first invocation to begin recording</div>
          <button
            onClick={() => navigate('/select')}
            className="mt-4 px-5 py-2.5 bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 rounded-lg text-sm hover:bg-cyan-500/20 transition-colors"
          >
            Begin your first Summoning
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-6">
      <h3 className="text-lg font-semibold text-gray-100 mb-4 font-nephilim tracking-wide">
        Recent Invocations
      </h3>
      <div className="space-y-2 max-h-[400px] overflow-y-auto">
        {pullHistory.slice().reverse().slice(0, 20).map((record, index) => (
          <motion.div
            key={`${record.timestamp}-${index}`}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.03 }}
            className="flex items-center justify-between p-3 rounded-lg bg-white/[0.03] border border-white/[0.06]"
            style={{ borderLeftWidth: 3, borderLeftColor: RARITY_COLORS[record.rarity] || RARITY_COLORS.common }}
          >
            <div className="flex items-center gap-3">
              <div
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: RARITY_COLORS[record.rarity], boxShadow: `0 0 6px ${RARITY_COLORS[record.rarity]}66` }}
              />
              <div>
                <div className={`text-sm font-semibold ${RARITY_TEXT[record.rarity] || 'text-gray-300'}`}>
                  {PERSONA_NAMES[record.personaKey] || record.personaKey}
                </div>
                <div className="text-xs text-white/60">{formatOrderLabel(getRecordOrder(record))}</div>
              </div>
            </div>
            <div className="text-xs text-white/60">{formatTime(record.timestamp)}</div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------
// Main Dashboard Component
// ---------------------------------------------------------------

export const SeekerDashboard: React.FC<SeekerDashboardProps> = ({
  userId,
  className = ''
}) => {
  const navigate = useNavigate()
  const [summary, setSummary] = useState<SeekerSummary | null>(null)
  const [factions, setFactions] = useState<Faction[]>([])
  const [selectedPersonaLore, setSelectedPersonaLore] = useState<string | null>(null)
  const [loreFragments, setLoreFragments] = useState<LoreFragment[]>([])
  const [allLoreFragments, setAllLoreFragments] = useState<LoreFragment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabId>('profile')

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        const [summaryData, factionData] = await Promise.all([
          getSeekerSummary(userId),
          getFactionInfo()
        ])
        setSummary(summaryData)
        setFactions(factionData.factions)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [userId])

  // Load lore for selected persona (used in profile tab)
  useEffect(() => {
    const loadLore = async () => {
      if (!selectedPersonaLore) {
        setLoreFragments([])
        return
      }
      try {
        const lore = await getPersonaLoreWithContent(userId, selectedPersonaLore)
        setLoreFragments(lore)
      } catch (err) {
        console.error('Failed to load lore:', err)
      }
    }
    loadLore()
  }, [userId, selectedPersonaLore])

  // Load all persona lore for the codex tab
  useEffect(() => {
    const loadAllLore = async () => {
      if (!summary || activeTab !== 'codex') return
      try {
        const allPersonaKeys = summary.persona_affinities.map(a => a.persona_key)
        const lorePromises = allPersonaKeys.map(key =>
          getPersonaLoreWithContent(userId, key).catch(() => [] as LoreFragment[])
        )
        const results = await Promise.all(lorePromises)
        setAllLoreFragments(results.flat())
      } catch (err) {
        console.error('Failed to load all lore:', err)
      }
    }
    loadAllLore()
  }, [userId, summary, activeTab])

  // Determine which tabs are visible
  const visibleTabs = useMemo(() => {
    if (!summary) return TABS.filter(t => !t.condition)
    return TABS.filter(t => !t.condition || t.condition(summary))
  }, [summary])

  const handlePersonaClick = (personaKey: string) => {
    // Store the selected persona key so Chat.tsx can pick it up
    localStorage.setItem('nephilim_pending_persona', personaKey)
    navigate('/chat')
  }

  if (loading) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <div className="animate-pulse text-white/60">Loading your journey...</div>
      </div>
    )
  }

  if (error || !summary) {
    return (
      <div className={`text-center p-8 ${className}`}>
        <p className="text-red-400">{error || 'Failed to load dashboard'}</p>
      </div>
    )
  }

  const currentFaction = factions.find(f => f.key === summary.faction_primary)

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Tab Bar */}
      <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-1.5 flex gap-1 overflow-x-auto">
        {visibleTabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              relative flex-1 min-w-0 px-3 py-2.5 rounded-lg
              font-nephilim text-sm tracking-wide
              transition-colors duration-200
              ${activeTab === tab.id
                ? 'text-nephilim-cyan'
                : 'text-white/60 hover:text-white/80'
              }
            `}
          >
            {activeTab === tab.id && (
              <motion.div
                layoutId="dashboard-tab-indicator"
                className="absolute inset-0 bg-white/[0.08] border border-cyan-500/20 rounded-lg"
                transition={{ type: 'spring', bounce: 0.2, duration: 0.5 }}
              />
            )}
            <span className="relative z-10 flex items-center justify-center gap-1.5 whitespace-nowrap">
              <span className="text-xs">{tab.icon}</span>
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="sm:hidden">{tab.label.split(' ')[0]}</span>
            </span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        {activeTab === 'profile' && (
          <motion.div
            key="profile"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.3 }}
            className="space-y-8"
          >
            {/* Header - Rank & Resonance */}
            <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-6">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
                <div>
                  <h2 className="text-2xl font-bold text-gray-100 mb-1">Seeker&apos;s Progress</h2>
                  <p className="text-sm text-gray-200/60">Your journey through the Nephilim Realm</p>
                </div>
                <SeekerRankBadge
                  rank={summary.rank || 'Initiate'}
                  resonance={summary.total_resonance || 0}
                  showResonance
                  size="lg"
                />
              </div>

              {summary.rank_progress && (
                <ResonanceProgress progress={summary.rank_progress} />
              )}
            </div>

            {/* Faction */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-6"
            >
              <h3 className="text-lg font-semibold text-gray-100 mb-4">House Allegiance</h3>

              {currentFaction ? (
                <div className="flex items-center gap-4">
                  <div
                    className="w-16 h-16 rounded-lg flex items-center justify-center text-2xl"
                    style={{ backgroundColor: `${currentFaction.color}20` }}
                  >
                    <span role="img" aria-label="house">&#x1F3DB;&#xFE0F;</span>
                  </div>
                  <div>
                    <h4
                      className="text-xl font-bold"
                      style={{ color: currentFaction.color }}
                    >
                      {currentFaction.name}
                    </h4>
                    <p className="text-sm text-gray-200/60">
                      Patron: {currentFaction.patron}
                    </p>
                    <p className="text-xs text-gray-200/50 mt-1">
                      {currentFaction.values}
                    </p>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="text-gray-200/60 mb-4">You have not yet chosen a House</p>
                  <FactionSelector
                    factions={factions}
                    currentFaction={summary.faction_primary}
                    onSelect={async (key) => {
                      console.log('Selected faction:', key)
                    }}
                  />
                </div>
              )}
            </motion.div>

            {/* Persona Affinities */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-6"
            >
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Nephilim Bonds</h3>

              {summary.persona_affinities.length > 0 ? (
                <div className="grid gap-4 md:grid-cols-2">
                  {summary.persona_affinities.map((affinity, index) => (
                    <motion.div
                      key={affinity.persona_key}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 + index * 0.1 }}
                      className="cursor-pointer hover:bg-white/5 rounded-lg p-3 transition-colors"
                      onClick={() => setSelectedPersonaLore(
                        selectedPersonaLore === affinity.persona_key ? null : affinity.persona_key
                      )}
                    >
                      <AffinityMeter
                        affinity={affinity}
                        personaName={PERSONA_NAMES[affinity.persona_key] || affinity.persona_key}
                        personaColor={PERSONA_COLORS[affinity.persona_key]}
                        showDetails
                      />
                    </motion.div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-200/50 text-center py-4">
                  No bonds formed yet. Start a conversation with a Nephilim to begin.
                </p>
              )}
            </motion.div>

            {/* Lore Codex (when persona selected in profile tab) */}
            {selectedPersonaLore && loreFragments.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-6"
              >
                <LoreCodex
                  fragments={loreFragments}
                  personaName={PERSONA_NAMES[selectedPersonaLore] || selectedPersonaLore}
                  personaColor={PERSONA_COLORS[selectedPersonaLore]}
                  currentMessages={
                    summary.persona_affinities.find(a => a.persona_key === selectedPersonaLore)?.messages_count || 0
                  }
                />
              </motion.div>
            )}

            {/* Stats Summary */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="grid grid-cols-2 md:grid-cols-4 gap-4"
            >
              <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-nephilim-cyan">
                  {summary.total_resonance?.toLocaleString() || 0}
                </div>
                <div className="text-xs text-gray-200/60">Total Resonance</div>
              </div>
              <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-nephilim-magenta">
                  {summary.persona_affinities.length}
                </div>
                <div className="text-xs text-gray-200/60">Bonds Formed</div>
              </div>
              <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-purple-400">
                  {summary.unlocked_lore_count}
                </div>
                <div className="text-xs text-gray-200/60">Lore Unlocked</div>
              </div>
              <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-amber-400">
                  {summary.persona_affinities.reduce((sum, a) => sum + a.messages_count, 0)}
                </div>
                <div className="text-xs text-gray-200/60">Total Messages</div>
              </div>
            </motion.div>
          </motion.div>
        )}

        {activeTab === 'bonds' && (
          <motion.div
            key="bonds"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.3 }}
            className="space-y-6"
          >
            {/* Constellation Map */}
            <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-2 font-nephilim tracking-wide">
                Constellation of Bonds
              </h3>
              <p className="text-sm text-gray-200/50 mb-6">
                Your connections to the Nephilim, mapped across the void
              </p>
              <ConstellationMap summary={summary} onPersonaClick={handlePersonaClick} />
            </div>

            {/* Affinity Details */}
            <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Bond Details</h3>
              {summary.persona_affinities.length > 0 ? (
                <div className="space-y-4">
                  {PERSONA_ORDER.map((key, i) => {
                    const aff = summary.persona_affinities.find(a => a.persona_key === key)
                    if (!aff) {
                      return (
                        <motion.div
                          key={key}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.08 }}
                          className="flex items-center gap-3 p-3 rounded-lg opacity-30"
                        >
                          <div
                            className="w-8 h-8 rounded-full border flex items-center justify-center text-xs"
                            style={{ borderColor: PERSONA_COLORS[key] + '40' }}
                          >
                            ?
                          </div>
                          <div>
                            <span className="text-sm text-gray-200/50 font-nephilim">
                              {PERSONA_NAMES[key]}
                            </span>
                            <p className="text-xs text-white/60">Bond not yet formed</p>
                          </div>
                        </motion.div>
                      )
                    }
                    return (
                      <motion.div
                        key={key}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.08 }}
                        className="p-3 rounded-lg hover:bg-white/5 transition-colors cursor-pointer"
                        onClick={() => handlePersonaClick(key)}
                        role="button"
                        aria-label={`Chat with ${PERSONA_NAMES[key] || key}`}
                      >
                        <AffinityMeter
                          affinity={aff}
                          personaName={PERSONA_NAMES[key] || key}
                          personaColor={PERSONA_COLORS[key]}
                          showDetails
                        />
                      </motion.div>
                    )
                  })}
                </div>
              ) : (
                <p className="text-gray-200/50 text-center py-6">
                  No bonds formed yet. Speak with a Nephilim to forge your first connection.
                </p>
              )}
            </div>
          </motion.div>
        )}

        {activeTab === 'codex' && (
          <motion.div
            key="codex"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.3 }}
            className="space-y-6"
          >
            <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-2 font-nephilim tracking-wide">
                The Lore Codex
              </h3>
              <p className="text-sm text-gray-200/50 mb-6">
                Fragments of knowledge gathered from all Nephilim
              </p>

              {/* Show all lore fragments grouped across personas */}
              {(() => {
                // Group fragments by persona key prefix in fragment_id
                const personaGroups: Record<string, LoreFragment[]> = {}

                for (const frag of allLoreFragments) {
                  // Determine which persona this fragment belongs to
                  let matchedPersona = 'unknown'
                  for (const key of PERSONA_ORDER) {
                    const shortName = key.replace('nephilim_', '')
                    if (frag.fragment_id.toLowerCase().includes(shortName)) {
                      matchedPersona = key
                      break
                    }
                  }
                  if (!personaGroups[matchedPersona]) {
                    personaGroups[matchedPersona] = []
                  }
                  personaGroups[matchedPersona].push(frag)
                }

                const personaKeys = Object.keys(personaGroups).filter(k => k !== 'unknown')
                const unknownFrags = personaGroups['unknown'] || []

                if (allLoreFragments.length === 0) {
                  return (
                    <div className="text-center py-8">
                      <div className="animate-pulse text-white/60">
                        Loading lore fragments...
                      </div>
                    </div>
                  )
                }

                return (
                  <div className="space-y-8">
                    {personaKeys.map(key => (
                      <div key={key}>
                        <LoreCodex
                          fragments={personaGroups[key]}
                          personaName={PERSONA_NAMES[key] || key}
                          personaColor={PERSONA_COLORS[key]}
                          currentMessages={
                            summary.persona_affinities.find(a => a.persona_key === key)?.messages_count || 0
                          }
                        />
                      </div>
                    ))}
                    {unknownFrags.length > 0 && (
                      <div>
                        <LoreCodex
                          fragments={unknownFrags}
                          personaName="Ancient Texts"
                          personaColor="#00ffff"
                          currentMessages={0}
                        />
                      </div>
                    )}
                  </div>
                )
              })()}
            </div>
          </motion.div>
        )}

        {activeTab === 'chronicle' && (
          <motion.div
            key="chronicle"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.3 }}
            className="space-y-6"
          >
            {/* Invocation Stats */}
            <ChronicleStats />

            {/* Recent Invocations */}
            <ChronicleHistory />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default SeekerDashboard
