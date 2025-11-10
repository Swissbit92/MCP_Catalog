import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence, Variants } from 'framer-motion';
import { usePersona } from '../context/PersonaContext';
import { useAudio } from '../context/AudioContext';

// Particle component for floating background effects
const FloatingParticles: React.FC = () => {
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

const Header: React.FC = () => {
  const location = useLocation();
  const { selectedPersona, currentSession } = usePersona();
  const { isMuted, toggleMute } = useAudio();
  const [currentTheme, setCurrentTheme] = useState<'legendary' | 'epic' | 'rare'>('legendary');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Update theme based on current page and selected persona
  useEffect(() => {
    let newTheme: 'legendary' | 'epic' | 'rare' = 'legendary';

    // Priority: Selected persona > Current page
    if (selectedPersona) {
      switch (selectedPersona.rarity) {
        case 'legendary':
          newTheme = 'legendary';
          break;
        case 'epic':
          newTheme = 'epic';
          break;
        case 'rare':
          newTheme = 'rare';
          break;
        default:
          newTheme = 'legendary';
      }
    } else {
      // Fallback to page-based theming
      switch (location.pathname) {
        case '/':
          newTheme = 'legendary';
          break;
        case '/select':
          newTheme = 'epic';
          break;
        case '/chat':
          newTheme = 'rare';
          break;
        default:
          newTheme = 'legendary';
      }
    }

    console.log('Header theme changed to:', newTheme, 'for persona:', selectedPersona?.display_name || 'none', 'path:', location.pathname);
    setCurrentTheme(newTheme);
  }, [location.pathname, selectedPersona]);

  // Get theme-based background animation
  const getBackgroundAnimation = () => {
    const themeColors = {
      legendary: {
        primary: 'rgba(255, 215, 0, 0.15)',
        secondary: 'rgba(255, 240, 166, 0.08)',
        accent: 'rgba(255, 208, 80, 0.12)'
      },
      epic: {
        primary: 'rgba(186, 120, 255, 0.15)',
        secondary: 'rgba(246, 212, 255, 0.08)',
        accent: 'rgba(186, 120, 255, 0.12)'
      },
      rare: {
        primary: 'rgba(66, 245, 255, 0.15)',
        secondary: 'rgba(212, 246, 255, 0.08)',
        accent: 'rgba(66, 245, 255, 0.12)'
      }
    };

    const colors = themeColors[currentTheme];

    return {
      background: [
        `radial-gradient(circle at 20% 50%, ${colors.primary}, transparent 50%)`,
        `radial-gradient(circle at 80% 20%, ${colors.secondary}, transparent 50%)`,
        `radial-gradient(circle at 40% 80%, ${colors.accent}, transparent 50%)`,
        `radial-gradient(circle at 60% 30%, ${colors.primary}, transparent 50%)`,
        `radial-gradient(circle at 20% 50%, ${colors.primary}, transparent 50%)`,
      ]
    };
  };

  // Rarity-based colors for active page highlighting
  const getActiveColor = (path: string) => {
    if (location.pathname === path) {
      switch (path) {
        case '/': return 'text-yellow-300 drop-shadow-[0_0_12px_rgba(255,215,0,0.9)]'; // Legendary gold
        case '/select': return 'text-purple-300 drop-shadow-[0_0_12px_rgba(186,120,255,0.9)]'; // Epic purple
        case '/chat': return 'text-cyan-300 drop-shadow-[0_0_12px_rgba(66,245,255,0.9)]'; // Rare cyan
        default: return 'text-gray-300';
      }
    }
    return 'text-gray-300 hover:text-white transition-all duration-300';
  };

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0, y: -20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.6,
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: -10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.4 }
    }
  };

  const navItemVariants = {
    idle: { scale: 1 },
    hover: { scale: 1.05 },
    tap: { scale: 0.95 }
  };

  // Mobile menu variants
  const mobileMenuVariants: Variants = {
    closed: {
      x: '100%',
      transition: {
        type: 'spring',
        stiffness: 400,
        damping: 40
      }
    },
    open: {
      x: 0,
      transition: {
        type: 'spring',
        stiffness: 400,
        damping: 40
      }
    }
  };

  const backdropVariants = {
    closed: { opacity: 0 },
    open: { opacity: 1 }
  };

  // Close mobile menu when clicking outside or on navigation
  const closeMobileMenu = () => setIsMobileMenuOpen(false);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMobileMenuOpen) {
        closeMobileMenu();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isMobileMenuOpen]);

  return (
    <motion.header
      className="relative overflow-hidden"
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
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

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          className="flex justify-between items-center h-16"
          variants={containerVariants}
        >
          {/* Enhanced Logo/Branding Section */}
          <motion.div
            className="flex items-center space-x-3"
            variants={itemVariants}
          >
            <motion.div
              className="flex items-center space-x-2"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {/* Enhanced logo with animated glow */}
              <motion.div
                className="relative w-8 h-8 rounded-lg bg-gradient-to-br from-yellow-400 via-orange-500 to-red-500 flex items-center justify-center shadow-lg"
                whileHover={{
                  rotate: [0, -10, 10, 0],
                  scale: 1.1,
                  transition: { duration: 0.5 }
                }}
                animate={{
                  boxShadow: [
                    "0 0 20px rgba(255, 215, 0, 0.3)",
                    "0 0 30px rgba(255, 215, 0, 0.5)",
                    "0 0 20px rgba(255, 215, 0, 0.3)"
                  ]
                }}
                transition={{
                  duration: 3,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                <motion.span
                  className="text-slate-900 font-bold text-sm relative z-10"
                  animate={{
                    rotate: [0, 10, -10, 0],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: 1
                  }}
                >
                  🎭
                </motion.span>

                {/* Animated background glow */}
                <motion.div
                  className="absolute inset-0 rounded-lg bg-gradient-to-br from-yellow-300 to-orange-400 opacity-50"
                  animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.3, 0.6, 0.3]
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: 0.5
                  }}
                />
              </motion.div>

              <div className="hidden sm:block">
                {/* Animated typography with gradient effects */}
                <motion.h1
                  className="text-lg font-bold bg-gradient-to-r from-yellow-300 via-orange-300 to-pink-300 bg-clip-text text-transparent relative"
                  variants={itemVariants}
                  animate={{
                    backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"],
                  }}
                  transition={{
                    duration: 4,
                    repeat: Infinity,
                    ease: "linear"
                  }}
                  style={{
                    backgroundSize: "200% 200%",
                    filter: "drop-shadow(0 0 8px rgba(255, 215, 0, 0.3))"
                  }}
                >
                  Persona Chat
                </motion.h1>
                <motion.p
                  className="text-xs text-slate-400 leading-tight"
                  variants={itemVariants}
                  animate={{
                    textShadow: [
                      "0 0 4px rgba(148, 163, 184, 0.3)",
                      "0 0 8px rgba(255, 215, 0, 0.2)",
                      "0 0 4px rgba(148, 163, 184, 0.3)"
                    ]
                  }}
                  transition={{
                    duration: 3,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                >
                  Gacha Style
                </motion.p>
              </div>
            </motion.div>
          </motion.div>

          {/* Enhanced Navigation */}
          <motion.nav
            className="flex items-center space-x-1"
            variants={itemVariants}
          >
            {[
              { to: '/', label: 'Home', color: 'yellow' },
              { to: '/select', label: 'Characters', color: 'purple' },
              { to: '/chat', label: 'Chat', color: 'cyan' }
            ].map((item, index) => (
              <motion.div
                key={item.to}
                className="relative"
                initial="idle"
                whileHover="hover"
                whileTap="tap"
                variants={navItemVariants}
                custom={index}
              >
                <Link
                  to={item.to}
                  className={`relative px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300 ${getActiveColor(item.to)} overflow-hidden`}
                >
                  {/* Background glow effect */}
                  <motion.div
                    className={`absolute inset-0 rounded-lg opacity-0 ${
                      item.color === 'yellow' ? 'bg-yellow-500/20' :
                      item.color === 'purple' ? 'bg-purple-500/20' :
                      'bg-cyan-500/20'
                    }`}
                    whileHover={{ opacity: 0.3 }}
                    transition={{ duration: 0.2 }}
                  />

                  {/* Animated text with glow */}
                  <motion.span
                    className="relative z-10"
                    animate={location.pathname === item.to ? {
                      textShadow: [
                        `0 0 8px rgba(${item.color === 'yellow' ? '255,215,0' : item.color === 'purple' ? '186,120,255' : '66,245,255'}, 0.6)`,
                        `0 0 12px rgba(${item.color === 'yellow' ? '255,215,0' : item.color === 'purple' ? '186,120,255' : '66,245,255'}, 0.8)`,
                        `0 0 8px rgba(${item.color === 'yellow' ? '255,215,0' : item.color === 'purple' ? '186,120,255' : '66,245,255'}, 0.6)`
                      ]
                    } : {}}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                  >
                    <AnimatePresence mode="wait">
                      <motion.span
                        key={location.pathname === item.to ? 'active' : 'inactive'}
                        initial={{ opacity: 0, y: -5 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 5 }}
                        transition={{ duration: 0.2 }}
                      >
                        {item.label}
                      </motion.span>
                    </AnimatePresence>
                  </motion.span>

                  {/* Hover particle effect */}
                  <motion.div
                    className="absolute inset-0 opacity-0"
                    whileHover={{ opacity: 1 }}
                  >
                    {[...Array(3)].map((_, i) => (
                      <motion.div
                        key={i}
                        className={`absolute w-1 h-1 rounded-full ${
                          item.color === 'yellow' ? 'bg-yellow-400' :
                          item.color === 'purple' ? 'bg-purple-400' :
                          'bg-cyan-400'
                        }`}
                        initial={{
                          x: '50%',
                          y: '50%',
                          scale: 0,
                          opacity: 0
                        }}
                        animate={{
                          x: [`50%`, `${40 + Math.random() * 20}%`],
                          y: [`50%`, `${30 + Math.random() * 40}%`],
                          scale: [0, 1, 0],
                          opacity: [0, 0.8, 0]
                        }}
                        transition={{
                          duration: 1.5,
                          delay: i * 0.2,
                          repeat: Infinity,
                          ease: "easeOut"
                        }}
                      />
                    ))}
                  </motion.div>
                </Link>
              </motion.div>
            ))}
          </motion.nav>

           {/* Audio Control and Mobile Menu */}
           <motion.div
             className="flex items-center space-x-2"
             variants={itemVariants}
           >
             {/* Audio Mute Button */}
             <motion.button
               className={`p-2 rounded-lg transition-colors duration-200 ${
                 isMuted
                   ? 'text-red-400 hover:text-red-300 hover:bg-red-900/20'
                   : 'text-green-400 hover:text-green-300 hover:bg-green-900/20'
               }`}
               whileHover={{ scale: 1.1 }}
               whileTap={{ scale: 0.9 }}
               onClick={toggleMute}
               aria-label={isMuted ? 'Unmute audio' : 'Mute audio'}
               title={isMuted ? 'Unmute audio' : 'Mute audio'}
             >
               <motion.svg
                 className="w-5 h-5"
                 fill="none"
                 stroke="currentColor"
                 viewBox="0 0 24 24"
                 animate={isMuted ? { opacity: 0.5 } : { opacity: 1 }}
                 transition={{ duration: 0.2 }}
               >
                 {isMuted ? (
                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15zM17 7l4 4m0 0l-4 4m4-4H13" />
                 ) : (
                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M12 9a3 3 0 000 6m-3-3h6m-6 0v6a3 3 0 01-3 3H6a3 3 0 01-3-3V9a3 3 0 013-3h1.5a3 3 0 013 3z" />
                 )}
               </motion.svg>
             </motion.button>

             {/* Mobile Menu Button */}
             <motion.button
               className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-slate-700/50 transition-colors duration-200 md:hidden"
               whileHover={{ scale: 1.1 }}
               whileTap={{ scale: 0.9 }}
               onClick={() => setIsMobileMenuOpen(true)}
               aria-label="Open mobile menu"
             >
              <motion.svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                animate={isMobileMenuOpen ? { rotate: 90 } : {
                  rotate: [0, 90, 180, 270, 360],
                }}
                transition={isMobileMenuOpen ? { duration: 0.2 } : {
                  duration: 4,
                  repeat: Infinity,
                  ease: "linear",
                  delay: 2
                }}
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </motion.svg>
            </motion.button>
          </motion.div>
        </motion.div>
      </div>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden"
              variants={backdropVariants}
              initial="closed"
              animate="open"
              exit="closed"
              onClick={closeMobileMenu}
            />

            {/* Mobile Menu Panel */}
            <motion.div
              className="fixed top-0 right-0 h-full w-80 bg-gradient-to-b from-slate-900/95 via-slate-800/95 to-slate-900/95 backdrop-blur-xl border-l border-slate-700/50 z-50 md:hidden"
              variants={mobileMenuVariants}
              initial="closed"
              animate="open"
              exit="closed"
            >
              {/* Mobile Menu Header */}
              <div className="flex items-center justify-between p-4 border-b border-slate-700/50">
                <h2 className="text-lg font-semibold text-white">Menu</h2>
                <motion.button
                  className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-slate-700/50 transition-colors duration-200"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={closeMobileMenu}
                  aria-label="Close mobile menu"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </motion.button>
              </div>

              {/* Mobile Menu Content */}
              <div className="flex-1 p-4 space-y-4">
                {/* Current Persona Display */}
                {selectedPersona && (
                  <motion.div
                    className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center">
                        <span className="text-slate-900 font-bold text-sm">🎭</span>
                      </div>
                      <div>
                        <h3 className="text-white font-medium">{selectedPersona.display_name}</h3>
                        <p className="text-slate-400 text-sm capitalize">{selectedPersona.rarity}</p>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Current Session Display */}
                {currentSession && (
                  <motion.div
                    className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                  >
                    <h4 className="text-white font-medium mb-2">Current Session</h4>
                    <p className="text-slate-300 text-sm">{currentSession.title}</p>
                    <p className="text-slate-400 text-xs mt-1">
                      {currentSession.message_count} messages
                    </p>
                  </motion.div>
                )}

                {/* Mobile Navigation */}
                <motion.nav
                  className="space-y-2"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <Link
                    to="/"
                    className="block px-4 py-3 rounded-lg text-gray-300 hover:text-white hover:bg-slate-700/50 transition-all duration-200 font-medium"
                    onClick={closeMobileMenu}
                  >
                    🏠 Home
                  </Link>
                  <Link
                    to="/select"
                    className="block px-4 py-3 rounded-lg text-gray-300 hover:text-white hover:bg-slate-700/50 transition-all duration-200 font-medium"
                    onClick={closeMobileMenu}
                  >
                    🎭 Characters
                  </Link>
                  <Link
                    to="/chat"
                    className="block px-4 py-3 rounded-lg text-gray-300 hover:text-white hover:bg-slate-700/50 transition-all duration-200 font-medium"
                    onClick={closeMobileMenu}
                  >
                    💬 Chat
                  </Link>
                </motion.nav>

                {/* Theme Indicator */}
                <motion.div
                  className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  <h4 className="text-white font-medium mb-2">Current Theme</h4>
                  <div className="flex items-center space-x-2">
                    <div className={`w-3 h-3 rounded-full ${
                      currentTheme === 'legendary' ? 'bg-yellow-400' :
                      currentTheme === 'epic' ? 'bg-purple-400' :
                      'bg-cyan-400'
                    }`} />
                    <span className="text-slate-300 capitalize">{currentTheme}</span>
                  </div>
                </motion.div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </motion.header>
  );
};

export default Header;
