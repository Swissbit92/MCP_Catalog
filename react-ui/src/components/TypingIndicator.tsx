import React from 'react';
import { motion } from 'framer-motion';

interface TypingIndicatorProps {
  className?: string;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ className = '' }) => {
  return (
    <motion.div
      className={`flex items-center gap-3 px-4 py-3 bg-gray-50 rounded-2xl border border-gray-200 shadow-sm max-w-fit ${className}`}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
    >
      <div className="flex items-center gap-1">
        <motion.div
          className="w-2.5 h-2.5 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full shadow-sm"
          animate={{
            y: [0, -10, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        <motion.div
          className="w-2.5 h-2.5 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full shadow-sm"
          animate={{
            y: [0, -10, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 0.2,
          }}
        />
        <motion.div
          className="w-2.5 h-2.5 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full shadow-sm"
          animate={{
            y: [0, -10, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 0.4,
          }}
        />
      </div>
      <span className="text-sm text-gray-600 font-medium">Assistant is typing...</span>
    </motion.div>
  );
};