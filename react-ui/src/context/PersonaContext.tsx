import React, { createContext, useState, useContext, ReactNode, useEffect, useCallback } from 'react';
import { ChatSession, SessionWithMessages, fetchSessions, createSession, getSessionWithMessages, updateSession, deleteSession, sendMessageToSession, exportSession, importSession, clearSessionMessages as clearSessionMessagesApi } from '../services/api';
import { Message } from '../components/MessageBubble';
import { predictWebSearch, formatPredictionLog } from '../utils/searchHeuristics';

interface Persona {
  key: string;
  display_name: string;
  style: string;
  image: string;
  avatar?: string;
  rarity: string;
  coordinator_label?: string;
  bg?: string;
  voice?: { // Optional, as not all personas might have it
    greeting: string;
  };
}

interface PullRecord {
  personaKey: string;
  rarity: string;
  timestamp: number;
  pullCount: number; // 1, 5, or 10
}

interface PullStats {
  totalPulls: number;
  totalSpent: number; // in gems
  legendaryCount: number;
  epicCount: number;
  rareCount: number;
  commonCount: number;
  averageRarity: number;
  bestStreak: number;
}

interface PersonaContextType {
  selectedPersona: Persona | null;
  setSelectedPersona: (persona: Persona | null) => void;
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  messages: Message[];
  setCurrentSession: (session: ChatSession | null) => void;
  loadSessions: () => Promise<void>;
  refreshSessions: () => Promise<void>;
  createNewSession: (personaKey: string, title?: string) => Promise<ChatSession>;
  loadSessionMessages: (sessionId: string) => Promise<void>;
  updateSessionTitle: (sessionId: string, title: string) => Promise<void>;
  deleteSessionById: (sessionId: string) => Promise<void>;
  clearSessionMessages: (sessionId: string) => Promise<void>;
  sendMessage: (message: string, sessionId?: string) => Promise<Message>;
  retryMessage: (messageId: string) => Promise<void>;
  exportCurrentSession: () => Promise<string>;
  importSessionData: (exportData: any) => Promise<ChatSession>;
  // Search status
  isSearching: boolean;
  // Collection management
  collectedPersonas: Set<string>;
  addToCollection: (personaKey: string) => void;
  isCollected: (personaKey: string) => boolean;
  collectionStats: { total: number; legendary: number; epic: number; rare: number; common: number };
  // Pull history
  pullHistory: PullRecord[];
  addPullRecord: (record: Omit<PullRecord, 'timestamp'>) => void;
  pullStats: PullStats;
}

const PersonaContext = createContext<PersonaContextType | undefined>(undefined);

