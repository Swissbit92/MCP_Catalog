import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence, Variants } from 'framer-motion';

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

const backdropVariants: Variants = {
  closed: { opacity: 0 },
  open: { opacity: 1 }
};

interface MobileMenuProps {
  isMobileMenuOpen: boolean;
  setIsMobileMenuOpen: (open: boolean) => void;
  selectedPersona: any;
  currentSession: any;
  currentTheme: 'legendary' | 'epic' | 'rare';
}

export const MobileMenu: React.FC<MobileMenuProps> = ({
  isMobileMenuOpen,
  setIsMobileMenuOpen,
  selectedPersona,
  currentSession,
  currentTheme,
}) => {
  // Close mobile menu
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMobileMenuOpen]);

  return (
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
                  to="/nephilim"
                  className="block px-4 py-3 rounded-lg text-fuchsia-300 hover:text-white hover:bg-fuchsia-900/30 transition-all duration-200 font-medium border border-fuchsia-500/30"
                  onClick={closeMobileMenu}
                >
                  ✨ NEPHILIM Realm
                </Link>
                <Link
                  to="/select"
                  className="block px-4 py-3 rounded-lg text-gray-300 hover:text-white hover:bg-slate-700/50 transition-all duration-200 font-medium"
                  onClick={closeMobileMenu}
                >
                  🤖 Agents
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
  );
};
