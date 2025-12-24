import React from 'react';
import { motion } from 'framer-motion';

// Particle component for floating background effects
export const FloatingParticles: React.FC = () => {
  const particles = Array.from({ length: 12 }, (_, i) => i);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((particle) => (
        <motion.div
          key={particle}
          className="absolute w-2 h-2 bg-white/40 rounded-full shadow-lg"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
          }}
          animate={{
            y: [0, -30, 0],
            x: [0, Math.random() * 15 - 7.5, 0],
            opacity: [0.3, 0.8, 0.3],
            scale: [0.8, 1.2, 0.8],
          }}
          transition={{
            duration: 4 + Math.random() * 3,
            repeat: Infinity,
            delay: Math.random() * 3,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
};

interface HeaderBackgroundProps {
  currentTheme: 'legendary' | 'epic' | 'rare';
  getBackgroundAnimation: () => {
    background: string[];
  };
}

export const HeaderBackground: React.FC<HeaderBackgroundProps> = ({
  currentTheme,
  getBackgroundAnimation,
}) => {
  return (
    <>
      {/* Enhanced glassmorphism background with multiple layers */}
      <div className="absolute inset-0 bg-gradient-to-r from-slate-900/95 via-slate-800/95 to-slate-900/95 backdrop-blur-xl"></div>
      <div className="absolute inset-0 bg-gradient-to-r from-slate-900/80 via-slate-800/80 to-slate-900/80 backdrop-blur-lg"></div>
      <div className="absolute inset-0 bg-gradient-to-r from-slate-900/60 via-slate-800/60 to-slate-900/60 backdrop-blur-md"></div>

      {/* Dynamic theme-based background animation - HIGHLY VISIBLE */}
      <motion.div
        className="absolute inset-0 opacity-60"
        animate={getBackgroundAnimation()}
        transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
        key={currentTheme} // Force re-animation when theme changes
      ></motion.div>

      {/* Floating particles */}
      <FloatingParticles />

      {/* HIGHLY VISIBLE animated border */}
      <motion.div
        className="absolute bottom-0 left-0 right-0 h-1"
        animate={{
          background: [
            "linear-gradient(to right, transparent, rgba(255, 215, 0, 0.8), transparent)",
            "linear-gradient(to right, transparent, rgba(186, 120, 255, 0.8), transparent)",
            "linear-gradient(to right, transparent, rgba(66, 245, 255, 0.8), transparent)",
            "linear-gradient(to right, transparent, rgba(255, 215, 0, 0.8), transparent)",
          ],
          boxShadow: [
            "0 0 10px rgba(255, 215, 0, 0.5)",
            "0 0 10px rgba(186, 120, 255, 0.5)",
            "0 0 10px rgba(66, 245, 255, 0.5)",
            "0 0 10px rgba(255, 215, 0, 0.5)",
          ]
        }}
        transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
      ></motion.div>
    </>
  );
};
