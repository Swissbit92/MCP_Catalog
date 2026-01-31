import React, { useEffect } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Home from './pages/Home';
import NephilimHome from './pages/NephilimHome';
import NephilimOnboarding from './pages/NephilimOnboarding';
import CharacterCardV2Showcase from './pages/CharacterCardV2Showcase';
import Chat from './pages/Chat';
import Header from './components/Header';
import CharacterCollection from './components/CharacterCollection';
import { AudioProvider } from './context/AudioContext';
import { usePersona } from './context/PersonaContext';

function App() {
  const { selectedPersona } = usePersona();
  const location = useLocation();

  // Check if we're in NEPHILIM mode
  const isNephilimRoute = location.pathname.startsWith('/nephilim');
  const isNephilimPersona = selectedPersona?.key?.startsWith('nephilim_');

  // Apply rarity-based theme to body element (Option 6: Glassmorphic + Rarity Hybrid)
  // With NEPHILIM persona-specific theming support
  useEffect(() => {
    const classes: string[] = [];

    // Add rarity class
    const rarity = selectedPersona?.rarity || 'common';
    classes.push(`rarity-${rarity}`);

    // Add NEPHILIM mode and persona-specific classes
    if (isNephilimRoute || isNephilimPersona) {
      classes.push('nephilim-mode');

      // Add persona-specific class for NEPHILIM personas
      if (selectedPersona?.key?.startsWith('nephilim_')) {
        const personaName = selectedPersona.key.replace('nephilim_', '');
        classes.push(`nephilim-${personaName}`);
      }
    }

    document.body.className = classes.join(' ');

    return () => {
      // Cleanup: reset to default
      document.body.className = 'rarity-common';
    };
  }, [selectedPersona, isNephilimRoute, isNephilimPersona]);

  // Hide header on NEPHILIM immersive pages
  const hideHeader = location.pathname === '/nephilim' || location.pathname === '/nephilim/onboarding';

  return (
    <AudioProvider>
      <div className="App h-screen flex flex-col">
        {!hideHeader && <Header />}
        <div className="flex-1 overflow-auto">
          <Routes>
            {/* Legacy routes */}
            <Route path="/" element={<Home />} />
            <Route path="/select" element={<CharacterCardV2Showcase />} />
            <Route path="/cards-v2" element={<CharacterCardV2Showcase />} />
            <Route path="/collection" element={<CharacterCollection onCharacterSelect={(key) => window.location.href = `/chat?persona=${key}`} />} />
            <Route path="/chat" element={<Chat />} />

            {/* Session-based chat route */}
            <Route path="/chat/:sessionId" element={<Chat />} />

            {/* NEPHILIM routes */}
            <Route path="/nephilim" element={<NephilimHome />} />
            <Route path="/nephilim/onboarding" element={<NephilimOnboarding />} />
          </Routes>
        </div>
      </div>
    </AudioProvider>
  );
}

export default App;