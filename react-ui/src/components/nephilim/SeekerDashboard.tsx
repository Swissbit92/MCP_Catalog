// src/components/nephilim/SeekerDashboard.tsx
/**
 * NEPHILIM Seeker Dashboard
 *
 * Comprehensive view of user's progression, affinities,
 * and unlocked lore across all personas.
 */

import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
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

interface SeekerDashboardProps {
  userId: string
  className?: string
}

// NEPHILIM persona colors
const PERSONA_COLORS: Record<string, string> = {
  'nephilim_eeva': '#e0c3fc',
  'nephilim_aegis': '#4a90d9',
  'nephilim_solace': '#7eb8da',
  'nephilim_nyx': '#9b59b6',
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

export const SeekerDashboard: React.FC<SeekerDashboardProps> = ({
  userId,
  className = ''
}) => {
  const [summary, setSummary] = useState<SeekerSummary | null>(null)
  const [factions, setFactions] = useState<Faction[]>([])
  const [selectedPersonaLore, setSelectedPersonaLore] = useState<string | null>(null)
  const [loreFragments, setLoreFragments] = useState<LoreFragment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
    <div className={`space-y-8 ${className}`}>
      {/* Header - Rank & Resonance */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="nephilim-glass rounded-xl p-6"
      >
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">Seeker's Progress</h2>
            <p className="text-sm text-white/60">Your journey through the Nephilim Realm</p>
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
      </motion.div>

      {/* Faction */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="nephilim-glass rounded-xl p-6"
      >
        <h3 className="text-lg font-semibold text-white mb-4">House Allegiance</h3>

        {currentFaction ? (
          <div className="flex items-center gap-4">
            <div
              className="w-16 h-16 rounded-lg flex items-center justify-center text-2xl"
              style={{ backgroundColor: `${currentFaction.color}20` }}
            >
              🏛️
            </div>
            <div>
              <h4
                className="text-xl font-bold"
                style={{ color: currentFaction.color }}
              >
                {currentFaction.name}
              </h4>
              <p className="text-sm text-white/60">
                Patron: {currentFaction.patron}
              </p>
              <p className="text-xs text-white/50 mt-1">
                {currentFaction.values}
              </p>
            </div>
          </div>
        ) : (
          <div>
            <p className="text-white/60 mb-4">You have not yet chosen a House</p>
            <FactionSelector
              factions={factions}
              currentFaction={summary.faction_primary}
              onSelect={async (key) => {
                // This would call setSeekerFaction API
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
        className="nephilim-glass rounded-xl p-6"
      >
        <h3 className="text-lg font-semibold text-white mb-4">Nephilim Bonds</h3>

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
          <p className="text-white/50 text-center py-4">
            No bonds formed yet. Start a conversation with a Nephilim to begin.
          </p>
        )}
      </motion.div>

      {/* Lore Codex (when persona selected) */}
      {selectedPersonaLore && loreFragments.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="nephilim-glass rounded-xl p-6"
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
        <div className="nephilim-glass rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-nephilim-cyan">
            {summary.total_resonance?.toLocaleString() || 0}
          </div>
          <div className="text-xs text-white/60">Total Resonance</div>
        </div>
        <div className="nephilim-glass rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-nephilim-magenta">
            {summary.persona_affinities.length}
          </div>
          <div className="text-xs text-white/60">Bonds Formed</div>
        </div>
        <div className="nephilim-glass rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-purple-400">
            {summary.unlocked_lore_count}
          </div>
          <div className="text-xs text-white/60">Lore Unlocked</div>
        </div>
        <div className="nephilim-glass rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-amber-400">
            {summary.persona_affinities.reduce((sum, a) => sum + a.messages_count, 0)}
          </div>
          <div className="text-xs text-white/60">Total Messages</div>
        </div>
      </motion.div>
    </div>
  )
}

export default SeekerDashboard
