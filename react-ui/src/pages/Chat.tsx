import React, { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { TypingIndicator } from '../components/TypingIndicator'
import { ToolIndicator } from '../components/ToolIndicator'
import { ChatHeader } from '../components/ChatHeader'
import { ChatInput } from '../components/ChatInput'
import { ErrorBoundary } from '../components/ErrorBoundary'
import { VirtualizedMessageList } from '../components/VirtualizedMessageList'
import SessionList from '../components/SessionList'
import { ResonanceToast } from '../components/ResonanceToast'
import { LoreRevealOverlay } from '../components/LoreRevealOverlay'
import NephilimBackground from '../components/NephilimBackground'
import { fetchPersonas, greetWithSession, checkLoreUnlocks } from '../services/api'
import { usePersona } from '../context/PersonaContext'

/** Extract NEPHILIM persona short name from key (e.g. nephilim_cipher -> cipher) */
const extractPersonaName = (key: string): 'eeva' | 'aegis' | 'solace' | 'nyx' | 'cipher' | 'aurora' | null => {
  if (!key.startsWith('nephilim_')) return null
  const name = key.replace('nephilim_', '')
  const valid = ['eeva', 'aegis', 'solace', 'nyx', 'cipher', 'aurora'] as const
  return valid.includes(name as any) ? (name as typeof valid[number]) : null
}

/** Map persona short names to ambient orb colors */
const personaOrbColors: Record<string, [string, string, string]> = {
  eeva: ['rgba(224, 195, 252, 0.12)', 'rgba(196, 167, 231, 0.08)', 'rgba(224, 195, 252, 0.06)'],
  aegis: ['rgba(74, 144, 217, 0.12)', 'rgba(107, 163, 224, 0.08)', 'rgba(74, 144, 217, 0.06)'],
  solace: ['rgba(126, 184, 218, 0.12)', 'rgba(94, 174, 211, 0.08)', 'rgba(126, 184, 218, 0.06)'],
  nyx: ['rgba(155, 89, 182, 0.15)', 'rgba(255, 0, 255, 0.10)', 'rgba(155, 89, 182, 0.06)'],
  cipher: ['rgba(46, 204, 113, 0.12)', 'rgba(39, 174, 96, 0.08)', 'rgba(46, 204, 113, 0.06)'],
  aurora: ['rgba(243, 156, 18, 0.12)', 'rgba(230, 126, 34, 0.08)', 'rgba(243, 156, 18, 0.06)'],
}

const defaultOrbColors: [string, string, string] = [
  'rgba(0, 255, 255, 0.08)',
  'rgba(255, 0, 255, 0.06)',
  'rgba(0, 255, 255, 0.05)',
]

const Chat: React.FC = () => {
  const [input, setInput] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [initializingSession, setInitializingSession] = useState<boolean>(false)
  const [personas, setPersonas] = useState<any[]>([])
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false)
  const [showResonanceToast, setShowResonanceToast] = useState<boolean>(false)
  const [loreFragment, setLoreFragment] = useState<{ title: string; content: string; rarity: string } | null>(null)
  const [touchStartX, setTouchStartX] = useState<number>(0)
  const [touchEndX, setTouchEndX] = useState<number>(0)
  const initializingRef = useRef<string | null>(null)
  const resonanceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { selectedPersona, currentSession, messages, sessions, createNewSession, sendMessage, exportCurrentSession, importSessionData, loadSessionMessages, setSelectedPersona, clearSessionMessages, retryMessage, refreshSessions, isSearching, toolType } = usePersona()

  useEffect(() => {
    return () => {
      if (resonanceTimerRef.current) clearTimeout(resonanceTimerRef.current)
    }
  }, [])

  useEffect(() => {
    const loadPersonas = async () => {
      try {
        const fetchedPersonas = await fetchPersonas()
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
        }))
        setPersonas(processedPersonas)
        if (refreshSessions) {
          await refreshSessions()
        }
      } catch (error) {
        console.error('Failed to load personas:', error)
      }
    }
    loadPersonas()
  }, [refreshSessions])

  // Auto-select persona from constellation/dashboard navigation
  useEffect(() => {
    const pendingPersona = localStorage.getItem('nephilim_pending_persona')
    if (pendingPersona && personas.length > 0) {
      const targetPersona = personas.find(p => p.key === pendingPersona)
      if (targetPersona) {
        setSelectedPersona(targetPersona)
      }
      localStorage.removeItem('nephilim_pending_persona')
    }
  }, [personas, setSelectedPersona])

  useEffect(() => {
    if (!selectedPersona) return
    if (initializingRef.current === selectedPersona.key) return
    if (currentSession && currentSession.persona_key === selectedPersona.key) return

    initializingRef.current = selectedPersona.key
    setInitializingSession(true)

    const initializeChat = async () => {
      try {
        const existingSessions = sessions.filter(s => s.persona_key === selectedPersona.key)
        if (existingSessions.length > 0) {
          const mostRecentSession = existingSessions.reduce((latest, current) =>
            new Date(current.updated_at) > new Date(latest.updated_at) ? current : latest
          )
          if (!currentSession || currentSession.id !== mostRecentSession.id) {
            await loadSessionMessages(mostRecentSession.id)
          }
        } else {
          const newSession = await createNewSession(selectedPersona.key, `Chat with ${selectedPersona.display_name}`)
          const personaLabel = selectedPersona.coordinator_label || selectedPersona.display_name
          await greetWithSession(newSession.id, personaLabel)
          await loadSessionMessages(newSession.id)
        }
      } catch (error) {
        console.error('Error initializing chat:', error)
      } finally {
        initializingRef.current = null
        setInitializingSession(false)
      }
    }

    initializeChat()
  }, [selectedPersona, currentSession, sessions, loadSessionMessages, createNewSession])

  const handleSendMessage = async () => {
    if (input.trim() && currentSession && selectedPersona && !initializingSession) {
      setInput('')
      setLoading(true)

      try {
        await sendMessage(input)
        if (selectedPersona.key.startsWith('nephilim_')) {
          if (resonanceTimerRef.current) clearTimeout(resonanceTimerRef.current)
          setShowResonanceToast(true)
          resonanceTimerRef.current = setTimeout(() => setShowResonanceToast(false), 4000)

          // Check for newly unlocked lore fragments (non-blocking)
          try {
            const userId = localStorage.getItem('nephilim_user_id') || 'default_seeker'
            const loreResult = await checkLoreUnlocks(userId, selectedPersona.key)
            if (loreResult.newly_unlocked > 0 && loreResult.fragments.length > 0) {
              const frag = loreResult.fragments[0]
              setTimeout(() => {
                setLoreFragment({
                  title: frag.fragment_title || frag.title || 'Unknown Fragment',
                  content: frag.fragment || frag.content || '',
                  rarity: frag.rarity || 'common',
                })
              }, 2500)
            }
          } catch (loreError) {
            // Silently ignore lore check failures — do not disrupt chat flow
          }
        }
      } catch (error) {
        console.error('Error sending message:', error)
      } finally {
        setLoading(false)
      }
    }
  }

  const handleRetryMessage = useCallback(async (messageId: string) => {
    try {
      await retryMessage(messageId)
    } catch (error) {
      console.error('Failed to retry message:', error)
      alert('Failed to retry message. Please try again.')
    }
  }, [retryMessage])

  // No persona selected — void-themed prompt
  if (!selectedPersona) {
    return (
      <NephilimBackground particles={true} skyline={false} intensity={0.4}>
        <div className="flex flex-col h-full items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-semibold text-gray-100 mb-4">No Persona Selected</h1>
            <p className="text-gray-400 mb-6">Please select a character first to start chatting.</p>
            <a
              href="/select"
              className="px-6 py-3 bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 rounded-lg hover:bg-cyan-500/30 transition-colors"
            >
              Select Character
            </a>
          </div>
        </div>
      </NephilimBackground>
    )
  }

  const handleExport = async () => {
    try {
      const exportData = await exportCurrentSession()
      const blob = new Blob([exportData], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${currentSession?.title || 'chat'}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to export chat:', error)
      alert('Failed to export chat. Please try again.')
    }
  }

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      const exportData = JSON.parse(text)

      if (!exportData.version || !exportData.session || !exportData.messages) {
        throw new Error('Invalid export file format')
      }

      const newSession = await importSessionData(exportData)
      await loadSessionMessages(newSession.id)

      alert('Chat imported successfully!')
    } catch (error) {
      console.error('Failed to import chat:', error)
      alert(`Failed to import chat: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      event.target.value = ''
    }
  }

  const handleClearChat = async () => {
    if (!currentSession) return

    if (window.confirm('Are you sure you want to clear all messages in this chat? This action cannot be undone.')) {
      try {
        await clearSessionMessages(currentSession.id)
      } catch (error) {
        console.error('Failed to clear chat:', error)
        alert('Failed to clear chat. Please try again.')
      }
    }
  }

  const handleSessionSelect = async (session: any) => {
    const sessionPersona = personas.find(p => p.key === session.persona_key)
    if (sessionPersona) {
      setSelectedPersona(sessionPersona)
    }
    await loadSessionMessages(session.id)
    setIsSidebarOpen(false)
  }

  // Touch handlers for swipe gestures
  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStartX(e.targetTouches[0].clientX)
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    setTouchEndX(e.targetTouches[0].clientX)
  }

  const handleTouchEnd = () => {
    if (!touchStartX || !touchEndX) return

    const distance = touchStartX - touchEndX
    const isLeftSwipe = distance > 50

    if (isLeftSwipe && isSidebarOpen) {
      setIsSidebarOpen(false)
    }

    setTouchStartX(0)
    setTouchEndX(0)
  }

  // Derive persona name for NephilimBackground
  const nephilimPersona = extractPersonaName(selectedPersona.key)
  const orbColors = nephilimPersona
    ? personaOrbColors[nephilimPersona] || defaultOrbColors
    : defaultOrbColors

  return (
    <NephilimBackground persona={nephilimPersona} particles={true} skyline={false} intensity={0.5}>
      <div className="flex h-full overflow-hidden relative transition-all duration-500">
        {/* Ambient gradient orbs */}
        <motion.div
          className="absolute w-[600px] h-[600px] rounded-full pointer-events-none opacity-60"
          style={{
            background: `radial-gradient(circle, ${orbColors[0]}, transparent 70%)`,
            top: '10%',
            left: '-5%',
            filter: 'blur(60px)',
          }}
          animate={{
            x: [0, 40, -20, 0],
            y: [0, -30, 20, 0],
          }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute w-[500px] h-[500px] rounded-full pointer-events-none opacity-50"
          style={{
            background: `radial-gradient(circle, ${orbColors[1]}, transparent 70%)`,
            top: '50%',
            right: '-10%',
            filter: 'blur(80px)',
          }}
          animate={{
            x: [0, -30, 20, 0],
            y: [0, 25, -35, 0],
          }}
          transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute w-[400px] h-[400px] rounded-full pointer-events-none opacity-40"
          style={{
            background: `radial-gradient(circle, ${orbColors[2]}, transparent 70%)`,
            bottom: '5%',
            left: '30%',
            filter: 'blur(70px)',
          }}
          animate={{
            x: [0, 25, -15, 0],
            y: [0, -20, 30, 0],
          }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        />

        {/* Content container */}
        <div className="relative z-10 flex h-full w-full">
          {/* Desktop: always-visible sidebar */}
          <div className="hidden md:block w-80 flex-shrink-0 h-full">
            <SessionList onSessionSelect={handleSessionSelect} />
          </div>

          {/* Mobile: slide-in overlay sidebar */}
          <AnimatePresence>
            {isSidebarOpen && (
              <>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="fixed inset-0 bg-black/50 z-40 md:hidden"
                  onClick={() => setIsSidebarOpen(false)}
                />
                <motion.div
                  initial={{ x: -320 }}
                  animate={{ x: 0 }}
                  exit={{ x: -320 }}
                  transition={{ type: 'spring', damping: 30, stiffness: 350 }}
                  className="fixed z-50 h-full w-80 md:hidden"
                >
                  <SessionList onSessionSelect={handleSessionSelect} />
                </motion.div>
              </>
            )}
          </AnimatePresence>

          {/* Main Chat Area */}
          <div
            className="flex-1 flex flex-col overflow-hidden relative"
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

            {/* Messages Container */}
            <ErrorBoundary>
              <div className="flex-1 min-h-0 relative flex flex-col">
                {messages.length === 0 && currentSession && !initializingSession ? (
                  <div className="flex-1 flex items-center justify-center text-center text-white/60">
                    Start a conversation with {selectedPersona.display_name}!
                  </div>
                ) : messages.length === 0 && initializingSession ? (
                  <div className="flex-1 flex items-center justify-center text-center text-white/60">
                    <div>
                      <TypingIndicator personaName={selectedPersona.display_name} />
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

                {/* Resonance Toast */}
                <AnimatePresence>
                  {showResonanceToast && (
                    <motion.div
                      className="fixed bottom-28 left-1/2 -translate-x-1/2 z-30 pointer-events-none"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.4 }}
                    >
                      <ResonanceToast amount={5} />
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Indicators */}
                <AnimatePresence mode="wait">
                  {isSearching && !initializingSession && toolType !== 'none' && (
                    <div className="fixed bottom-24 left-4 md:left-6 z-50 pointer-events-none">
                      <ToolIndicator
                        toolType={toolType}
                        personaName={selectedPersona?.display_name}
                        celestial_order={selectedPersona?.celestial_order ?? 'wanderer'}
                      />
                    </div>
                  )}
                  {!isSearching && loading && !initializingSession && (
                    <div className="fixed bottom-24 left-4 md:left-6 z-50 pointer-events-none">
                      <TypingIndicator personaName={selectedPersona.display_name} />
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

      {/* Lore Reveal Overlay — shown when a new lore fragment is unlocked */}
      <AnimatePresence>
        {loreFragment && (
          <LoreRevealOverlay
            fragment={loreFragment}
            personaName={selectedPersona.display_name}
            onDismiss={() => setLoreFragment(null)}
          />
        )}
      </AnimatePresence>
    </NephilimBackground>
  )
}

export default Chat
