import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ChatSession } from '../services/api'
import { usePersona } from '../context/PersonaContext'
import { formatOrderLabel } from '../utils/celestialOrder'

interface SessionListProps {
  onSessionSelect: (session: ChatSession) => void
}

// Rarity-based color schemes matching the app's design system
const getRarityStyles = (rarity?: string) => {
  switch (rarity) {
    case 'legendary':
      return {
        border: 'border-yellow-400/50',
        bg: 'bg-yellow-500/10',
        text: 'text-yellow-600',
        hover: 'hover:bg-yellow-500/20',
        accent: 'bg-yellow-500',
      }
    case 'epic':
      return {
        border: 'border-purple-400/50',
        bg: 'bg-purple-500/10',
        text: 'text-purple-600',
        hover: 'hover:bg-purple-500/20',
        accent: 'bg-purple-500',
      }
    case 'rare':
      return {
        border: 'border-cyan-400/50',
        bg: 'bg-cyan-500/10',
        text: 'text-cyan-600',
        hover: 'hover:bg-cyan-500/20',
        accent: 'bg-cyan-500',
      }
    case 'common':
    default:
      return {
        border: 'border-gray-400/50',
        bg: 'bg-gray-500/10',
        text: 'text-gray-600',
        hover: 'hover:bg-gray-500/20',
        accent: 'bg-gray-500',
      }
  }
}

