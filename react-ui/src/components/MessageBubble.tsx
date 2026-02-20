import React from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle } from 'lucide-react'
import { Avatar2D } from './Avatar2D'
import { RichContent } from './RichContent'
import { SourceIndicator } from './SourceIndicator'
import { Message as ApiMessage, confirmTrade, cancelTrade, approveStrategy, rejectStrategy, deleteWallet } from '../services/api'
import TradeProposalCard from './TradeProposalCard'
import StrategyApprovalCard from './StrategyApprovalCard'
import WalletDeletionCard from './WalletDeletionCard'

export interface Message extends ApiMessage {
  latency?: number
  status?: 'sending' | 'sent' | 'delivered' | 'failed'
  retryCount?: number
}

interface MessageBubbleProps {
  message: Message
  personaAvatar?: string
  userAvatar?: string
  showTimestamp?: boolean
  onRetry?: (messageId: string) => void
  personaRarity?: string
  personaName?: string
}

interface ParsedContent {
  mainContent: string
  citationSection: string | null
  hasCitations: boolean
}

/**
 * Parse message content to extract citation section
 */
function parseMessageContent(content: string): ParsedContent {
  const citationMarkers = [
    /🔍\s*\*\*Sources:\*\*/i,
    /🔍\s*Sources:/i,
    /\*\*Sources:\*\*/i,
    /\nSources:\n/i
  ]

  for (const marker of citationMarkers) {
    const match = content.search(marker)
    if (match !== -1) {
      const mainContent = content.substring(0, match).trim()
      const citationSection = content.substring(match).trim()
      return {
        mainContent,
        citationSection,
        hasCitations: true
      }
    }
  }

  return {
    mainContent: content,
    citationSection: null,
    hasCitations: false
  }
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
  const isUser = message.role === 'user'

  const parsed = React.useMemo(() => parseMessageContent(message.content), [message.content])

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
              ? 'bg-gradient-to-br from-cyan-600/80 to-blue-700/80 text-white rounded-br-md'
              : 'bg-white/[0.08] backdrop-blur-lg text-gray-200 rounded-bl-md border-l-2 border-cyan-500/50'
          }`}
          style={!isUser ? { textShadow: '0 0 20px rgba(0, 255, 255, 0.1)' } : undefined}
          whileHover={{ scale: 1.02 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
          {/* Persona indicator for assistant messages */}
          {!isUser && personaName && (
            <div className="flex items-center gap-1 mb-2">
              <div className="px-2 py-0.5 rounded-full text-xs font-medium bg-white/10 text-cyan-300">
                {personaName}
              </div>
            </div>
          )}

          {/* Main content */}
          <RichContent content={parsed.mainContent} />

          {/* Citation section - styled differently */}
          {parsed.hasCitations && parsed.citationSection && (
            <div className="mt-4 pt-3 border-t border-white/20">
              <RichContent content={parsed.citationSection} className="text-sm text-gray-400" />
            </div>
          )}

          {/* Citation warning - if web search was used but citations are missing/invalid */}
          {!isUser && message.used_search && !parsed.hasCitations && message.citation_valid === false && (
            <div className="flex items-center gap-2 mt-3 pt-2 border-t border-yellow-500/30 bg-yellow-500/10 px-3 py-2 rounded-lg">
              <AlertTriangle size={14} className="text-yellow-400 flex-shrink-0" />
              <span className="text-xs text-yellow-300">
                This response used web search but citations were not included
              </span>
            </div>
          )}

          {/* Source indicator - shows data source and cache status */}
          {!isUser && message.metadata && (
            <SourceIndicator metadata={message.metadata} />
          )}
        </motion.div>

        {/* Wallet proposal cards — rendered below the text bubble for assistant messages */}
        {!isUser && (() => {
          const proposalType = message.metadata?.proposal_type
          const proposal = (message.metadata as any)?.proposal

          if (proposalType === 'trade_proposal' && proposal) {
            return (
              <TradeProposalCard
                proposal={proposal}
                onConfirm={async (proposalId: string) => {
                  await confirmTrade(proposalId)
                }}
                onCancel={(proposalId: string) => {
                  cancelTrade(proposalId).catch(() => {/* fire-and-forget */})
                }}
              />
            )
          }

          if (proposalType === 'strategy_proposal' && proposal) {
            return (
              <StrategyApprovalCard
                proposal={proposal}
                onApprove={async (proposalId: string, strategyConfig: any) => {
                  await approveStrategy(proposalId, strategyConfig)
                }}
                onReject={(proposalId: string) => {
                  rejectStrategy(proposalId).catch(() => {/* fire-and-forget */})
                }}
              />
            )
          }

          if (proposalType === 'wallet_deletion' && proposal) {
            return (
              <WalletDeletionCard
                proposal={proposal}
                onConfirm={async (userId: string) => {
                  await deleteWallet(userId)
                }}
                onCancel={() => {/* dismiss — no backend call needed */}}
              />
            )
          }

          return null
        })()}

        {/* Timestamp, Latency, and Status */}
        <div className={`mt-1 flex items-center gap-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
          {/* Timestamp and Latency */}
          {(showTimestamp && message.timestamp) || message.latency ? (
            <div className="text-xs text-gray-400 flex items-center gap-2">
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
  )
})
