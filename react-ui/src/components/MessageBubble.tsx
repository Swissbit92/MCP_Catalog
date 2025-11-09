import React from 'react';
import { motion } from 'framer-motion';
import { Avatar2D } from './Avatar2D';
import { RichContent } from './RichContent';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
}

interface MessageBubbleProps {
  message: Message;
  personaAvatar?: string;
  userAvatar?: string;
  showTimestamp?: boolean;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  personaAvatar,
  userAvatar,
  showTimestamp = false,
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
          />
        </div>
      )}

      {/* Message bubble */}
      <div className={`max-w-[70%] ${isUser ? 'order-first' : ''}`}>
        <motion.div
          className={`px-4 py-3 rounded-2xl shadow-sm ${
            isUser
              ? 'bg-gradient-to-br from-blue-500 to-purple-600 text-white rounded-br-md'
              : 'bg-gray-100 text-gray-900 rounded-bl-md border border-gray-200'
          }`}
          whileHover={{ scale: 1.02 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
          <RichContent content={message.content} />
        </motion.div>

        {/* Timestamp */}
        {showTimestamp && message.timestamp && (
          <div className={`text-xs text-gray-500 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit'
            })}
          </div>
        )}
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
};