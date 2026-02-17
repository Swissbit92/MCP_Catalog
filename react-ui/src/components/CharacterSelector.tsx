import React from 'react';
import { motion } from 'framer-motion';

interface PersonaJson {
  key: string;
  display_name: string;
  coordinator_label: string;
  rarity: string;
  image?: string;
  avatar?: string;
}

interface CharacterSelectorProps {
  personas: PersonaJson[];
  currentIndex: number;
  onCharacterSelect: (index: number) => void;
  isTransitioning?: boolean;
}

const CharacterSelector: React.FC<CharacterSelectorProps> = ({
  personas,
  currentIndex,
  onCharacterSelect,
  isTransitioning = false
}) => {
  // Convert API image paths to React app paths
  const getImagePath = (apiPath: string) => {
    if (!apiPath) return '/images/ui/default_avatar.png';
    // Handle both old format (ui/images/) and new format (images/personas/)
    if (apiPath.startsWith('images/')) {
      return '/' + apiPath;
    }
    return apiPath.replace('ui/images/', '/images/');
  };

  return (
    <div className="w-full max-w-4xl mx-auto mt-8">
      {/* Thumbnail Grid */}
      <div className="flex justify-center gap-3 md:gap-4 overflow-x-auto pb-4 px-4 scrollbar-hide">
        {personas.map((persona, index) => (
          <motion.button
            key={persona.key}
            onClick={() => onCharacterSelect(index)}
            disabled={isTransitioning}
            className={`
              relative flex-shrink-0 w-14 h-14 md:w-16 md:h-16 rounded-lg overflow-hidden
              border-2 transition-all duration-300
              ${index === currentIndex
                ? 'border-cyan-400 shadow-lg shadow-cyan-400/30 scale-110'
                : 'border-white/[0.1] hover:border-white/[0.2] hover:scale-105'
              }
              ${isTransitioning ? 'opacity-60 cursor-not-allowed' : ''}
            `}
            whileHover={{ scale: isTransitioning ? 1 : (index === currentIndex ? 1.1 : 1.05) }}
            whileTap={{ scale: isTransitioning ? 1 : 0.95 }}
          >
            {/* Character Image */}
            <img
              src={getImagePath(persona.avatar || persona.image || '')}
              alt={persona.display_name}
              className="w-full h-full object-cover"
              onError={(e) => {
                // Fallback to default image
                const target = e.target as HTMLImageElement;
                target.src = '/images/ui/default_avatar.png';
              }}
            />

            {/* Rarity Indicator */}
            <div className={`
              absolute top-1 right-1 w-2 h-2 rounded-full
              ${persona.rarity === 'legendary' ? 'bg-yellow-400' :
                persona.rarity === 'epic' ? 'bg-purple-400' :
                persona.rarity === 'rare' ? 'bg-blue-400' : 'bg-gray-400'}
            `} />

            {/* NEPHILIM Indicator */}
            {persona.key.startsWith('nephilim_') && (
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-400 via-purple-500 to-pink-500" />
            )}

            {/* Selection Indicator */}
            {index === currentIndex && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute inset-0 bg-cyan-400/20 border-2 border-cyan-400 rounded-lg"
              />
            )}
          </motion.button>
        ))}
      </div>

      {/* Character Counter - Always visible, no fade animation */}
      <div className="text-center mt-4">
        <span className="text-gray-300 text-sm">
          {currentIndex + 1} of {personas.length}
        </span>
      </div>
    </div>
  );
};

export default CharacterSelector;