import React, { useRef, useEffect } from 'react';
import { VariableSizeList as List } from 'react-window';
import AutoSizer from 'react-virtualized-auto-sizer';
import { MessageBubble } from './MessageBubble';

interface Message {
  id: string;
  role: string;
  content: string;
  timestamp: string;
  [key: string]: any;
}

interface VirtualizedMessageListProps {
  messages: Message[];
  personaAvatar: string;
  userAvatar: string;
  personaRarity: string;
  personaName: string;
  onRetry: (messageId: string) => Promise<void>;
  showTypingIndicator?: boolean;
  typingIndicatorComponent?: React.ReactNode;
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
  const listRef = useRef<List>(null);
  const rowHeights = useRef<{ [index: number]: number }>({});

  // Estimate row height based on message content
  const getRowHeight = (index: number): number => {
    // Return cached height if available
    if (rowHeights.current[index]) {
      return rowHeights.current[index];
    }

    // Estimate height based on content length
    const message = messages[index];
    const contentLength = message?.content?.length || 0;

    // Base height + variable height based on content
    // Rough estimate: 20px per line (assuming ~80 chars per line)
    const estimatedLines = Math.ceil(contentLength / 80);
    const estimatedHeight = 100 + (estimatedLines * 20); // 100px base + content

    return Math.max(estimatedHeight, 120); // Minimum 120px
  };

  const setRowHeight = (index: number, size: number) => {
    listRef.current?.resetAfterIndex(0);
    rowHeights.current = { ...rowHeights.current, [index]: size };
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (listRef.current && messages.length > 0) {
      listRef.current.scrollToItem(messages.length - 1, 'end');
    }
  }, [messages.length]);

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const rowRef = useRef<HTMLDivElement>(null);
    const message = messages[index];

    useEffect(() => {
      if (rowRef.current) {
        const height = rowRef.current.getBoundingClientRect().height;
        if (height !== rowHeights.current[index]) {
          setRowHeight(index, height);
        }
      }
    }, [index]);

    return (
      <div style={style}>
        <div ref={rowRef} className="px-4 md:px-6 py-2">
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
    );
  };

  // Handle empty state
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-gray-500">
          {showTypingIndicator ? typingIndicatorComponent : 'No messages yet'}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-0">
      <AutoSizer>
        {({ height, width }) => (
          <List
            ref={listRef}
            height={height}
            itemCount={messages.length}
            itemSize={getRowHeight}
            width={width}
            overscanCount={5}
          >
            {Row}
          </List>
        )}
      </AutoSizer>
    </div>
  );
};
