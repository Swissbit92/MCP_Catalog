import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ChatSession } from '../services/api';
import { usePersona } from '../context/PersonaContext';
import { fetchPersonas } from '../services/api';

interface SessionListProps {
  onSessionSelect: (session: ChatSession) => void;
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
      };
    case 'epic':
      return {
        border: 'border-purple-400/50',
        bg: 'bg-purple-500/10',
        text: 'text-purple-600',
        hover: 'hover:bg-purple-500/20',
        accent: 'bg-purple-500',
      };
    case 'rare':
      return {
        border: 'border-cyan-400/50',
        bg: 'bg-cyan-500/10',
        text: 'text-cyan-600',
        hover: 'hover:bg-cyan-500/20',
        accent: 'bg-cyan-500',
      };
    case 'common':
    default:
      return {
        border: 'border-gray-400/50',
        bg: 'bg-gray-500/10',
        text: 'text-gray-600',
        hover: 'hover:bg-gray-500/20',
        accent: 'bg-gray-500',
      };
  }
};

// Dynamic background animation function (matching header)
const getBackgroundAnimation = (rarity?: string) => {
  const themeColors = {
    legendary: {
      primary: 'rgba(255, 215, 0, 0.08)',
      secondary: 'rgba(255, 240, 166, 0.05)',
      accent: 'rgba(255, 208, 80, 0.06)'
    },
    epic: {
      primary: 'rgba(186, 120, 255, 0.08)',
      secondary: 'rgba(246, 212, 255, 0.05)',
      accent: 'rgba(186, 120, 255, 0.06)'
    },
    rare: {
      primary: 'rgba(66, 245, 255, 0.08)',
      secondary: 'rgba(212, 246, 255, 0.05)',
      accent: 'rgba(66, 245, 255, 0.06)'
    },
    common: {
      primary: 'rgba(156, 163, 175, 0.08)',
      secondary: 'rgba(209, 213, 219, 0.05)',
      accent: 'rgba(156, 163, 175, 0.06)'
    }
  };

  const colors = themeColors[rarity as keyof typeof themeColors] || themeColors.common;

  return {
    background: [
      `radial-gradient(circle at 20% 50%, ${colors.primary}, transparent 50%)`,
      `radial-gradient(circle at 80% 20%, ${colors.secondary}, transparent 50%)`,
      `radial-gradient(circle at 40% 80%, ${colors.accent}, transparent 50%)`,
      `radial-gradient(circle at 60% 30%, ${colors.primary}, transparent 50%)`,
      `radial-gradient(circle at 20% 50%, ${colors.primary}, transparent 50%)`,
    ]
  };
};

