import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import CharacterCardV2Showcase from './pages/CharacterCardV2Showcase';
import Chat from './pages/Chat';
import Header from './components/Header';
import CharacterCollection from './components/CharacterCollection';
import { AudioProvider } from './context/AudioContext';

function App() {
  return (
    <AudioProvider>
      <div className="App h-screen flex flex-col">
        <Header />
        <div className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/select" element={<CharacterCardV2Showcase />} />
            <Route path="/cards-v2" element={<CharacterCardV2Showcase />} />
            <Route path="/collection" element={<CharacterCollection onCharacterSelect={(key) => window.location.href = `/chat?persona=${key}`} />} />
            <Route path="/chat" element={<Chat />} />
          </Routes>
        </div>
      </div>
    </AudioProvider>
  );
}

export default App;