import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import CardReveal from '../components/CardReveal';
import CharacterCard from '../components/CharacterCard';
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
type SelectionMode = 'gacha' | 'static';

const CharacterSelection: React.FC = () => {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [filteredPersonas, setFilteredPersonas] = useState<Persona[]>([]);
  const [currentPersona, setCurrentPersona] = useState<Persona | null>(null);
  const [pullState, setPullState] = useState<PullState>('ready');
  const [selectionMode, setSelectionMode] = useState<SelectionMode>('gacha');
  const [searchQuery, setSearchQuery] = useState('');
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
        setFilteredPersonas(mappedPersonas);
      } catch (error) {
        console.error('Failed to fetch personas:', error);
      }
    };

    getPersonas();
  }, []);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredPersonas(personas);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = personas.filter(persona =>
        persona.display_name.toLowerCase().includes(query) ||
        persona.style.toLowerCase().includes(query) ||
        persona.key.toLowerCase().includes(query) ||
        persona.rarity.toLowerCase().includes(query)
      );
      setFilteredPersonas(filtered);
    }
  }, [searchQuery, personas]);

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

  const handleSwitchToStatic = () => {
    setSelectionMode('static');
    setCurrentPersona(null);
    setPullState('ready');
  };

  const handleSwitchToGacha = () => {
    setSelectionMode('gacha');
    setCurrentPersona(null);
    setPullState('ready');
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

      {pullState === 'ready' && selectionMode === 'gacha' && (
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
            <motion.button
              className={styles['pull-button']}
              onClick={handlePullCharacter}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              🎯 Pull Character
            </motion.button>
            <motion.button
              className={styles['pull-button']}
              onClick={handleSwitchToStatic}
              style={{
                background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                boxShadow: '0 8px 32px rgba(139, 92, 246, 0.3)'
              }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              📚 Browse Collection
            </motion.button>
          </div>
        </motion.div>
      )}

      {pullState === 'ready' && selectionMode === 'static' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className={styles['pull-button-container']} style={{ padding: '1rem' }}>
            <div className={styles['pull-instructions']}>
              <h2>Character Collection</h2>
              <p>Choose your favorite character from our collection!</p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
              <input
                type="text"
                placeholder="Search by name, style, or rarity..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  padding: '0.75rem 1rem',
                  borderRadius: '25px',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  background: 'rgba(255, 255, 255, 0.1)',
                  color: 'white',
                  fontSize: '1rem',
                  width: '100%',
                  maxWidth: '400px',
                  outline: 'none',
                  backdropFilter: 'blur(10px)'
                }}
              />
              <motion.button
                className={styles['pull-button']}
                onClick={handleSwitchToGacha}
                style={{
                  background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                  boxShadow: '0 8px 32px rgba(245, 158, 11, 0.3)'
                }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                🎲 Try Your Luck
              </motion.button>
            </div>
          </div>
          <div className={styles['cards-grid']}>
            {filteredPersonas.map((persona) => (
              <CharacterCard
                key={persona.key}
                personaKey={persona.key}
                name={persona.display_name}
                style={persona.style}
                image={`/images/${persona.image}`}
                rarity={persona.rarity}
                onSelect={handleCharacterSelect}
                isSelected={false}
              />
            ))}
          </div>
          {filteredPersonas.length === 0 && searchQuery && (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
              No characters found matching "{searchQuery}"
            </div>
          )}
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

               <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
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

                 <motion.button
                   className={styles['pull-button']}
                   onClick={handleSwitchToStatic}
                   style={{
                     background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                     boxShadow: '0 8px 32px rgba(139, 92, 246, 0.3)'
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
  );
};

export default CharacterSelection;
