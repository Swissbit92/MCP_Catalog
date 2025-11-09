import React, { createContext, useState, useContext, ReactNode, useEffect } from 'react';
import { ChatSession, Message, SessionWithMessages, fetchSessions, createSession, getSessionWithMessages, updateSession, deleteSession, sendMessageToSession, exportSession, importSession, clearSessionMessages as clearSessionMessagesApi } from '../services/api';

interface Persona {
  key: string;
  display_name: string;
  style: string;
  image: string;
  avatar?: string;
  rarity: string;
  coordinator_label?: string;
  voice?: { // Optional, as not all personas might have it
    greeting: string;
  };
}

interface PersonaContextType {
  selectedPersona: Persona | null;
  setSelectedPersona: (persona: Persona | null) => void;
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  messages: Message[];
  setCurrentSession: (session: ChatSession | null) => void;
  loadSessions: () => Promise<void>;
  createNewSession: (personaKey: string, title?: string) => Promise<ChatSession>;
  loadSessionMessages: (sessionId: string) => Promise<void>;
  updateSessionTitle: (sessionId: string, title: string) => Promise<void>;
  deleteSessionById: (sessionId: string) => Promise<void>;
  clearSessionMessages: (sessionId: string) => Promise<void>;
  sendMessage: (message: string, sessionId?: string) => Promise<Message>;
  exportCurrentSession: () => Promise<string>;
  importSessionData: (exportData: any) => Promise<ChatSession>;
}

const PersonaContext = createContext<PersonaContextType | undefined>(undefined);

export const PersonaProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);

  const loadSessions = async () => {
    try {
      const fetchedSessions = await fetchSessions();
      setSessions(fetchedSessions);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

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
      setMessages(sessionData.messages);
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

  const sendMessage = async (message: string, sessionId?: string): Promise<Message> => {
    const targetSessionId = sessionId || currentSession?.id;
    if (!targetSessionId) {
      throw new Error('No session selected');
    }

    // Only update UI messages if this is for the current session
    const shouldUpdateUI = !sessionId || targetSessionId === currentSession?.id;

    console.log('Sending message to session:', targetSessionId, 'Message:', message);

    if (shouldUpdateUI) {
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: message,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, userMessage]);
    }

    try {
      const assistantMessage = await sendMessageToSession(targetSessionId, message);
      console.log('Received assistant message:', assistantMessage);

      if (shouldUpdateUI) {
        setMessages(prev => [...prev, assistantMessage]);
        // Refresh session list to update message count
        loadSessions();
      }

      return assistantMessage;
    } catch (error) {
      console.error('Error sending message:', error);
      if (shouldUpdateUI) {
        // Remove the user message if sending failed
        setMessages(prev => prev.slice(0, -1));
      }
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

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  return (
    <PersonaContext.Provider value={{
      selectedPersona,
      setSelectedPersona,
      sessions,
      currentSession,
      messages,
      setCurrentSession,
      loadSessions,
      createNewSession,
      loadSessionMessages,
      updateSessionTitle,
      deleteSessionById,
      clearSessionMessages,
      sendMessage,
      exportCurrentSession,
      importSessionData,
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
