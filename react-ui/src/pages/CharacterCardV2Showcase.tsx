import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import CharacterCard from '../components/CharacterCard'
import SummoningRitual from '../components/SummoningRitual'
import BondsForged from '../components/BondsForged'
import InvocationLog from '../components/InvocationLog'
import NephilimBackground from '../components/NephilimBackground'
import { fetchPersonas } from '../services/api'
import { usePersona } from '../context/PersonaContext'
import { formatOrderLabel } from '../utils/celestialOrder'

interface Persona {
  key: string
  display_name: string
  style: string
  image: string
  avatar?: string
  bg?: string
  rarity: string
  celestial_order?: string
  coordinator_label?: string
  voice?: {
    greeting: string
  }
}

// Staggered entrance animation variants
const containerVariants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.07 }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.9 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: 'spring' as const, stiffness: 300, damping: 20 }
  }
}

const CharacterCardV2Showcase: React.FC = () => {
  const [searchParams] = useSearchParams()
  // Support both old and new tab names for backward compatibility
  const TAB_ALIASES: Record<string, 'cards' | 'ritual' | 'bonds' | 'chronicle'> = {
    cards: 'cards',
    pull: 'ritual',
    ritual: 'ritual',
    collection: 'bonds',
    bonds: 'bonds',
    history: 'chronicle',
    chronicle: 'chronicle',
  }
  const rawTab = searchParams.get('tab') || 'cards'
  const initialTab = TAB_ALIASES[rawTab] || 'cards'

  const [personas, setPersonas] = useState<Persona[]>([])
  const [filteredPersonas, setFilteredPersonas] = useState<Persona[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState<'cards' | 'ritual' | 'bonds' | 'chronicle'>(initialTab)
  const [hoveredPersona, setHoveredPersona] = useState<Persona | null>(null)
  const { setSelectedPersona, selectedPersona } = usePersona()
  const navigate = useNavigate()

  // The persona to show in the preview panel: hovered takes priority, then selected
  const previewPersona = hoveredPersona || selectedPersona as Persona | null

  useEffect(() => {
    const getPersonas = async () => {
      try {
        const fetchedPersonas = await fetchPersonas()
        const mappedPersonas = fetchedPersonas.map(p => ({
          key: p.key,
          display_name: p.display_name || p.key,
          style: p.style,
          image: p.image.replace('images/', ''),
          avatar: p.avatar ? p.avatar.replace('images/', '') : undefined,
          bg: p.bg ? p.bg.replace('images/', '') : undefined,
          rarity: p.rarity,
          celestial_order: p.celestial_order,
          coordinator_label: p.coordinator_label,
          voice: p.voice,
        }))

        // Startup synchronization: clean up localStorage for removed personas
        const currentPersonaKeys = new Set(mappedPersonas.map(p => p.key))
        const storedCollected = localStorage.getItem('collectedPersonas')
        if (storedCollected) {
          const collectedPersonas = JSON.parse(storedCollected)
          const validCollected = collectedPersonas.filter((key: string) => currentPersonaKeys.has(key))
          if (validCollected.length !== collectedPersonas.length) {
            localStorage.setItem('collectedPersonas', JSON.stringify(validCollected))
          }
        }

        setPersonas(mappedPersonas)
        setFilteredPersonas(mappedPersonas)
      } catch (error) {
        console.error('Failed to fetch personas:', error)
        setPersonas([])
        setFilteredPersonas([])
      }
    }

    getPersonas()
  }, [])

  // Filter personas based on search query
  React.useEffect(() => {
    let filtered = personas

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(persona =>
        persona.display_name.toLowerCase().includes(query) ||
        persona.style.toLowerCase().includes(query) ||
        persona.key.toLowerCase().includes(query) ||
        (persona.celestial_order || 'wanderer').toLowerCase().includes(query) ||
        formatOrderLabel(persona.celestial_order || 'wanderer').toLowerCase().includes(query)
      )
    }

    setFilteredPersonas(filtered)
  }, [searchQuery, personas])

  // Card click - selection only (no navigation)
  const handleCardSelect = (personaKey: string) => {
    const personaToSelect = personas.find(p => p.key === personaKey)
    if (personaToSelect) {
      setSelectedPersona(personaToSelect)
    }
  }

  // Choose button - navigate to chat
  const handleChoose = (personaKey: string) => {
    const personaToSelect = personas.find(p => p.key === personaKey)
    if (personaToSelect) {
      setSelectedPersona(personaToSelect)
      navigate('/chat')
    }
  }

  // Navigate to chat from preview panel
  const handleBeginConversation = () => {
    if (previewPersona) {
      setSelectedPersona(previewPersona)
      navigate('/chat')
    }
  }

  // NEPHILIM glassmorphic tab button classes
  const activeTabStyle = 'bg-white/[0.1] border border-cyan-500/50 text-cyan-300 shadow-lg'
  const inactiveTabStyle = 'text-gray-400 hover:text-gray-200 hover:bg-white/[0.05]'
  const tabClass = (tab: string) =>
    `px-6 py-3 rounded-full font-medium transition-all duration-300 ${
      activeTab === tab ? activeTabStyle : inactiveTabStyle
    }`

  if (personas.length === 0) {
    return (
      <NephilimBackground particles={true} skyline={false} intensity={0.4}>
        <div className="min-h-screen flex items-center justify-center">
          <div className="relative z-10 text-center">
            <div className="text-gray-200 text-xl mb-4">Loading Companions...</div>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto"></div>
          </div>
        </div>
      </NephilimBackground>
    )
  }

  return (
    <NephilimBackground particles={true} skyline={true} intensity={0.5}>
      <div className="min-h-screen">
        <div className="relative z-10 max-w-[1600px] mx-auto px-4 py-8">
          {/* Header */}
          <div className="text-center mb-6">
            <h1 className="text-4xl md:text-6xl font-nephilim text-cyan-300 mb-4 tracking-wider">
              Companions
            </h1>
            <p className="text-xl text-gray-200 max-w-3xl mx-auto mb-4">
              Choose your companion from the Nephilim and Wanderers who await your call.
            </p>

            {/* Tab Navigation */}
            <div className="flex justify-center mb-8">
              <div className="bg-[#141418]/60 backdrop-blur-xl rounded-full p-1 border border-white/[0.1]">
                <button onClick={() => setActiveTab('cards')} className={tabClass('cards')}>
                  Companions
                </button>
                <button onClick={() => setActiveTab('ritual')} className={tabClass('ritual')}>
                  Summoning Ritual
                </button>
                <button onClick={() => setActiveTab('bonds')} className={tabClass('bonds')}>
                  Bonds Forged
                </button>
                <button onClick={() => setActiveTab('chronicle')} className={tabClass('chronicle')}>
                  Invocation Chronicle
                </button>
              </div>
            </div>
          </div>

          {/* Tab Content */}
          <AnimatePresence mode="wait">
            {activeTab === 'cards' ? (
              <motion.div
                key="cards"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                {/* Search Bar */}
                <div className="flex justify-center mb-6">
                  <input
                    type="text"
                    placeholder="Search by name, style, or order..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="px-6 py-3 rounded-full bg-[#141418] border border-white/[0.1] text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/30 max-w-md w-full"
                  />
                </div>

                {/* Order Legend */}
                <div className="flex flex-wrap justify-center gap-4 mb-6">
                  {[
                    { order: 'archon', color: 'from-yellow-400 to-amber-600', label: 'Archon' },
                    { order: 'warden', color: 'from-purple-400 to-pink-600', label: 'Warden' },
                    { order: 'sage', color: 'from-cyan-400 to-blue-600', label: 'Sage' },
                    { order: 'wanderer', color: 'from-gray-400 to-slate-600', label: 'Wanderer' }
                  ].map(({ order, color, label }) => (
                    <div key={order} className="flex items-center gap-2 bg-[#141418]/80 backdrop-blur-sm rounded-full px-4 py-2 border border-white/[0.1]">
                      <div className={`w-3 h-3 rounded-full bg-gradient-to-r ${color}`}></div>
                      <span className="text-gray-200 font-medium text-sm">{label}</span>
                    </div>
                  ))}
                </div>

                {/* Main Layout: Grid + Preview Panel */}
                <div className="flex gap-6">
                  {/* Cards Grid - 60% on desktop */}
                  <div className="w-full md:w-[60%]">
                    <motion.div
                      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 justify-items-center"
                      variants={containerVariants}
                      initial="hidden"
                      animate="show"
                      key={searchQuery}
                    >
                      {filteredPersonas.map((persona, index) => (
                        <motion.div
                          key={persona.key}
                          variants={itemVariants}
                          onMouseEnter={() => setHoveredPersona(persona)}
                          onMouseLeave={() => setHoveredPersona(null)}
                        >
                          <CharacterCard
                            name={persona.display_name}
                            style={persona.style}
                            image={`/images/${persona.image}`}
                            celestial_order={persona.celestial_order ?? 'wanderer'}
                            onSelect={handleCardSelect}
                            onChoose={handleChoose}
                            isSelected={selectedPersona?.key === persona.key}
                            personaKey={persona.key}
                            index={index}
                          />
                        </motion.div>
                      ))}
                    </motion.div>
                  </div>

                  {/* Live Preview Panel - 40% on desktop, hidden on mobile */}
                  <div className="hidden md:block w-[40%]">
                    <div className="sticky top-8">
                      <AnimatePresence mode="wait">
                        {previewPersona ? (
                          <motion.div
                            key={previewPersona.key}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                            className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl overflow-hidden"
                          >
                            {/* Preview Image */}
                            <div className="relative w-full aspect-[3/4] overflow-hidden">
                              <img
                                src={`/images/${previewPersona.image}`}
                                alt={previewPersona.display_name}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  (e.target as HTMLImageElement).src = '/images/ui/default_avatar.png'
                                }}
                              />
                              {/* Gradient overlay at bottom of image */}
                              <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#0B0B0D] to-transparent" />
                              {/* Rarity glow at top */}
                              <div className={`absolute top-0 left-0 right-0 h-1 ${
                                previewPersona.celestial_order === 'archon' ? 'bg-gradient-to-r from-yellow-400 to-amber-500' :
                                previewPersona.celestial_order === 'warden' ? 'bg-gradient-to-r from-purple-400 to-fuchsia-500' :
                                previewPersona.celestial_order === 'sage' ? 'bg-gradient-to-r from-cyan-400 to-blue-500' :
                                'bg-gradient-to-r from-gray-400 to-gray-500'
                              }`} />
                            </div>

                            {/* Preview Info */}
                            <div className="p-6 -mt-12 relative z-10">
                              {/* Type badge */}
                              <div className="flex items-center gap-2 mb-2">
                                {previewPersona.key.startsWith('nephilim_') ? (
                                  <span className="text-xs font-bold uppercase tracking-widest px-2 py-1 rounded bg-gradient-to-r from-cyan-500/20 to-fuchsia-500/20 border border-cyan-400/30 text-cyan-400">
                                    Nephilim
                                  </span>
                                ) : (
                                  <span className="text-xs font-bold uppercase tracking-widest px-2 py-1 rounded bg-white/[0.08] border border-white/[0.15] text-gray-300">
                                    Wanderer
                                  </span>
                                )}
                                <span className="text-xs font-bold uppercase tracking-widest px-2 py-1 rounded bg-white/[0.08] border border-white/[0.15] text-gray-400">
                                  {formatOrderLabel(previewPersona.celestial_order || 'wanderer')}
                                </span>
                              </div>

                              {/* Name */}
                              <h2 className="text-2xl font-nephilim text-gray-100 mb-1 tracking-wide">
                                {previewPersona.display_name}
                              </h2>

                              {/* Style description */}
                              <p className="text-gray-200 text-sm mb-3 leading-relaxed italic">
                                {previewPersona.style}
                              </p>

                              {/* Domain / coordinator label */}
                              {previewPersona.coordinator_label && (
                                <div className="mb-4">
                                  <div className="text-xs font-bold uppercase tracking-widest text-cyan-400/80 mb-1">Domain</div>
                                  <p className="text-gray-200 text-sm">{previewPersona.coordinator_label}</p>
                                </div>
                              )}

                              {/* Greeting preview */}
                              {previewPersona.voice?.greeting && (
                                <div className="mb-4 p-3 bg-white/[0.03] rounded-lg border border-white/[0.05]">
                                  <div className="text-xs font-bold uppercase tracking-widest text-fuchsia-400/80 mb-1">Greeting</div>
                                  <p className="text-gray-300 text-sm italic leading-relaxed">
                                    &ldquo;{previewPersona.voice.greeting}&rdquo;
                                  </p>
                                </div>
                              )}

                              {/* CTA Button */}
                              <motion.button
                                onClick={handleBeginConversation}
                                className="w-full py-3 px-6 rounded-lg font-bold text-sm uppercase tracking-widest bg-gradient-to-r from-cyan-500 to-fuchsia-500 text-black shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 transition-shadow"
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                              >
                                Begin Conversation
                              </motion.button>
                            </div>
                          </motion.div>
                        ) : (
                          <motion.div
                            key="empty-preview"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="bg-white/[0.03] backdrop-blur-xl border border-white/[0.08] rounded-xl p-8 text-center min-h-[400px] flex flex-col items-center justify-center"
                          >
                            <div className="text-4xl mb-4 opacity-30">⬡</div>
                            <p className="text-gray-400 text-sm">
                              Hover over a card to preview
                            </p>
                            <p className="text-gray-500 text-xs mt-1">
                              or click to select a companion
                            </p>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                </div>

                {/* Companion Interactions Info */}
                <div className="text-center mt-8">
                  <div className="bg-[#141418]/80 backdrop-blur-xl rounded-2xl p-6 max-w-2xl mx-auto border border-white/[0.1]">
                    <h3 className="text-xl font-bold text-gray-100 mb-4">Companion Interactions</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
                      <div className="text-gray-200">
                        <div className="font-semibold text-cyan-300 mb-2">Holographic Foil</div>
                        <div className="text-sm">Pointer-tracking 3D tilt with dynamic light effects on every card</div>
                      </div>
                      <div className="text-gray-200">
                        <div className="font-semibold text-fuchsia-300 mb-2">Order Resonance</div>
                        <div className="text-sm">Each companion radiates unique energy based on their Celestial Order</div>
                      </div>
                      <div className="text-gray-200">
                        <div className="font-semibold text-cyan-300 mb-2">Fluid Animations</div>
                        <div className="text-sm">Spring-physics entrance effects with smooth hover interactions</div>
                      </div>
                      <div className="text-gray-200">
                        <div className="font-semibold text-fuchsia-300 mb-2">Selection States</div>
                        <div className="text-sm">Glowing selection aura with the invocation button</div>
                      </div>
                    </div>
                    <div className="mt-6 p-4 bg-[#0B0B0D]/60 rounded-lg border border-white/[0.05]">
                      <div className="text-sm text-gray-300">
                        <strong className="text-cyan-400">Tip:</strong> Hover over the cards to activate holographic tracking.
                        Each companion responds uniquely to your presence.
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ) : activeTab === 'ritual' ? (
              <motion.div
                key="ritual"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <SummoningRitual onCharacterSelect={handleCardSelect} />
              </motion.div>
            ) : activeTab === 'bonds' ? (
              <motion.div
                key="bonds"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <BondsForged
                  onCharacterSelect={handleCardSelect}
                  onChoose={handleChoose}
                  selectedPersonaKey={selectedPersona?.key || null}
                />
              </motion.div>
            ) : (
              <motion.div
                key="chronicle"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <InvocationLog />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </NephilimBackground>
  )
}

export default CharacterCardV2Showcase
