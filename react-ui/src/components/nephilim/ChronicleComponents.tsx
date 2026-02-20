import React from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { usePersona } from '../../context/PersonaContext'
import { formatOrderLabel } from '../../utils/celestialOrder'
import { PERSONA_NAMES } from './ConstellationMap'

const getRecordOrder = (rec: { rarity?: string; celestial_order?: string }): string => {
  if (rec.celestial_order) return rec.celestial_order.toLowerCase()
  const m: Record<string, string> = { legendary: 'archon', epic: 'warden', rare: 'sage', common: 'wanderer' }
  return m[rec.rarity?.toLowerCase() || ''] || 'wanderer'
}

export const ChronicleStats: React.FC = () => {
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

export const ChronicleHistory: React.FC = () => {
  const navigate = useNavigate()
  const { pullHistory } = usePersona()

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
