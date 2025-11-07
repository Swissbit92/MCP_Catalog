import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CharacterCard from '../components/CharacterCard';
import { fetchPersonas } from '../services/api';
import { usePersona } from '../context/PersonaContext';
import styles from '../components/CharacterCard.module.css'; // Import styles

interface Persona {
  key: string;
  display_name: string;
  style: string;
  image: string;
  rarity: string;
  voice?: { // Optional, as not all personas might have it
    greeting: string;
  };
}

const CharacterSelection: React.FC = () => {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const { selectedPersona, setSelectedPersona } = usePersona();
  const navigate = useNavigate();

  useEffect(() => {
    const getPersonas = async () => {
      const fetchedPersonas = await fetchPersonas();
      const mappedPersonas = fetchedPersonas.map(p => ({
        key: p.key,
        display_name: p.display_name || p.key,
        style: p.style,
        image: p.image.replace('ui/images/', ''), // Remove 'ui/images/' prefix
        rarity: p.rarity,
        voice: p.voice,
      }));
      setPersonas(mappedPersonas);
    };

    getPersonas();
  }, []);

  const handleCharacterSelect = (personaKey: string) => {
    const personaToSelect = personas.find(p => p.key === personaKey);
    if (personaToSelect) {
      setSelectedPersona(personaToSelect);
      navigate('/chat');
    }
  };

  return (
    <div>
      <h1>Character Selection</h1>
      {personas.length === 0 && <p>Loading personas...</p>}
      <div className={styles['cards-grid']}> {/* Use the CSS module class for the grid */}
        {personas.map((persona) => (
          <CharacterCard
            key={persona.key}
            personaKey={persona.key}
            name={persona.display_name}
            style={persona.style}
            image={`/images/${persona.image}`}
            rarity={persona.rarity}
            onSelect={handleCharacterSelect}
            isSelected={selectedPersona?.key === persona.key}
          />
        ))}
      </div>
    </div>
  );
};

export default CharacterSelection;
