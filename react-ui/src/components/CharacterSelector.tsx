import React from 'react';
import { motion } from 'framer-motion';

interface PersonaJson {
  key: string;
  display_name: string;
  coordinator_label: string;
  rarity: string;
  image_path?: string;
}

interface CharacterSelectorProps {
  personas: PersonaJson[];
  currentIndex: number;
  onCharacterSelect: (index: number) => void;
}

const CharacterSelector: React.FC<CharacterSelectorProps> = ({
  personas,
  currentIndex,
  onCharacterSelect
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, duration: 0.4 }}
      className="w-full max-w-4xl mx-auto mt-8"
    >
      {/* Thumbnail Grid */}
      <div className="flex justify-center gap-3 md:gap-4 overflow-x-auto pb-4 px-4 scrollbar-hide">
        {personas.map((persona, index) => (
          <motion.button
            key={persona.key}
            onClick={() => onCharacterSelect(index)}
            className={`
              relative flex-shrink-0 w-14 h-14 md:w-16 md:h-16 rounded-lg overflow-hidden
              border-2 transition-all duration-300
              ${index === currentIndex
                ? 'border-blue-400 shadow-lg shadow-blue-400/30 scale-110'
                : 'border-slate-600/50 hover:border-slate-500/70 hover:scale-105'
              }
            `}
            whileHover={{ scale: index === currentIndex ? 1.1 : 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            {/* Character Image */}
            <img
              src={`/images/${persona.image_path || `${persona.key}_card.png`}`}
              alt={persona.display_name}
              className="w-full h-full object-cover"
              onError={(e) => {
                // Fallback to default image
                const target = e.target as HTMLImageElement;
                target.src = '/images/default_avatar.png';
              }}
            />

            {/* Rarity Indicator */}
            <div className={`
              absolute top-1 right-1 w-2 h-2 rounded-full
              ${persona.rarity === 'legendary' ? 'bg-yellow-400' :
                persona.rarity === 'epic' ? 'bg-purple-400' :
                persona.rarity === 'rare' ? 'bg-blue-400' : 'bg-gray-400'}
            `} />

            {/* Selection Indicator */}
            {index === currentIndex && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute inset-0 bg-blue-400/20 border-2 border-blue-400 rounded-lg"
              />
            )}
          </motion.button>
        ))}
      </div>

      {/* Character Counter */}
      <div className="text-center mt-4">
        <span className="text-slate-400 text-sm">
          {currentIndex + 1} of {personas.length}
        </span>
      </div>
    </motion.div>
  );
};

export default CharacterSelector;