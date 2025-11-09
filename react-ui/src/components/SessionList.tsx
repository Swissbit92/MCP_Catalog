import React, { useState } from 'react';
import { ChatSession } from '../services/api';
import { usePersona } from '../context/PersonaContext';

interface SessionListProps {
  onSessionSelect: (session: ChatSession) => void;
}

const SessionList: React.FC<SessionListProps> = ({ onSessionSelect }) => {
  const { sessions, currentSession, deleteSessionById, updateSessionTitle } = usePersona();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

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
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Chat History</h2>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            No chat sessions yet. Start a conversation!
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`p-4 border-b border-gray-100 hover:bg-gray-50 cursor-pointer ${
                currentSession?.id === session.id ? 'bg-blue-50 border-blue-200' : ''
              }`}
              onClick={() => onSessionSelect(session)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1 min-w-0">
                  {editingId === session.id ? (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') handleEditSave();
                          if (e.key === 'Escape') handleEditCancel();
                        }}
                        className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                        autoFocus
                      />
                      <button
                        onClick={(e) => { e.stopPropagation(); handleEditSave(); }}
                        className="px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600"
                      >
                        Save
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleEditCancel(); }}
                        className="px-2 py-1 text-xs bg-gray-500 text-white rounded hover:bg-gray-600"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <>
                      <h3 className="text-sm font-medium text-gray-900 truncate">
                        {session.title}
                      </h3>
                      <p className="text-xs text-gray-500 mt-1">
                        {session.message_count} messages • {new Date(session.updated_at).toLocaleDateString()}
                      </p>
                    </>
                  )}
                </div>
                {editingId !== session.id && (
                  <div className="flex gap-1 ml-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleEditStart(session); }}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Rename"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(session.id); }}
                      className="p-1 text-gray-400 hover:text-red-600"
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default SessionList;