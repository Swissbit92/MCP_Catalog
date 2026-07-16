import React, { useRef, useEffect } from 'react'
import { MessageBubble } from './MessageBubble'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'narrator'
  content: string
  timestamp: Date
  [key: string]: any
}

interface VirtualizedMessageListProps {
  messages: Message[]
  personaAvatar: string
  userAvatar: string
  personaRarity: string
  personaName: string
  onRetry: (messageId: string) => Promise<void>
  showTypingIndicator?: boolean
  typingIndicatorComponent?: React.ReactNode
  loadingIndicator?: React.ReactNode
  // ADR-011: conversation-control actions, shown only on the latest assistant reply
  onRegenerate?: () => void
  onContinue?: () => void
  onUndo?: () => void
}

export const VirtualizedMessageList: React.FC<VirtualizedMessageListProps> = ({
  messages,
  personaAvatar,
  userAvatar,
  personaRarity,
  personaName,
  onRetry,
  showTypingIndicator,
  typingIndicatorComponent,
  loadingIndicator,
  onRegenerate,
  onContinue,
  onUndo,
}) => {
  const lastAssistantId = [...messages].reverse().find(m => m.role === 'assistant')?.id
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive or loading indicator changes
  useEffect(() => {
    if (scrollRef.current && (messages.length > 0 || loadingIndicator)) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages.length, loadingIndicator])

  // Handle empty state
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-white/60">
          {showTypingIndicator ? typingIndicatorComponent : 'No messages yet'}
        </div>
      </div>
    )
  }

  return (
    <div
      ref={scrollRef}
      className="flex-1 min-h-0 overflow-y-auto"
      style={{ background: 'transparent' }}
    >
      {messages.map((message) => (
        <div key={message.id} className="px-4 md:px-6 py-2">
          <MessageBubble
            message={message}
            personaAvatar={personaAvatar}
            userAvatar={userAvatar}
            showTimestamp={true}
            onRetry={onRetry}
            personaRarity={personaRarity}
            personaName={personaName}
            isLatestAssistant={message.role === 'assistant' && message.id === lastAssistantId}
            onRegenerate={onRegenerate}
            onContinue={onContinue}
            onUndo={onUndo}
          />
        </div>
      ))}
      {loadingIndicator && (
        <div className="px-4 md:px-6 py-2">
          {loadingIndicator}
        </div>
      )}
    </div>
  )
}
