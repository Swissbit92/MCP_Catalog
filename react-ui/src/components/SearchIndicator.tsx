import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Search } from 'lucide-react';
import {
  isNephilimPersona,
  getRandomLoadingMessage,
  NEPHILIM_SOURCE_NARRATIVES,
} from './nephilim/mcpNarratives';

interface SearchIndicatorProps {
  personaName?: string;
  personaKey?: string;
  celestial_order?: string;
  searchType?: 'brave_mcp' | 'llm';
  className?: string;
}

// Celestial Order-based color schemes (matching persona colors)
const getOrderColors = (celestial_order?: string) => {
  switch (celestial_order) {
    case 'archon':
      return {
        gradient: 'from-yellow-400 to-amber-500',
        glow: 'shadow-yellow-500/30',
        icon: 'text-yellow-600',
        text: 'text-yellow-700',
      };
    case 'warden':
      return {
        gradient: 'from-purple-400 to-violet-500',
        glow: 'shadow-purple-500/30',
        icon: 'text-purple-600',
        text: 'text-purple-700',
      };
    case 'sage':
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

// NEPHILIM persona colors
const NEPHILIM_COLORS: Record<string, string> = {
  nephilim_eeva: '#e0c3fc',
  nephilim_aegis: '#4a90d9',
  nephilim_solace: '#7eb8da',
  nephilim_nyx: '#b07cc6',
  nephilim_cipher: '#2ecc71',
  nephilim_aurora: '#f39c12',
};

export const SearchIndicator: React.FC<SearchIndicatorProps> = ({
  personaName = 'Assistant',
  personaKey,
  celestial_order = 'wanderer',
  searchType = 'brave_mcp',
  className = ''
}) => {
  const isNephilimMode = isNephilimPersona(personaKey);
  const [loadingMessage, setLoadingMessage] = useState('');

  // Rotate loading messages in NEPHILIM mode
  useEffect(() => {
    if (isNephilimMode) {
      setLoadingMessage(getRandomLoadingMessage(searchType));
      const interval = setInterval(() => {
        setLoadingMessage(getRandomLoadingMessage(searchType));
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [isNephilimMode, searchType]);

  // NEPHILIM mode rendering
  if (isNephilimMode) {
    const personaColor = personaKey ? NEPHILIM_COLORS[personaKey] : '#00ffff';
    const narrative = NEPHILIM_SOURCE_NARRATIVES[searchType];
    const sourceColor = narrative?.color || personaColor;

    return (
      <motion.div
        className={`nephilim-glass flex items-center gap-3 px-4 py-3 rounded-xl max-w-fit ${className}`}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        style={{
          borderColor: `${sourceColor}40`,
          boxShadow: `0 0 20px ${sourceColor}20`,
        }}
      >
        {/* Animated mystical icon */}
        <motion.div
          className="text-2xl"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.7, 1, 0.7],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        >
          {narrative?.icon || '✧'}
        </motion.div>

        {/* Animated energy dots */}
        <div className="flex items-center gap-1">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: sourceColor }}
              animate={{
                y: [0, -6, 0],
                opacity: [0.5, 1, 0.5],
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
                ease: 'easeInOut',
                delay: i * 0.15,
              }}
            />
          ))}
        </div>

        {/* Narrative text */}
        <motion.span
          className="text-sm font-medium"
          style={{ color: sourceColor }}
          key={loadingMessage}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {loadingMessage || `${personaName} is searching...`}
        </motion.span>
      </motion.div>
    );
  }

  // Standard mode rendering
  const colors = getOrderColors(celestial_order);

  return (
    <motion.div
      className={`flex items-center gap-3 px-4 py-3 bg-white/80 backdrop-blur-sm rounded-2xl border-2 border-transparent shadow-lg ${colors.glow} max-w-fit ${className}`}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
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
