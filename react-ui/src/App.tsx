import React, { useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { MotionConfig } from 'framer-motion'
import NephilimHome from './pages/NephilimHome'
import NephilimOnboarding from './pages/NephilimOnboarding'
import CharacterCardV2Showcase from './pages/CharacterCardV2Showcase'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import LoginPage from './pages/LoginPage'
import Header from './components/Header'
import ProtectedRoute from './components/ProtectedRoute'
import { AudioProvider } from './context/AudioContext'
import { usePersona } from './context/PersonaContext'
import { useAuth } from './context/AuthContext'
import { getDisplayOrder } from './utils/celestialOrder'

/** Redirects to /select if user already completed onboarding. */
function OnboardingGuard({ children }: { children: React.ReactNode }) {
  const { onboardingCompleted, isLoading } = useAuth()

  if (isLoading) return null
  if (onboardingCompleted) return <Navigate to="/select" replace />

  return <>{children}</>
}

function App() {
  const { selectedPersona } = usePersona()
  const location = useLocation()

  // Apply rarity-based theme to body element
  // NEPHILIM mode is always active
  useEffect(() => {
    const classes: string[] = []

    // Add order class — derived from celestial_order when available
    const order = selectedPersona ? getDisplayOrder(selectedPersona) : 'wanderer'
    classes.push(`order-${order}`)

    // Always apply NEPHILIM mode
    classes.push('nephilim-mode')

    // Add persona-specific class for NEPHILIM personas
    if (selectedPersona?.key?.startsWith('nephilim_')) {
      const personaName = selectedPersona.key.replace('nephilim_', '')
      classes.push(`nephilim-${personaName}`)
    }

    document.body.className = classes.join(' ')

    return () => {
      // Cleanup: reset to default
      document.body.className = 'order-wanderer nephilim-mode'
    }
  }, [selectedPersona])

  // Hide header on landing, onboarding, and login pages
  const hideHeader = location.pathname === '/' || location.pathname === '/onboarding' || location.pathname === '/login'

  return (
    <MotionConfig reducedMotion="user">
      <AudioProvider>
        <div className="App h-screen flex flex-col">
          {!hideHeader && <Header />}
          <div className="flex-1 overflow-auto pb-16 md:pb-0">
            <Routes>
              <Route path="/" element={
                <ProtectedRoute>
                  <NephilimHome />
                </ProtectedRoute>
              } />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/onboarding" element={
                <ProtectedRoute>
                  <OnboardingGuard>
                    <NephilimOnboarding />
                  </OnboardingGuard>
                </ProtectedRoute>
              } />
              <Route path="/select" element={
                <ProtectedRoute>
                  <CharacterCardV2Showcase />
                </ProtectedRoute>
              } />
              <Route path="/chat" element={
                <ProtectedRoute>
                  <Chat />
                </ProtectedRoute>
              } />
              <Route path="/chat/:sessionId" element={
                <ProtectedRoute>
                  <Chat />
                </ProtectedRoute>
              } />
              <Route path="/dashboard" element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              } />
            </Routes>
          </div>
        </div>
      </AudioProvider>
    </MotionConfig>
  )
}

export default App
