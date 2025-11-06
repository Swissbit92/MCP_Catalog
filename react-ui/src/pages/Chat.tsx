import React, { useState, useEffect } from 'react';
import ChatMessage from '../components/ChatMessage';
import { sendMessage } from '../services/api';
import { usePersona } from '../context/PersonaContext';

interface Message {
  text: string;
  isUser: boolean;
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const { selectedPersona } = usePersona();

  useEffect(() => {
    if (selectedPersona && selectedPersona.voice?.greeting) {
      setMessages([{ text: selectedPersona.voice.greeting, isUser: false }]);
    } else {
      setMessages([{ text: 'Hi there! How can I help you today?', isUser: false }]);
    }
  }, [selectedPersona]);

  const handleSendMessage = async () => {
    if (input.trim() && selectedPersona) {
      const userMessage = { text: input, isUser: true };
      setMessages((prevMessages) => [...prevMessages, userMessage]);
      setInput('');
      setLoading(true);

      try {
        const history = messages.map(msg => ({ role: msg.isUser ? 'user' : 'assistant', content: msg.text }));
        const aiResponse = await sendMessage(selectedPersona.key, input, history);
        setMessages((prevMessages) => [
          ...prevMessages,
          { text: aiResponse, isUser: false },
        ]);
      } catch (error) {
        console.error('Error sending message:', error);
        setMessages((prevMessages) => [
          ...prevMessages,
          { text: 'Error: Could not send message.', isUser: false },
        ]);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      padding: '1rem',
      boxSizing: 'border-box',
    }}>
      <h1 style={{ textAlign: 'center' }}>Chat</h1>
      <div style={{
        flexGrow: 1,
        overflowY: 'auto',
        border: '1px solid #ccc',
        borderRadius: '0.5rem',
        padding: '1rem',
        marginBottom: '1rem',
        display: 'flex',
        flexDirection: 'column',
      }}>
        {messages.map((msg, index) => (
          <ChatMessage key={index} message={msg.text} isUser={msg.isUser} />
        ))}
        {loading && <ChatMessage message="Typing..." isUser={false} />}
      </div>
      <div style={{ display: 'flex' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              handleSendMessage();
            }
          }}
          style={{
            flexGrow: 1,
            padding: '0.5rem',
            border: '1px solid #ccc',
            borderRadius: '0.5rem',
            marginRight: '0.5rem',
          }}
          placeholder="Type a message..."
          disabled={loading || !selectedPersona}
        />
        <button
          onClick={handleSendMessage}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '0.5rem',
            cursor: 'pointer',
          }}
          disabled={loading || !selectedPersona}
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default Chat;