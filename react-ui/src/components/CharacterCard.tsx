import React from 'react';
import { motion } from 'framer-motion';
import styles from './CharacterCard.module.css';

interface CharacterCardProps {
  name: string;
  style: string;
  image: string;
  rarity: string;
  onSelect: (key: string) => void; // Card click - selection only (no navigation)
  onChoose?: (key: string) => void; // Choose button - navigate to chat
  isSelected: boolean;
  personaKey: string;
  index?: number;
}

const CharacterCard: React.FC<CharacterCardProps> = ({ name, style, image, rarity, onSelect, onChoose, isSelected, personaKey, index = 0 }) => {
  const rarityClass = styles[`rarity-${rarity.toLowerCase()}`];
  const selectedClass = isSelected ? styles['selected'] : '';

  const handleChooseClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click from firing
    if (onChoose) {
      onChoose(personaKey); // Navigate to chat
    } else {
      onSelect(personaKey); // Fallback to old behavior
    }
  };

  const handleCardClick = () => {
    onSelect(personaKey); // Just select the card (visual feedback only)
  };

  return (
    <motion.div
      className={`${styles['card-outer']} ${rarityClass} ${selectedClass}`}
      onClick={handleCardClick}
      style={{ cursor: 'pointer' }}
      initial={{ opacity: 0, y: 20, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        opacity: { duration: 0.6, delay: index * 0.1 },
        y: { type: 'spring', stiffness: 300, damping: 20, delay: index * 0.1 },
        default: { duration: 0.15, ease: [0.4, 0, 0.2, 1] }
      }}
      whileHover={{
        scale: 1.05,
        transition: { duration: 0.15, ease: [0.4, 0, 0.2, 1] }
      }}
      whileTap={{ scale: 0.96 }}
    >
      <div className={styles['card-frame']}></div>
      <div className={styles['card-foil']}></div>
      <div className={styles['card-glint']}></div>
      <div className={styles['card-body']}>
        <img
          src={image}
          alt={name}
          className={styles['card-img']}
        />
        <div className={styles['card-name']}>{name}</div>
        <div className={styles['card-tagline']}>{style}</div>
        <div className={styles['rarity-badge']}>{rarity}</div>
        <div className={styles['card-choose']}>
          <motion.button
            className={styles['choose-pill']}
            onClick={handleChooseClick}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          >
            Choose
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
};

export default CharacterCard;