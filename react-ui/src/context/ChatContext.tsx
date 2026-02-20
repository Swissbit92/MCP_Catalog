import React, { createContext, useState, useContext, ReactNode, useEffect, useCallback } from 'react'
import {
  ChatSession,
  SessionWithMessages,
  fetchPersonas as fetchPersonasApi,
  fetchSessions,
  createSession,
  getSessionWithMessages,
  updateSession,
  deleteSession,
  sendMessageToSession,
  exportSession,
  importSession,
  clearSessionMessages as clearSessionMessagesApi,
  ChatApiResponse,
} from '../services/api'
import { Message } from '../components/MessageBubble'
import { predictWebSearch, formatPredictionLog } from '../utils/searchHeuristics'
import { Persona } from '../types/personas'

export interface ChatContextType {
  personas: Persona[]
  selectedPersona: Persona | null
  setSelectedPersona: (persona: Persona | null) => void
  sessions: ChatSession[]
  currentSession: ChatSession | null
  messages: Message[]
  setCurrentSession: (session: ChatSession | null) => void
  loadSessions: () => Promise<void>
  refreshSessions: () => Promise<void>
  createNewSession: (personaKey: string, title?: string) => Promise<ChatSession>
  loadSessionMessages: (sessionId: string) => Promise<void>
  updateSessionTitle: (sessionId: string, title: string) => Promise<void>
  deleteSessionById: (sessionId: string) => Promise<void>
  clearSessionMessages: (sessionId: string) => Promise<void>
  sendMessage: (message: string, sessionId?: string) => Promise<Message>
  retryMessage: (messageId: string) => Promise<void>
  exportCurrentSession: () => Promise<string>
  importSessionData: (exportData: any) => Promise<ChatSession>
  // Tool status
  isSearching: boolean
  toolType: 'brave' | 'mongodb' | 'none'
}

