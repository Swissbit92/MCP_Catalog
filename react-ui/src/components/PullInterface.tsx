import React, { useState } from 'react';
import { motion } from 'framer-motion';
import CharacterCardV2 from '../components/CharacterCardV2';
import EnergyParticles from '../components/EnergyParticles';
import { fetchPersonas } from '../services/api';
import { usePersona } from '../context/PersonaContext';
import { useAudio } from '../context/AudioContext';

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

interface PullInterfaceProps {
  onCharacterSelect: (personaKey: string) => void;
}

const PullInterface: React.FC<PullInterfaceProps> = ({ onCharacterSelect }) => {
  const { addToCollection, addPullRecord } = usePersona();
  const { playPullSound, playRevealSound, playCelebrationSound } = useAudio();
  const [isPulling, setIsPulling] = useState(false);
  const [pullStage, setPullStage] = useState<'idle' | 'building' | 'revealing' | 'complete'>('idle');
  const [pulledCharacter, setPulledCharacter] = useState<Persona | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [pullCount, setPullCount] = useState(1);
  const [hapticFeedback, setHapticFeedback] = useState<'none' | 'light' | 'medium' | 'heavy'>('none');

  // Haptic feedback simulation
  const triggerHapticFeedback = (intensity: 'light' | 'medium' | 'heavy') => {
    setHapticFeedback(intensity);
    // Visual feedback - screen shake
    if (typeof window !== 'undefined') {
      document.body.style.animation = `shake-${intensity} 0.3s ease-in-out`;
      setTimeout(() => {
        document.body.style.animation = '';
      }, 300);
    }
    // Reset haptic state
    setTimeout(() => setHapticFeedback('none'), 300);
  };

  const handlePull = async () => {
    if (isPulling) return;

    // Play pull sound and haptic feedback
    playPullSound();
    triggerHapticFeedback('light');

    setIsPulling(true);
    setShowResult(false);
    setPullStage('building');

    try {
      // Stage 1: Building energy (0.5s)
      await new Promise(resolve => setTimeout(resolve, 500));
      setPullStage('building');

      // Stage 2: API call with building tension (1s)
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Get random character (in real implementation, this would come from backend)
      const personas = await fetchPersonas();
      const randomIndex = Math.floor(Math.random() * personas.length);
      const character = {
        key: personas[randomIndex].key,
        display_name: personas[randomIndex].display_name || personas[randomIndex].key,
        style: personas[randomIndex].style,
        image: personas[randomIndex].image.replace('ui/images/', ''),
        rarity: personas[randomIndex].rarity,
      };

      setPulledCharacter(character);
      setPullStage('revealing');

      // Play reveal sound and haptic feedback
      playRevealSound();
      triggerHapticFeedback('medium');

      // Record the pull
      addPullRecord({
        personaKey: character.key,
        rarity: character.rarity,
        pullCount: pullCount,
      });

      // Stage 3: Dramatic reveal (0.8s)
      await new Promise(resolve => setTimeout(resolve, 800));

      // Play celebration sound and haptic feedback based on rarity
      playCelebrationSound(character.rarity);
      triggerHapticFeedback(character.rarity === 'legendary' ? 'heavy' : 'medium');

      setPullStage('complete');
      setShowResult(true);
      setIsPulling(false);

    } catch (error) {
      console.error('Pull failed:', error);
      setIsPulling(false);
      setPullStage('idle');
    }
  };

  const handleCharacterSelect = (personaKey: string) => {
    // Add to collection
    addToCollection(personaKey);
    onCharacterSelect(personaKey);
    // Reset for next pull
    setPulledCharacter(null);
    setShowResult(false);
    setPullStage('idle');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex flex-col">
      {/* Haptic feedback CSS animations */}
      <style>{`
        @keyframes shake-light {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-2px); }
          75% { transform: translateX(2px); }
        }
        @keyframes shake-medium {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-5px); }
          75% { transform: translateX(5px); }
        }
        @keyframes shake-heavy {
          0%, 100% { transform: translateX(0) rotate(0deg); }
          25% { transform: translateX(-8px) rotate(-1deg); }
          75% { transform: translateX(8px) rotate(1deg); }
        }
      `}</style>
      {/* Header */}
      <div className="text-center py-8 px-4">
        <h1 className="text-4xl md:text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-purple-400 to-blue-400 mb-4">
          Character Gacha
        </h1>
        <p className="text-xl text-gray-300 max-w-2xl mx-auto">
          Pull for legendary characters with holographic cards and physics-based interactions
        </p>
      </div>

      {/* Pull Interface */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 pb-8">
        {!showResult ? (
          <div className="text-center space-y-8">
            {/* Pull Count Selector */}
            <div className="flex justify-center gap-4 mb-8">
              {[1, 5, 10].map((count) => (
                <motion.button
                  key={count}
                  onClick={() => setPullCount(count)}
                  className={`px-6 py-3 rounded-full font-bold text-lg transition-all duration-300 ${
                    pullCount === count
                      ? 'bg-gradient-to-r from-yellow-400 to-orange-500 text-black shadow-lg shadow-yellow-400/50 scale-110'
                      : 'bg-gray-700 text-white hover:bg-gray-600'
                  }`}
                  whileHover={{ scale: pullCount === count ? 1.1 : 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  disabled={isPulling}
                >
                  {count}x Pull
                </motion.button>
              ))}
            </div>

            {/* Central Pull Area */}
            <div className="relative">
              {/* Energy Particles Background */}
              <EnergyParticles isActive={!isPulling} />

              {/* Animated Background Ring */}
              <motion.div
                className="absolute inset-0 rounded-full border-4 border-yellow-400/30"
                animate={pullStage === 'building' ? {
                  scale: [1, 1.3, 1.1],
                  opacity: [0.3, 1, 0.7],
                  borderColor: ['rgba(251, 191, 36, 0.3)', 'rgba(251, 191, 36, 0.8)', 'rgba(251, 191, 36, 0.5)']
                } : pullStage === 'revealing' ? {
                  scale: [1.1, 1.5, 1.2],
                  opacity: [0.7, 1, 0.8],
                  borderColor: ['rgba(251, 191, 36, 0.5)', 'rgba(34, 197, 94, 0.8)', 'rgba(251, 191, 36, 0.6)']
                } : {}}
                transition={{
                  duration: pullStage === 'building' ? 1.5 : pullStage === 'revealing' ? 0.8 : 2,
                  repeat: (pullStage === 'building' || pullStage === 'revealing') ? Infinity : 0,
                  ease: "easeInOut"
                }}
              />

              {/* Screen Flash Effect */}
              {pullStage === 'revealing' && (
                <motion.div
                  className="absolute inset-0 bg-white rounded-full"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: [0, 0.8, 0] }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                />
              )}

              {/* Pull Button */}
              <motion.button
                onClick={handlePull}
                disabled={isPulling}
                className="relative w-48 h-48 rounded-full bg-gradient-to-br from-yellow-400 via-orange-500 to-red-500 shadow-2xl shadow-yellow-400/50 flex items-center justify-center text-2xl font-bold text-black disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden"
                animate={pullStage === 'building' ? {
                  scale: [1, 1.1, 1],
                  boxShadow: [
                    '0 25px 50px -12px rgba(251, 191, 36, 0.25)',
                    '0 25px 50px -12px rgba(251, 191, 36, 0.5)',
                    '0 25px 50px -12px rgba(251, 191, 36, 0.25)'
                  ]
                } : pullStage === 'revealing' ? {
                  scale: [1, 1.2, 1.1],
                  boxShadow: [
                    '0 25px 50px -12px rgba(34, 197, 94, 0.5)',
                    '0 25px 50px -12px rgba(251, 191, 36, 0.7)',
                    '0 25px 50px -12px rgba(34, 197, 94, 0.4)'
                  ]
                } : {}}
                transition={{
                  duration: pullStage === 'building' ? 0.8 : pullStage === 'revealing' ? 0.4 : 0.3,
                  repeat: (pullStage === 'building' || pullStage === 'revealing') ? Infinity : 0,
                  ease: "easeInOut"
                }}
                whileHover={!isPulling ? { scale: 1.05 } : {}}
                whileTap={!isPulling ? { scale: 0.95 } : {}}
              >
                {/* Animated Background */}
                <motion.div
                  className="absolute inset-0 bg-gradient-to-br from-yellow-300 to-orange-400"
                  animate={pullStage === 'building' ? {
                    scale: [1, 1.15, 1.05],
                    opacity: [1, 0.9, 1]
                  } : pullStage === 'revealing' ? {
                    scale: [1.05, 1.2, 1.1],
                    opacity: [1, 0.8, 1],
                    background: [
                      'linear-gradient(to bottom right, rgb(253 224 71), rgb(249 115 22))',
                      'linear-gradient(to bottom right, rgb(34 197 94), rgb(22 163 74))',
                      'linear-gradient(to bottom right, rgb(253 224 71), rgb(249 115 22))'
                    ]
                  } : {}}
                  transition={{
                    duration: pullStage === 'building' ? 1 : pullStage === 'revealing' ? 0.6 : 1.5,
                    repeat: (pullStage === 'building' || pullStage === 'revealing') ? Infinity : 0,
                    ease: "easeInOut"
                  }}
                />

                {/* Button Content */}
                <div className="relative z-10 text-center">
                  {pullStage === 'building' ? (
                    <div>
                      <motion.div
                        className="text-6xl mb-2"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                      >
                        ⚡
                      </motion.div>
                      <div className="text-lg">Building Power...</div>
                    </div>
                  ) : pullStage === 'revealing' ? (
                    <div>
                      <motion.div
                        className="text-6xl mb-2"
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 0.3, repeat: Infinity }}
                      >
                        ✨
                      </motion.div>
                      <div className="text-lg">Revealing...</div>
                    </div>
                  ) : (
                    <div>
                      <div className="text-4xl mb-2">🎴</div>
                      <div>Pull Character</div>
                    </div>
                  )}
                </div>
              </motion.button>
            </div>

            {/* Pull Cost Display */}
            <div className="text-gray-400">
              <div className="text-sm">Cost: {pullCount * 100} 💎</div>
              <div className="text-xs mt-1">Higher pull counts have better odds!</div>
            </div>
          </div>
        ) : (
          /* Pull Result Display */
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className="text-center space-y-6"
          >
            {/* Success Message */}
            <motion.div
              initial={{ y: -20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="text-2xl font-bold text-yellow-400"
            >
              Character Pulled! 🎉
            </motion.div>

            {/* Character Card with Shake Effect */}
            <motion.div
              initial={{ scale: 0, rotateY: 180 }}
              animate={{
                scale: 1,
                rotateY: 0,
                x: [0, -5, 5, -3, 3, 0] // Shake animation
              }}
              transition={{
                scale: { type: "spring", stiffness: 200, damping: 20, delay: 0.5 },
                rotateY: { type: "spring", stiffness: 200, damping: 20, delay: 0.5 },
                x: { duration: 0.6, delay: 0.8, ease: "easeOut" }
              }}
            >
              {pulledCharacter && (
                <CharacterCardV2
                  name={pulledCharacter.display_name}
                  style={pulledCharacter.style}
                  image={`/images/${pulledCharacter.image}`}
                  rarity={pulledCharacter.rarity}
                  onSelect={handleCharacterSelect}
                  isSelected={false}
                  personaKey={pulledCharacter.key}
                  index={0}
                />
              )}
            </motion.div>

            {/* Rarity-based Celebration Effects */}
            {pulledCharacter && (
              <div className="absolute inset-0 pointer-events-none overflow-hidden">
                {/* Legendary Celebration */}
                {pulledCharacter.rarity === 'legendary' && (
                  <>
                    <motion.div
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{
                        scale: [0, 2, 1.5],
                        opacity: [0, 1, 0.9],
                        rotate: [0, 180, 360]
                      }}
                      transition={{
                        duration: 2,
                        delay: 1.2,
                        ease: "easeOut"
                      }}
                      className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"
                    >
                      <div className="text-8xl animate-pulse">🌟</div>
                    </motion.div>
                    {/* Confetti-like particles */}
                    {[...Array(20)].map((_, i) => (
                      <motion.div
                        key={i}
                        initial={{
                          x: '50vw',
                          y: '50vh',
                          scale: 0,
                          opacity: 0
                        }}
                        animate={{
                          x: `${50 + (Math.random() - 0.5) * 100}vw`,
                          y: `${50 + (Math.random() - 0.5) * 100}vh`,
                          scale: [0, 1, 0],
                          opacity: [0, 1, 0],
                          rotate: [0, 360]
                        }}
                        transition={{
                          duration: 3,
                          delay: 1.5 + i * 0.1,
                          ease: "easeOut"
                        }}
                        className="absolute w-4 h-4 text-yellow-400"
                      >
                        {['✨', '⭐', '🎊'][Math.floor(Math.random() * 3)]}
                      </motion.div>
                    ))}
                  </>
                )}

                {/* Epic Celebration */}
                {pulledCharacter.rarity === 'epic' && (
                  <motion.div
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{
                      scale: [0, 1.8, 1.2],
                      opacity: [0, 1, 0.7],
                      rotate: [0, -180, -360]
                    }}
                    transition={{
                      duration: 1.8,
                      delay: 1.2,
                      ease: "easeOut"
                    }}
                    className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"
                  >
                    <div className="text-6xl animate-pulse">💎</div>
                  </motion.div>
                )}

                {/* Rare Celebration */}
                {pulledCharacter.rarity === 'rare' && (
                  <motion.div
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{
                      scale: [0, 1.5, 1],
                      opacity: [0, 1, 0.6],
                      rotate: [0, 90, 180]
                    }}
                    transition={{
                      duration: 1.5,
                      delay: 1.2,
                      ease: "easeOut"
                    }}
                    className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"
                  >
                    <div className="text-5xl animate-pulse">🔥</div>
                  </motion.div>
                )}
              </div>
            )}

            {/* Action Buttons */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 1.5 }}
              className="flex gap-4 justify-center"
            >
              <motion.button
                onClick={() => handleCharacterSelect(pulledCharacter!.key)}
                className="px-8 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold rounded-full shadow-lg hover:shadow-xl transition-all duration-300"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Select Character
              </motion.button>
              <motion.button
                onClick={() => {
                  setPulledCharacter(null);
                  setShowResult(false);
                  setPullStage('idle');
                }}
                className="px-8 py-3 bg-gray-600 text-white font-bold rounded-full shadow-lg hover:bg-gray-500 transition-all duration-300"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Pull Again
              </motion.button>
            </motion.div>
          </motion.div>
        )}
      </div>

      {/* Footer Info */}
      <div className="text-center py-4 px-4 border-t border-gray-700">
        <div className="text-sm text-gray-400">
          Experience the next generation of gacha with interactive holographic cards
        </div>
      </div>
    </div>
  );
};

export default PullInterface;