import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { MessageBubble } from '../components/MessageBubble';
import { TypingIndicator } from '../components/TypingIndicator';
import SessionList from '../components/SessionList';
import { fetchPersonas, greetWithSession } from '../services/api';
import { usePersona } from '../context/PersonaContext';

const Chat: React.FC = () => {
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [initializingSession, setInitializingSession] = useState<boolean>(false);
  const [personas, setPersonas] = useState<any[]>([]);
  const initializingRef = useRef<string | null>(null); // Track which persona we're initializing for
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { selectedPersona, currentSession, messages, sessions, createNewSession, sendMessage, exportCurrentSession, importSessionData, loadSessionMessages, setSelectedPersona } = usePersona();

  useEffect(() => {
    const loadPersonas = async () => {
      try {
        const fetchedPersonas = await fetchPersonas();
        // Process personas the same way as CharacterSelection to include avatar field
        const processedPersonas = fetchedPersonas.map(p => ({
          key: p.key,
          display_name: p.display_name || p.key,
          style: p.style,
          image: p.image.replace('ui/images/', ''),
          avatar: p.avatar ? p.avatar.replace('ui/images/', '') : undefined,
          rarity: p.rarity,
          coordinator_label: p.coordinator_label,
          voice: p.voice,
        }));
        setPersonas(processedPersonas);
      } catch (error) {
        console.error('Failed to load personas:', error);
      }
    };
    loadPersonas();
  }, []);



  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  useEffect(() => {
    if (selectedPersona && !initializingRef.current) {
      // Prevent multiple initializations for the same persona
      initializingRef.current = selectedPersona.key;
      setInitializingSession(true);

      const initializeChat = async () => {
        try {
          const existingSessions = sessions.filter(s => s.persona_key === selectedPersona.key);
          if (existingSessions.length > 0) {
            // Load the most recent session for this persona
            const mostRecentSession = existingSessions.reduce((latest, current) =>
              new Date(current.updated_at) > new Date(latest.updated_at) ? current : latest
            );
            if (!currentSession || currentSession.id !== mostRecentSession.id) {
              await loadSessionMessages(mostRecentSession.id);
            }
          } else {
            // No existing sessions, create a new one with greeting
            const newSession = await createNewSession(selectedPersona.key, `Chat with ${selectedPersona.display_name}`);

            // Generate greeting for the persona and add it directly as an assistant message
            const personaLabel = selectedPersona.coordinator_label || selectedPersona.display_name;
            await greetWithSession(newSession.id, personaLabel);

            // Load the session messages to display the greeting
            await loadSessionMessages(newSession.id);
          }
        } catch (error) {
          console.error('Error initializing chat:', error);
        } finally {
          initializingRef.current = null;
          setInitializingSession(false);
        }
      };

      initializeChat();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPersona?.key]); // Only depend on the persona key to prevent double execution

  const handleSendMessage = async () => {
    if (input.trim() && currentSession && !initializingSession) {
      setInput('');
      setLoading(true);

      try {
        await sendMessage(input);
      } catch (error) {
        console.error('Error sending message:', error);
        // Error handling is done in the context
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

  const handleExport = async () => {
    try {
      const exportData = await exportCurrentSession();
      const blob = new Blob([exportData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${currentSession?.title || 'chat'}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export chat:', error);
      alert('Failed to export chat. Please try again.');
    }
  };

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const exportData = JSON.parse(text);

      // Validate the export data structure
      if (!exportData.version || !exportData.session || !exportData.messages) {
        throw new Error('Invalid export file format');
      }

      const newSession = await importSessionData(exportData);
      await loadSessionMessages(newSession.id);

      alert('Chat imported successfully!');
    } catch (error) {
      console.error('Failed to import chat:', error);
      alert(`Failed to import chat: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      // Reset the input
      event.target.value = '';
    }
  };

  const handleSessionSelect = async (session: any) => {
    // When switching sessions, update the selected persona to match the session
    const sessionPersona = personas.find(p => p.key === session.persona_key);
    if (sessionPersona) {
      setSelectedPersona(sessionPersona);
    }
    await loadSessionMessages(session.id);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <SessionList onSessionSelect={handleSessionSelect} />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-semibold text-gray-900">
            {currentSession?.title || `Chat with ${selectedPersona.display_name}`}
          </h1>
          {currentSession && (
            <div className="flex gap-2">
              <label className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer" title="Import Chat">
                Import
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImport}
                  className="hidden"
                />
              </label>
              <button
                onClick={handleExport}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                title="Export Chat"
              >
                Export
              </button>
            </div>
          )}
        </div>
        </div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.length === 0 && currentSession && !initializingSession ? (
            <div className="text-center text-gray-500 mt-8">
              Start a conversation with {selectedPersona.display_name}!
            </div>
          ) : messages.length === 0 && initializingSession ? (
            <div className="text-center text-gray-500 mt-8">
              <TypingIndicator />
              <p className="mt-2">Loading {selectedPersona.display_name}...</p>
            </div>
          ) : (
            messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                personaAvatar={selectedPersona.avatar ? `/images/${selectedPersona.avatar}` : `/images/${selectedPersona.image}`}
                userAvatar="/images/user_avatar.png"
                showTimestamp={false}
              />
            ))
          )}
          {loading && !initializingSession && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <motion.div
          className="bg-white border-t border-gray-200 px-6 py-4"
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.3 }}
        >
          <div className="flex gap-3">
            <motion.input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
              placeholder={initializingSession ? "Loading character..." : "Type a message..."}
              disabled={loading || !currentSession || initializingSession}
              whileFocus={{ scale: 1.01 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            />
            <motion.button
              onClick={handleSendMessage}
              disabled={loading || !currentSession || !input.trim() || initializingSession}
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-medium rounded-2xl hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:from-blue-500 disabled:hover:to-purple-600 transition-all duration-200"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            >
              Send
            </motion.button>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Chat;