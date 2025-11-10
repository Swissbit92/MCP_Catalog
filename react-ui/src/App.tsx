import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import CharacterSelection from './pages/CharacterSelection';
import Chat from './pages/Chat';
import Header from './components/Header';

function App() {
  return (
    <div className="App h-screen flex flex-col">
      <Header />
      <div className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/select" element={<CharacterSelection />} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;