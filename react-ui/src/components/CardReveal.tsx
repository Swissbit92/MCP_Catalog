import React from 'react';
import { motion } from 'framer-motion';
import CharacterCard from './CharacterCard';

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

interface CardRevealProps {
  persona: Persona;
  onSelect: (key: string) => void;
  isRevealing: boolean;
  onRevealComplete: () => void;
}

const CardReveal: React.FC<CardRevealProps> = ({
  persona,
  onSelect,
  isRevealing,
  onRevealComplete
}) => {
  return (
    <div className="card-reveal-container">
      <motion.div
        className="card-reveal-card"
        initial={{ rotateY: 180, scale: 0.8 }}
        animate={{
          rotateY: isRevealing ? 0 : 180,
          scale: isRevealing ? 1 : 0.8
        }}
        transition={{
          duration: 0.8,
          ease: "easeOut",
          delay: isRevealing ? 0.3 : 0
        }}
        onAnimationComplete={() => {
          if (isRevealing) {
            onRevealComplete();
          }
        }}
      >
        {/* Card Back */}
        <motion.div
          className="card-back"
          initial={{ opacity: 1 }}
          animate={{ opacity: isRevealing ? 0 : 1 }}
          transition={{ duration: 0.4, delay: isRevealing ? 0.2 : 0 }}
        >
          <div className="card-back-pattern">
            <div className="card-back-shine"></div>
          </div>
        </motion.div>

        {/* Card Front */}
        <motion.div
          className="card-front"
          initial={{ opacity: 0 }}
          animate={{ opacity: isRevealing ? 1 : 0 }}
          transition={{ duration: 0.4, delay: isRevealing ? 0.4 : 0 }}
        >
          <CharacterCard
            personaKey={persona.key}
            name={persona.display_name}
            style={persona.style}
            image={`/images/${persona.image}`}
            rarity={persona.rarity}
            onSelect={onSelect}
            isSelected={false}
          />
        </motion.div>
      </motion.div>
    </div>
  );
};

export default CardReveal;