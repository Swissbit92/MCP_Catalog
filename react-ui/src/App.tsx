import React, { useEffect } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { MotionConfig } from 'framer-motion'
import NephilimHome from './pages/NephilimHome'
import NephilimOnboarding from './pages/NephilimOnboarding'
import CharacterCardV2Showcase from './pages/CharacterCardV2Showcase'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import Header from './components/Header'
import { AudioProvider } from './context/AudioContext'
import { usePersona } from './context/PersonaContext'
import { orderToRarityClass, getDisplayOrder } from './utils/celestialOrder'

function App() {
  const { selectedPersona } = usePersona()
  const location = useLocation()

  // Apply rarity-based theme to body element
  // NEPHILIM mode is always active
  useEffect(() => {
    const classes: string[] = []

    // Add rarity class — derived from celestial_order when available
    const order = selectedPersona ? getDisplayOrder(selectedPersona) : 'wanderer'
    const rarityClass = orderToRarityClass(order)
    classes.push(`rarity-${rarityClass}`)

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
      document.body.className = 'rarity-common nephilim-mode'
    }
  }, [selectedPersona])

  // Hide header on landing and onboarding pages
  const hideHeader = location.pathname === '/' || location.pathname === '/onboarding'

  return (
    <MotionConfig reducedMotion="user">
      <AudioProvider>
        <div className="App h-screen flex flex-col">
          {!hideHeader && <Header />}
          <div className="flex-1 overflow-auto pb-16 md:pb-0">
            <Routes>
              <Route path="/" element={<NephilimHome />} />
              <Route path="/select" element={<CharacterCardV2Showcase />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/chat/:sessionId" element={<Chat />} />
              <Route path="/onboarding" element={<NephilimOnboarding />} />
              <Route path="/dashboard" element={<Dashboard />} />
            </Routes>
          </div>
        </div>
      </AudioProvider>
    </MotionConfig>
  )
}

export default App
