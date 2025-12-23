import React from 'react';
import { motion } from 'framer-motion';
import { Search } from 'lucide-react';

interface SearchIndicatorProps {
  personaName?: string;
  rarity?: string;
  className?: string;
}

// Rarity-based color schemes (matching persona colors)
const getRarityColors = (rarity?: string) => {
  switch (rarity) {
    case 'legendary':
      return {
        gradient: 'from-yellow-400 to-amber-500',
        glow: 'shadow-yellow-500/30',
        icon: 'text-yellow-600',
        text: 'text-yellow-700',
      };
    case 'epic':
      return {
        gradient: 'from-purple-400 to-violet-500',
        glow: 'shadow-purple-500/30',
        icon: 'text-purple-600',
        text: 'text-purple-700',
      };
    case 'rare':
      return {
        gradient: 'from-blue-400 to-cyan-500',
        glow: 'shadow-blue-500/30',
        icon: 'text-blue-600',
        text: 'text-blue-700',
      };
    default:
      return {
        gradient: 'from-gray-400 to-slate-500',
        glow: 'shadow-gray-500/30',
        icon: 'text-gray-600',
        text: 'text-gray-700',
      };
  }
};

export const SearchIndicator: React.FC<SearchIndicatorProps> = ({
  personaName = 'Assistant',
  rarity = 'common',
  className = ''
}) => {
  const colors = getRarityColors(rarity);

  return (
    <motion.div
      className={`flex items-center gap-3 px-4 py-3 bg-white/80 backdrop-blur-sm rounded-2xl border-2 border-transparent shadow-lg ${colors.glow} max-w-fit ${className}`}
      initial={{ opacity: 0, scale: 0.8, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.8, y: 10 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      style={{
        borderImage: `linear-gradient(135deg, var(--tw-gradient-stops)) 1`,
      }}
    >
      {/* Animated search icon */}
      <motion.div
        className={`${colors.icon}`}
        animate={{
          rotate: [0, 360],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: 'linear',
        }}
      >
        <Search size={20} />
      </motion.div>

      {/* Animated dots */}
      <div className="flex items-center gap-1">
        <motion.div
          className={`w-2.5 h-2.5 bg-gradient-to-r ${colors.gradient} rounded-full shadow-md`}
          animate={{
            y: [0, -8, 0],
            scale: [1, 1.3, 1],
          }}
          transition={{
            duration: 1,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        <motion.div
          className={`w-2.5 h-2.5 bg-gradient-to-r ${colors.gradient} rounded-full shadow-md`}
          animate={{
            y: [0, -8, 0],
            scale: [1, 1.3, 1],
          }}
          transition={{
            duration: 1,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 0.15,
          }}
        />
        <motion.div
          className={`w-2.5 h-2.5 bg-gradient-to-r ${colors.gradient} rounded-full shadow-md`}
          animate={{
            y: [0, -8, 0],
            scale: [1, 1.3, 1],
          }}
          transition={{
            duration: 1,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 0.3,
          }}
        />
      </div>

      {/* Text with persona name */}
      <span className={`text-sm font-semibold ${colors.text}`}>
        {personaName} is searching the web...
      </span>
    </motion.div>
  );
};
