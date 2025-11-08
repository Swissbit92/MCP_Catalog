import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Header: React.FC = () => {
  const location = useLocation();

  // Rarity-based colors for active page highlighting
  const getActiveColor = (path: string) => {
    if (location.pathname === path) {
      switch (path) {
        case '/': return 'text-yellow-300 drop-shadow-[0_0_8px_rgba(255,215,0,0.8)]'; // Legendary gold
        case '/select': return 'text-purple-300 drop-shadow-[0_0_8px_rgba(186,120,255,0.8)]'; // Epic purple
        case '/chat': return 'text-cyan-300 drop-shadow-[0_0_8px_rgba(66,245,255,0.8)]'; // Rare cyan
        default: return 'text-gray-300';
      }
    }
    return 'text-gray-300 hover:text-white transition-colors duration-200';
  };

  return (
    <header className="relative bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-b border-slate-700/50 backdrop-blur-sm">
      {/* Subtle background pattern */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(255,255,255,0.02),transparent_50%)] opacity-30"></div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo/Branding Section */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center shadow-lg">
                <span className="text-slate-900 font-bold text-sm">🎭</span>
              </div>
              <div className="hidden sm:block">
                <h1 className="text-lg font-bold bg-gradient-to-r from-yellow-300 to-orange-300 bg-clip-text text-transparent">
                  Persona Chat
                </h1>
                <p className="text-xs text-slate-400 leading-tight">Gacha Style</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex items-center space-x-1">
            <Link
              to="/"
              className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 ${getActiveColor('/')}`}
            >
              Home
            </Link>
            <Link
              to="/select"
              className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 ${getActiveColor('/select')}`}
            >
              Characters
            </Link>
            <Link
              to="/chat"
              className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 ${getActiveColor('/chat')}`}
            >
              Chat
            </Link>
          </nav>

          {/* Mobile Menu Button (placeholder for Phase 3) */}
          <div className="md:hidden">
            <button className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-slate-700/50 transition-colors duration-200">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
