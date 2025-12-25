import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import CharacterSelector from './CharacterSelector';

const mockPersonas = [
  {
    key: 'eeva',
    display_name: 'Eeva — Bitcoin Expert',
    coordinator_label: 'Cryptocurrency Analyst',
    rarity: 'legendary',
    image_path: 'eeva_card.png'
  },
  {
    key: 'frieren',
    display_name: 'Frieren',
    coordinator_label: 'Ancient Mage',
    rarity: 'epic',
    image_path: 'frieren_card.png'
  }
];

describe('CharacterSelector', () => {
  const mockOnCharacterSelect = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders character thumbnails for all personas', () => {
    render(
      <CharacterSelector
        personas={mockPersonas}
        currentIndex={0}
        onCharacterSelect={mockOnCharacterSelect}
      />
    );

    // Should render thumbnails for both characters
    const thumbnails = screen.getAllByRole('button');
    expect(thumbnails).toHaveLength(2);
  });

  it('displays character images with correct alt text', () => {
    render(
      <CharacterSelector
        personas={mockPersonas}
        currentIndex={0}
        onCharacterSelect={mockOnCharacterSelect}
      />
    );

    const images = screen.getAllByRole('img');
    expect(images).toHaveLength(2);
    expect(images[0]).toHaveAttribute('alt', 'Eeva — Bitcoin Expert');
    expect(images[1]).toHaveAttribute('alt', 'Frieren');
  });

  it('shows correct character counter', () => {
    render(
      <CharacterSelector
        personas={mockPersonas}
        currentIndex={0}
        onCharacterSelect={mockOnCharacterSelect}
      />
    );

    expect(screen.getByText('1 of 2')).toBeInTheDocument();
  });

  it('updates counter when currentIndex changes', () => {
    render(
      <CharacterSelector
        personas={mockPersonas}
        currentIndex={1}
        onCharacterSelect={mockOnCharacterSelect}
      />
    );

    expect(screen.getByText('2 of 2')).toBeInTheDocument();
  });

  it('highlights currently selected character', () => {
    render(
      <CharacterSelector
        personas={mockPersonas}
        currentIndex={0}
        onCharacterSelect={mockOnCharacterSelect}
      />
    );

    const thumbnails = screen.getAllByRole('button');
    expect(thumbnails[0]).toHaveClass('border-blue-400');
    expect(thumbnails[1]).toHaveClass('border-slate-600/50');
  });

  it('calls onCharacterSelect when thumbnail is clicked', () => {
    render(
      <CharacterSelector
        personas={mockPersonas}
        currentIndex={0}
        onCharacterSelect={mockOnCharacterSelect}
      />
    );

    const thumbnails = screen.getAllByRole('button');
    fireEvent.click(thumbnails[1]);

    expect(mockOnCharacterSelect).toHaveBeenCalledWith(1);
  });

  it('shows rarity indicators', () => {
    render(
      <CharacterSelector
        personas={mockPersonas}
        currentIndex={0}
        onCharacterSelect={mockOnCharacterSelect}
      />
    );

    // Should have rarity indicators (small colored dots)
    const rarityIndicators = document.querySelectorAll('[class*="bg-yellow-400"], [class*="bg-purple-400"]');
    expect(rarityIndicators.length).toBeGreaterThan(0);
  });

  it('handles image load errors gracefully', () => {
    render(
      <CharacterSelector
        personas={mockPersonas}
        currentIndex={0}
        onCharacterSelect={mockOnCharacterSelect}
      />
    );

    const images = screen.getAllByRole('img');
    fireEvent.error(images[0]);

    // Should fallback to default image
    expect(images[0]).toHaveAttribute('src', '/images/ui/default_avatar.png');
  });

  it('applies responsive sizing classes', () => {
    render(
      <CharacterSelector
        personas={mockPersonas}
        currentIndex={0}
        onCharacterSelect={mockOnCharacterSelect}
      />
    );

    const thumbnails = screen.getAllByRole('button');
    expect(thumbnails[0]).toHaveClass('w-14', 'h-14', 'md:w-16', 'md:h-16');
  });

  it('has proper accessibility with button roles', () => {
    render(
      <CharacterSelector
        personas={mockPersonas}
        currentIndex={0}
        onCharacterSelect={mockOnCharacterSelect}
      />
    );

    const thumbnails = screen.getAllByRole('button');
    expect(thumbnails[0]).toBeInTheDocument();
    expect(thumbnails[1]).toBeInTheDocument();
  });

  it('disables thumbnails during transitions', () => {
    render(
      <CharacterSelector
        personas={mockPersonas}
        currentIndex={0}
        onCharacterSelect={mockOnCharacterSelect}
        isTransitioning={true}
      />
    );

    const thumbnails = screen.getAllByRole('button');
    expect(thumbnails[0]).toBeDisabled();
    expect(thumbnails[1]).toBeDisabled();
    expect(thumbnails[0]).toHaveClass('opacity-60', 'cursor-not-allowed');
  });

  it('enables thumbnails when not transitioning', () => {
    render(
      <CharacterSelector
        personas={mockPersonas}
        currentIndex={0}
        onCharacterSelect={mockOnCharacterSelect}
        isTransitioning={false}
      />
    );

    const thumbnails = screen.getAllByRole('button');
    expect(thumbnails[0]).not.toBeDisabled();
    expect(thumbnails[1]).not.toBeDisabled();
    expect(thumbnails[0]).not.toHaveClass('opacity-60');
  });
});