import React, { createContext, useState, useContext, ReactNode } from 'react';

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

interface PersonaContextType {
  selectedPersona: Persona | null;
  setSelectedPersona: (persona: Persona | null) => void;
}

const PersonaContext = createContext<PersonaContextType | undefined>(undefined);

export const PersonaProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);

  return (
    <PersonaContext.Provider value={{ selectedPersona, setSelectedPersona }}>
      {children}
    </PersonaContext.Provider>
  );
};

export const usePersona = () => {
  const context = useContext(PersonaContext);
  if (context === undefined) {
    throw new Error('usePersona must be used within a PersonaProvider');
  }
  return context;
};
