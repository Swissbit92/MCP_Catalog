import React from 'react'
import { motion } from 'framer-motion'
import { usePersona } from '../context/PersonaContext'
import { fetchPersonas } from '../services/api'

interface BondsForgedProps {
  onCharacterSelect: (personaKey: string) => void
  onChoose?: (personaKey: string) => void
  selectedPersonaKey?: string | null
}

const RARITY_COLORS: Record<string, string> = {
  common: '#C0C0C0',
  rare: '#00BFFF',
  epic: '#DA70D6',
  legendary: '#FFD700',
}

const RARITY_TEXT_CLASSES: Record<string, string> = {
  common: 'text-gray-400',
  rare: 'text-cyan-400',
  epic: 'text-purple-400',
  legendary: 'text-yellow-400',
}

const BondsForged: React.FC<BondsForgedProps> = ({ onCharacterSelect, onChoose, selectedPersonaKey }) => {
  const { isCollected, collectionStats, pullHistory } = usePersona()
  const [personas, setPersonas] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    const loadPersonas = async () => {
      try {
        const data = await fetchPersonas()
        setPersonas(data)
      } catch (error) {
        console.error('Failed to load personas:', error)
      } finally {
        setLoading(false)
      }
    }
    loadPersonas()
  }, [])

  // Calculate bond level (duplicate count) for each persona
  const getBondLevel = (personaKey: string): number => {
    return pullHistory.filter(r => r.personaKey === personaKey).length
  }

  const collectedPersonasData = personas.filter(persona => isCollected(persona.key))
  const uncollectedPersonasData = personas.filter(persona => !isCollected(persona.key))

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B0B0D] flex items-center justify-center">
        <div className="text-center">
          <motion.div
            className="w-12 h-12 rounded-full border-2 border-cyan-400/30 border-t-cyan-400 mx-auto mb-4"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          />
          <div className="text-gray-400 font-nephilim tracking-wider">Consulting the void...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0B0B0D]">
      {/* Header */}
      <div className="text-center py-8 px-4">
        <h1 className="text-4xl md:text-5xl font-nephilim font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-cyan-400 mb-3">
          Bonds Forged
        </h1>
        <p className="text-lg text-gray-400 max-w-2xl mx-auto mb-6">
          Your constellation of awakened companions
        </p>

        {/* Collection Stats */}
        <div className="flex justify-center gap-4 mb-8 flex-wrap">
          <div className="bg-white/[0.05] backdrop-blur-xl rounded-xl px-5 py-3 border border-white/[0.1]">
            <div className="text-2xl font-bold text-cyan-400">{collectionStats.total}</div>
            <div className="text-xs text-gray-500">Bonded</div>
          </div>
          <div className="bg-white/[0.05] backdrop-blur-xl rounded-xl px-5 py-3 border border-white/[0.1]">
            <div className="text-2xl font-bold text-gray-500">{uncollectedPersonasData.length}</div>
            <div className="text-xs text-gray-500">Awaiting</div>
          </div>
          <div className="bg-white/[0.05] backdrop-blur-xl rounded-xl px-5 py-3 border border-white/[0.1]">
            <div className="text-2xl font-bold text-fuchsia-400">
              {personas.length > 0 ? Math.round((collectedPersonasData.length / personas.length) * 100) : 0}%
            </div>
            <div className="text-xs text-gray-500">Complete</div>
          </div>
        </div>
      </div>

      {/* Collection Grid */}
      <div className="max-w-7xl mx-auto px-4 pb-8">
        {/* Bonded Companions */}
        {collectedPersonasData.length > 0 && (
          <div className="mb-10">
            <h2 className="font-nephilim text-lg tracking-wider text-gray-300 mb-4">
              Active Bonds
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {collectedPersonasData.map((persona, index) => {
                const bondLevel = getBondLevel(persona.key)
                const rarityColor = RARITY_COLORS[persona.rarity] || RARITY_COLORS.common
                const isSelected = selectedPersonaKey === persona.key

                return (
                  <motion.div
                    key={persona.key}
                    initial={{ opacity: 0, y: 20, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ delay: index * 0.06 }}
                    className="group cursor-pointer"
                    onClick={() => onCharacterSelect(persona.key)}
                  >
                    <div
                      className={`relative rounded-xl overflow-hidden transition-all duration-300 ${
                        isSelected ? 'ring-2 ring-cyan-400 ring-offset-2 ring-offset-[#0B0B0D]' : ''
                      }`}
                      style={{
                        border: `2px solid ${rarityColor}44`,
                        boxShadow: `0 0 20px ${rarityColor}22`,
                      }}
                    >
                      {/* Character image */}
                      <div className="aspect-[3/4] overflow-hidden">
                        <img
                          src={`/images/${persona.image.replace('images/', '')}`}
                          alt={persona.display_name || persona.key}
                          className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                        />
                      </div>

                      {/* Rarity glow overlay */}
                      <div
                        className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                        style={{
                          background: `linear-gradient(to top, ${rarityColor}33 0%, transparent 50%)`,
                        }}
                      />

                      {/* Info bar */}
                      <div className="absolute bottom-0 left-0 right-0 bg-black/70 backdrop-blur-sm p-2">
                        <div className={`text-sm font-semibold truncate ${RARITY_TEXT_CLASSES[persona.rarity] || 'text-gray-300'}`}>
                          {persona.display_name || persona.key}
                        </div>
                        <div className="flex items-center justify-between mt-0.5">
                          <div className="text-xs text-gray-500 capitalize">{persona.rarity}</div>
                          {bondLevel > 1 && (
                            <div className="text-xs text-fuchsia-400">
                              Bond Lv. {bondLevel}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Bond level indicator */}
                      {bondLevel > 0 && (
                        <div
                          className="absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                          style={{
                            backgroundColor: rarityColor + '33',
                            border: `1px solid ${rarityColor}`,
                            color: rarityColor,
                          }}
                        >
                          {bondLevel}
                        </div>
                      )}
                    </div>

                    {/* Choose button on hover */}
                    {onChoose && (
                      <motion.button
                        className="w-full mt-2 py-1.5 rounded-lg text-xs font-nephilim tracking-wider text-cyan-400 border border-cyan-400/30 bg-cyan-400/5 hover:bg-cyan-400/10 transition-colors opacity-0 group-hover:opacity-100"
                        onClick={(e) => {
                          e.stopPropagation()
                          onChoose(persona.key)
                        }}
                        whileTap={{ scale: 0.95 }}
                      >
                        Commune
                      </motion.button>
                    )}
                  </motion.div>
                )
              })}
            </div>
          </div>
        )}

        {/* Uncollected / Awaiting Invocation */}
        {uncollectedPersonasData.length > 0 && (
          <div>
            <h2 className="font-nephilim text-lg tracking-wider text-gray-500 mb-4">
              Awaiting Invocation
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {uncollectedPersonasData.map((persona, index) => (
                <motion.div
                  key={persona.key}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: (collectedPersonasData.length + index) * 0.04 }}
                >
                  <div className="relative rounded-xl overflow-hidden border border-white/[0.06] bg-white/[0.02]">
                    {/* Silhouette */}
                    <div className="aspect-[3/4] overflow-hidden relative">
                      <img
                        src={`/images/${persona.image.replace('images/', '')}`}
                        alt="Unknown"
                        className="w-full h-full object-cover"
                        style={{ filter: 'brightness(0) contrast(0.8)' }}
                      />
                      {/* Question mark overlay */}
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-4xl text-white/10 font-nephilim">?</span>
                      </div>
                    </div>

                    {/* Info bar */}
                    <div className="absolute bottom-0 left-0 right-0 bg-black/70 backdrop-blur-sm p-2">
                      <div className="text-sm text-gray-500 font-semibold">???</div>
                      <div className="text-xs text-gray-500">Awaiting Invocation</div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {personas.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-full border-2 border-cyan-400/20 flex items-center justify-center mx-auto mb-4">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-cyan-400/40">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
            </div>
            <div className="text-lg text-gray-400 mb-2">No companions found</div>
            <div className="text-gray-500">Begin your summoning ritual to forge new bonds</div>
          </div>
        )}
      </div>
    </div>
  )
}

export default BondsForged
