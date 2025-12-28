import React from 'react';
import { motion } from 'framer-motion';
import { Search, AlertTriangle } from 'lucide-react';
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

interface ParsedContent {
  mainContent: string;
  citationSection: string | null;
  hasCitations: boolean;
}

/**
 * Parse message content to extract citation section
 */
function parseMessageContent(content: string): ParsedContent {
  // Look for citation markers (with or without emoji)
  const citationMarkers = [
    /🔍\s*\*\*Sources:\*\*/i,
    /🔍\s*Sources:/i,
    /\*\*Sources:\*\*/i,
    /\nSources:\n/i
  ];

  for (const marker of citationMarkers) {
    const match = content.search(marker);
    if (match !== -1) {
      const mainContent = content.substring(0, match).trim();
      const citationSection = content.substring(match).trim();
      return {
        mainContent,
        citationSection,
        hasCitations: true
      };
    }
  }

  return {
    mainContent: content,
    citationSection: null,
    hasCitations: false
  };
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

  // Parse content to extract citations
  const parsed = React.useMemo(() => parseMessageContent(message.content), [message.content]);



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

          {/* Main content */}
          <RichContent content={parsed.mainContent} />

          {/* Citation section - styled differently */}
          {parsed.hasCitations && parsed.citationSection && (
            <div className="mt-4 pt-3 border-t border-gray-300/50">
              <RichContent content={parsed.citationSection} className="text-sm text-gray-700" />
            </div>
          )}

          {/* Citation warning - if web search was used but citations are missing/invalid */}
          {!isUser && message.used_search && !parsed.hasCitations && message.citation_valid === false && (
            <div className="flex items-center gap-2 mt-3 pt-2 border-t border-yellow-200 bg-yellow-50 px-3 py-2 rounded-lg">
              <AlertTriangle size={14} className="text-yellow-600 flex-shrink-0" />
              <span className="text-xs text-yellow-800">
                ⚠️ This response used web search but citations were not included
              </span>
            </div>
          )}

          {/* Search badge - shows if web search was used */}
          {!isUser && message.used_search && (
            <div className="flex items-center gap-1.5 mt-3 pt-2 border-t border-gray-200/50">
              <div className="flex items-center gap-1 px-2 py-1 bg-blue-50 rounded-full">
                <Search size={12} className="text-blue-600" />
                <span className="text-xs font-medium text-blue-700">
                  Web-enhanced answer
                </span>
              </div>
              {message.search_results_count && message.search_results_count > 0 && (
                <span className="text-xs text-gray-500">
                  ({message.search_results_count} source{message.search_results_count > 1 ? 's' : ''})
                </span>
              )}
            </div>
          )}

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
                <span className="text-blue-400 font-mono text-xs">
                  <span className="sr-only">Response time: </span>
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