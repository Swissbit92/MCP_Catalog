import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAudio } from '../context/AudioContext'
import { SeekerRankBadge } from './nephilim/SeekerRankBadge'
import { getRankProgress } from '../services/api'

const Header: React.FC = () => {
  const location = useLocation()
  const { isMuted, toggleMute } = useAudio()
  const [seekerRank, setSeekerRank] = useState('Initiate')

  // Get seeker info from localStorage
  const seekerName = typeof window !== 'undefined'
    ? localStorage.getItem('nephilim_user_name') || 'Seeker'
    : 'Seeker'

  // Fetch current rank from API on mount
  useEffect(() => {
    const userId = localStorage.getItem('nephilim_user_id') || 'default_seeker'
    const fetchRank = async () => {
      try {
        const data = await getRankProgress(userId)
        setSeekerRank(data.current_rank || 'Initiate')
      } catch {
        // Silently fall back to Initiate
      }
    }
    fetchRank()
  }, [])

  const desktopNavItems = [
    { to: '/select', label: 'Companions' },
    { to: '/chat', label: 'Chat' },
    { to: '/dashboard', label: 'Dashboard' },
  ]

  const mobileNavItems = [
    { to: '/chat', label: 'Chat', icon: '\u{1F4AC}' },
    { to: '/', label: 'Realm', icon: '\u2B21' },
    { to: '/select', label: 'Companions', icon: '\u2726' },
    { to: '/dashboard', label: 'Profile', icon: '\u25C7' },
  ]

  // Match both exact paths and prefix paths (e.g., /chat and /chat/session-id)
  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }

  return (
    <>
      {/* Desktop Top Bar */}
      <header className="hidden md:block bg-[#0B0B0D]/95 backdrop-blur-xl border-b border-cyan-500/20 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          {/* Left: Wordmark */}
          <Link
            to="/"
            className="font-nephilim text-sm tracking-[0.15em] text-nephilim-cyan hover:text-cyan-300 transition-colors"
          >
            NEPHILIM
          </Link>

          {/* Center: Navigation */}
          <nav className="flex items-center gap-1" aria-label="Main navigation">
            {desktopNavItems.map((item) => (
              <Link
                key={item.label}
                to={item.to}
                className={`relative px-4 py-2 text-sm font-medium transition-colors duration-200 ${
                  isActive(item.to)
                    ? 'text-cyan-300'
                    : 'text-gray-300 hover:text-gray-200'
                }`}
              >
                {item.label}
                {isActive(item.to) && (
                  <motion.div
                    layoutId="desktopActiveIndicator"
                    className="absolute bottom-0 left-2 right-2 h-0.5 bg-cyan-400 rounded-full"
                    style={{ boxShadow: '0 0 8px rgba(0, 255, 255, 0.5)' }}
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                  />
                )}
              </Link>
            ))}
          </nav>

          {/* Right: Rank, Audio, Name */}
          <div className="flex items-center gap-3">
            <SeekerRankBadge rank={seekerRank} size="sm" animated={false} />
            <button
              onClick={toggleMute}
              className={`p-2 rounded-lg transition-colors ${
                isMuted ? 'text-red-400 hover:text-red-300' : 'text-cyan-400 hover:text-cyan-300'
              }`}
              aria-label={isMuted ? 'Unmute audio' : 'Mute audio'}
            >
              {isMuted ? '\u{1F507}' : '\u{1F50A}'}
            </button>
            <span className="text-sm text-gray-300 font-medium">{seekerName}</span>
          </div>
        </div>
      </header>

      {/* Mobile Bottom Tab Bar */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#0B0B0D]/95 backdrop-blur-xl border-t border-cyan-500/20"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
        aria-label="Mobile navigation"
      >
        <div className="flex items-center justify-around h-16">
          {mobileNavItems.map((item) => (
            <Link
              key={item.label}
              to={item.to}
              className={`relative flex flex-col items-center justify-center min-w-[44px] min-h-[44px] px-2 py-1 transition-colors ${
                isActive(item.to) ? 'text-cyan-300' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              <span className="text-xs mt-0.5 font-medium">{item.label}</span>
              {isActive(item.to) && (
                <motion.div
                  layoutId="mobileActiveIndicator"
                  className="absolute bottom-1 w-1.5 h-1.5 rounded-full bg-cyan-400"
                  style={{ boxShadow: '0 0 6px rgba(0, 255, 255, 0.6)' }}
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                />
              )}
            </Link>
          ))}
          {/* Audio toggle as 5th tab */}
          <button
            onClick={toggleMute}
            className={`flex flex-col items-center justify-center min-w-[44px] min-h-[44px] px-2 py-1 transition-colors ${
              isMuted ? 'text-red-400' : 'text-gray-400 hover:text-gray-200'
            }`}
            aria-label={isMuted ? 'Unmute' : 'Mute'}
          >
            <span className="text-lg">{isMuted ? '\u{1F507}' : '\u{1F50A}'}</span>
            <span className="text-xs mt-0.5 font-medium">Audio</span>
          </button>
        </div>
      </nav>
    </>
  )
}

export default Header
