import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import CardReveal from '../components/CardReveal';
import RarityEffects from '../components/RarityEffects';
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

const CharacterSelection: React.FC = () => {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [currentPersona, setCurrentPersona] = useState<Persona | null>(null);
  const [pullState, setPullState] = useState<PullState>('ready');
  const [showEffects, setShowEffects] = useState(false);
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
    if (currentPersona) {
      setShowEffects(true);
      // Keep effects active indefinitely until user makes a choice
      // Effects will be cleared when handlePullAgain is called
    }
  };

  const handleCharacterSelect = (personaKey: string) => {
    const personaToSelect = personas.find(p => p.key === personaKey);
    if (personaToSelect) {
      setShowEffects(false);
      setSelectedPersona(personaToSelect);
      // Small delay to let effects fade out before navigation
      setTimeout(() => {
        navigate('/chat');
      }, 300);
    }
  };

  const handlePullAgain = () => {
    setShowEffects(false);
    // Small delay to let effects fade out before resetting
    setTimeout(() => {
      setCurrentPersona(null);
      setPullState('ready');
    }, 300);
  };

  if (personas.length === 0) {
    return (
      <div className={styles['pull-button-container']}>
        <div className={styles['pull-instructions']}>
          <h2>Loading Characters...</h2>
          <p>Please wait while we prepare your character selection.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1>Character Selection</h1>

      {/* Rarity Effects Overlay */}
      {currentPersona && (
        <RarityEffects
          rarity={currentPersona.rarity}
          isActive={showEffects}
        />
      )}

      {pullState === 'ready' && (
        <motion.div
          className={styles['pull-button-container']}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className={styles['pull-instructions']}>
            <h2>Ready to Pull?</h2>
            <p>Click the button below to pull a random character and start your conversation!</p>
          </div>
          <motion.button
            className={styles['pull-button']}
            onClick={handlePullCharacter}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            🎯 Pull Character
          </motion.button>
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
              className={styles['pull-button-container']}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              style={{ padding: '1rem', minHeight: 'auto' }}
            >
              <div className={styles['pull-instructions']}>
                <h2>You pulled: {currentPersona.display_name}!</h2>
                <p>Rarity: <strong>{currentPersona.rarity}</strong></p>
              </div>

              <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                <motion.button
                  className={styles['pull-button']}
                  onClick={handleCharacterSelect.bind(null, currentPersona.key)}
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
              </div>
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
};

export default CharacterSelection;
