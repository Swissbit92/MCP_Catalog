import React from 'react';
import { motion } from 'framer-motion';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled: boolean;
  loading: boolean;
  initializingSession: boolean;
  hasCurrentSession: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSend,
  disabled,
  loading,
  initializingSession,
  hasCurrentSession
}) => {
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const isDisabled = loading || !hasCurrentSession || initializingSession;
  const isSendDisabled = loading || !hasCurrentSession || !value.trim() || initializingSession;

  return (
    <motion.div
      className="bg-white border-t border-gray-200 px-4 md:px-6 py-3 md:py-4 flex-shrink-0"
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: 0.2, duration: 0.3 }}
    >
      <div className="flex gap-2 md:gap-3">
        <motion.input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyPress={handleKeyPress}
          className="glass-input flex-1 px-4 py-3 md:py-3 rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed text-base md:text-base"
          placeholder={initializingSession ? "Loading character..." : "Type a message..."}
          disabled={isDisabled}
          whileFocus={{ scale: 1.01 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          // Mobile keyboard optimizations
          autoComplete="off"
          autoCorrect="on"
          autoCapitalize="sentences"
          spellCheck="true"
        />
        <motion.button
          onClick={onSend}
          disabled={isSendDisabled}
          className="btn-rarity-primary px-4 md:px-6 py-3 rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed min-w-[60px] md:min-w-[80px] touch-manipulation"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
          <span className="hidden sm:inline">Send</span>
          <span className="sm:hidden">📤</span>
        </motion.button>
      </div>
    </motion.div>
  );
};
