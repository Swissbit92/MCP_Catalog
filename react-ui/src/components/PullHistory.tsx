import React from 'react';
import { motion } from 'framer-motion';
import { usePersona } from '../context/PersonaContext';

const PullHistory: React.FC = () => {
  const { pullHistory, pullStats } = usePersona();

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleString();
  };

  const getRarityColor = (rarity: string) => {
    switch (rarity) {
      case 'legendary': return 'text-yellow-400';
      case 'epic': return 'text-purple-400';
      case 'rare': return 'text-blue-400';
      default: return 'text-gray-400';
    }
  };

  const getRarityEmoji = (rarity: string) => {
    switch (rarity) {
      case 'legendary': return '🌟';
      case 'epic': return '💎';
      case 'rare': return '🔥';
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
            <div className="text-2xl font-bold text-blue-400">{pullStats.legendaryCount + pullStats.epicCount + pullStats.rareCount}</div>
            <div className="text-sm text-gray-400">Rare+ Pulls</div>
          </div>
          <div className="bg-black/30 backdrop-blur-sm rounded-lg p-4 border border-white/10">
            <div className="text-2xl font-bold text-green-400">{pullStats.bestStreak}</div>
            <div className="text-sm text-gray-400">Best Streak</div>
          </div>
        </div>

        {/* Rarity Breakdown */}
        <div className="mt-6 bg-black/30 backdrop-blur-sm rounded-lg p-6 border border-white/10">
          <h3 className="text-xl font-bold text-white mb-4">Rarity Breakdown</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-3xl mb-2">🌟</div>
              <div className="text-xl font-bold text-yellow-400">{pullStats.legendaryCount}</div>
              <div className="text-sm text-gray-400">Legendary</div>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-2">💎</div>
              <div className="text-xl font-bold text-purple-400">{pullStats.epicCount}</div>
              <div className="text-sm text-gray-400">Epic</div>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-2">🔥</div>
              <div className="text-xl font-bold text-blue-400">{pullStats.rareCount}</div>
              <div className="text-sm text-gray-400">Rare</div>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-2">⚪</div>
              <div className="text-xl font-bold text-gray-400">{pullStats.commonCount}</div>
              <div className="text-sm text-gray-400">Common</div>
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
                  <div className="text-2xl">{getRarityEmoji(record.rarity)}</div>
                  <div>
                    <div className={`font-semibold ${getRarityColor(record.rarity)}`}>
                      {record.personaKey}
                    </div>
                    <div className="text-sm text-gray-400 capitalize">
                      {record.rarity} • {record.pullCount}x pull
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