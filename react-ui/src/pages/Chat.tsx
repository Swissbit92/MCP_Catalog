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
import { RankCeremonyOverlay } from '../components/RankCeremonyOverlay'
import { CapabilityUnlockToast } from '../components/nephilim/CapabilityUnlockToast'
import type { RankCeremony, CapabilityUnlock } from '../services/api/types'
import NephilimBackground from '../components/NephilimBackground'
import { greetWithSession, checkLoreUnlocks, getSessionMeta } from '../services/api'
import { usePersona } from '../context/PersonaContext'
import { useAuth } from '../context/AuthContext'

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

// ADR-011: conversation-control slash commands (mirrors the Telegram gateway's /help)
const HELP_TEXT = [
  'Here\'s what I can do:',
  '',
  '/regen — reroll my last reply',
  '/continue — have me continue my last reply',
  '/undo — delete the last exchange',
  '/sys <text> — set a scene beat (e.g. /sys it\'s late and quiet)',
  '/note [text | clear] — standing direction; no text shows it, \'clear\' removes it',
  '/impersonate [hint] — draft a reply as you, fills the composer',
  '/whoami — who you\'re talking to',
  '/help — this list',
].join('\n')

const Chat: React.FC = () => {
  const { user } = useAuth()
  const [input, setInput] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [initializingSession, setInitializingSession] = useState<boolean>(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false)
  const [showResonanceToast, setShowResonanceToast] = useState<boolean>(false)
  const [loreFragment, setLoreFragment] = useState<{ title: string; content: string; rarity: string } | null>(null)
  const [rankCeremony, setRankCeremony] = useState<RankCeremony | null>(null)
  const [capabilityUnlock, setCapabilityUnlock] = useState<CapabilityUnlock | null>(null)
  const touchStartX = useRef<number>(0)
  const touchEndX = useRef<number>(0)
  const initializingRef = useRef<string | null>(null)
  const resonanceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const {
    personas, selectedPersona, currentSession, messages, sessions, createNewSession, sendMessage,
    exportCurrentSession, importSessionData, loadSessionMessages, setSelectedPersona, clearSessionMessages,
    retryMessage, refreshSessions, isSearching, toolType,
    regenerateLastReply, continueLastReply, undoLastExchange, narrate, impersonate,
    setAuthorNote, getAuthorNote, clearAuthorNote,
  } = usePersona()

  useEffect(() => {
    return () => {
      if (resonanceTimerRef.current) clearTimeout(resonanceTimerRef.current)
    }
  }, [])

  useEffect(() => {
    if (refreshSessions) refreshSessions()
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

  // ── ADR-011 conversation-control handlers ───────────────────────────────────

  const handleRegenerate = useCallback(async () => {
    try {
      setLoading(true)
      await regenerateLastReply()
    } catch (error) {
      console.error('Failed to regenerate reply:', error)
      alert('Failed to regenerate reply. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [regenerateLastReply])

  const handleContinue = useCallback(async () => {
    try {
      setLoading(true)
      await continueLastReply()
    } catch (error) {
      console.error('Failed to continue reply:', error)
      alert('Failed to continue reply. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [continueLastReply])

  const handleUndo = useCallback(async () => {
    try {
      await undoLastExchange()
    } catch (error) {
      console.error('Failed to undo last exchange:', error)
      alert('Failed to undo. Please try again.')
    }
  }, [undoLastExchange])

  /** Intercepts a leading "/" command; returns true if handled (never sent as chat text). */
  const handleSlashCommand = useCallback(async (raw: string): Promise<boolean> => {
    const trimmed = raw.trim()
    if (!trimmed.startsWith('/') || !currentSession) return false

    const spaceIdx = trimmed.indexOf(' ')
    const cmd = (spaceIdx === -1 ? trimmed : trimmed.slice(0, spaceIdx)).toLowerCase()
    const arg = spaceIdx === -1 ? '' : trimmed.slice(spaceIdx + 1).trim()

    try {
      switch (cmd) {
        case '/regen':
          await handleRegenerate()
          return true
        case '/continue':
          await handleContinue()
          return true
        case '/undo':
          await handleUndo()
          return true
        case '/sys':
          if (!arg) {
            alert('Give me a scene to set, like: /sys it\'s raining outside')
            return true
          }
          setLoading(true)
          try {
            await narrate(arg)
          } finally {
            setLoading(false)
          }
          return true
        case '/note':
          if (!arg) {
            const note = await getAuthorNote()
            alert(note ? `Current direction:\n${note}` : 'No standing direction set. Set one with /note <text>.')
          } else if (arg.toLowerCase() === 'clear') {
            await clearAuthorNote()
            alert('Cleared — no standing direction now.')
          } else {
            await setAuthorNote(arg)
            alert('Got it — I\'ll keep that in mind from now on.')
          }
          return true
        case '/impersonate': {
          const draft = await impersonate(arg || undefined)
          setInput(draft || '')
          return true
        }
        case '/whoami': {
          const meta = await getSessionMeta(currentSession.id)
          const name = meta.display_name || meta.persona_key || 'someone'
          alert(`You're talking to ${name}${meta.nsfw ? ' (adult mode)' : ''}.\n${meta.message_count} messages so far.`)
          return true
        }
        case '/help':
          alert(HELP_TEXT)
          return true
        default:
          alert(`Unknown command: ${cmd}\n\n${HELP_TEXT}`)
          return true
      }
    } catch (error) {
      console.error(`Slash command ${cmd} failed:`, error)
      alert('That command failed. Please try again.')
      return true
    }
  }, [currentSession, handleRegenerate, handleContinue, handleUndo, narrate, getAuthorNote, clearAuthorNote, setAuthorNote, impersonate])

  const handleSendMessage = useCallback(async () => {
    if (input.trim() && currentSession && selectedPersona && !initializingSession) {
      const trimmedInput = input.trim()
      if (trimmedInput.startsWith('/')) {
        setInput('')
        if (await handleSlashCommand(trimmedInput)) return
      }
      setInput('')
      setLoading(true)

      try {
        const responseMsg = await sendMessage(input)
        if (selectedPersona.key.startsWith('nephilim_')) {
          if (resonanceTimerRef.current) clearTimeout(resonanceTimerRef.current)
          setShowResonanceToast(true)
          resonanceTimerRef.current = setTimeout(() => setShowResonanceToast(false), 4000)

          // Check for rank ceremony in response metadata
          const ceremony = responseMsg.metadata?.rank_ceremony
          if (ceremony) {
            setTimeout(() => setRankCeremony(ceremony), 1500)
          }

          // Phase-2: diegetic capability-unlock beat (show the first if several)
          const unlocks = responseMsg.metadata?.capability_unlocks
          if (unlocks && unlocks.length > 0) {
            setTimeout(() => setCapabilityUnlock(unlocks[0]), 2200)
          }

          // Check for newly unlocked lore fragments (non-blocking)
          try {
            const userId = user?.sub || 'default_seeker'
            const loreResult = await checkLoreUnlocks(userId, selectedPersona.key)
            if (loreResult.newly_unlocked > 0 && loreResult.fragments.length > 0) {
              const frag = loreResult.fragments[0]
              // If a rank ceremony is active, delay lore reveal so ceremony shows first
              const loreDelay = ceremony ? 6000 : 2500
              setTimeout(() => {
                setLoreFragment({
                  title: frag.fragment_title || 'Unknown Fragment',
                  content: frag.fragment || '',
                  rarity: frag.rarity || 'common',
                })
              }, loreDelay)
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
  }, [input, currentSession, selectedPersona, initializingSession, sendMessage, user, handleSlashCommand])

  const handleRetryMessage = useCallback(async (messageId: string) => {
    try {
      await retryMessage(messageId)
    } catch (error) {
      console.error('Failed to retry message:', error)
      alert('Failed to retry message. Please try again.')
    }
  }, [retryMessage])

  const handleSessionSelect = useCallback(async (session: { id: string; persona_key: string }) => {
    const sessionPersona = personas.find(p => p.key === session.persona_key)
    if (sessionPersona) {
      setSelectedPersona(sessionPersona)
    }
    await loadSessionMessages(session.id)
    setIsSidebarOpen(false)
  }, [personas, setSelectedPersona, loadSessionMessages])

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

  // Touch handlers for swipe gestures
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.targetTouches[0].clientX
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    touchEndX.current = e.targetTouches[0].clientX
  }

  const handleTouchEnd = () => {
    if (!touchStartX.current || !touchEndX.current) return

    const distance = touchStartX.current - touchEndX.current
    const isLeftSwipe = distance > 50

    if (isLeftSwipe && isSidebarOpen) {
      setIsSidebarOpen(false)
    }

    touchStartX.current = 0
    touchEndX.current = 0
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
                    onRegenerate={handleRegenerate}
                    onContinue={handleContinue}
                    onUndo={handleUndo}
                    loadingIndicator={
                      !initializingSession ? (
                        isSearching && toolType !== 'none' ? (
                          <ToolIndicator
                            toolType={toolType}
                            personaName={selectedPersona?.display_name}
                            personaKey={selectedPersona?.key}
                          />
                        ) : loading ? (
                          <TypingIndicator personaName={selectedPersona.display_name} />
                        ) : null
                      ) : null
                    }
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

      {/* Phase-2: diegetic capability-unlock beat (self-managed AnimatePresence) */}
      <CapabilityUnlockToast
        unlock={capabilityUnlock}
        onDismiss={() => setCapabilityUnlock(null)}
      />

      {/* Rank Ceremony Overlay — shown when seeker ranks up */}
      <AnimatePresence>
        {rankCeremony && (
          <RankCeremonyOverlay
            ceremony={rankCeremony}
            onDismiss={() => setRankCeremony(null)}
          />
        )}
      </AnimatePresence>

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
