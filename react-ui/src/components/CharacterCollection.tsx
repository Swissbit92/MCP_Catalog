import React from 'react';
import { motion } from 'framer-motion';
import CharacterCard from './CharacterCard';
import { usePersona } from '../context/PersonaContext';
import { fetchPersonas } from '../services/api';

interface CharacterCollectionProps {
  onCharacterSelect: (personaKey: string) => void;
  onChoose?: (personaKey: string) => void;
  selectedPersonaKey?: string | null;
}

const CharacterCollection: React.FC<CharacterCollectionProps> = ({ onCharacterSelect, onChoose, selectedPersonaKey }) => {
  const { isCollected, collectionStats } = usePersona();
  const [personas, setPersonas] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const loadPersonas = async () => {
      try {
        const data = await fetchPersonas();
        setPersonas(data);
      } catch (error) {
        console.error('Failed to load personas:', error);
      } finally {
        setLoading(false);
      }
    };
    loadPersonas();
  }, []);

  const collectedPersonasData = personas.filter(persona => isCollected(persona.key));

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading collection...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="text-center py-8 px-4">
        <h1 className="text-4xl md:text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-purple-400 to-blue-400 mb-4">
          Character Collection
        </h1>
        <p className="text-xl text-gray-300 max-w-2xl mx-auto mb-6">
          Your holographic card collection
        </p>

        {/* Collection Stats */}
        <div className="flex justify-center gap-6 mb-8">
          <div className="glass-card rounded-lg px-4 py-2">
            <div className="text-2xl font-bold text-yellow-400">{collectionStats.total}</div>
            <div className="text-sm text-gray-400">Total</div>
          </div>
          <div className="glass-card rounded-lg px-4 py-2">
            <div className="text-2xl font-bold text-purple-400">{collectionStats.legendary}</div>
            <div className="text-sm text-gray-400">Archon</div>
          </div>
          <div className="glass-card rounded-lg px-4 py-2">
            <div className="text-2xl font-bold text-blue-400">{collectionStats.epic}</div>
            <div className="text-sm text-gray-400">Warden</div>
          </div>
          <div className="glass-card rounded-lg px-4 py-2">
            <div className="text-2xl font-bold text-green-400">{collectionStats.rare}</div>
            <div className="text-sm text-gray-400">Sage</div>
          </div>
        </div>
      </div>

      {/* Collection Grid */}
      <div className="max-w-7xl mx-auto px-4 pb-8">
        {collectedPersonasData.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">📭</div>
            <div className="text-xl text-gray-400 mb-4">No characters collected yet</div>
            <div className="text-gray-500">Pull some characters to start your collection!</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {collectedPersonasData.map((persona, index) => (
              <motion.div
                key={persona.key}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex justify-center"
              >
                <CharacterCard
                  name={persona.display_name || persona.key}
                  style={persona.style}
                  image={`/images/${persona.image.replace('images/', '')}`}
                  celestial_order={persona.celestial_order ?? 'wanderer'}
                  onSelect={onCharacterSelect}
                  onChoose={onChoose}
                  isSelected={selectedPersonaKey === persona.key}
                  personaKey={persona.key}
                  index={index}
                />
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="text-center py-4 px-4 border-t border-gray-700 mt-8">
        <div className="text-sm text-gray-400">
          Keep pulling to complete your collection!
        </div>
      </div>
    </div>
  );
};

export default CharacterCollection;