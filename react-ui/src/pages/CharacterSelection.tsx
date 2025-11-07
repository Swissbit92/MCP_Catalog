import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
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

const CharacterSelection: React.FC = () => {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [filteredPersonas, setFilteredPersonas] = useState<Persona[]>([]);
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
          coordinator_label: p.coordinator_label,
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

  const handleCharacterSelect = (personaKey: string) => {
    const personaToSelect = personas.find(p => p.key === personaKey);
    if (personaToSelect) {
      setSelectedPersona(personaToSelect);
      navigate('/chat');
    }
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
      <h1>Character Collection</h1>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className={styles['pull-button-container']} style={{ padding: '1rem' }}>
          <div className={styles['pull-instructions']}>
            <h2>Choose your favorite character</h2>
            <p>Browse our complete collection!</p>
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
    </div>
  );
};

export default CharacterSelection;
