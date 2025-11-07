import React, { useState, useEffect } from 'react';
import { MessageBubble, Message } from '../components/MessageBubble';
import { TypingIndicator } from '../components/TypingIndicator';
import { sendMessage, getPersonaGreeting } from '../services/api';
import { usePersona } from '../context/PersonaContext';

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const { selectedPersona } = usePersona();



  useEffect(() => {
    const loadGreeting = async () => {
      if (selectedPersona) {
        try {
          const personaLabel = selectedPersona.coordinator_label || selectedPersona.display_name;
          const greeting = await getPersonaGreeting(personaLabel);
          setMessages([{
            id: 'greeting',
            role: 'assistant',
            content: greeting,
            timestamp: new Date()
          }]);
        } catch (error) {
          console.error('Error loading greeting:', error);
          // Fallback to static greeting
          setMessages([{
            id: 'greeting',
            role: 'assistant',
            content: selectedPersona.voice?.greeting || `Hello! I'm ${selectedPersona.display_name}. How can I help you today? (Using fallback greeting - backend may not be running)`,
            timestamp: new Date()
          }]);
        }
      } else {
        setMessages([{
          id: 'greeting',
          role: 'assistant',
          content: 'Hi there! How can I help you today?',
          timestamp: new Date()
        }]);
      }
    };

    loadGreeting();
  }, [selectedPersona]);

  const handleSendMessage = async () => {
    if (input.trim() && selectedPersona) {
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: input,
        timestamp: new Date()
      };
      setMessages((prevMessages) => [...prevMessages, userMessage]);
      setInput('');
      setLoading(true);

      try {
        const history = messages.map(msg => ({ role: msg.role, content: msg.content }));
        const personaLabel = selectedPersona.coordinator_label || selectedPersona.display_name;
        const aiResponse = await sendMessage(personaLabel, input, history);
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: aiResponse,
          timestamp: new Date()
        };
        setMessages((prevMessages) => [...prevMessages, assistantMessage]);
      } catch (error) {
        console.error('Error sending message:', error);
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${error instanceof Error ? error.message : 'Could not send message. Backend may not be running.'}`,
          timestamp: new Date()
        };
        setMessages((prevMessages) => [...prevMessages, errorMessage]);
      } finally {
        setLoading(false);
      }
    }
  };

  // If no persona is selected, show a message
  if (!selectedPersona) {
    return (
      <div className="flex flex-col h-screen bg-gray-50 items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-gray-900 mb-4">No Persona Selected</h1>
          <p className="text-gray-600 mb-6">Please select a character first to start chatting.</p>
          <a
            href="/select"
            className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Select Character
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
        <h1 className="text-2xl font-semibold text-center text-gray-900">
          Chat with {selectedPersona.display_name}
        </h1>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            personaAvatar={`/images/${selectedPersona.image}`}
            userAvatar="/images/user_avatar.png"
            showTimestamp={false}
          />
        ))}
        {loading && <TypingIndicator />}
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            className="flex-1 px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            placeholder="Type a message..."
            disabled={loading || !selectedPersona}
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || !selectedPersona || !input.trim()}
            className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-medium rounded-2xl hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:from-blue-500 disabled:hover:to-purple-600 transition-all duration-200"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chat;