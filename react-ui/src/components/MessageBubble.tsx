import React from 'react';
import { Avatar2D } from './Avatar2D';

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
    <div className={`flex gap-3 mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
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
        <div
          className={`px-4 py-3 rounded-2xl shadow-sm ${
            isUser
              ? 'bg-gradient-to-br from-blue-500 to-purple-600 text-white rounded-br-md'
              : 'bg-gray-100 text-gray-900 rounded-bl-md border border-gray-200'
          }`}
        >
          <div className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </div>
        </div>

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
    </div>
  );
};