const SessionList: React.FC<SessionListProps> = ({ onSessionSelect }) => {
  const navigate = useNavigate()
  const { personas, sessions, currentSession, deleteSessionById, updateSessionTitle } = usePersona()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const personasLoaded = personas.length > 0

  // Get persona info for a session
  const getPersonaForSession = (personaKey: string) => {
    return personas.find(p => p.key === personaKey)
  }

  const handleEditStart = (session: ChatSession) => {
    setEditingId(session.id)
    setEditTitle(session.title)
  }

  const handleEditSave = async () => {
    if (editingId && editTitle.trim()) {
      await updateSessionTitle(editingId, editTitle.trim())
    }
    setEditingId(null)
    setEditTitle('')
  }

  const handleEditCancel = () => {
    setEditingId(null)
    setEditTitle('')
  }

  const handleDelete = async (sessionId: string) => {
    if (window.confirm('Are you sure you want to delete this chat session?')) {
      await deleteSessionById(sessionId)
    }
  }

  const visibleSessions = personasLoaded
    ? sessions.filter(s => personas.some(p => p.key === s.persona_key))
    : sessions

  return (
    <div className="w-80 bg-[#0B0B0D]/95 backdrop-blur-xl border-r border-white/[0.1] flex flex-col h-full relative overflow-hidden">
      {/* Header */}
      <div className="relative p-4 border-b border-white/[0.1]">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold font-nephilim text-nephilim-cyan drop-shadow-lg">Memory Archives</h2>
          <button
            onClick={() => navigate('/select')}
            className="p-1.5 bg-white/[0.05] hover:bg-white/[0.12] border border-white/[0.1] hover:border-cyan-500/30 rounded-lg text-gray-400 hover:text-cyan-300 transition-all backdrop-blur-sm"
            aria-label="New conversation"
            title="New conversation"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-1">Your conversations</p>
      </div>

      {/* Sessions List */}
      <div className="relative flex-1 overflow-y-auto p-2">
        {visibleSessions.length === 0 ? (
          <div className="relative p-6 text-center text-gray-400">
            <div className="text-4xl mb-2">&#x25C7;</div>
            <p className="font-medium">No conversations yet</p>
            <p className="text-sm mt-1">Start chatting with a character!</p>
          </div>
        ) : (
          visibleSessions.map((session) => {
            const persona = getPersonaForSession(session.persona_key)
            const rarityStyles = getRarityStyles(persona?.rarity)
            const isActive = currentSession?.id === session.id

            return (
              <motion.div
                key={session.id}
                className={`relative mx-2 my-1 p-3 rounded-lg border border-white/[0.08] hover:bg-white/[0.05] cursor-pointer transition-all duration-100 backdrop-blur-sm overflow-hidden ${
                  isActive ? `${rarityStyles.bg} ${rarityStyles.border} border-2 shadow-lg` : 'bg-white/[0.03]'
                }`}
                onClick={() => onSessionSelect(session)}
                whileHover={{ scale: 1.02, transition: { duration: 0.1 } }}
                whileTap={{ scale: 0.98 }}
              >
                {/* Rarity-based background glow for active sessions */}
                {isActive && (
                  <motion.div
                    className={`absolute inset-0 ${rarityStyles.bg} opacity-20`}
                    animate={{
                      boxShadow: [
                        `inset 0 0 20px ${rarityStyles.accent}20`,
                        `inset 0 0 30px ${rarityStyles.accent}30`,
                        `inset 0 0 20px ${rarityStyles.accent}20`,
                      ]
                    }}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                  />
                )}
                <div className="flex justify-between items-start gap-3">
                  {/* Persona Avatar */}
                  <div className="flex-shrink-0 relative">
                    {persona?.avatar ? (
                      <motion.div
                        className="relative"
                        animate={isActive ? {
                          boxShadow: [
                            `0 0 10px ${rarityStyles.accent}40`,
                            `0 0 20px ${rarityStyles.accent}60`,
                            `0 0 10px ${rarityStyles.accent}40`,
                          ]
                        } : {}}
                        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                      >
                        <img
                          src={`/images/${persona.avatar}`}
                          alt={persona.display_name}
                          className="w-10 h-10 rounded-lg object-cover relative z-10"
                        />
                        {/* Rarity glow ring */}
                        <div className={`absolute inset-0 rounded-lg ${rarityStyles.border} border-2 opacity-60 scale-110`} />
                      </motion.div>
                    ) : (
                      <motion.div
                        className={`w-10 h-10 rounded-lg ${rarityStyles.bg} ${rarityStyles.border} border-2 flex items-center justify-center relative`}
                        animate={isActive ? {
                          boxShadow: [
                            `0 0 10px ${rarityStyles.accent}40`,
                            `0 0 20px ${rarityStyles.accent}60`,
                            `0 0 10px ${rarityStyles.accent}40`,
                          ]
                        } : {}}
                        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                      >
                        <span className="text-lg relative z-10">&#x1F3AD;</span>
                        {/* Rarity glow ring */}
                        <div className={`absolute inset-0 rounded-lg ${rarityStyles.border} border-2 opacity-60 scale-110`} />
                      </motion.div>
                    )}
                  </div>

                  {/* Session Content */}
                  <div className="flex-1 min-w-0">
                    {editingId === session.id ? (
                      <div className="space-y-2">
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleEditSave()
                              if (e.key === 'Escape') handleEditCancel()
                            }}
                             className="flex-1 px-3 py-2 text-sm bg-white/[0.05] border border-white/[0.1] rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-transparent text-gray-200 placeholder-gray-500"
                            placeholder="Enter session title..."
                            autoFocus
                          />
                        </div>
                        <div className="flex gap-2">
                           <button
                             onClick={(e) => { e.stopPropagation(); handleEditSave() }}
                             className="px-3 py-1 text-xs bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                           >
                             Save
                           </button>
                           <button
                             onClick={(e) => { e.stopPropagation(); handleEditCancel() }}
                             className="px-3 py-1 text-xs bg-white/10 text-gray-300 rounded-md hover:bg-white/20 transition-colors"
                           >
                             Cancel
                           </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-medium text-gray-200 truncate flex-1">
                            {session.title}
                          </h3>
                           {persona && (
                             <motion.span
                               className={`text-xs px-2 py-0.5 rounded-full ${rarityStyles.bg} ${rarityStyles.text} border ${rarityStyles.border} font-medium`}
                               animate={isActive ? {
                                 boxShadow: [
                                   `0 0 6px ${rarityStyles.accent}40`,
                                   `0 0 12px ${rarityStyles.accent}60`,
                                   `0 0 6px ${rarityStyles.accent}40`,
                                 ]
                               } : {}}
                               transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                             >
                               {formatOrderLabel(persona.celestial_order || 'wanderer')}
                             </motion.span>
                           )}
                        </div>

                        {persona && (
                          <p className="text-xs text-gray-400 mb-1 truncate">
                            with {persona.display_name}
                          </p>
                        )}

                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <span>{session.message_count} messages</span>
                          <span>{new Date(session.updated_at).toLocaleDateString()}</span>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Action Buttons */}
                  {editingId !== session.id && (
                    <div className="flex gap-1 flex-shrink-0">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleEditStart(session) }}
                        className="p-2 text-gray-500 hover:text-gray-200 hover:bg-white/10 rounded-md transition-colors"
                        title="Rename conversation"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(session.id) }}
                        className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-900/20 rounded-md transition-colors"
                        title="Delete conversation"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>
              </motion.div>
            )
          })
        )}
      </div>
    </div>
  )
}

export default SessionList
