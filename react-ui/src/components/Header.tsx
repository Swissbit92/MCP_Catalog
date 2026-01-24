import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { motion, Variants } from 'framer-motion';
import { usePersona } from '../context/PersonaContext';
import { useAudio } from '../context/AudioContext';
import { HeaderBackground } from './header/HeaderVisuals';
import { HeaderBranding, DesktopNavigation } from './header/HeaderNavigation';
import { MobileMenu } from './header/MobileMenu';

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

  // Animation variants
  const containerVariants: Variants = {
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

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: -10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.4 }
    }
  };

  const navItemVariants: Variants = {
    idle: { scale: 1 },
    hover: { scale: 1.05 },
    tap: { scale: 0.95 }
  };

  return (
    <motion.header
      className="relative overflow-hidden"
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      {/* Header Background with all visual effects */}
      <HeaderBackground
        currentTheme={currentTheme}
        getBackgroundAnimation={getBackgroundAnimation}
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          className="flex justify-between items-center h-16"
          variants={containerVariants}
        >
          {/* Enhanced Logo/Branding Section */}
          <HeaderBranding itemVariants={itemVariants} />

          {/* Enhanced Navigation */}
          <DesktopNavigation
            itemVariants={itemVariants}
            navItemVariants={navItemVariants}
          />

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
      <MobileMenu
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
        selectedPersona={selectedPersona}
        currentSession={currentSession}
        currentTheme={currentTheme}
      />
    </motion.header>
  );
};

export default Header;