export const PersonaProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);

  // Collection management
  const [collectedPersonas, setCollectedPersonas] = useState<Set<string>>(() => {
    const stored = localStorage.getItem('collectedPersonas');
    return stored ? new Set(JSON.parse(stored)) : new Set();
  });

  // Pull history
  const [pullHistory, setPullHistory] = useState<PullRecord[]>(() => {
    const stored = localStorage.getItem('pullHistory');
    return stored ? JSON.parse(stored) : [];
  });

  const loadSessions = useCallback(async () => {
    try {
      const fetchedSessions = await fetchSessions();
      setSessions(fetchedSessions);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  }, []);

  const createNewSession = async (personaKey: string, title?: string): Promise<ChatSession> => {
    const newSession = await createSession(personaKey, title);
    setSessions(prev => [newSession, ...prev]);
    setCurrentSession(newSession);
    setMessages([]);
    return newSession;
  };

  const loadSessionMessages = async (sessionId: string) => {
    try {
      const sessionData: SessionWithMessages = await getSessionWithMessages(sessionId);
      setCurrentSession(sessionData.session);
      // Convert API messages to UI messages
      const uiMessages: Message[] = sessionData.messages.map(apiMsg => ({
        ...apiMsg,
        latency: apiMsg.latency_ms,
      }));
      setMessages(uiMessages);
    } catch (error) {
      console.error('Failed to load session messages:', error);
    }
  };

  const updateSessionTitle = async (sessionId: string, title: string) => {
    try {
      const updatedSession = await updateSession(sessionId, { title });
      setSessions(prev => prev.map(s => s.id === sessionId ? updatedSession : s));
      if (currentSession?.id === sessionId) {
        setCurrentSession(updatedSession);
      }
    } catch (error) {
      console.error('Failed to update session title:', error);
    }
  };

  const deleteSessionById = async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const clearSessionMessages = async (sessionId: string) => {
    try {
      await clearSessionMessagesApi(sessionId);
      // Clear messages in UI if this is the current session
      if (currentSession?.id === sessionId) {
        setMessages([]);
      }
      // Update the session's updated_at timestamp in the sessions list
      setSessions(prev => prev.map(s =>
        s.id === sessionId
          ? { ...s, updated_at: new Date().toISOString() }
          : s
      ));
    } catch (error) {
      console.error('Failed to clear session messages:', error);
      throw error; // Re-throw so UI can handle the error
    }
  };

  const sendMessage = async (message: string, sessionId?: string, retryCount = 0): Promise<Message> => {
    const targetSessionId = sessionId || currentSession?.id;
    if (!targetSessionId) {
      throw new Error('No session selected');
    }

    // Only update UI messages if this is for the current session
    const shouldUpdateUI = !sessionId || targetSessionId === currentSession?.id;

    // Predict if web search will be used (client-side heuristic)
    const prediction = predictWebSearch(message, selectedPersona?.rarity);
    console.log(formatPredictionLog(prediction, message));

    console.log('[PersonaContext] Sending message:', {
      sessionId: targetSessionId,
      message: message.substring(0, 50) + (message.length > 50 ? '...' : ''),
      retryCount,
      predictedSearch: prediction.willSearch,
      confidence: prediction.confidence
    });

    // Record start time for latency tracking
    const startTime = Date.now();

    if (shouldUpdateUI) {
      const userMessage: Message = {
        id: `user-${Date.now()}-${retryCount}`,
        role: 'user',
        content: message,
        timestamp: new Date(),
        status: 'sending',
      };
      setMessages(prev => [...prev, userMessage]);

      // Use heuristic to decide which indicator to show
      // Only set isSearching=true if we predict a web search will happen
      if (prediction.willSearch && prediction.confidence === 'high') {
        console.log('[PersonaContext] 🔍 Showing SearchIndicator (high confidence prediction)');
        setIsSearching(true);
      } else {
        console.log('[PersonaContext] ⌨️ Showing TypingIndicator (no search predicted)');
        setIsSearching(false);
      }
    }

    try {
      const assistantMessage = await sendMessageToSession(targetSessionId, message);

      // Calculate latency
      const endTime = Date.now();
      const latency = endTime - startTime;

      // Add latency and status to the assistant message
      const assistantMessageWithMetadata: Message = {
        ...assistantMessage,
        latency,
        status: 'delivered',
      };

      // Log prediction accuracy
      const predictionCorrect = prediction.willSearch === assistantMessage.used_search;
      console.log('[PersonaContext] Response received:', {
        latency_ms: latency,
        used_search: assistantMessage.used_search,
        search_results_count: assistantMessage.search_results_count,
        predicted_search: prediction.willSearch,
        prediction_correct: predictionCorrect ? '✅' : '❌',
        prediction_confidence: prediction.confidence
      });

      if (shouldUpdateUI) {
        // Stop search indicator (response received)
        setIsSearching(false);

        // Update the user message status to sent
        setMessages(prev => prev.map(msg =>
          msg.id.startsWith('user-') && msg.content === message && msg.status === 'sending'
            ? { ...msg, status: 'sent' }
            : msg
        ));

        // Add the assistant message
        setMessages(prev => [...prev, assistantMessageWithMetadata]);
        // Refresh session list to update message count
        loadSessions();
      }

      return assistantMessageWithMetadata;
    } catch (error) {
      console.error('[PersonaContext] Error sending message:', error);

      if (shouldUpdateUI) {
        // Stop search indicator on error
        setIsSearching(false);

        // Update the user message status to failed
        setMessages(prev => prev.map(msg =>
          msg.id.startsWith('user-') && msg.content === message && msg.status === 'sending'
            ? { ...msg, status: 'failed', retryCount }
            : msg
        ));
      }

      throw error;
    }
  };

  const retryMessage = async (messageId: string): Promise<void> => {
    const messageToRetry = messages.find(msg => msg.id === messageId);
    if (!messageToRetry || messageToRetry.role !== 'user' || messageToRetry.status !== 'failed') {
      throw new Error('Message not found or not retryable');
    }

    const retryCount = (messageToRetry.retryCount || 0) + 1;

    try {
      await sendMessage(messageToRetry.content, currentSession?.id, retryCount);
      // Remove the failed message from the UI
      setMessages(prev => prev.filter(msg => msg.id !== messageId));
    } catch (error) {
      console.error('Retry failed:', error);
      throw error;
    }
  };

  const exportCurrentSession = async (): Promise<string> => {
    if (!currentSession) {
      throw new Error('No current session to export');
    }
    const exportData = await exportSession(currentSession.id);
    return JSON.stringify(exportData, null, 2);
  };

  const importSessionData = async (exportData: any): Promise<ChatSession> => {
    const newSession = await importSession(exportData);
    setSessions(prev => [newSession, ...prev]);
    return newSession;
  };

  // Collection management functions
  const addToCollection = (personaKey: string) => {
    setCollectedPersonas(prev => {
      const newSet = new Set(prev);
      newSet.add(personaKey);
      localStorage.setItem('collectedPersonas', JSON.stringify(Array.from(newSet)));
      return newSet;
    });
  };

  const isCollected = (personaKey: string) => {
    return collectedPersonas.has(personaKey);
  };

  // Calculate collection stats
  const collectionStats = React.useMemo(() => {
    const stats = { total: collectedPersonas.size, legendary: 0, epic: 0, rare: 0, common: 0 };
    // Note: We'd need persona data to calculate rarity stats, but for now just return total
    return stats;
  }, [collectedPersonas]);

  // Pull history functions
  const addPullRecord = (record: Omit<PullRecord, 'timestamp'>) => {
    const newRecord: PullRecord = {
      ...record,
      timestamp: Date.now(),
    };
    setPullHistory(prev => {
      const newHistory = [...prev, newRecord];
      localStorage.setItem('pullHistory', JSON.stringify(newHistory));
      return newHistory;
    });
  };

  // Calculate pull stats
  const pullStats = React.useMemo((): PullStats => {
    const stats: PullStats = {
      totalPulls: pullHistory.length,
      totalSpent: pullHistory.reduce((sum, record) => sum + (record.pullCount * 100), 0),
      legendaryCount: pullHistory.filter(r => r.rarity === 'legendary').length,
      epicCount: pullHistory.filter(r => r.rarity === 'epic').length,
      rareCount: pullHistory.filter(r => r.rarity === 'rare').length,
      commonCount: pullHistory.filter(r => r.rarity === 'common').length,
      averageRarity: 0,
      bestStreak: 0,
    };

    // Calculate average rarity (legendary=4, epic=3, rare=2, common=1)
    if (stats.totalPulls > 0) {
      const rarityScores = pullHistory.map(r => {
        switch (r.rarity) {
          case 'legendary': return 4;
          case 'epic': return 3;
          case 'rare': return 2;
          default: return 1;
        }
      });
      stats.averageRarity = rarityScores.reduce((sum, score) => sum + score, 0) / stats.totalPulls;
    }

    // Calculate best streak (consecutive rare+ pulls)
    let currentStreak = 0;
    let bestStreak = 0;
    for (const record of pullHistory.slice().reverse()) {
      if (record.rarity === 'rare' || record.rarity === 'epic' || record.rarity === 'legendary') {
        currentStreak++;
        bestStreak = Math.max(bestStreak, currentStreak);
      } else {
        currentStreak = 0;
      }
    }
    stats.bestStreak = bestStreak;

    return stats;
  }, [pullHistory]);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  return (
    <PersonaContext.Provider value={{
      selectedPersona,
      setSelectedPersona,
      sessions,
      currentSession,
      messages,
      setCurrentSession,
      loadSessions,
      refreshSessions: loadSessions,
      createNewSession,
      loadSessionMessages,
      updateSessionTitle,
      deleteSessionById,
      clearSessionMessages,
      sendMessage,
      retryMessage,
      exportCurrentSession,
      importSessionData,
      isSearching,
      collectedPersonas,
      addToCollection,
      isCollected,
      collectionStats,
      pullHistory,
      addPullRecord,
      pullStats,
    }}>
      {children}
    </PersonaContext.Provider>
  );
};

export const usePersona = () => {
  const context = useContext(PersonaContext);
  if (context === undefined) {
    throw new Error('usePersona must be used within a PersonaProvider');
  }
  return context;
};
