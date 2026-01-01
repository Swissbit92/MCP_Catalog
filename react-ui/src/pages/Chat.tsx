import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageBubble } from '../components/MessageBubble';
import { TypingIndicator } from '../components/TypingIndicator';
import { ToolIndicator } from '../components/ToolIndicator';
import SessionList from '../components/SessionList';
import { fetchPersonas, greetWithSession } from '../services/api';
import { usePersona } from '../context/PersonaContext';
import { Menu, X } from 'lucide-react';

// Floating particles component for glassmorphism effect
const FloatingParticles: React.FC<{ isActive: boolean }> = React.memo(({ isActive }) => {
  const particles = React.useMemo(() => {
    return Array.from({ length: 8 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      xOffset: Math.random() * 10 - 5,
      duration: 3 + Math.random() * 2,
      delay: Math.random() * 2,
    }));
  }, []); // Empty dependency array ensures particles are generated only once

  // Only animate when active (typing, searching, or loading)
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((particle) => (
        <motion.div
          key={particle.id}
          className="absolute w-1.5 h-1.5 bg-white/30 rounded-full shadow-sm"
          style={{
            left: `${particle.left}%`,
            top: `${particle.top}%`,
          }}
          animate={isActive ? {
            y: [0, -20, 0],
            x: [0, particle.xOffset, 0],
            opacity: [0.2, 0.6, 0.2],
            scale: [0.6, 1.0, 0.6],
          } : {
            opacity: 0.1,
            scale: 0.6,
          }}
          transition={{
            duration: particle.duration,
            repeat: isActive ? Infinity : 0,
            delay: particle.delay,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
});

// Persona color schemes based on rarity (matching character cards)
const getPersonaColorScheme = (rarity?: string) => {
  switch (rarity) {
    case 'legendary':
      return {
        primary: 'from-yellow-500 to-amber-600',
        secondary: 'from-yellow-400 to-amber-500',
        accent: 'text-yellow-600',
        bgGradient: 'from-yellow-100/20 to-amber-100/20',
      };
    case 'epic':
      return {
        primary: 'from-purple-500 to-violet-600',
        secondary: 'from-purple-400 to-violet-500',
        accent: 'text-purple-600',
        bgGradient: 'from-purple-100/20 to-violet-100/20',
      };
    case 'rare':
      return {
        primary: 'from-blue-500 to-cyan-600',
        secondary: 'from-blue-400 to-cyan-500',
        accent: 'text-blue-600',
        bgGradient: 'from-blue-100/20 to-cyan-100/20',
      };
    case 'common':
    default:
      return {
        primary: 'from-gray-500 to-slate-600',
        secondary: 'from-gray-400 to-slate-500',
        accent: 'text-gray-600',
        bgGradient: 'from-gray-100/20 to-slate-100/20',
      };
  }
};

const Chat: React.FC = () => {
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [initializingSession, setInitializingSession] = useState<boolean>(false);
  const [personas, setPersonas] = useState<any[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [touchStartX, setTouchStartX] = useState<number>(0);
  const [touchEndX, setTouchEndX] = useState<number>(0);
  const initializingRef = useRef<string | null>(null); // Track which persona we're initializing for
  const messagesEndRef = useRef<HTMLDivElement>(null);
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

  // Get persona background and color scheme
  const personaBackground = selectedPersona?.bg ? `/images/${selectedPersona.bg.replace('images/', '')}` : null;
  const colorScheme = getPersonaColorScheme(selectedPersona?.rarity);

  return (
    <div className="flex h-full overflow-hidden relative transition-all duration-500">
      {/* Deep space gradient background (Option 6: Glassmorphic + Rarity Hybrid) */}
      <div className="absolute inset-0 space-background"></div>
      <div className="absolute inset-0 nebula-overlay"></div>

      {/* Floating particles - only animate when there's activity */}
      <FloatingParticles isActive={loading || isSearching || input.length > 0} />

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
        <div className="bg-white border-b border-gray-200 px-4 md:px-6 py-4 shadow-sm flex-shrink-0">
        <div className="flex justify-between items-center gap-3">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            {/* Sidebar Toggle Button */}
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
              aria-label="Toggle sidebar"
            >
              {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <h1 className="text-xl md:text-2xl font-semibold text-gray-900 truncate min-w-0">
              {currentSession?.title || `Chat with ${selectedPersona.display_name}`}
            </h1>
          </div>
          {currentSession && (
            <div className="flex gap-1 md:gap-2 flex-shrink-0">
              <label className="px-3 md:px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer text-sm md:text-base" title="Import Chat">
                <span className="hidden sm:inline">Import</span>
                <span className="sm:hidden">📥</span>
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImport}
                  className="hidden"
                />
              </label>
              <button
                onClick={handleExport}
                className="px-3 md:px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm md:text-base"
                title="Export Chat"
              >
                <span className="hidden sm:inline">Export</span>
                <span className="sm:hidden">📤</span>
              </button>
              <button
                onClick={handleClearChat}
                className="px-3 md:px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors text-sm md:text-base"
                title="Clear Chat"
              >
                <span className="hidden sm:inline">Clear</span>
                <span className="sm:hidden">🗑️</span>
              </button>
            </div>
          )}
        </div>
        </div>

        {/* Messages Container - with indicators positioned absolutely inside */}
        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-4 min-h-0 relative">
          <div className="space-y-3 md:space-y-4 pb-20">
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
                  userAvatar="/images/ui/user_avatar.png"
                  showTimestamp={true}
                  onRetry={handleRetryMessage}
                  personaRarity={selectedPersona.rarity}
                  personaName={selectedPersona.display_name}
                />
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Indicators - positioned absolutely inside Messages Container to not affect flex layout */}
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

        {/* Input Area */}
        <motion.div
          className="bg-white border-t border-gray-200 px-4 md:px-6 py-3 md:py-4 flex-shrink-0"
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.3 }}
        >
          <div className="flex gap-2 md:gap-3">
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
              className="flex-1 px-4 py-3 md:py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 text-base md:text-base"
              placeholder={initializingSession ? "Loading character..." : "Type a message..."}
              disabled={loading || !currentSession || initializingSession}
              whileFocus={{ scale: 1.01 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              // Mobile keyboard optimizations
              autoComplete="off"
              autoCorrect="on"
              autoCapitalize="sentences"
              spellCheck="true"
            />
            <motion.button
              onClick={handleSendMessage}
              disabled={loading || !currentSession || !input.trim() || initializingSession}
               className={`px-4 md:px-6 py-3 bg-gradient-to-r ${colorScheme.primary} text-white font-medium rounded-2xl hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 min-w-[60px] md:min-w-[80px] touch-manipulation`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            >
              <span className="hidden sm:inline">Send</span>
              <span className="sm:hidden">📤</span>
            </motion.button>
          </div>
        </motion.div>
      </div>
      </div>
    </div>
  );
};

export default Chat;