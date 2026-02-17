import React, { useRef, useEffect, useCallback } from 'react'
import { FixedSizeList as List } from 'react-window'
import AutoSizer from 'react-virtualized-auto-sizer'
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
  const listRef = useRef<List>(null)

  // Fixed row height for simplicity (can be made dynamic later)
  const ROW_HEIGHT = 150

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (listRef.current && messages.length > 0) {
      listRef.current.scrollToItem(messages.length - 1, 'end')
    }
  }, [messages.length])

  // Memoize Row component to prevent recreation on every render
  const Row = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const message = messages[index]

    return (
      <div style={style}>
        <div className="px-4 md:px-6 py-2">
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
      </div>
    )
  }, [messages, personaAvatar, userAvatar, personaRarity, personaName, onRetry])

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
    <div className="flex-1 min-h-0" style={{ background: 'transparent' }}>
      <AutoSizer>
        {({ height, width }: { height: number; width: number }) => (
          <List
            ref={listRef}
            height={height}
            itemCount={messages.length}
            itemSize={ROW_HEIGHT}
            width={width}
            overscanCount={5}
            style={{ background: 'transparent' }}
          >
            {Row}
          </List>
        )}
      </AutoSizer>
    </div>
  )
}
