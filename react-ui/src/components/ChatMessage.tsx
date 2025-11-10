import React from 'react';

interface ChatMessageProps {
  message: string;
  isUser: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, isUser }) => {
  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: '0.5rem',
    }}>
      <div style={{
        backgroundColor: isUser ? '#dcf8c6' : '#ffffff',
        borderRadius: '0.5rem',
        padding: '0.5rem 0.75rem',
        maxWidth: '70%',
        boxShadow: '0 1px 0.5px rgba(0, 0, 0, 0.13)',
      }}>
        {message}
      </div>
    </div>
  );
};

export default ChatMessage;
