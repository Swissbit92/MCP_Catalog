import React from 'react';
import { motion } from 'framer-motion';
import { Avatar2D } from './Avatar2D';
import { RichContent } from './RichContent';
import { SourceIndicator } from './SourceIndicator';
import { Message as ApiMessage } from '../services/api';

export interface Message extends ApiMessage {
  latency?: number; // Response time in milliseconds
  status?: 'sending' | 'sent' | 'delivered' | 'failed';
  retryCount?: number;
}

interface MessageBubbleProps {
  message: Message;
  personaAvatar?: string;
  userAvatar?: string;
  showTimestamp?: boolean;
  onRetry?: (messageId: string) => void;
  personaRarity?: string;
  personaName?: string;
}

export const MessageBubble: React.FC<MessageBubbleProps> = React.memo(({
  message,
  personaAvatar,
  userAvatar,
  showTimestamp = false,
  onRetry,
  personaRarity,
  personaName,
}) => {
  const isUser = message.role === 'user';



  return (
    <motion.div
      className={`flex gap-3 mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 25,
        duration: 0.4
      }}
    >
      {/* Avatar - only show for assistant messages */}
      {!isUser && (
        <div className="flex-shrink-0">
          <Avatar2D
            src={personaAvatar}
            alt="Assistant"
            size="sm"
            className="mt-1"
            rarity={personaRarity}
          />
        </div>
      )}

      {/* Message bubble */}
      <div className={`max-w-[85%] md:max-w-[70%] ${isUser ? 'order-first' : ''}`}>
        <motion.div
          className={`px-4 py-3 rounded-2xl shadow-sm ${
            isUser
              ? 'bg-gradient-to-br from-blue-500 to-purple-600 text-white rounded-br-md'
              : 'bg-gray-100 text-gray-900 rounded-bl-md border border-gray-200'
          }`}
          whileHover={{ scale: 1.02 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
          {/* Persona indicator for assistant messages */}
          {!isUser && personaName && (
            <div className="flex items-center gap-1 mb-2">
              <div className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                personaRarity === 'legendary' ? 'bg-yellow-100 text-yellow-800' :
                personaRarity === 'epic' ? 'bg-purple-100 text-purple-800' :
                personaRarity === 'rare' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {personaName}
              </div>
            </div>
          )}
          <RichContent content={message.content} />

          {/* Source indicator - shows data source and cache status */}
          {!isUser && message.metadata && (
            <SourceIndicator metadata={message.metadata} />
          )}
        </motion.div>

        {/* Timestamp, Latency, and Status */}
        <div className={`mt-1 flex items-center gap-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
          {/* Timestamp and Latency */}
          {(showTimestamp && message.timestamp) || message.latency ? (
            <div className="text-xs text-gray-500 flex items-center gap-2">
              {showTimestamp && message.timestamp && (
                <span>
                  {message.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              )}
              {message.latency && (
                <span className="text-blue-400 font-mono">
                  {message.latency < 1000
                    ? `${message.latency}ms`
                    : `${(message.latency / 1000).toFixed(1)}s`
                  }
                </span>
              )}
            </div>
          ) : null}

          {/* Status Indicators and Retry */}
          {message.status && (
            <div className="flex items-center gap-1">
              {message.status === 'sending' && (
                <div className="flex items-center gap-1 text-xs text-gray-400">
                  <div className="w-3 h-3 border border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                  <span>Sending...</span>
                </div>
              )}
              {message.status === 'failed' && (
                <div className="flex items-center gap-1">
                  <span className="text-xs text-red-400">Failed</span>
                  {onRetry && (
                    <button
                      onClick={() => onRetry(message.id)}
                      className="text-xs text-blue-400 hover:text-blue-300 underline"
                      title="Retry sending message"
                    >
                      Retry
                    </button>
                  )}
                  {message.retryCount && message.retryCount > 0 && (
                    <span className="text-xs text-gray-400">
                      ({message.retryCount} attempt{message.retryCount > 1 ? 's' : ''})
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Avatar - only show for user messages */}
      {isUser && (
        <div className="flex-shrink-0">
          <Avatar2D
            src={userAvatar}
            alt="You"
            size="sm"
            className="mt-1"
          />
        </div>
      )}
    </motion.div>
  );
});