const ChatContext = createContext<ChatContextType | undefined>(undefined)

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [personas, setPersonas] = useState<Persona[]>([])
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null)
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isSearching, setIsSearching] = useState<boolean>(false)
  const [toolType, setToolType] = useState<'brave' | 'mongodb' | 'none'>('none')

  const loadSessions = useCallback(async () => {
    try {
      const fetchedSessions = await fetchSessions()
      setSessions(fetchedSessions)
    } catch (error) {
      console.error('Failed to load sessions:', error)
    }
  }, [])

  // Fetch and process personas once on mount
  useEffect(() => {
    let cancelled = false
    fetchPersonasApi().then(raw => {
      if (cancelled) return
      const processed: Persona[] = raw.map(p => ({
        key: p.key,
        display_name: p.display_name || p.key,
        style: p.style,
        image: p.image?.replace('images/', '') ?? '',
        avatar: p.avatar ? p.avatar.replace('images/', '') : undefined,
        bg: p.bg ? p.bg.replace('images/', '') : undefined,
        rarity: p.rarity,
        celestial_order: p.celestial_order,
        coordinator_label: p.coordinator_label,
        mcp_access: p.allowed_mcp,
        voice: p.voice?.greeting ? { greeting: String(p.voice.greeting) } : undefined,
      }))
      setPersonas(processed)
    })
    return () => { cancelled = true }
  }, [])

  const createNewSession = useCallback(async (personaKey: string, title?: string): Promise<ChatSession> => {
    const newSession = await createSession(personaKey, title)
    setSessions(prev => [newSession, ...prev])
    setCurrentSession(newSession)
    setMessages([])
    return newSession
  }, [])

  const loadSessionMessages = useCallback(async (sessionId: string) => {
    try {
      const sessionData: SessionWithMessages = await getSessionWithMessages(sessionId)
      setCurrentSession(sessionData.session)
      // Convert API messages to UI messages
      const uiMessages: Message[] = sessionData.messages.map(apiMsg => ({
        ...apiMsg,
        latency: apiMsg.latency_ms,
      }))
      setMessages(uiMessages)
    } catch (error) {
      console.error('Failed to load session messages:', error)
    }
  }, [])

  const updateSessionTitle = useCallback(async (sessionId: string, title: string) => {
    try {
      const updatedSession = await updateSession(sessionId, { title })
      setSessions(prev => prev.map(s => s.id === sessionId ? updatedSession : s))
      setCurrentSession(prev => prev?.id === sessionId ? updatedSession : prev)
    } catch (error) {
      console.error('Failed to update session title:', error)
    }
  }, [])

  const deleteSessionById = useCallback(async (sessionId: string) => {
    try {
      await deleteSession(sessionId)
      setSessions(prev => prev.filter(s => s.id !== sessionId))
      setCurrentSession(prev => {
        if (prev?.id === sessionId) {
          setMessages([])
          return null
        }
        return prev
      })
    } catch (error) {
      console.error('Failed to delete session:', error)
    }
  }, [])

  const clearSessionMessages = useCallback(async (sessionId: string) => {
    try {
      await clearSessionMessagesApi(sessionId)
      // Clear messages in UI if this is the current session
      setCurrentSession(prev => {
        if (prev?.id === sessionId) {
          setMessages([])
        }
        return prev
      })
      // Update the session's updated_at timestamp in the sessions list
      setSessions(prev => prev.map(s =>
        s.id === sessionId
          ? { ...s, updated_at: new Date().toISOString() }
          : s
      ))
    } catch (error) {
      console.error('Failed to clear session messages:', error)
      throw error // Re-throw so UI can handle the error
    }
  }, [])

  const sendMessage = async (message: string, sessionId?: string, retryCount = 0): Promise<Message> => {
    const targetSessionId = sessionId || currentSession?.id
    if (!targetSessionId) {
      throw new Error('No session selected')
    }

    // Only update UI messages if this is for the current session
    const shouldUpdateUI = !sessionId || targetSessionId === currentSession?.id

    // Predict if web search will be used (client-side heuristic)
    const prediction = predictWebSearch(message, selectedPersona?.rarity)
    console.log(formatPredictionLog(prediction, message))

    console.log('[ChatContext] Sending message:', {
      sessionId: targetSessionId,
      message: message.substring(0, 50) + (message.length > 50 ? '...' : ''),
      retryCount,
      predictedSearch: prediction.willSearch,
      confidence: prediction.confidence
    })

    // Record start time for latency tracking
    const startTime = Date.now()

    if (shouldUpdateUI) {
      const userMessage: Message = {
        id: `user-${Date.now()}-${retryCount}`,
        role: 'user',
        content: message,
        timestamp: new Date(),
        status: 'sending',
      }
      setMessages(prev => [...prev, userMessage])

      // Use heuristic to decide which indicator to show
      // Show ToolIndicator for brave/mongodb, TypingIndicator otherwise
      if ((prediction.toolType === 'brave' || prediction.toolType === 'mongodb') && prediction.confidence === 'high') {
        const toolName = prediction.toolType === 'brave' ? 'Web Search' : 'MongoDB'
        console.log(`[ChatContext] Showing ToolIndicator (${toolName}, high confidence prediction)`)
        setIsSearching(true)
        setToolType(prediction.toolType)
      } else {
        console.log('[ChatContext] Showing TypingIndicator (no tool predicted)')
        setIsSearching(false)
        setToolType('none')
      }
    }

    try {
      const apiResponse: ChatApiResponse = await sendMessageToSession(targetSessionId, message)

      // Calculate latency
      const endTime = Date.now()
      const latency = endTime - startTime

      // Log prediction accuracy and multi-message status
      const predictionCorrect = prediction.willSearch === apiResponse.used_search
      console.log('[ChatContext] Response received:', {
        latency_ms: latency,
        used_search: apiResponse.used_search,
        search_results_count: apiResponse.search_results_count,
        predicted_search: prediction.willSearch,
        prediction_correct: predictionCorrect ? 'correct' : 'incorrect',
        prediction_confidence: prediction.confidence,
        message_flow: apiResponse.message_flow,
        message_count: apiResponse.message_count
      })

      if (shouldUpdateUI) {
        // Update the user message status to sent
        setMessages(prev => prev.map(msg =>
          msg.id.startsWith('user-') && msg.content === message && msg.status === 'sending'
            ? { ...msg, status: 'sent' }
            : msg
        ))

        // Phase 2: Handle multi-message responses with staggered rendering
        if (apiResponse.message_flow === 'multi' && Array.isArray(apiResponse.answer)) {
          console.log('[ChatContext] Phase 2: Rendering multi-message response with staggering')

          // Stop tool indicator before first message
          setIsSearching(false)
          setToolType('none')

          // Add messages one by one with staggered delays
          for (let i = 0; i < apiResponse.answer.length; i++) {
            const messageContent = apiResponse.answer[i]

            // Show typing indicator before each message (except the first)
            if (i > 0) {
              setIsSearching(false)
              setToolType('none')
              // Small delay before showing typing indicator
              await new Promise(resolve => setTimeout(resolve, 300))
              // Show typing indicator via loading state (we don't have a separate multi-message typing state)
              // The TypingIndicator in Chat.tsx is shown when loading=true
              // We'll use a brief pause instead to simulate thinking time
              await new Promise(resolve => setTimeout(resolve, 1200))
            }

            // Create and add the message
            const assistantMessage: Message = {
              id: `assistant-${Date.now()}-${i}`,
              role: 'assistant',
              content: messageContent,
              timestamp: new Date(),
              latency: i === 0 ? latency : undefined,  // Only show latency on first message
              used_search: apiResponse.used_search,  // All messages get search status
              search_results_count: apiResponse.search_results_count,  // All messages get result count
              citation_valid: apiResponse.citation_valid,  // All messages get citation status
              metadata: apiResponse.metadata ?? undefined,  // All messages get metadata (source tags!)
              emotional_state: apiResponse.emotional_state ?? undefined,  // All messages get emotional state
              status: 'delivered',
            }

            setMessages(prev => [...prev, assistantMessage])

            // Brief pause before next message
            if (i < apiResponse.answer.length - 1) {
              await new Promise(resolve => setTimeout(resolve, 200))
            }
          }

          // Refresh session list to update message count
          loadSessions()

          // Return the first message for compatibility
          return {
            id: `assistant-${Date.now()}-0`,
            role: 'assistant',
            content: apiResponse.answer[0],
            timestamp: new Date(),
            latency,
            used_search: apiResponse.used_search,
            search_results_count: apiResponse.search_results_count,
            citation_valid: apiResponse.citation_valid,
            metadata: apiResponse.metadata ?? undefined,
            emotional_state: apiResponse.emotional_state ?? undefined,
            status: 'delivered',
          }
        } else {
          // Single message (existing behavior)
          setIsSearching(false)
          setToolType('none')

          const assistantMessageWithMetadata: Message = {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: Array.isArray(apiResponse.answer) ? apiResponse.answer[0] : apiResponse.answer,
            timestamp: new Date(),
            latency,
            used_search: apiResponse.used_search,
            search_results_count: apiResponse.search_results_count,
            citation_valid: apiResponse.citation_valid,
            metadata: apiResponse.metadata ?? undefined,
            emotional_state: apiResponse.emotional_state ?? undefined,
            status: 'delivered',
          }

          // Add the assistant message
          setMessages(prev => [...prev, assistantMessageWithMetadata])
          // Refresh session list to update message count
          loadSessions()

          return assistantMessageWithMetadata
        }
      }

      // If not updating UI, just return a dummy message for compatibility
      return {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: Array.isArray(apiResponse.answer) ? apiResponse.answer[0] : apiResponse.answer,
        timestamp: new Date(),
        latency,
        status: 'delivered',
      }
    } catch (error) {
      console.error('[ChatContext] Error sending message:', error)

      if (shouldUpdateUI) {
        // Stop tool indicator on error
        setIsSearching(false)
        setToolType('none')

        // Update the user message status to failed
        setMessages(prev => prev.map(msg =>
          msg.id.startsWith('user-') && msg.content === message && msg.status === 'sending'
            ? { ...msg, status: 'failed', retryCount }
            : msg
        ))
      }

      throw error
    }
  }

  const retryMessage = async (messageId: string): Promise<void> => {
    const messageToRetry = messages.find(msg => msg.id === messageId)
    if (!messageToRetry || messageToRetry.role !== 'user' || messageToRetry.status !== 'failed') {
      throw new Error('Message not found or not retryable')
    }

    const retryCount = (messageToRetry.retryCount || 0) + 1

    try {
      await sendMessage(messageToRetry.content, currentSession?.id, retryCount)
      // Remove the failed message from the UI
      setMessages(prev => prev.filter(msg => msg.id !== messageId))
    } catch (error) {
      console.error('Retry failed:', error)
      throw error
    }
  }

  const exportCurrentSession = useCallback(async (): Promise<string> => {
    if (!currentSession) {
      throw new Error('No current session to export')
    }
    const exportData = await exportSession(currentSession.id)
    return JSON.stringify(exportData, null, 2)
  }, [currentSession])

  const importSessionData = useCallback(async (exportData: any): Promise<ChatSession> => {
    const newSession = await importSession(exportData)
    setSessions(prev => [newSession, ...prev])
    return newSession
  }, [])

  // Load sessions on mount
  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  return (
    <ChatContext.Provider value={{
      personas,
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
      toolType,
    }}>
      {children}
    </ChatContext.Provider>
  )
}

export const useChat = () => {
  const context = useContext(ChatContext)
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider')
  }
  return context
}
