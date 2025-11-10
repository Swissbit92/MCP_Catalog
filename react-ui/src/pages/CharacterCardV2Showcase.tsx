import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CharacterCardV2 from '../components/CharacterCardV2';
import PullInterface from '../components/PullInterface';
import CharacterCollection from '../components/CharacterCollection';
import PullHistory from '../components/PullHistory';
import { fetchPersonas } from '../services/api';

interface Persona {
  key: string;
  display_name: string;
  style: string;
  image: string;
  rarity: string;
  voice?: {
    greeting: string;
  };
}

const CharacterCardV2Showcase: React.FC = () => {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'cards' | 'pull' | 'collection' | 'history'>('cards');

  useEffect(() => {
    const getPersonas = async () => {
      try {
        const fetchedPersonas = await fetchPersonas();
        const mappedPersonas = fetchedPersonas.map(p => ({
          key: p.key,
          display_name: p.display_name || p.key,
          style: p.style,
          image: p.image.replace('ui/images/', ''),
          rarity: p.rarity,
        }));
        setPersonas(mappedPersonas);
      } catch (error) {
        console.error('Failed to fetch personas:', error);
      }
    };

    getPersonas();
  }, []);

  const handleCardSelect = (personaKey: string) => {
    setSelectedCard(personaKey === selectedCard ? null : personaKey);
  };

  if (personas.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="text-white text-xl mb-4">Loading Holographic Cards...</div>
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-400 mx-auto"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl md:text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-purple-400 to-blue-400 mb-4">
            Holographic Character Cards V2
          </h1>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto mb-8">
            Experience the next generation of gacha-style character cards with premium holographic effects,
            dynamic rarity theming, and immersive visual design.
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

        {/* Rarity Legend */}
        <div className="flex flex-wrap justify-center gap-4 mb-8">
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8 justify-items-center">
          {personas.map((persona, index) => (
            <CharacterCardV2
              key={persona.key}
              name={persona.display_name}
              style={persona.style}
              image={`/images/${persona.image}`}
              rarity={persona.rarity}
              onSelect={handleCardSelect}
              isSelected={selectedCard === persona.key}
              personaKey={persona.key}
              index={index}
            />
          ))}
        </div>

        {/* Instructions */}
        <div className="text-center mt-12">
          <div className="bg-black/20 backdrop-blur-sm rounded-2xl p-6 max-w-2xl mx-auto border border-white/10">
            <h3 className="text-xl font-bold text-white mb-4">Interactive Features</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
              <div className="text-gray-300">
                <div className="font-semibold text-yellow-400 mb-2">✨ Holographic Effects</div>
                <div className="text-sm">Multi-layered backgrounds with animated foil effects</div>
              </div>
              <div className="text-gray-300">
                <div className="font-semibold text-purple-400 mb-2">🎯 Rarity Theming</div>
                <div className="text-sm">Dynamic colors and glows based on character rarity</div>
              </div>
              <div className="text-gray-300">
                <div className="font-semibold text-blue-400 mb-2">🎮 3D Physics Engine</div>
                <div className="text-sm">Mouse-following tilt with realistic shadows and parallax</div>
              </div>
              <div className="text-gray-300">
                <div className="font-semibold text-green-400 mb-2">🎨 Selection States</div>
                <div className="text-sm">Animated rings and sparkles for selected cards</div>
              </div>
            </div>
            <div className="mt-6 p-4 bg-black/30 rounded-lg">
              <div className="text-sm text-gray-300">
                <strong className="text-cyan-400">💡 Pro Tip:</strong> Move your mouse over the cards to see the realistic 3D physics in action!
                The cards tilt and cast dynamic shadows that follow your cursor movement.
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