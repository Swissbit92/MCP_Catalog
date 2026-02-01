import React, { useRef, useState } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import styles from './CharacterCardV2.module.css';

interface CharacterCardV2Props {
  name: string;
  style: string;
  image: string;
  rarity: string;
  onSelect: (key: string) => void;
  isSelected: boolean;
  personaKey: string;
  index?: number;
  isNephilim?: boolean;
}

const CharacterCardV2: React.FC<CharacterCardV2Props> = ({
  name,
  style,
  image,
  rarity,
  onSelect,
  isSelected,
  personaKey,
  index = 0,
  isNephilim = false
}) => {
  // Auto-detect NEPHILIM from personaKey if not explicitly set
  const isNephilimCard = isNephilim || personaKey.startsWith('nephilim_');
  const rarityClass = styles[`rarity-${rarity.toLowerCase()}`];
  const selectedClass = isSelected ? styles['selected'] : '';
  const nephilimClass = isNephilimCard ? styles['nephilim-card'] : '';

  // Physics setup for 3D tilt effects
  const cardRef = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  // Motion values for mouse tracking
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Spring physics for smooth animations
  const rotateX = useSpring(useTransform(mouseY, [-0.5, 0.5], [15, -15]), {
    stiffness: 300,
    damping: 30
  });
  const rotateY = useSpring(useTransform(mouseX, [-0.5, 0.5], [-15, 15]), {
    stiffness: 300,
    damping: 30
  });

  // Dynamic shadow based on tilt
  const shadowX = useTransform(rotateY, [-15, 15], [-20, 20]);
  const shadowY = useTransform(rotateX, [-15, 15], [10, -10]);

  // Subtle character portrait movement (opposite direction for parallax effect)
  const portraitX = useTransform(rotateY, [-15, 15], [2, -2]);
  const portraitY = useTransform(rotateX, [-15, 15], [-1, 1]);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;

    const rect = cardRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    // Calculate mouse position relative to card center (-0.5 to 0.5)
    const x = (e.clientX - centerX) / (rect.width / 2);
    const y = (e.clientY - centerY) / (rect.height / 2);

    mouseX.set(x);
    mouseY.set(y);
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    // Reset to center position smoothly
    mouseX.set(0);
    mouseY.set(0);
  };

  const handleChooseClick = () => {
    onSelect(personaKey);
  };

  // Rarity-based color schemes for dynamic styling
  const getRarityColors = (rarity: string) => {
    switch (rarity.toLowerCase()) {
      case 'legendary':
        return {
          primary: '#FFD700',
          secondary: '#FFA500',
          glow: 'rgba(255, 215, 0, 0.8)',
          gradient: 'linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FF8C00 100%)'
        };
      case 'epic':
        return {
          primary: '#DA70D6',
          secondary: '#9370DB',
          glow: 'rgba(218, 112, 214, 0.8)',
          gradient: 'linear-gradient(135deg, #DA70D6 0%, #9370DB 50%, #8A2BE2 100%)'
        };
      case 'rare':
        return {
          primary: '#00BFFF',
          secondary: '#1E90FF',
          glow: 'rgba(0, 191, 255, 0.8)',
          gradient: 'linear-gradient(135deg, #00BFFF 0%, #1E90FF 50%, #0000FF 100%)'
        };
      default: // common
        return {
          primary: '#C0C0C0',
          secondary: '#A9A9A9',
          glow: 'rgba(192, 192, 192, 0.6)',
          gradient: 'linear-gradient(135deg, #C0C0C0 0%, #A9A9A9 50%, #808080 100%)'
        };
    }
  };

  const colors = getRarityColors(rarity);

  return (
    <motion.div
      ref={cardRef}
      className={`${styles['card-outer']} ${rarityClass} ${selectedClass} ${nephilimClass}`}
      style={{
        '--rarity-primary': colors.primary,
        '--rarity-secondary': colors.secondary,
        '--rarity-glow': colors.glow,
        '--rarity-gradient': colors.gradient,
        rotateX: isHovered ? rotateX : 0,
        rotateY: isHovered ? rotateY : 0,
        transformStyle: 'preserve-3d',
        transformOrigin: 'center center'
      } as React.CSSProperties}
      initial={{ opacity: 0, y: 20, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 20,
        duration: 0.6,
        delay: index * 0.1
      }}
      whileHover={{
        y: -8,
        scale: 1.03,
        transition: { type: 'spring', stiffness: 400, damping: 25 }
      }}
      whileTap={{ scale: 0.98 }}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Holographic Background Layers */}
      <div className={styles['holo-bg-layer-1']} />
      <div className={styles['holo-bg-layer-2']} />
      <div className={styles['holo-bg-layer-3']} />

      {/* Animated Foil Effect */}
      <div className={styles['foil-effect']} />

      {/* Dynamic Glow Ring */}
      <div className={styles['glow-ring']} />

      {/* Card Content */}
      <div className={styles['card-body']}>
        {/* Character Image with Holographic Overlay */}
        <div className={styles['image-container']}>
          <motion.img
            src={image}
            alt={name}
            className={styles['card-img']}
            style={{
              x: isHovered ? portraitX : 0,
              y: isHovered ? portraitY : 0,
              transform: 'translateZ(20px)' // Push image forward in 3D space
            }}
            whileHover={{ scale: 1.05 }}
            transition={{ type: 'spring', stiffness: 300, damping: 20 }}
          />
          <div className={styles['image-holo-overlay']} />
        </div>

        {/* Character Info */}
        <div className={styles['info-section']}>
          <div className={styles['character-name']}>{name}</div>
          <div className={styles['character-style']}>{style}</div>
          <div className={styles['rarity-indicator']}>
            <span className={styles['rarity-badge']}>{rarity}</span>
            {isNephilimCard && (
              <span className={styles['nephilim-badge']}>NEPHILIM</span>
            )}
          </div>
        </div>

        {/* Action Button */}
        <div className={styles['action-section']}>
          <motion.button
            className={styles['select-button']}
            onClick={handleChooseClick}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          >
            <span className={styles['button-text']}>Select</span>
            <div className={styles['button-glow']} />
          </motion.button>
        </div>
      </div>

      {/* Dynamic Shadow */}
      <motion.div
        className={styles['dynamic-shadow']}
        style={{
          x: shadowX,
          y: shadowY,
          opacity: isHovered ? 0.6 : 0.3,
          scale: isHovered ? 1.1 : 1
        }}
        transition={{ type: 'spring', stiffness: 400, damping: 40 }}
      />

      {/* Selection Indicator */}
      {isSelected && (
        <motion.div
          className={styles['selection-indicator']}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 500, damping: 20 }}
        >
          <div className={styles['selection-ring']} />
          <div className={styles['selection-sparkles']} />
        </motion.div>
      )}
    </motion.div>
  );
};

export default CharacterCardV2;