import React, { useRef, useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAudio } from '../context/AudioContext'
import { SeekerRankBadge } from './nephilim/SeekerRankBadge'
import { getRankProgress } from '../services/api'
import { useAuth } from '../context/AuthContext'

const Header: React.FC = () => {
  const location = useLocation()
  const { isMuted, toggleMute } = useAudio()
  const [seekerRank, setSeekerRank] = useState('Initiate')
  const { user, isAuthenticated, logout } = useAuth()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Get seeker info from auth context
  const seekerName = user?.name || 'Seeker'

  // Fetch current rank from API on mount
  useEffect(() => {
    const userId = user?.sub || 'default_seeker'
    const fetchRank = async () => {
      try {
        const data = await getRankProgress(userId)
        setSeekerRank(data.current_rank || 'Initiate')
      } catch {
        // Silently fall back to Initiate
      }
    }
    fetchRank()
  }, [user?.sub])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [dropdownOpen])

  const handleLogout = async () => {
    setDropdownOpen(false)
    await logout()
  }

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

  // Derive initials for avatar fallback
  const getInitials = (name: string) => {
    const parts = name.trim().split(' ')
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    return name.slice(0, 2).toUpperCase()
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

          {/* Right: Rank, Audio, User */}
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

            {/* User avatar + dropdown */}
            {isAuthenticated && user ? (
              <div ref={dropdownRef} style={{ position: 'relative' }}>
                <button
                  onClick={() => setDropdownOpen(o => !o)}
                  aria-label="User menu"
                  style={{
                    display: 'flex', alignItems: 'center', gap: '8px',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '40px', padding: '4px 10px 4px 4px',
                    cursor: 'pointer', transition: 'all 0.2s',
                  }}
                >
                  {/* Avatar */}
                  {user.avatar ? (
                    <img
                      src={user.avatar}
                      alt={user.name}
                      style={{ width: '28px', height: '28px', borderRadius: '50%', objectFit: 'cover', border: '1.5px solid rgba(0,191,255,0.4)' }}
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    <div style={{
                      width: '28px', height: '28px', borderRadius: '50%',
                      background: 'radial-gradient(circle at 40% 35%, rgba(0,255,255,0.45), rgba(0,191,255,0.08))',
                      border: '1.5px solid rgba(0,255,255,0.4)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontFamily: "'Orbitron', sans-serif", fontSize: '9px', fontWeight: 700, color: '#00ffff',
                    }}>
                      {getInitials(user.name)}
                    </div>
                  )}
                  <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.8)', fontWeight: 500, maxWidth: '100px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {user.name.split(' ')[0]}
                  </span>
                  {/* Caret */}
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none" style={{ transform: dropdownOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s', opacity: 0.5 }}>
                    <path d="M2 3.5L5 6.5L8 3.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>

                {/* Dropdown menu */}
                <AnimatePresence>
                  {dropdownOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -6, scale: 0.96 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -6, scale: 0.96 }}
                      transition={{ duration: 0.15 }}
                      style={{
                        position: 'absolute', top: 'calc(100% + 8px)', right: 0,
                        minWidth: '200px',
                        background: 'rgba(17,17,21,0.97)',
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: '12px',
                        boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
                        backdropFilter: 'blur(20px)',
                        overflow: 'hidden',
                        zIndex: 100,
                      }}
                    >
                      {/* Menu items */}
                      <div style={{ padding: '6px' }}>
                        <Link
                          to="/dashboard"
                          onClick={() => setDropdownOpen(false)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: '9px',
                            padding: '11px 15px', borderRadius: '8px',
                            fontSize: '13px', fontWeight: 500, color: 'rgba(255,255,255,0.55)',
                            textDecoration: 'none', transition: 'all 0.15s',
                          }}
                          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'rgba(255,255,255,0.92)' }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(255,255,255,0.55)' }}
                        >
                          👤 My Seeker Profile
                        </Link>
                        <Link
                          to="/dashboard"
                          onClick={() => setDropdownOpen(false)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: '9px',
                            padding: '11px 15px', borderRadius: '8px',
                            fontSize: '13px', fontWeight: 500, color: 'rgba(255,255,255,0.55)',
                            textDecoration: 'none', transition: 'all 0.15s',
                          }}
                          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'rgba(255,255,255,0.92)' }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(255,255,255,0.55)' }}
                        >
                          ✦ Progression
                        </Link>
                        <button
                          onClick={() => setDropdownOpen(false)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: '9px', width: '100%',
                            padding: '11px 15px', borderRadius: '8px',
                            fontSize: '13px', fontWeight: 500, color: 'rgba(255,255,255,0.55)',
                            background: 'transparent', border: 'none', cursor: 'pointer',
                            textAlign: 'left', transition: 'all 0.15s',
                          }}
                          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'rgba(255,255,255,0.92)' }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(255,255,255,0.55)' }}
                        >
                          ⚙ Settings
                        </button>
                        {/* Separator */}
                        <div style={{ height: '1px', background: 'rgba(255,255,255,0.08)', margin: '4px 0' }} />
                        <button
                          onClick={handleLogout}
                          style={{
                            display: 'flex', alignItems: 'center', gap: '9px', width: '100%',
                            padding: '11px 15px', borderRadius: '8px',
                            fontSize: '13px', fontWeight: 500, color: 'rgba(255,80,80,0.8)',
                            background: 'transparent', border: 'none', cursor: 'pointer',
                            textAlign: 'left', transition: 'all 0.15s',
                          }}
                          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,0,0,0.06)'; e.currentTarget.style.color = 'rgba(255,110,110,1)' }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(255,80,80,0.8)' }}
                        >
                          ⏏ Sign Out
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <span className="text-sm text-gray-300 font-medium">{seekerName}</span>
            )}
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
