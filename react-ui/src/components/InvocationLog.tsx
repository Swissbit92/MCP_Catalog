import React from 'react'
import { motion } from 'framer-motion'
import { usePersona } from '../context/PersonaContext'

const RARITY_BORDER_COLORS: Record<string, string> = {
  common: '#C0C0C0',
  rare: '#00BFFF',
  epic: '#DA70D6',
  legendary: '#FFD700',
}

const RARITY_TEXT_COLORS: Record<string, string> = {
  common: 'text-gray-400',
  rare: 'text-cyan-400',
  epic: 'text-purple-400',
  legendary: 'text-yellow-400',
}

const RARITY_LABELS: Record<string, string> = {
  common: 'Wanderer',
  rare: 'Sage',
  epic: 'Warden',
  legendary: 'Archon',
}

const formatNarrativeTime = (timestamp: number): string => {
  const now = Date.now()
  const diff = now - timestamp
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return 'Moments ago'
  if (minutes < 60) return `${minutes} cycle${minutes !== 1 ? 's' : ''} ago`
  if (hours < 24) return `${hours} eon${hours !== 1 ? 's' : ''} ago`
  if (days < 7) return `${days} age${days !== 1 ? 's' : ''} ago`
  return `${Math.floor(days / 7)} epoch${Math.floor(days / 7) !== 1 ? 's' : ''} ago`
}

const InvocationLog: React.FC = () => {
  const { pullHistory, pullStats } = usePersona()

  return (
    <div className="min-h-screen bg-[#0B0B0D]">
      {/* Header */}
      <div className="text-center py-8 px-4">
        <h1 className="text-4xl md:text-5xl font-nephilim font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-cyan-400 mb-3">
          Invocation Chronicle
        </h1>
        <p className="text-lg text-gray-400 max-w-2xl mx-auto">
          A record of every bond forged and deepened through the ritual
        </p>
      </div>

      {/* Stats Overview */}
      <div className="max-w-6xl mx-auto px-4 mb-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white/[0.05] backdrop-blur-xl rounded-xl p-4 border border-white/[0.1]">
            <div className="text-2xl font-bold text-cyan-400">{pullStats.totalPulls}</div>
            <div className="text-sm text-gray-500">Total Invocations</div>
          </div>
          <div className="bg-white/[0.05] backdrop-blur-xl rounded-xl p-4 border border-white/[0.1]">
            <div className="text-2xl font-bold text-fuchsia-400">{pullStats.totalSpent}</div>
            <div className="text-sm text-gray-500">Essence Spent</div>
          </div>
          <div className="bg-white/[0.05] backdrop-blur-xl rounded-xl p-4 border border-white/[0.1]">
            <div className="text-2xl font-bold text-purple-400">{pullStats.archonCount + pullStats.wardenCount + pullStats.sageCount}</div>
            <div className="text-sm text-gray-500">Sage+ Bonds</div>
          </div>
          <div className="bg-white/[0.05] backdrop-blur-xl rounded-xl p-4 border border-white/[0.1]">
            <div className="text-2xl font-bold text-green-400">{pullStats.bestStreak}</div>
            <div className="text-sm text-gray-500">Best Streak</div>
          </div>
        </div>

        {/* Rarity Breakdown */}
        <div className="mt-6 bg-white/[0.05] backdrop-blur-xl rounded-xl p-6 border border-white/[0.1]">
          <h3 className="text-lg font-nephilim tracking-wider text-gray-200 mb-4">Order Attunement</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { rarity: 'legendary', count: pullStats.archonCount },
              { rarity: 'epic', count: pullStats.wardenCount },
              { rarity: 'rare', count: pullStats.sageCount },
              { rarity: 'common', count: pullStats.wandererCount },
            ].map(({ rarity, count }) => (
              <div key={rarity} className="text-center">
                <div
                  className="w-8 h-8 rounded-full mx-auto mb-2"
                  style={{
                    backgroundColor: RARITY_BORDER_COLORS[rarity] + '33',
                    border: `2px solid ${RARITY_BORDER_COLORS[rarity]}`,
                    boxShadow: `0 0 12px ${RARITY_BORDER_COLORS[rarity]}44`,
                  }}
                />
                <div className={`text-xl font-bold ${RARITY_TEXT_COLORS[rarity]}`}>{count}</div>
                <div className="text-sm text-gray-500">{RARITY_LABELS[rarity] || rarity}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Chronicle Entries */}
      <div className="max-w-4xl mx-auto px-4 pb-8">
        <h2 className="text-xl font-nephilim tracking-wider text-gray-200 mb-6">Recent Invocations</h2>

        {pullHistory.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-full border-2 border-cyan-400/20 flex items-center justify-center mx-auto mb-4">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-cyan-400/40">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <div className="text-lg text-gray-400 mb-2">The Chronicle is empty</div>
            <div className="text-gray-500">Perform your first invocation to begin recording your journey</div>
          </div>
        ) : (
          <div className="space-y-3">
            {pullHistory.slice().reverse().map((record, index) => (
              <motion.div
                key={`${record.timestamp}-${index}`}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.04 }}
                className="bg-white/[0.03] backdrop-blur-sm rounded-lg p-4 border border-white/[0.06] flex items-center justify-between"
                style={{
                  borderLeftWidth: 3,
                  borderLeftColor: RARITY_BORDER_COLORS[record.rarity] || RARITY_BORDER_COLORS.common,
                }}
              >
                <div className="flex items-center gap-4">
                  <div
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{
                      backgroundColor: RARITY_BORDER_COLORS[record.rarity],
                      boxShadow: `0 0 8px ${RARITY_BORDER_COLORS[record.rarity]}66`,
                    }}
                  />
                  <div>
                    <div className={`font-semibold ${RARITY_TEXT_COLORS[record.rarity]}`}>
                      {record.personaKey}
                    </div>
                    <div className="text-sm text-gray-500">
                      {RARITY_LABELS[record.rarity] || 'Unknown'} Bond
                    </div>
                  </div>
                </div>
                <div className="text-sm text-gray-500 font-mono">
                  {formatNarrativeTime(record.timestamp)}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default InvocationLog
