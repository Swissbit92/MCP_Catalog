import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { fetchPersonas, fetchCharacterBio } from '../services/api'
import BoltedPlateBorder from './BoltedPlateBorder'
import CharacterSelector from './CharacterSelector'
import NephilimBackground from './NephilimBackground'

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
  const [isTransitioning, setIsTransitioning] = useState(false);
  // Panel is always visible - no show/hide state needed

  // Load personas on component mount
  useEffect(() => {
    const loadPersonas = async () => {
      try {
        const personasData = await fetchPersonas();
        setPersonas(personasData);
      } catch (error) {
        console.error('Failed to load personas:', error);
        // Fallback to hardcoded data
        const fallbackPersonas: PersonaJson[] = [
          {
            key: 'eeva',
            display_name: 'Eeva — Bitcoin Expert',
            coordinator_label: 'Cryptocurrency Analyst',
            image: 'personas/eeva/card.png',
            avatar: 'personas/eeva/avatar.png',
            rarity: 'legendary',
            style: 'nerdy, charming, concise',
            logo: 'personas/eeva/logo.png',
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
        const bio = await fetchCharacterBio(currentPersona.key);
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

  const handlePrev = () => {
    if (isTransitioning) return;
    setIsTransitioning(true);
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : personas.length - 1));
    setTimeout(() => setIsTransitioning(false), 300);
  };

  const handleNext = () => {
    if (isTransitioning) return;
    setIsTransitioning(true);
    setCurrentIndex((prev) => (prev < personas.length - 1 ? prev + 1 : 0));
    setTimeout(() => setIsTransitioning(false), 300);
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (isTransitioning) return;

      switch (event.key) {
        case 'ArrowLeft':
          event.preventDefault();
          handlePrev();
          break;
        case 'ArrowRight':
          event.preventDefault();
          handleNext();
          break;
        case 'Home':
          event.preventDefault();
          setIsTransitioning(true);
          setCurrentIndex(0);
          setTimeout(() => setIsTransitioning(false), 300);
          break;
        case 'End':
          event.preventDefault();
          setIsTransitioning(true);
          setCurrentIndex(personas.length - 1);
          setTimeout(() => setIsTransitioning(false), 300);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isTransitioning, personas.length]);

  // Navigation handlers - panel is always visible

  // Convert API image paths to React app paths
  const getImagePath = (apiPath: string) => {
    // Handle both old format (ui/images/) and new format (images/personas/)
    if (apiPath.startsWith('images/')) {
      return '/' + apiPath;
    }
    return apiPath.replace('ui/images/', '/images/');
  };

  if (personas.length === 0) {
    return (
      <NephilimBackground particles={true} skyline={false} intensity={0.4}>
        <div className="flex items-center justify-center py-20">
          <div className="text-gray-200 text-xl">Loading characters...</div>
        </div>
      </NephilimBackground>
    )
  }

  const currentPersona = personas[currentIndex]

  return (
    <NephilimBackground particles={true} skyline={false} intensity={0.4}>
    <div className="relative w-full">
      {/* Navigation Arrows - Outside Panel */}
      <button
        onClick={handlePrev}
        disabled={isTransitioning}
        className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-[#141418]/80 hover:bg-[#1C1C22] hover:scale-110 text-cyan-300 p-4 rounded-full transition-all duration-300 z-10 shadow-lg hover:shadow-xl border border-white/[0.1] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
      >
        ‹
      </button>
      <button
        onClick={handleNext}
        disabled={isTransitioning}
        className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-[#141418]/80 hover:bg-[#1C1C22] hover:scale-110 text-cyan-300 p-4 rounded-full transition-all duration-300 z-10 shadow-lg hover:shadow-xl border border-white/[0.1] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
      >
        ›
      </button>

      {/* Character Counter - Always visible, no fade animation */}
      <div className="absolute top-4 right-4 bg-[#141418]/80 text-gray-300 px-3 py-1 rounded-full text-sm z-20 border border-white/[0.1]">
        {currentIndex + 1} / {personas.length}
      </div>

      {/* Main Overlay Panel - Glassmorphic */}
      <motion.div
        key={currentPersona.key}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-6xl mx-auto bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl overflow-hidden shadow-[0_8px_32px_0_rgba(0,0,0,0.36)]"
      >
          {/* Background Texture */}
          <div
            className="absolute inset-0 opacity-10 pointer-events-none"
            style={{
              backgroundImage: `
                radial-gradient(circle at 25% 25%, rgba(0,255,255,0.1) 1px, transparent 1px),
                radial-gradient(circle at 75% 75%, rgba(255,0,255,0.08) 1px, transparent 1px)
              `,
              backgroundSize: '50px 50px',
            }}
          />

        <div className="flex min-h-[600px]">
          {/* Information Section - Left Side */}
          <div className="w-1/2 h-[600px] p-8 flex flex-col justify-center space-y-6">
            {/* Character Name and Title - Outside Border */}
            <motion.div
              key={`header-${currentPersona.key}`}
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{
                delay: 0.1,
                duration: 0.5,
                ease: [0.25, 0.46, 0.45, 0.94]
              }}
            >
              <h2 className="text-3xl md:text-4xl font-bold text-gray-100 mb-2 tracking-wide drop-shadow-lg">
                {currentPersona.display_name}
              </h2>
              <p className="text-xl text-gray-200 font-medium tracking-wider drop-shadow-md">
                {currentPersona.coordinator_label}
              </p>
            </motion.div>

            {/* Bio Content - Inside Bolted Plate Border */}
            <BoltedPlateBorder rarity={currentPersona.rarity} className="flex-1">
              <motion.div
                key={`bio-${currentPersona.key}`}
                initial={{ opacity: 0, y: 40, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{
                  delay: 0.3,
                  duration: 0.6,
                  ease: [0.25, 0.46, 0.45, 0.94]
                }}
                className="h-full flex flex-col justify-center"
              >
                <div className="text-gray-200 text-base md:text-lg leading-relaxed overflow-y-auto font-light tracking-wide">
                  {isLoadingBio ? (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center space-x-2 text-gray-400"
                    >
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full"
                      />
                      <span>Loading character bio...</span>
                    </motion.div>
                  ) : characterBio ? (
                    <motion.div
                      key={`content-${currentPersona.key}`}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.4, duration: 0.3 }}
                      className="space-y-4"
                    >
                      {characterBio.summary}
                    </motion.div>
                  ) : (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="text-gray-400"
                    >
                      Bio not available
                    </motion.div>
                  )}
                </div>
              </motion.div>
            </BoltedPlateBorder>
          </div>

          {/* Character Image - Right Side */}
          <div className="w-1/2 h-[600px] flex items-center justify-center p-8">
            <motion.div
              key={currentPersona.key} // Re-animate when character changes
              initial={{ opacity: 0, scale: 0.9, rotateY: -10 }}
              animate={{ opacity: 1, scale: 1, rotateY: 0 }}
              transition={{
                duration: 0.5,
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
                  e.currentTarget.src = '/images/ui/default_avatar.png'; // Fallback
                }}
              />
            </motion.div>
          </div>
        </div>

        {/* Character Selector */}
        <CharacterSelector
          personas={personas}
          currentIndex={currentIndex}
          onCharacterSelect={setCurrentIndex}
          isTransitioning={isTransitioning}
        />
      </motion.div>
    </div>
    </NephilimBackground>
  );
};

export default CharacterShowcase;