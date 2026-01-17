import React from 'react';
import { Menu, X } from 'lucide-react';

interface ChatHeaderProps {
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  sessionTitle: string | undefined;
  personaName: string;
  onExport?: () => Promise<void>;
  onImport?: (event: React.ChangeEvent<HTMLInputElement>) => Promise<void>;
  onClear?: () => Promise<void>;
  hasCurrentSession: boolean;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  isSidebarOpen,
  onToggleSidebar,
  sessionTitle,
  personaName,
  onExport,
  onImport,
  onClear,
  hasCurrentSession
}) => {
  return (
    <div className="bg-white border-b border-gray-200 px-4 md:px-6 py-4 shadow-sm flex-shrink-0">
      <div className="flex justify-between items-center gap-3">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          {/* Sidebar Toggle Button */}
          <button
            onClick={onToggleSidebar}
            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
            aria-label="Toggle sidebar"
          >
            {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <h1 className="text-xl md:text-2xl font-semibold text-gray-900 truncate min-w-0">
            {sessionTitle || `Chat with ${personaName}`}
          </h1>
        </div>
        {hasCurrentSession && (
          <div className="flex gap-1 md:gap-2 flex-shrink-0">
            <label className="px-3 md:px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer text-sm md:text-base" title="Import Chat">
              <span className="hidden sm:inline">Import</span>
              <span className="sm:hidden">📥</span>
              <input
                type="file"
                accept=".json"
                onChange={onImport}
                className="hidden"
              />
            </label>
            <button
              onClick={onExport}
              className="px-3 md:px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm md:text-base"
              title="Export Chat"
            >
              <span className="hidden sm:inline">Export</span>
              <span className="sm:hidden">📤</span>
            </button>
            <button
              onClick={onClear}
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
  );
};
