import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface RarityEffectsProps {
  rarity: string;
  isActive: boolean;
}

const RarityEffects: React.FC<RarityEffectsProps> = ({
  rarity,
  isActive
}) => {
  const getEffectConfig = (rarity: string) => {
    switch (rarity.toLowerCase()) {
      case 'legendary':
        return {
          screenFlash: true,
          shake: true,
          particles: true,
          color: '#FFD700',
          duration: 3,
          particleCount: 30
        };
      case 'epic':
        return {
          screenFlash: false,
          shake: true,
          particles: true,
          color: '#A855F7',
          duration: 2.5,
          particleCount: 25
        };
      case 'rare':
        return {
          screenFlash: false,
          shake: false,
          particles: true,
          color: '#3B82F6',
          duration: 2,
          particleCount: 20
        };
      default:
        return {
          screenFlash: false,
          shake: false,
          particles: true,
          color: '#6B7280',
          duration: 1.5,
          particleCount: 15
        };
    }
  };

  const config = getEffectConfig(rarity);

  return (
    <AnimatePresence>
      {isActive && (
        <>
          {/* Screen Flash for Legendary */}
          {config.screenFlash && (
            <motion.div
              className="rarity-screen-flash"
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 0.8, 0.8, 0] }}
              transition={{ duration: 1, times: [0, 0.1, 0.9, 1] }}
            />
          )}

          {/* Screen Shake */}
          {config.shake && (
            <motion.div
              className="rarity-screen-shake"
              animate={{
                x: [0, -8, 8, -5, 5, -3, 3, 0],
                y: [0, 3, -3, 2, -2, 1, -1, 0]
              }}
              transition={{
                duration: 1.2,
                ease: "easeInOut",
                repeat: 3
              }}
            />
          )}

          {/* Particle Burst */}
          {config.particles && (
            <div className="rarity-particles">
              {Array.from({ length: config.particleCount }).map((_, i) => (
                <motion.div
                  key={i}
                  className="rarity-particle"
                  style={{
                    backgroundColor: config.color,
                    left: '50%',
                    top: '50%',
                    boxShadow: `0 0 10px ${config.color}80`
                  }}
                  initial={{
                    x: 0,
                    y: 0,
                    scale: 0,
                    opacity: 0
                  }}
                  animate={{
                    x: (Math.random() - 0.5) * 400,
                    y: (Math.random() - 0.5) * 400,
                    scale: [0, 1.5, 0],
                    opacity: [0, 1, 1, 0]
                  }}
                  transition={{
                    duration: config.duration,
                    delay: Math.random() * 0.5,
                    ease: "easeOut"
                  }}
                />
              ))}
            </div>
          )}

          {/* Rarity Glow Overlay */}
          <motion.div
            className="rarity-glow-overlay"
            style={{
              boxShadow: `inset 0 0 150px ${config.color}30, 0 0 50px ${config.color}20`,
              background: `radial-gradient(circle at center, ${config.color}10 0%, transparent 70%)`
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.4, 0.4, 0] }}
            transition={{ duration: config.duration }}
          />
        </>
      )}
    </AnimatePresence>
  );
};

export default RarityEffects;