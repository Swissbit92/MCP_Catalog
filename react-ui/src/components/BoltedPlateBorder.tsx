import React from 'react';
import { motion } from 'framer-motion';

interface BoltedPlateBorderProps {
  children: React.ReactNode;
  celestial_order: string;
  className?: string;
}

const getOrderColors = (order: string) => {
  switch (order.toLowerCase()) {
    case 'archon':
      return {
        base: 'border-yellow-400/30',
        glow: 'shadow-yellow-400/50',
        accent: 'border-yellow-300'
      };
    case 'warden':
      return {
        base: 'border-purple-400/30',
        glow: 'shadow-purple-400/50',
        accent: 'border-purple-300'
      };
    case 'sage':
      return {
        base: 'border-blue-400/30',
        glow: 'shadow-blue-400/50',
        accent: 'border-blue-300'
      };
    case 'wanderer':
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
  celestial_order,
  className = ''
}) => {
  const [isHovered, setIsHovered] = React.useState(false);
  const colors = getOrderColors(celestial_order);

  return (
    <motion.div
      className={`relative ${className}`}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{
        opacity: 1,
        scale: isHovered ? 1.02 : 1
      }}
      transition={{
        duration: 0.5,
        ease: [0.25, 0.46, 0.45, 0.94]
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Base Plate with Circular Cutouts */}
      <div
        className={`
          relative bg-slate-800/40 backdrop-blur-md border-2 ${colors.base}
          shadow-2xl ${colors.glow} shadow-slate-900/30
          rounded-lg overflow-hidden
        `}
        style={{
          background: 'linear-gradient(135deg, rgba(15,23,42,0.6) 0%, rgba(30,41,59,0.3) 100%)',
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
            opacity: [0.03, 0.08, 0.03],
            scale: [1, 1.005, 1]
          }}
          transition={{
            duration: celestial_order === 'archon' ? 4 : celestial_order === 'warden' ? 5 : 6,
            repeat: Infinity,
            ease: [0.4, 0, 0.6, 1]
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