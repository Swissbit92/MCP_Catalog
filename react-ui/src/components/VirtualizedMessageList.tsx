import React, { useRef, useEffect } from 'react'
import { MessageBubble } from './MessageBubble'

interface Message {
  id: string
  role: 'user' | 'assistant'
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
}

export const VirtualizedMessageList: React.FC<VirtualizedMessageListProps> = ({
  messages,
  personaAvatar,
  userAvatar,
  personaRarity,
  personaName,
  onRetry,
  showTypingIndicator,
  typingIndicatorComponent
}) => {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current && messages.length > 0) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages.length])

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
          />
        </div>
      ))}
    </div>
  )
}
