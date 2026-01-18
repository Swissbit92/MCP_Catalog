import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TypingIndicator } from '../components/TypingIndicator';
import { ToolIndicator } from '../components/ToolIndicator';
import { ChatHeader } from '../components/ChatHeader';
import { ChatInput } from '../components/ChatInput';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { VirtualizedMessageList } from '../components/VirtualizedMessageList';
import SessionList from '../components/SessionList';
import { fetchPersonas, greetWithSession } from '../services/api';
import { usePersona } from '../context/PersonaContext';

const Chat: React.FC = () => {
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [initializingSession, setInitializingSession] = useState<boolean>(false);
  const [personas, setPersonas] = useState<any[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [touchStartX, setTouchStartX] = useState<number>(0);
  const [touchEndX, setTouchEndX] = useState<number>(0);
  const initializingRef = useRef<string | null>(null); // Track which persona we're initializing for
  const { selectedPersona, currentSession, messages, sessions, createNewSession, sendMessage, exportCurrentSession, importSessionData, loadSessionMessages, setSelectedPersona, clearSessionMessages, retryMessage, refreshSessions, isSearching, toolType } = usePersona();

  useEffect(() => {
    const loadPersonas = async () => {
      try {
        const fetchedPersonas = await fetchPersonas();
        // Process personas the same way as character selection pages to include avatar field
        const processedPersonas = fetchedPersonas.map(p => ({
          key: p.key,
          display_name: p.display_name || p.key,
          style: p.style,
          image: p.image.replace('images/', ''),
          avatar: p.avatar ? p.avatar.replace('images/', '') : undefined,
          bg: p.bg ? p.bg.replace('images/', '') : undefined,
          rarity: p.rarity,
          coordinator_label: p.coordinator_label,
          voice: p.voice,
        }));
        setPersonas(processedPersonas);
        // Refresh sessions to clean up any orphaned sessions for removed personas
        if (refreshSessions) {
          await refreshSessions();
        }
      } catch (error) {
        console.error('Failed to load personas:', error);
      }
    };
    loadPersonas();
  }, [refreshSessions]);

  useEffect(() => {
    // Only initialize when persona key changes or when we don't have a matching session yet
    if (!selectedPersona) return;
    
    // Prevent re-initialization if we're already initializing this persona
    if (initializingRef.current === selectedPersona.key) return;
    
    // Skip if we already have a session for this persona loaded
    if (currentSession && currentSession.persona_key === selectedPersona.key) return;

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
  }, [selectedPersona, currentSession, sessions, loadSessionMessages, createNewSession]);

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

  const handleClearChat = async () => {
    if (!currentSession) return;

    if (window.confirm('Are you sure you want to clear all messages in this chat? This action cannot be undone.')) {
      try {
        await clearSessionMessages(currentSession.id);
        // The context will automatically clear the messages in the UI
      } catch (error) {
        console.error('Failed to clear chat:', error);
        alert('Failed to clear chat. Please try again.');
      }
    }
  };

  const handleRetryMessage = async (messageId: string) => {
    try {
      await retryMessage(messageId);
    } catch (error) {
      console.error('Failed to retry message:', error);
      alert('Failed to retry message. Please try again.');
    }
  };

  const handleSessionSelect = async (session: any) => {
    // When switching sessions, update the selected persona to match the session
    const sessionPersona = personas.find(p => p.key === session.persona_key);
    if (sessionPersona) {
      setSelectedPersona(sessionPersona);
    }
    await loadSessionMessages(session.id);
    // Close sidebar after selection
    setIsSidebarOpen(false);
  };

  // Touch handlers for swipe gestures
  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStartX(e.targetTouches[0].clientX);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    setTouchEndX(e.targetTouches[0].clientX);
  };

  const handleTouchEnd = () => {
    if (!touchStartX || !touchEndX) return;

    const distance = touchStartX - touchEndX;
    const isLeftSwipe = distance > 50; // Minimum swipe distance

    // Close sidebar on left swipe
    if (isLeftSwipe && isSidebarOpen) {
      setIsSidebarOpen(false);
    }

    // Reset touch coordinates
    setTouchStartX(0);
    setTouchEndX(0);
  };

  // Get persona background
  const personaBackground = selectedPersona?.bg ? `/images/${selectedPersona.bg.replace('images/', '')}` : null;

  return (
    <div className="flex h-full overflow-hidden relative transition-all duration-500">
      {/* Deep space gradient background (Option 6: Glassmorphic + Rarity Hybrid) */}
      <div className="absolute inset-0 space-background"></div>
      <div className="absolute inset-0 nebula-overlay"></div>

    {/* Subtle character background for gacha style */}
    {personaBackground && (
      <div
        className="absolute inset-0 opacity-10 pointer-events-none"
        style={{
          backgroundImage: `url(${personaBackground})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      />
    )}

      {/* Content container */}
      <div className="relative z-10 flex h-full w-full">
      {/* Sidebar Overlay */}
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.div
        initial={{ x: -320 }}
        animate={{
          x: isSidebarOpen ? 0 : -320,
          width: 320
        }}
        transition={{ type: 'spring', damping: 30, stiffness: 350 }}
        className="fixed z-50 h-full"
      >
        <SessionList onSessionSelect={handleSessionSelect} />
      </motion.div>

      {/* Main Chat Area */}
      <div
        className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 relative ${
          isSidebarOpen ? 'md:ml-[320px]' : ''
        }`}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Header */}
        <ErrorBoundary>
          <ChatHeader
            isSidebarOpen={isSidebarOpen}
            onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
            sessionTitle={currentSession?.title}
            personaName={selectedPersona.display_name}
            onExport={handleExport}
            onImport={handleImport}
            onClear={handleClearChat}
            hasCurrentSession={!!currentSession}
          />
        </ErrorBoundary>

        {/* Messages Container - with indicators positioned absolutely inside */}
        <ErrorBoundary>
          <div className="flex-1 min-h-0 relative flex flex-col">
            {messages.length === 0 && currentSession && !initializingSession ? (
              <div className="flex-1 flex items-center justify-center text-center text-gray-500">
                Start a conversation with {selectedPersona.display_name}!
              </div>
            ) : messages.length === 0 && initializingSession ? (
              <div className="flex-1 flex items-center justify-center text-center text-gray-500">
                <div>
                  <TypingIndicator />
                  <p className="mt-2">Loading {selectedPersona.display_name}...</p>
                </div>
              </div>
            ) : (
              <VirtualizedMessageList
                messages={messages}
                personaAvatar={selectedPersona.avatar ? `/images/${selectedPersona.avatar}` : `/images/${selectedPersona.image}`}
                userAvatar="/images/ui/user_avatar.png"
                personaRarity={selectedPersona.rarity}
                personaName={selectedPersona.display_name}
                onRetry={handleRetryMessage}
              />
            )}

            {/* Indicators - positioned absolutely to not affect flex layout */}
            <AnimatePresence mode="wait">
              {isSearching && !initializingSession && toolType !== 'none' && (
                <div className="fixed bottom-24 left-4 md:left-6 z-50 pointer-events-none">
                  <ToolIndicator
                    toolType={toolType}
                    personaName={selectedPersona?.display_name}
                    rarity={selectedPersona?.rarity}
                  />
                </div>
              )}
              {!isSearching && loading && !initializingSession && (
                <div className="fixed bottom-24 left-4 md:left-6 z-50 pointer-events-none">
                  <TypingIndicator />
                </div>
              )}
            </AnimatePresence>
          </div>
        </ErrorBoundary>

        {/* Input Area */}
        <ErrorBoundary>
          <ChatInput
          value={input}
          onChange={setInput}
          onSend={handleSendMessage}
          disabled={loading || !currentSession || initializingSession}
          loading={loading}
          initializingSession={initializingSession}
          hasCurrentSession={!!currentSession}
          />
        </ErrorBoundary>
      </div>
      </div>
    </div>
  );
};

export default Chat;