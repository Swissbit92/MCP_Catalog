import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import CharacterCard from '../components/CharacterCard';
import PullInterface from '../components/PullInterface';
import CharacterCollection from '../components/CharacterCollection';
import PullHistory from '../components/PullHistory';
import { fetchPersonas } from '../services/api';
import { usePersona } from '../context/PersonaContext';

interface Persona {
  key: string;
  display_name: string;
  style: string;
  image: string;
  avatar?: string;
  bg?: string;
  rarity: string;
  coordinator_label?: string;
  voice?: {
    greeting: string;
  };
}

const CharacterCardV2Showcase: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialTab = (searchParams.get('tab') as 'cards' | 'pull' | 'collection' | 'history') || 'cards';

  const [personas, setPersonas] = useState<Persona[]>([]);
  const [filteredPersonas, setFilteredPersonas] = useState<Persona[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'cards' | 'pull' | 'collection' | 'history'>(initialTab);
  const { setSelectedPersona } = usePersona();
  const navigate = useNavigate();

  useEffect(() => {
    const getPersonas = async () => {
      try {
        const fetchedPersonas = await fetchPersonas();
        const mappedPersonas = fetchedPersonas.map(p => ({
          key: p.key,
          display_name: p.display_name || p.key,
          style: p.style,
          image: p.image.replace('images/', ''),
          avatar: p.avatar ? p.avatar.replace('images/', '') : undefined,
          bg: p.bg ? p.bg.replace('images/', '') : undefined,
          rarity: p.rarity,
          coordinator_label: p.coordinator_label,
          voice: p.voice,
        }));

        // Startup synchronization: clean up localStorage for removed personas
        const currentPersonaKeys = new Set(mappedPersonas.map(p => p.key));
        const storedCollected = localStorage.getItem('collectedPersonas');
        if (storedCollected) {
          const collectedPersonas = JSON.parse(storedCollected);
          const validCollected = collectedPersonas.filter((key: string) => currentPersonaKeys.has(key));
          if (validCollected.length !== collectedPersonas.length) {
            localStorage.setItem('collectedPersonas', JSON.stringify(validCollected));
            console.log(`Cleaned up ${collectedPersonas.length - validCollected.length} removed personas from collection`);
          }
        }

        setPersonas(mappedPersonas);
        setFilteredPersonas(mappedPersonas);
      } catch (error) {
        console.error('Failed to fetch personas:', error);
        // Fallback to empty state if API fails
        setPersonas([]);
        setFilteredPersonas([]);
      }
    };

    getPersonas();
  }, []);

  // Filter personas based on search query
  React.useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredPersonas(personas);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = personas.filter(persona =>
        persona.display_name.toLowerCase().includes(query) ||
        persona.style.toLowerCase().includes(query) ||
        persona.key.toLowerCase().includes(query) ||
        persona.rarity.toLowerCase().includes(query)
      );
      setFilteredPersonas(filtered);
    }
  }, [searchQuery, personas]);

  const handleCardSelect = async (personaKey: string) => {
    const personaToSelect = personas.find(p => p.key === personaKey);
    if (personaToSelect) {
      setSelectedPersona(personaToSelect);
      // Navigate to chat - let the Chat component handle session logic
      navigate('/chat');
    }
  };

  if (personas.length === 0) {
    return (
      <div className="min-h-screen relative overflow-hidden flex items-center justify-center">
        {/* Deep space gradient background (Option 6: Glassmorphic + Rarity Hybrid) */}
        <div className="absolute inset-0 space-background"></div>
        <div className="absolute inset-0 nebula-overlay"></div>

        <div className="relative z-10 text-center">
          <div className="text-white text-xl mb-4">Loading Classic Cards...</div>
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-400 mx-auto"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Deep space gradient background (Option 6: Glassmorphic + Rarity Hybrid) */}
      <div className="absolute inset-0 space-background"></div>
      <div className="absolute inset-0 nebula-overlay"></div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="text-4xl md:text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-purple-400 to-blue-400 mb-4">
            Classic Character Cards
          </h1>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto mb-8">
            Experience the timeless gacha-style character cards featuring your AI companions.
            Classic foil effects, elegant rarity theming, and smooth animations that started it all.
          </p>

          {/* Tab Navigation */}
          <div className="flex justify-center mb-8">
            <div className="bg-black/30 backdrop-blur-sm rounded-full p-1 border border-white/10">
              <button
                onClick={() => setActiveTab('cards')}
                className={`px-6 py-3 rounded-full font-medium transition-all duration-300 ${
                  activeTab === 'cards'
                    ? 'bg-gradient-to-r from-yellow-400 to-orange-500 text-black shadow-lg'
                    : 'text-white hover:bg-white/10'
                }`}
              >
                Card Gallery
              </button>
              <button
                onClick={() => setActiveTab('pull')}
                className={`px-6 py-3 rounded-full font-medium transition-all duration-300 ${
                  activeTab === 'pull'
                    ? 'bg-gradient-to-r from-yellow-400 to-orange-500 text-black shadow-lg'
                    : 'text-white hover:bg-white/10'
                }`}
              >
                Gacha Pull
              </button>
              <button
                onClick={() => setActiveTab('collection')}
                className={`px-6 py-3 rounded-full font-medium transition-all duration-300 ${
                  activeTab === 'collection'
                    ? 'bg-gradient-to-r from-yellow-400 to-orange-500 text-black shadow-lg'
                    : 'text-white hover:bg-white/10'
                }`}
              >
                My Collection
              </button>
              <button
                onClick={() => setActiveTab('history')}
                className={`px-6 py-3 rounded-full font-medium transition-all duration-300 ${
                  activeTab === 'history'
                    ? 'bg-gradient-to-r from-yellow-400 to-orange-500 text-black shadow-lg'
                    : 'text-white hover:bg-white/10'
                }`}
              >
                Pull History
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
            placeholder="Search by name, style, or rarity..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-6 py-3 rounded-full bg-black/30 backdrop-blur-sm border border-white/10 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent max-w-md w-full"
          />
        </div>

        {/* Rarity Legend */}
        <div className="flex flex-wrap justify-center gap-4 mb-6">
          {[
            { rarity: 'legendary', color: 'from-yellow-400 to-amber-600', label: 'Legendary' },
            { rarity: 'epic', color: 'from-purple-400 to-pink-600', label: 'Epic' },
            { rarity: 'rare', color: 'from-blue-400 to-cyan-600', label: 'Rare' },
            { rarity: 'common', color: 'from-gray-400 to-slate-600', label: 'Common' }
          ].map(({ rarity, color, label }) => (
            <div key={rarity} className="flex items-center gap-2 bg-black/30 backdrop-blur-sm rounded-full px-4 py-2 border border-white/10">
              <div className={`w-3 h-3 rounded-full bg-gradient-to-r ${color}`}></div>
              <span className="text-white font-medium">{label}</span>
            </div>
          ))}
        </div>

        {/* Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 justify-items-center">
          {filteredPersonas.map((persona, index) => (
            <CharacterCard
              key={persona.key}
              name={persona.display_name}
              style={persona.style}
              image={`/images/${persona.image}`}
              rarity={persona.rarity}
              onSelect={handleCardSelect}
              isSelected={false}
              personaKey={persona.key}
              index={index}
            />
          ))}
        </div>

        {/* Instructions */}
        <div className="text-center mt-8">
          <div className="bg-black/20 backdrop-blur-sm rounded-2xl p-6 max-w-2xl mx-auto border border-white/10">
            <h3 className="text-xl font-bold text-white mb-4">Interactive Features</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
              <div className="text-gray-300">
                <div className="font-semibold text-yellow-400 mb-2">✨ Classic Foil Effects</div>
                <div className="text-sm">Traditional card frames with elegant foil overlays and glint effects</div>
              </div>
              <div className="text-gray-300">
                <div className="font-semibold text-purple-400 mb-2">🎯 Rarity Theming</div>
                <div className="text-sm">Beautiful gradient colors and styling based on character rarity</div>
              </div>
              <div className="text-gray-300">
                <div className="font-semibold text-blue-400 mb-2">🎮 Smooth Animations</div>
                <div className="text-sm">Gentle hover effects with subtle lift and rotation animations</div>
              </div>
              <div className="text-gray-300">
                <div className="font-semibold text-green-400 mb-2">🎨 Selection States</div>
                <div className="text-sm">Clean selection highlighting with the classic "Choose" button</div>
              </div>
            </div>
            <div className="mt-6 p-4 bg-black/30 rounded-lg">
              <div className="text-sm text-gray-300">
                <strong className="text-cyan-400">💡 Pro Tip:</strong> Hover over the cards to see the classic gacha animations!
                Each card has its own personality with smooth entrance effects and elegant interactions.
              </div>
            </div>
          </div>
        </div>
            </motion.div>
          ) : activeTab === 'pull' ? (
            <motion.div
              key="pull"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <PullInterface onCharacterSelect={handleCardSelect} />
            </motion.div>
          ) : activeTab === 'collection' ? (
            <motion.div
              key="collection"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <CharacterCollection onCharacterSelect={handleCardSelect} />
            </motion.div>
          ) : (
            <motion.div
              key="history"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <PullHistory />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default CharacterCardV2Showcase;