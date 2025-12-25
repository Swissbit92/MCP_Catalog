import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence, Variants } from 'framer-motion';

// Rarity-based colors for active page highlighting
const getActiveColor = (pathname: string, path: string): string => {
  if (pathname === path) {
    switch (path) {
      case '/': return 'text-yellow-300 drop-shadow-[0_0_12px_rgba(255,215,0,0.9)]'; // Legendary gold
      case '/select': return 'text-purple-300 drop-shadow-[0_0_12px_rgba(186,120,255,0.9)]'; // Epic purple
      case '/chat': return 'text-cyan-300 drop-shadow-[0_0_12px_rgba(66,245,255,0.9)]'; // Rare cyan
      default: return 'text-gray-300';
    }
  }
  return 'text-gray-300 hover:text-white transition-all duration-300';
};

interface HeaderBrandingProps {
  itemVariants: Variants;
}

export const HeaderBranding: React.FC<HeaderBrandingProps> = ({ itemVariants }) => {
  return (
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
  );
};

interface DesktopNavigationProps {
  itemVariants: Variants;
  navItemVariants: Variants;
}

export const DesktopNavigation: React.FC<DesktopNavigationProps> = ({
  itemVariants,
  navItemVariants,
}) => {
  const location = useLocation();

  const navItems = [
    { to: '/', label: 'Home', color: 'yellow' },
    { to: '/select', label: 'Characters', color: 'purple' },
    { to: '/chat', label: 'Chat', color: 'cyan' }
  ];

  return (
    <motion.nav
      className="flex items-center space-x-1"
      variants={itemVariants}
    >
      {navItems.map((item, index) => (
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
            className={`relative px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300 ${getActiveColor(location.pathname, item.to)} overflow-hidden`}
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
  );
};
