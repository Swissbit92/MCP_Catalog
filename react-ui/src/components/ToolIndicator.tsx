import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Search, Database, Brain, Wallet } from 'lucide-react';
import { isNephilimPersona, NEPHILIM_LOADING_MESSAGES } from './nephilim/mcpNarratives';

export type ToolType = 'brave' | 'mongodb' | 'wallet' | 'generic';

interface ToolIndicatorProps {
  toolType: ToolType;
  personaName?: string;
  personaKey?: string;
  className?: string;
}

// Tool-type color map — matches mcpNarratives.ts hex values exactly
const TOOL_COLORS: Record<ToolType, string> = {
  brave: '#2ecc71',    // Cipher's Archives green
  mongodb: '#f39c12',  // Aurora's Crystal Grid amber
  wallet: '#FFD700',   // E.E.V.A.'s Solana Nexus gold
  generic: '#b07cc6',  // Inner Wisdom purple
};

// Tool-specific configuration
const getToolConfig = (toolType: ToolType) => {
  switch (toolType) {
    case 'brave':
      return { icon: Search, text: 'searching the web' };
    case 'mongodb':
      return { icon: Database, text: 'analyzing Bitcoin data' };
    case 'wallet':
      return { icon: Wallet, text: 'consulting the Solana Nexus' };
    case 'generic':
    default:
      return { icon: Brain, text: 'processing your request' };
  }
};

// Map toolType to NEPHILIM loading message category
const getNephilimMessages = (toolType: ToolType): string[] => {
  switch (toolType) {
    case 'brave':
      return NEPHILIM_LOADING_MESSAGES.search;
    case 'mongodb':
      return NEPHILIM_LOADING_MESSAGES.trading;
    case 'wallet':
      // Wallet uses trading messages as closest match
      return [
        'E.E.V.A. channels the Solana streams...',
        'The Nexus pulses with on-chain data...',
        'Consulting Jupiter exchange flows...',
        'Reading the blockchain currents...',
      ];
    case 'generic':
    default:
      return NEPHILIM_LOADING_MESSAGES.thinking;
  }
};

export const ToolIndicator: React.FC<ToolIndicatorProps> = ({
  toolType,
  personaName = 'Assistant',
  personaKey,
  className = ''
}) => {
  const config = getToolConfig(toolType);
  const IconComponent = config.icon;
  const color = TOOL_COLORS[toolType] || TOOL_COLORS.generic;
  const nephilimMode = isNephilimPersona(personaKey);

  // Rotating NEPHILIM loading messages
  const [messageIndex, setMessageIndex] = useState(0);
  const nephilimMessages = nephilimMode ? getNephilimMessages(toolType) : [];

  useEffect(() => {
    if (!nephilimMode || nephilimMessages.length <= 1) return;
    const interval = setInterval(() => {
      setMessageIndex(prev => (prev + 1) % nephilimMessages.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [nephilimMode, nephilimMessages.length]);

  const displayText = nephilimMode
    ? nephilimMessages[messageIndex]
    : `${personaName} is ${config.text}...`;

  return (
    <motion.div
      className={`flex items-center gap-3 px-4 py-3 bg-white/[0.08] backdrop-blur-lg rounded-2xl border border-white/[0.1] shadow-sm max-w-fit ${className}`}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
    >
      {/* Animated icon */}
      <motion.div
        style={{ color }}
        animate={{ rotate: [0, 360] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
      >
        <IconComponent size={20} />
      </motion.div>

      {/* Animated dots */}
      <div className="flex items-center gap-1">
        {[0, 0.15, 0.3].map((delay, i) => (
          <motion.div
            key={i}
            className="w-2.5 h-2.5 rounded-full shadow-sm"
            style={{ backgroundColor: color }}
            animate={{
              y: [0, -8, 0],
              scale: [1, 1.3, 1],
            }}
            transition={{
              duration: 1,
              repeat: Infinity,
              ease: 'easeInOut',
              delay,
            }}
          />
        ))}
      </div>

      {/* Text */}
      <span className="text-sm font-medium" style={{ color }}>
        {displayText}
      </span>
    </motion.div>
  );
};
