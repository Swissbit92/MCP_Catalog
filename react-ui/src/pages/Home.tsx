import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import CardReveal from '../components/CardReveal';
import EnergyParticles from '../components/EnergyParticles';
import { fetchPersonas } from '../services/api';
import { usePersona } from '../context/PersonaContext';
import styles from '../components/CharacterCard.module.css';

interface Persona {
  key: string;
  display_name: string;
  style: string;
  image: string;
  rarity: string;
  voice?: {
    greeting: string;
  };
}

type PullState = 'ready' | 'pulling' | 'revealing' | 'revealed';

const Home: React.FC = () => {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [currentPersona, setCurrentPersona] = useState<Persona | null>(null);
  const [pullState, setPullState] = useState<PullState>('ready');
  const { setSelectedPersona } = usePersona();
  const navigate = useNavigate();

  useEffect(() => {
    const getPersonas = async () => {
      try {
        const fetchedPersonas = await fetchPersonas();
        const mappedPersonas = fetchedPersonas.map(p => ({
          key: p.key,
          display_name: p.display_name || p.key,
          style: p.style,
          image: p.image.replace('ui/images/', ''),
          bg: p.bg ? p.bg.replace('ui/images/', '') : undefined,
          rarity: p.rarity,
          voice: p.voice,
        }));
        setPersonas(mappedPersonas);
      } catch (error) {
        console.error('Failed to fetch personas:', error);
      }
    };

    getPersonas();
  }, []);

  const getRandomPersona = (): Persona => {
    if (personas.length === 0) {
      throw new Error('No personas available');
    }
    const randomIndex = Math.floor(Math.random() * personas.length);
    return personas[randomIndex];
  };

  const handlePullCharacter = () => {
    if (pullState !== 'ready' || personas.length === 0) return;

    setPullState('pulling');

    // Simulate pull delay for excitement
    setTimeout(() => {
      const pulledPersona = getRandomPersona();
      setCurrentPersona(pulledPersona);
      setPullState('revealing');
    }, 500);
  };

  const handleRevealComplete = () => {
    setPullState('revealed');
  };

  const handleCharacterSelect = (personaKey: string) => {
    const personaToSelect = personas.find(p => p.key === personaKey);
    if (personaToSelect) {
      setSelectedPersona(personaToSelect);
      navigate('/chat');
    }
  };

  const handlePullAgain = () => {
    // Immediately start pulling another character without going back to ready state
    setPullState('pulling');

    // Simulate pull delay for excitement
    setTimeout(() => {
      const pulledPersona = getRandomPersona();
      setCurrentPersona(pulledPersona);
      setPullState('revealing');
    }, 500);
  };

  const handleBrowseCollection = () => {
    navigate('/select?mode=static');
  };

  if (personas.length === 0) {
    return (
      <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 min-h-screen flex items-center justify-center">
        <EnergyParticles isActive={true} />
        <div className="relative z-10 bg-black/30 backdrop-blur-sm rounded-2xl border border-white/10 p-8 text-center">
          <h2 className="text-2xl font-bold text-white mb-4">Loading Characters...</h2>
          <p className="text-gray-300 mb-4">Please wait while we prepare your character selection.</p>
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-400 mx-auto"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 min-h-screen relative">
      <EnergyParticles isActive={true} />
      <div className="relative z-10">
        <div className="text-center py-8">
          <h1 className="text-4xl md:text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-purple-400 to-blue-400 mb-4">
            Persona Chat
          </h1>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            Experience the ultimate character chat experience with our gacha-style character selection system
          </p>
        </div>

      {pullState === 'ready' && (
        <motion.div
          className={`${styles['pull-button-container']} bg-black/30 backdrop-blur-sm rounded-2xl border border-white/10`}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className={`${styles['pull-instructions']} text-white`}>
            <h2 className="text-2xl font-bold mb-2">Ready to Pull?</h2>
            <p className="text-gray-300">Choose how you'd like to select your character!</p>
          </div>
          <div className="flex flex-col gap-4 items-center w-full max-w-md">
            <motion.button
              className={styles['pull-button']}
              onClick={handlePullCharacter}
              style={{
                background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
                boxShadow: '0 8px 32px rgba(251, 191, 36, 0.3)'
              }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              🎯 Pull Character
            </motion.button>
            <motion.button
              className={styles['pull-button']}
              onClick={handleBrowseCollection}
              style={{
                background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                boxShadow: '0 8px 32px rgba(245, 158, 11, 0.3)'
              }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              📚 Browse Collection
            </motion.button>
          </div>
        </motion.div>
      )}

      {/* Show CardReveal in all pull states once a persona is selected */}
      {currentPersona && (pullState === 'pulling' || pullState === 'revealing' || pullState === 'revealed') && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2rem' }}>
          <CardReveal
            persona={currentPersona}
            onSelect={handleCharacterSelect}
            isRevealing={pullState === 'revealing' || pullState === 'revealed'}
            onRevealComplete={handleRevealComplete}
          />

          {pullState === 'revealed' && (
            <motion.div
              className={`${styles['pull-button-container']} bg-black/30 backdrop-blur-sm rounded-2xl border border-white/10`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              style={{ padding: '1rem', minHeight: 'auto' }}
            >
              <div className={`${styles['pull-instructions']} text-white`}>
                <h2 className="text-2xl font-bold mb-2">You pulled: {currentPersona.display_name}!</h2>
                <p className="text-gray-300">Rarity: <strong className="text-yellow-400">{currentPersona.rarity}</strong></p>
              </div>

               <div className="flex gap-4 mt-4 flex-wrap justify-center">
                  <motion.button
                    className={styles['pull-button']}
                    onClick={handleCharacterSelect.bind(null, currentPersona.key)}
                    style={{
                      background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
                      boxShadow: '0 8px 32px rgba(251, 191, 36, 0.3)'
                    }}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    💬 Start Chat
                  </motion.button>

                 <motion.button
                   className={styles['pull-button']}
                   onClick={handlePullAgain}
                   style={{
                     background: 'linear-gradient(135deg, #4ade80 0%, #22c55e 100%)',
                     boxShadow: '0 8px 32px rgba(74, 222, 128, 0.3)'
                   }}
                   whileHover={{ scale: 1.05 }}
                   whileTap={{ scale: 0.95 }}
                 >
                   🔄 Pull Again
                 </motion.button>

                  <motion.button
                    className={styles['pull-button']}
                    onClick={handleBrowseCollection}
                    style={{
                      background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                      boxShadow: '0 8px 32px rgba(245, 158, 11, 0.3)'
                    }}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    📚 Browse All
                  </motion.button>
               </div>
            </motion.div>
          )}
        </div>
      )}
      </div>
    </div>
  );
};

export default Home;