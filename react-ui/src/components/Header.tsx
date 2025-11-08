import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

const Header: React.FC = () => {
  const location = useLocation();

  // Rarity-based colors for active page highlighting
  const getActiveColor = (path: string) => {
    if (location.pathname === path) {
      switch (path) {
        case '/': return 'text-yellow-300 drop-shadow-[0_0_8px_rgba(255,215,0,0.8)]'; // Legendary gold
        case '/select': return 'text-purple-300 drop-shadow-[0_0_8px_rgba(186,120,255,0.8)]'; // Epic purple
        case '/chat': return 'text-cyan-300 drop-shadow-[0_0_8px_rgba(66,245,255,0.8)]'; // Rare cyan
        default: return 'text-gray-300';
      }
    }
    return 'text-gray-300 hover:text-white transition-colors duration-200';
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

  return (
    <motion.header
      className="relative bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-b border-slate-700/50 backdrop-blur-sm"
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      {/* Animated background pattern */}
      <motion.div
        className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(255,255,255,0.02),transparent_50%)] opacity-30"
        animate={{
          background: [
            "radial-gradient(circle at 50% 50%, rgba(255,255,255,0.02), transparent 50%)",
            "radial-gradient(circle at 30% 70%, rgba(255,215,0,0.01), transparent 50%)",
            "radial-gradient(circle at 70% 30%, rgba(186,120,255,0.01), transparent 50%)",
            "radial-gradient(circle at 50% 50%, rgba(255,255,255,0.02), transparent 50%)"
          ]
        }}
        transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
      ></motion.div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          className="flex justify-between items-center h-16"
          variants={containerVariants}
        >
          {/* Logo/Branding Section */}
          <motion.div
            className="flex items-center space-x-3"
            variants={itemVariants}
          >
            <motion.div
              className="flex items-center space-x-2"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <motion.div
                className="w-8 h-8 rounded-lg bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center shadow-lg"
                whileHover={{
                  rotate: [0, -10, 10, 0],
                  transition: { duration: 0.5 }
                }}
              >
                <motion.span
                  className="text-slate-900 font-bold text-sm"
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
              </motion.div>
              <div className="hidden sm:block">
                <motion.h1
                  className="text-lg font-bold bg-gradient-to-r from-yellow-300 to-orange-300 bg-clip-text text-transparent"
                  variants={itemVariants}
                >
                  Persona Chat
                </motion.h1>
                <motion.p
                  className="text-xs text-slate-400 leading-tight"
                  variants={itemVariants}
                >
                  Gacha Style
                </motion.p>
              </div>
            </motion.div>
          </motion.div>

          {/* Navigation */}
          <motion.nav
            className="flex items-center space-x-1"
            variants={itemVariants}
          >
            {[
              { to: '/', label: 'Home' },
              { to: '/select', label: 'Characters' },
              { to: '/chat', label: 'Chat' }
            ].map((item, index) => (
              <motion.div
                key={item.to}
                variants={navItemVariants}
                initial="idle"
                whileHover="hover"
                whileTap="tap"
                custom={index}
              >
                <Link
                  to={item.to}
                  className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 ${getActiveColor(item.to)}`}
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
                </Link>
              </motion.div>
            ))}
          </motion.nav>

          {/* Mobile Menu Button */}
          <motion.div
            className="md:hidden"
            variants={itemVariants}
          >
            <motion.button
              className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-slate-700/50 transition-colors duration-200"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              <motion.svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                animate={{
                  rotate: [0, 90, 180, 270, 360],
                }}
                transition={{
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
    </motion.header>
  );
};

export default Header;
