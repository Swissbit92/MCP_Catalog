// src/components/nephilim/FactionSelector.tsx
/**
 * NEPHILIM Faction Selector
 *
 * Allows users to choose their House/Faction affiliation
 * during onboarding or from settings.
 */

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import type { Faction } from '../../services/api'

interface FactionSelectorProps {
  factions: Faction[]
  currentFaction?: string | null
  onSelect: (factionKey: string) => void
  loading?: boolean
  className?: string
}

export const FactionSelector: React.FC<FactionSelectorProps> = ({
  factions,
  currentFaction,
  onSelect,
  loading = false,
  className = ''
}) => {
  const [selected, setSelected] = useState<string | null>(currentFaction || null)

  const handleSelect = (key: string) => {
    setSelected(key)
    onSelect(key)
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="text-center mb-6">
        <h3 className="text-xl font-bold text-white mb-2">Choose Your House</h3>
        <p className="text-sm text-white/60">
          Your faction shapes your journey through the Nephilim Realm
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {factions.map((faction, index) => {
          const isSelected = selected === faction.key

          return (
            <motion.button
              key={faction.key}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              onClick={() => handleSelect(faction.key)}
              disabled={loading}
              className={`
                relative p-4 rounded-xl border-2 text-left
                transition-all duration-300
                ${isSelected
                  ? 'scale-105 shadow-xl'
                  : 'hover:scale-102 hover:shadow-lg opacity-80 hover:opacity-100'}
                ${loading ? 'cursor-not-allowed' : 'cursor-pointer'}
              `}
              style={{
                borderColor: isSelected ? faction.color : `${faction.color}40`,
                backgroundColor: isSelected ? `${faction.color}15` : `${faction.color}05`,
                boxShadow: isSelected ? `0 0 30px ${faction.color}30` : 'none'
              }}
            >
              {/* Selection indicator */}
              {isSelected && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute -top-2 -right-2 w-6 h-6 rounded-full flex items-center justify-center text-white text-xs"
                  style={{ backgroundColor: faction.color }}
                >
                  ✓
                </motion.div>
              )}

              {/* Faction icon/name */}
              <div className="mb-2">
                <span
                  className="text-lg font-bold"
                  style={{ color: faction.color }}
                >
                  {faction.name}
                </span>
              </div>

              {/* Patron */}
              <div className="text-xs text-white/50 mb-2">
                Patron: <span className="text-white/70">{faction.patron}</span>
              </div>

              {/* Values */}
              <p className="text-xs text-white/60 line-clamp-2">
                {faction.values}
              </p>

              {/* Color accent bar */}
              <div
                className="absolute bottom-0 left-0 right-0 h-1 rounded-b-xl"
                style={{ backgroundColor: isSelected ? faction.color : `${faction.color}40` }}
              />
            </motion.button>
          )
        })}
      </div>

      {selected && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mt-4"
        >
          <p className="text-sm text-white/70">
            You have chosen{' '}
            <span
              className="font-semibold"
              style={{ color: factions.find(f => f.key === selected)?.color }}
            >
              House {factions.find(f => f.key === selected)?.name.replace('House ', '')}
            </span>
          </p>
        </motion.div>
      )}
    </div>
  )
}

export default FactionSelector
