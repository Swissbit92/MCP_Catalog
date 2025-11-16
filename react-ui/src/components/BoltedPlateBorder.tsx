import React from 'react';
import { motion } from 'framer-motion';

interface BoltedPlateBorderProps {
  children: React.ReactNode;
  rarity: string;
  className?: string;
}

const getRarityColors = (rarity: string) => {
  switch (rarity.toLowerCase()) {
    case 'legendary':
      return {
        base: 'border-yellow-400/30',
        glow: 'shadow-yellow-400/50',
        accent: 'border-yellow-300'
      };
    case 'epic':
      return {
        base: 'border-purple-400/30',
        glow: 'shadow-purple-400/50',
        accent: 'border-purple-300'
      };
    case 'rare':
      return {
        base: 'border-blue-400/30',
        glow: 'shadow-blue-400/50',
        accent: 'border-blue-300'
      };
    case 'common':
    default:
      return {
        base: 'border-gray-400/30',
        glow: 'shadow-gray-400/50',
        accent: 'border-gray-300'
      };
  }
};

const BoltedPlateBorder: React.FC<BoltedPlateBorderProps> = ({
  children,
  rarity,
  className = ''
}) => {
  const colors = getRarityColors(rarity);

  return (
    <motion.div
      className={`relative ${className}`}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Base Plate with Circular Cutouts */}
      <div
        className={`
          relative bg-black/40 backdrop-blur-sm border-2 ${colors.base}
          shadow-2xl ${colors.glow}
          rounded-lg overflow-hidden
        `}
        style={{
          clipPath: `
            polygon(
              12px 0%, calc(100% - 12px) 0%,
              100% 12px, 100% calc(100% - 12px),
              calc(100% - 12px) 100%, 12px 100%,
              0% calc(100% - 12px), 0% 12px
            )
          `
        }}
      >
        {/* Inner Glow Layer */}
        <div
          className={`
            absolute inset-2 border ${colors.accent} opacity-20
            rounded-md pointer-events-none
          `}
          style={{
            clipPath: `
              polygon(
                8px 0%, calc(100% - 8px) 0%,
                100% 8px, 100% calc(100% - 8px),
                calc(100% - 8px) 100%, 8px 100%,
                0% calc(100% - 8px), 0% 8px
              )
            `
          }}
        />

        {/* Breathing Animation Overlay */}
        <motion.div
          className={`absolute inset-0 ${colors.accent} opacity-10 pointer-events-none`}
          animate={{
            opacity: [0.05, 0.15, 0.05],
            scale: [1, 1.02, 1]
          }}
          transition={{
            duration: rarity === 'legendary' ? 3 : rarity === 'epic' ? 4 : 5,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          style={{
            clipPath: `
              polygon(
                10px 0%, calc(100% - 10px) 0%,
                100% 10px, 100% calc(100% - 10px),
                calc(100% - 10px) 100%, 10px 100%,
                0% calc(100% - 10px), 0% 10px
              )
            `
          }}
        />

        {/* Content */}
        <div className="relative z-10 p-6">
          {children}
        </div>
      </div>
    </motion.div>
  );
};

export default BoltedPlateBorder;