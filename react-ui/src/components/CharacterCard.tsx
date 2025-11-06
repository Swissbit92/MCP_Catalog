import React from 'react';
import styles from './CharacterCard.module.css';

interface CharacterCardProps {
  name: string;
  style: string;
  image: string;
  rarity: string;
  onSelect: (key: string) => void;
  isSelected: boolean;
  personaKey: string;
}

const CharacterCard: React.FC<CharacterCardProps> = ({ name, style, image, rarity, onSelect, isSelected, personaKey }) => {
  const rarityClass = styles[`rarity-${rarity.toLowerCase()}`];
  const selectedClass = isSelected ? styles['selected'] : '';

  const handleChooseClick = () => {
    onSelect(personaKey);
  };

  return (
    <div className={`${styles['card-outer']} ${rarityClass} ${selectedClass}`}>
      <div className={styles['card-frame']}></div>
      <div className={styles['card-foil']}></div>
      <div className={styles['card-glint']}></div>
      <div className={styles['card-body']}>
        <img src={image} alt={name} className={styles['card-img']} />
        <div className={styles['card-name']}>{name}</div>
        <div className={styles['card-tagline']}>{style}</div>
        <div className={styles['rarity-badge']}>{rarity}</div>
        <div className={styles['card-choose']}>
          <button className={styles['choose-pill']} onClick={handleChooseClick}>Choose</button>
        </div>
      </div>
    </div>
  );
};

export default CharacterCard;