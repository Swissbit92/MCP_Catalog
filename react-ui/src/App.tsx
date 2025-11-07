import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import CharacterSelection from './pages/CharacterSelection';
import Chat from './pages/Chat';
import Header from './components/Header';

function App() {
  return (
    <div className="App">
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/select" element={<CharacterSelection />} />
        <Route path="/chat" element={<Chat />} />
      </Routes>
    </div>
  );
}

export default App;