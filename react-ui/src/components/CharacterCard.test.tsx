import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import CharacterCard from './CharacterCard';

// Mock the CSS module
jest.mock('./CharacterCard.module.css', () => ({
  __esModule: true,
  default: {
    'card-outer': 'card-outer',
    'rarity-legendary': 'rarity-legendary',
    'rarity-epic': 'rarity-epic',
    'selected': 'selected',
    'card-frame': 'card-frame',
    'card-foil': 'card-foil',
    'card-glint': 'card-glint',
    'card-body': 'card-body',
    'card-img': 'card-img',
    'card-name': 'card-name',
    'card-tagline': 'card-tagline',
    'rarity-badge': 'rarity-badge',
    'card-choose': 'card-choose',
    'choose-pill': 'choose-pill',
  },
}));

test('renders character card with name, style, image, rarity, and handles selection', () => {
  const name = 'Test Character';
  const style = 'Test Style';
  const image = '/images/test_image.png';
  const rarity = 'legendary';
  const celestial_order = 'archon';
  const personaKey = 'test-character';
  const onSelect = jest.fn();

  render(
    <CharacterCard
      name={name}
      style={style}
      image={image}
      rarity={rarity}
      celestial_order={celestial_order}
      onSelect={onSelect}
      isSelected={false}
      personaKey={personaKey}
    />
  );

  const characterName = screen.getByText(name);
  const characterStyle = screen.getByText(style);
  const characterImage = screen.getByAltText(name);
  // Display text now shows Celestial Order label: Archon instead of Legendary
  const characterRarity = screen.getByText('Archon');
  const chooseButton = screen.getByRole('button', { name: /choose/i });

  expect(characterName).toBeInTheDocument();
  expect(characterStyle).toBeInTheDocument();
  expect(characterImage).toBeInTheDocument();
  expect(characterImage).toHaveAttribute('src', image);
  expect(characterRarity).toBeInTheDocument();
  expect(chooseButton).toBeInTheDocument();

  fireEvent.click(chooseButton);
  expect(onSelect).toHaveBeenCalledWith(personaKey);
});

test('applies selected class when isSelected is true', () => {
  const name = 'Test Character';
  const style = 'Test Style';
  const image = '/images/test_image.png';
  const rarity = 'legendary';
  const celestial_order = 'archon';
  const personaKey = 'test-character';
  const onSelect = jest.fn();

  render(
    <CharacterCard
      name={name}
      style={style}
      image={image}
      rarity={rarity}
      celestial_order={celestial_order}
      onSelect={onSelect}
      isSelected={true}
      personaKey={personaKey}
    />
  );

  const cardOuter = screen.getByText(name).closest('.card-outer'); // Find the closest element with the class 'card-outer'
  expect(cardOuter).toHaveClass('selected');
});