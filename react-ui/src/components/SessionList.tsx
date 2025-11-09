import React, { useState, useEffect } from 'react';
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

const SessionList: React.FC<SessionListProps> = ({ onSessionSelect }) => {
  const { sessions, currentSession, deleteSessionById, updateSessionTitle } = usePersona();
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
          image: p.image.replace('ui/images/', ''),
          avatar: p.avatar ? p.avatar.replace('ui/images/', '') : undefined,
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

  return (
    <div className="w-80 bg-white border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gray-50/50">
        <h2 className="text-lg font-semibold text-gray-900">Chat History</h2>
        <p className="text-xs text-gray-600 mt-1">Your conversations</p>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            <div className="text-4xl mb-2">💬</div>
            <p className="font-medium">No conversations yet</p>
            <p className="text-sm mt-1">Start chatting with a character!</p>
          </div>
        ) : (
          sessions.map((session) => {
            const persona = getPersonaForSession(session.persona_key);
            const rarityStyles = getRarityStyles(persona?.rarity);
            const isActive = currentSession?.id === session.id;

            return (
              <div
                key={session.id}
                className={`p-4 border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-all duration-200 ${
                  isActive ? `${rarityStyles.bg} ${rarityStyles.border} border-2` : ''
                }`}
                onClick={() => onSessionSelect(session)}
              >
                <div className="flex justify-between items-start gap-3">
                  {/* Persona Avatar */}
                  <div className="flex-shrink-0">
                    {persona?.avatar ? (
                      <img
                        src={`/images/${persona.avatar}`}
                        alt={persona.display_name}
                        className="w-10 h-10 rounded-lg object-cover border-2 border-gray-200"
                      />
                    ) : (
                      <div className={`w-10 h-10 rounded-lg ${rarityStyles.bg} ${rarityStyles.border} border-2 flex items-center justify-center`}>
                        <span className="text-lg">🎭</span>
                      </div>
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
                            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Enter session title..."
                            autoFocus
                          />
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={(e) => { e.stopPropagation(); handleEditSave(); }}
                            className="px-3 py-1 text-xs bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors"
                          >
                            Save
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleEditCancel(); }}
                            className="px-3 py-1 text-xs bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-medium text-gray-900 truncate flex-1">
                            {session.title}
                          </h3>
                          {persona && (
                            <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${rarityStyles.bg} ${rarityStyles.text} border ${rarityStyles.border}`}>
                              {persona.rarity}
                            </span>
                          )}
                        </div>

                        {persona && (
                          <p className="text-xs text-gray-600 mb-1 truncate">
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
                        onClick={(e) => { e.stopPropagation(); handleEditStart(session); }}
                        className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                        title="Rename conversation"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(session.id); }}
                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                        title="Delete conversation"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default SessionList;