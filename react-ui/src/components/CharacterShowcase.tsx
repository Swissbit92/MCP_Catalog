import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { fetchPersonas, fetchCharacterBio } from '../services/api';
import BoltedPlateBorder from './BoltedPlateBorder';

interface PersonaJson {
  key: string;
  rarity: string;
  display_name: string;
  style: string;
  coordinator_label: string;
  image: string;
  avatar: string;
  logo: string;
  bg?: string;
  emoji: string;
  allowed_mcp: string[];
  lore: string[];
  voice: any;
  do: string[];
  dont: string[];
  behavior: any;
  emotional_profile: any;
  boundaries: any;
  dialogue_prefs: any;
  expertise: any;
  signature_moves: string[];
  example_phrases: string[];
  escalation_policy: any;
}

interface CharacterBio {
  key: string;
  summary: string;
  hash: string;
  updated: string;
}

const CharacterShowcase: React.FC = () => {
  const [personas, setPersonas] = useState<PersonaJson[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [characterBio, setCharacterBio] = useState<CharacterBio | null>(null);
  const [isLoadingBio, setIsLoadingBio] = useState(false);
  // Panel is always visible - no show/hide state needed

  // Load personas on component mount
  useEffect(() => {
    const loadPersonas = async () => {
      try {
        console.log('Loading personas from API...');
        const personasData = await fetchPersonas();
        console.log('Loaded personas:', personasData.length, 'characters');
        setPersonas(personasData);
      } catch (error) {
        console.error('Failed to load personas:', error);
        // Fallback to hardcoded data
        const fallbackPersonas: PersonaJson[] = [
          {
            key: 'eeva',
            display_name: 'Eeva — Bitcoin Expert',
            coordinator_label: 'Cryptocurrency Analyst',
            image: 'ui/images/eeva_card.png',
            avatar: 'ui/images/eeva_avatar.png',
            rarity: 'legendary',
            style: 'nerdy, charming, concise',
            logo: 'ui/images/eeva_logo.png',
            emoji: '🧠',
            allowed_mcp: ['chat', 'graphrag'],
            lore: ['Eeva grew up dismantling gadgets...'],
            voice: {},
            do: [],
            dont: [],
            behavior: {},
            emotional_profile: {},
            boundaries: {},
            dialogue_prefs: {},
            expertise: {},
            signature_moves: [],
            example_phrases: [],
            escalation_policy: {}
          }
        ];
        console.log('Using fallback data');
        setPersonas(fallbackPersonas);
      }
    };

    loadPersonas();
  }, []);

  // Load bio when character changes
  useEffect(() => {
    const loadBio = async () => {
      if (personas.length === 0) return;

      const currentPersona = personas[currentIndex];
      if (!currentPersona) return;

      setIsLoadingBio(true);
      try {
        console.log('Loading bio for:', currentPersona.key);
        const bio = await fetchCharacterBio(currentPersona.key);
        console.log('Loaded bio:', bio.summary.substring(0, 100) + '...');
        setCharacterBio(bio);
      } catch (error) {
        console.error('Failed to load character bio:', error);
        setCharacterBio(null);
      } finally {
        setIsLoadingBio(false);
      }
    };

    loadBio();
  }, [currentIndex, personas]);

  const handleNext = () => {
    setCurrentIndex((prev) => (prev + 1) % personas.length);
  };

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev - 1 + personas.length) % personas.length);
  };

  // Navigation handlers - panel is always visible

  // Convert API image paths to React app paths
  const getImagePath = (apiPath: string) => {
    return apiPath.replace('ui/images/', '/images/');
  };

  if (personas.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-white text-xl">Loading characters...</div>
      </div>
    );
  }

  const currentPersona = personas[currentIndex];

  return (
    <div className="relative w-full">
      {/* Main Overlay Panel - Always Visible */}
      <motion.div
        key={currentPersona.key} // Re-animate when character changes
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-6xl mx-auto bg-slate-900/50 backdrop-blur-2xl border border-slate-700/30 rounded-2xl overflow-hidden shadow-2xl shadow-slate-900/70"
      >
          {/* Background Texture */}
          <div
            className="absolute inset-0 opacity-10 pointer-events-none"
            style={{
              backgroundImage: `
                radial-gradient(circle at 25% 25%, rgba(59,130,246,0.15) 1px, transparent 1px),
                radial-gradient(circle at 75% 75%, rgba(147,51,234,0.1) 1px, transparent 1px)
              `,
              backgroundSize: '50px 50px',
            }}
          />

        {/* Navigation Arrows - Outside Panel */}
        <button
          onClick={handlePrev}
          className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-slate-700/60 hover:bg-slate-600/80 hover:scale-110 text-white p-4 rounded-full transition-all duration-300 z-10 shadow-lg hover:shadow-xl border border-slate-600/30"
        >
          ‹
        </button>
        <button
          onClick={handleNext}
          className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-slate-700/60 hover:bg-slate-600/80 hover:scale-110 text-white p-4 rounded-full transition-all duration-300 z-10 shadow-lg hover:shadow-xl border border-slate-600/30"
        >
          ›
        </button>

        {/* Character Counter */}
        <div className="absolute top-4 right-4 bg-black/50 text-white px-3 py-1 rounded-full text-sm z-10">
          {currentIndex + 1} / {personas.length}
        </div>

        <div className="flex min-h-[600px]">
          {/* Information Section - Left Side */}
          <div className="w-1/2 h-[600px] p-8 flex flex-col justify-center space-y-6">
            {/* Character Name and Title - Outside Border */}
            <motion.div
              key={`header-${currentPersona.key}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: 0.1,
                duration: 0.4,
                ease: [0.25, 0.46, 0.45, 0.94]
              }}
            >
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-2 tracking-wide drop-shadow-lg">
                {currentPersona.display_name}
              </h2>
              <p className="text-xl text-gray-300 font-medium tracking-wider drop-shadow-md">
                {currentPersona.coordinator_label}
              </p>
            </motion.div>

            {/* Bio Content - Inside Bolted Plate Border */}
            <BoltedPlateBorder rarity={currentPersona.rarity} className="flex-1">
              <motion.div
                key={`bio-${currentPersona.key}`}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: 0.3,
                  duration: 0.6,
                  ease: [0.25, 0.46, 0.45, 0.94]
                }}
                className="h-full flex flex-col justify-center"
              >
                <div className="text-slate-100 text-base md:text-lg leading-relaxed overflow-y-auto font-light tracking-wide">
                  {isLoadingBio ? (
                    <div className="text-gray-400">Loading character bio...</div>
                  ) : characterBio ? (
                    <div className="space-y-4">
                      {characterBio.summary}
                    </div>
                  ) : (
                    <div className="text-gray-400">Bio not available</div>
                  )}
                </div>
              </motion.div>
            </BoltedPlateBorder>
          </div>

          {/* Character Image - Right Side */}
          <div className="w-1/2 h-[600px] flex items-center justify-center p-8">
            <motion.div
              key={`image-${currentPersona.key}`}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{
        delay: 0.2,
        duration: 0.6,
        ease: [0.25, 0.46, 0.45, 0.94]
      }}
              className="relative"
            >
              <img
                src={getImagePath(currentPersona.image)}
                alt={currentPersona.display_name}
                className="w-full h-auto max-h-96 object-contain rounded-lg"
                onError={(e) => {
                  console.error('Character image failed to load:', e.currentTarget.src);
                  e.currentTarget.src = '/images/eeva_card.png'; // Fallback
                }}
              />
            </motion.div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default CharacterShowcase;