const SessionList: React.FC<SessionListProps> = ({ onSessionSelect }) => {
  const { sessions, currentSession, deleteSessionById, updateSessionTitle, selectedPersona } = usePersona();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [personas, setPersonas] = useState<any[]>([]);

  // Load personas for session display
  useEffect(() => {
    const loadPersonas = async () => {
      try {
        const fetchedPersonas = await fetchPersonas();
        const processedPersonas = fetchedPersonas.map(p => ({
          key: p.key,
          display_name: p.display_name || p.key,
          image: p.image.replace('images/', ''),
          avatar: p.avatar ? p.avatar.replace('images/', '') : undefined,
          rarity: p.rarity,
        }));
        setPersonas(processedPersonas);
      } catch (error) {
        console.error('Failed to load personas for session list:', error);
      }
    };
    loadPersonas();
  }, []);

  // Get persona info for a session
  const getPersonaForSession = (personaKey: string) => {
    return personas.find(p => p.key === personaKey);
  };

  const handleEditStart = (session: ChatSession) => {
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const handleEditSave = async () => {
    if (editingId && editTitle.trim()) {
      await updateSessionTitle(editingId, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle('');
  };

  const handleEditCancel = () => {
    setEditingId(null);
    setEditTitle('');
  };

  const handleDelete = async (sessionId: string) => {
    if (window.confirm('Are you sure you want to delete this chat session?')) {
      await deleteSessionById(sessionId);
    }
  };

  // Get current theme based on selected persona
  const currentTheme = selectedPersona?.rarity || 'common';

  return (
    <div className="w-80 bg-gradient-to-b from-slate-900/95 via-slate-800/95 to-slate-900/95 backdrop-blur-xl border-r border-slate-700/50 flex flex-col h-full relative overflow-hidden">
      {/* Enhanced glassmorphism background with multiple layers */}
      <div className="absolute inset-0 bg-gradient-to-r from-slate-900/95 via-slate-800/95 to-slate-900/95 backdrop-blur-xl"></div>
      <div className="absolute inset-0 bg-gradient-to-r from-slate-900/80 via-slate-800/80 to-slate-900/80 backdrop-blur-lg"></div>
      <div className="absolute inset-0 bg-gradient-to-r from-slate-900/60 via-slate-800/60 to-slate-900/60 backdrop-blur-md"></div>

      {/* Dynamic theme-based background animation - HIGHLY VISIBLE */}
      <motion.div
        className="absolute inset-0 opacity-60"
        animate={getBackgroundAnimation()}
        transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
        key={currentTheme} // Force re-animation when theme changes
      ></motion.div>

      {/* HIGHLY VISIBLE animated border */}
      <motion.div
        className="absolute bottom-0 left-0 right-0 h-1"
        animate={{
          background: [
            "linear-gradient(to right, transparent, rgba(255, 215, 0, 0.8), transparent)",
            "linear-gradient(to right, transparent, rgba(186, 120, 255, 0.8), transparent)",
            "linear-gradient(to right, transparent, rgba(66, 245, 255, 0.8), transparent)",
            "linear-gradient(to right, transparent, rgba(255, 215, 0, 0.8), transparent)",
          ],
          boxShadow: [
            "0 0 10px rgba(255, 215, 0, 0.5)",
            "0 0 10px rgba(186, 120, 255, 0.5)",
            "0 0 10px rgba(66, 245, 255, 0.5)",
            "0 0 10px rgba(255, 215, 0, 0.5)",
          ]
        }}
        transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
      ></motion.div>

      {/* Header */}
      <div className="relative p-4 border-b border-slate-700/50">
        <h2 className="text-lg font-semibold text-white drop-shadow-lg">Chat History</h2>
        <p className="text-xs text-gray-300 mt-1 drop-shadow-md">Your conversations</p>
      </div>

      {/* Sessions List */}
      <div className="relative flex-1 overflow-y-auto p-2">
        {sessions.length === 0 ? (
          <div className="relative p-6 text-center text-gray-300">
            <div className="text-4xl mb-2 drop-shadow-lg">💬</div>
            <p className="font-medium drop-shadow-md">No conversations yet</p>
            <p className="text-sm mt-1 drop-shadow-sm">Start chatting with a character!</p>
          </div>
        ) : (
          sessions.map((session) => {
            const persona = getPersonaForSession(session.persona_key);
            const rarityStyles = getRarityStyles(persona?.rarity);
            const isActive = currentSession?.id === session.id;

            return (
              <motion.div
                key={session.id}
                className={`relative mx-2 my-1 p-3 rounded-lg border border-slate-700/30 hover:bg-slate-800/30 cursor-pointer transition-all duration-100 backdrop-blur-sm overflow-hidden ${
                  isActive ? `${rarityStyles.bg} ${rarityStyles.border} border-2 shadow-lg` : 'bg-slate-800/20'
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
                        <span className="text-lg relative z-10">🎭</span>
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
                            onKeyPress={(e) => {
                              if (e.key === 'Enter') handleEditSave();
                              if (e.key === 'Escape') handleEditCancel();
                            }}
                             className="flex-1 px-3 py-2 text-sm bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-400"
                            placeholder="Enter session title..."
                            autoFocus
                          />
                        </div>
                        <div className="flex gap-2">
                           <button
                             onClick={(e) => { e.stopPropagation(); handleEditSave(); }}
                             className="px-3 py-1 text-xs bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                           >
                             Save
                           </button>
                           <button
                             onClick={(e) => { e.stopPropagation(); handleEditCancel(); }}
                             className="px-3 py-1 text-xs bg-slate-600 text-white rounded-md hover:bg-slate-700 transition-colors"
                           >
                             Cancel
                           </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-medium text-white truncate flex-1 drop-shadow-md">
                            {session.title}
                          </h3>
                           {persona && (
                             <motion.span
                               className={`text-xs px-2 py-0.5 rounded-full capitalize ${rarityStyles.bg} ${rarityStyles.text} border ${rarityStyles.border} font-medium`}
                               animate={isActive ? {
                                 boxShadow: [
                                   `0 0 6px ${rarityStyles.accent}40`,
                                   `0 0 12px ${rarityStyles.accent}60`,
                                   `0 0 6px ${rarityStyles.accent}40`,
                                 ]
                               } : {}}
                               transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                             >
                               {persona.rarity}
                             </motion.span>
                           )}
                        </div>

                        {persona && (
                          <p className="text-xs text-gray-300 mb-1 truncate drop-shadow-sm">
                            with {persona.display_name}
                          </p>
                        )}

                        <div className="flex items-center justify-between text-xs text-gray-400">
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
                        onClick={(e) => { e.stopPropagation(); handleEditStart(session); }}
                        className="p-2 text-gray-400 hover:text-white hover:bg-slate-700/50 rounded-md transition-colors"
                        title="Rename conversation"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(session.id); }}
                        className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-900/20 rounded-md transition-colors"
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
            );
          })
        )}
      </div>
    </div>
  );
};

export default SessionList;