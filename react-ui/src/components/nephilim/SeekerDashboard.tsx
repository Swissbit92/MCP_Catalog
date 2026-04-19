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

import React, { useEffect, useState, useMemo, useCallback } from 'react'
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
import { SeekerRankBadge } from './SeekerRankBadge'
import { ResonanceProgress } from './ResonanceProgress'
import { AffinityMeter } from './AffinityMeter'
import { LoreCodex } from './LoreCodex'
import { FactionSelector } from './FactionSelector'
import { ConstellationMap, PERSONA_COLORS, PERSONA_NAMES, PERSONA_ORDER } from './ConstellationMap'
import { ChronicleStats, ChronicleHistory } from './ChronicleComponents'
import { useChat } from '../../context/ChatContext'

interface SeekerDashboardProps {
  userId: string
  className?: string
}

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

export const SeekerDashboard: React.FC<SeekerDashboardProps> = ({
  userId,
  className = ''
}) => {
  const navigate = useNavigate()
  const { personas } = useChat()
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

  // Build relationship map from persona data (keyed by full persona key)
  const relationshipMap = useMemo(() => {
    const map: Record<string, Record<string, string>> = {}
    for (const p of personas) {
      if (p.relationships && p.key.startsWith('nephilim_'))
        map[p.key] = p.relationships
    }
    return map
  }, [personas])

  const visibleTabs = useMemo(() => {
    if (!summary) return TABS.filter(t => !t.condition)
    return TABS.filter(t => !t.condition || t.condition(summary))
  }, [summary])

  const handlePersonaClick = (personaKey: string) => {
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
      <div className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl p-1.5 flex gap-1 overflow-x-auto" role="tablist" aria-label="Dashboard sections">
        {visibleTabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            role="tab"
            aria-selected={activeTab === tab.id}
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
              <ConstellationMap summary={summary} onPersonaClick={handlePersonaClick} relationships={relationshipMap} />
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
                const personaGroups: Record<string, LoreFragment[]> = {}

                for (const frag of allLoreFragments) {
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
            <ChronicleStats />
            <ChronicleHistory />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default SeekerDashboard
