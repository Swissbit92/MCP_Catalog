import React from 'react';
import { motion } from 'framer-motion';
import { usePersona } from '../context/PersonaContext';
import { formatOrderLabel } from '../utils/celestialOrder';

const RARITY_TO_ORDER: Record<string, string> = {
  legendary: 'archon',
  epic: 'warden',
  rare: 'sage',
  common: 'wanderer',
}
const getRecordOrder = (record: { rarity?: string; celestial_order?: string }): string => {
  if (record.celestial_order) return record.celestial_order.toLowerCase()
  return RARITY_TO_ORDER[(record.rarity || 'common').toLowerCase()] || 'wanderer'
}

const PullHistory: React.FC = () => {
  const { pullHistory, pullStats } = usePersona();

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleString();
  };

  const getOrderColor = (order: string) => {
    switch (order) {
      case 'archon': return 'text-yellow-400';
      case 'warden': return 'text-purple-400';
      case 'sage': return 'text-blue-400';
      default: return 'text-gray-400';
    }
  };

  const getOrderEmoji = (order: string) => {
    switch (order) {
      case 'archon': return '🌟';
      case 'warden': return '💎';
      case 'sage': return '🔥';
      default: return '⚪';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="text-center py-8 px-4">
        <h1 className="text-4xl md:text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-purple-400 to-blue-400 mb-4">
          Pull History & Stats
        </h1>
        <p className="text-xl text-gray-300 max-w-2xl mx-auto">
          Track your gacha journey and pulling statistics
        </p>
      </div>

      {/* Stats Overview */}
      <div className="max-w-6xl mx-auto px-4 mb-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-black/30 backdrop-blur-sm rounded-lg p-4 border border-white/10">
            <div className="text-2xl font-bold text-yellow-400">{pullStats.totalPulls}</div>
            <div className="text-sm text-gray-400">Total Pulls</div>
          </div>
          <div className="bg-black/30 backdrop-blur-sm rounded-lg p-4 border border-white/10">
            <div className="text-2xl font-bold text-purple-400">{pullStats.totalSpent}</div>
            <div className="text-sm text-gray-400">Gems Spent</div>
          </div>
          <div className="bg-black/30 backdrop-blur-sm rounded-lg p-4 border border-white/10">
            <div className="text-2xl font-bold text-blue-400">{pullStats.archonCount + pullStats.wardenCount + pullStats.sageCount}</div>
            <div className="text-sm text-gray-400">Sage+ Pulls</div>
          </div>
          <div className="bg-black/30 backdrop-blur-sm rounded-lg p-4 border border-white/10">
            <div className="text-2xl font-bold text-green-400">{pullStats.bestStreak}</div>
            <div className="text-sm text-gray-400">Best Streak</div>
          </div>
        </div>

        {/* Rarity Breakdown */}
        <div className="mt-6 bg-black/30 backdrop-blur-sm rounded-lg p-6 border border-white/10">
          <h3 className="text-xl font-bold text-white mb-4">Order Breakdown</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-3xl mb-2">🌟</div>
              <div className="text-xl font-bold text-yellow-400">{pullStats.archonCount}</div>
              <div className="text-sm text-gray-400">Archon</div>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-2">💎</div>
              <div className="text-xl font-bold text-purple-400">{pullStats.wardenCount}</div>
              <div className="text-sm text-gray-400">Warden</div>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-2">🔥</div>
              <div className="text-xl font-bold text-blue-400">{pullStats.sageCount}</div>
              <div className="text-sm text-gray-400">Sage</div>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-2">⚪</div>
              <div className="text-xl font-bold text-gray-400">{pullStats.wandererCount}</div>
              <div className="text-sm text-gray-400">Wanderer</div>
            </div>
          </div>
        </div>
      </div>

      {/* Pull History */}
      <div className="max-w-4xl mx-auto px-4 pb-8">
        <h2 className="text-2xl font-bold text-white mb-6">Recent Pulls</h2>

        {pullHistory.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">📊</div>
            <div className="text-xl text-gray-400 mb-4">No pulls recorded yet</div>
            <div className="text-gray-500">Start pulling to see your history!</div>
          </div>
        ) : (
          <div className="space-y-3">
            {pullHistory.slice().reverse().map((record, index) => (
              <motion.div
                key={`${record.timestamp}-${index}`}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-black/20 backdrop-blur-sm rounded-lg p-4 border border-white/10 flex items-center justify-between"
              >
                <div className="flex items-center gap-4">
                  <div className="text-2xl">{getOrderEmoji(getRecordOrder(record))}</div>
                  <div>
                    <div className={`font-semibold ${getOrderColor(getRecordOrder(record))}`}>
                      {record.personaKey}
                    </div>
                    <div className="text-sm text-gray-400">
                      {formatOrderLabel(getRecordOrder(record))} • {record.pullCount}x pull
                    </div>
                  </div>
                </div>
                <div className="text-sm text-gray-500">
                  {formatTime(record.timestamp)}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PullHistory;