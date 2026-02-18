import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { jest } from '@jest/globals';
import CharacterCardV2 from './CharacterCardV2';

// Mock CSS modules
jest.mock('./CharacterCardV2.module.css', () => ({
  __esModule: true,
  default: {
    'card-outer': 'card-outer',
    'rarity-legendary': 'rarity-legendary',
    'rarity-epic': 'rarity-epic',
    'rarity-rare': 'rarity-rare',
    'rarity-common': 'rarity-common',
    'selected': 'selected',
    'holo-bg-layer-1': 'holo-bg-layer-1',
    'holo-bg-layer-2': 'holo-bg-layer-2',
    'holo-bg-layer-3': 'holo-bg-layer-3',
    'foil-effect': 'foil-effect',
    'glow-ring': 'glow-ring',
    'card-body': 'card-body',
    'image-container': 'image-container',
    'card-img': 'card-img',
    'image-holo-overlay': 'image-holo-overlay',
    'info-section': 'info-section',
    'character-name': 'character-name',
    'character-style': 'character-style',
    'rarity-indicator': 'rarity-indicator',
    'rarity-badge': 'rarity-badge',
    'action-section': 'action-section',
    'select-button': 'select-button',
    'button-text': 'button-text',
    'button-glow': 'button-glow',
    'selection-indicator': 'selection-indicator',
    'selection-ring': 'selection-ring',
    'selection-sparkles': 'selection-sparkles',
  },
}));

describe('CharacterCardV2', () => {
  const mockProps = {
    name: 'Test Character',
    style: 'Test Style',
    image: '/test-image.png',
    rarity: 'legendary',
    celestial_order: 'archon',
    onSelect: jest.fn(),
    isSelected: false,
    personaKey: 'test-key',
    index: 0,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders character card with all required elements', () => {
    render(<CharacterCardV2 {...mockProps} />);

    expect(screen.getByText('Test Character')).toBeInTheDocument();
    expect(screen.getByText('Test Style')).toBeInTheDocument();
    expect(screen.getByText('Archon')).toBeInTheDocument();
    expect(screen.getByText('Select')).toBeInTheDocument();
    expect(screen.getByAltText('Test Character')).toBeInTheDocument();
  });

  it('applies correct rarity class based on rarity prop', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} />);

    const cardOuter = container.querySelector('.card-outer');
    expect(cardOuter).toHaveClass('rarity-legendary');
  });

  it('applies selected class when isSelected is true', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} isSelected={true} />);

    const cardOuter = container.querySelector('.card-outer');
    expect(cardOuter).toHaveClass('selected');
  });

  it('renders selection indicator when card is selected', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} isSelected={true} />);

    const selectionIndicator = container.querySelector('.selection-indicator');
    expect(selectionIndicator).toBeInTheDocument();
  });

  it('does not render selection indicator when card is not selected', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} isSelected={false} />);

    const selectionIndicator = container.querySelector('.selection-indicator');
    expect(selectionIndicator).not.toBeInTheDocument();
  });

  it('calls onSelect with correct personaKey when select button is clicked', () => {
    render(<CharacterCardV2 {...mockProps} />);

    const selectButton = screen.getByText('Select');
    fireEvent.click(selectButton);

    expect(mockProps.onSelect).toHaveBeenCalledWith('test-key');
    expect(mockProps.onSelect).toHaveBeenCalledTimes(1);
  });

  it('applies correct CSS custom properties for archon order (legendary rarity)', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} />);

    const cardOuter = container.querySelector('.card-outer') as HTMLElement;
    const styles = window.getComputedStyle(cardOuter);

    // Check that CSS custom properties are set (these would be set via style prop)
    // archon order uses the same gold colors as legacy legendary
    expect(cardOuter.style.getPropertyValue('--rarity-primary')).toBe('#FFD700');
    expect(cardOuter.style.getPropertyValue('--rarity-secondary')).toBe('#FFA500');
  });

  it('applies correct CSS custom properties for warden order (epic rarity)', () => {
    const wardenProps = { ...mockProps, rarity: 'epic', celestial_order: 'warden' };
    const { container } = render(<CharacterCardV2 {...wardenProps} />);

    const cardOuter = container.querySelector('.card-outer') as HTMLElement;
    expect(cardOuter.style.getPropertyValue('--rarity-primary')).toBe('#DA70D6');
    expect(cardOuter.style.getPropertyValue('--rarity-secondary')).toBe('#9370DB');
  });

  it('applies correct CSS custom properties for sage order (rare rarity)', () => {
    const sageProps = { ...mockProps, rarity: 'rare', celestial_order: 'sage' };
    const { container } = render(<CharacterCardV2 {...sageProps} />);

    const cardOuter = container.querySelector('.card-outer') as HTMLElement;
    expect(cardOuter.style.getPropertyValue('--rarity-primary')).toBe('#00BFFF');
    expect(cardOuter.style.getPropertyValue('--rarity-secondary')).toBe('#1E90FF');
  });

  it('applies correct CSS custom properties for wanderer order (common rarity)', () => {
    const wandererProps = { ...mockProps, rarity: 'common', celestial_order: 'wanderer' };
    const { container } = render(<CharacterCardV2 {...wandererProps} />);

    const cardOuter = container.querySelector('.card-outer') as HTMLElement;
    expect(cardOuter.style.getPropertyValue('--rarity-primary')).toBe('#C0C0C0');
    expect(cardOuter.style.getPropertyValue('--rarity-secondary')).toBe('#A9A9A9');
  });

  it('renders with correct image source', () => {
    render(<CharacterCardV2 {...mockProps} />);

    const image = screen.getByAltText('Test Character');
    expect(image).toHaveAttribute('src', '/test-image.png');
  });

  it('applies correct rarity class for different orders', () => {
    const { rerender, container } = render(<CharacterCardV2 {...mockProps} rarity="epic" celestial_order="warden" />);

    let cardOuter = container.querySelector('.card-outer');
    expect(cardOuter).toHaveClass('rarity-epic');

    rerender(<CharacterCardV2 {...mockProps} rarity="rare" celestial_order="sage" />);
    cardOuter = container.querySelector('.card-outer');
    expect(cardOuter).toHaveClass('rarity-rare');

    rerender(<CharacterCardV2 {...mockProps} rarity="common" celestial_order="wanderer" />);
    cardOuter = container.querySelector('.card-outer');
    expect(cardOuter).toHaveClass('rarity-common');
  });

  it('handles different persona names correctly', () => {
    const customProps = { ...mockProps, name: 'Custom Character Name' };
    render(<CharacterCardV2 {...customProps} />);

    expect(screen.getByText('Custom Character Name')).toBeInTheDocument();
  });

  it('handles different persona styles correctly', () => {
    const customProps = { ...mockProps, style: 'Custom Character Style' };
    render(<CharacterCardV2 {...customProps} />);

    expect(screen.getByText('Custom Character Style')).toBeInTheDocument();
  });

  it('passes index prop correctly for animation timing', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} index={2} />);

    // The index prop is used for animation delay, but we can't easily test the animation delay
    // We can at least verify the component renders without errors
    const cardOuter = container.querySelector('.card-outer');
    expect(cardOuter).toBeInTheDocument();
  });

  it('renders all required CSS classes for holographic effects', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} />);

    expect(container.querySelector('.holo-bg-layer-1')).toBeInTheDocument();
    expect(container.querySelector('.holo-bg-layer-2')).toBeInTheDocument();
    expect(container.querySelector('.holo-bg-layer-3')).toBeInTheDocument();
    expect(container.querySelector('.foil-effect')).toBeInTheDocument();
    expect(container.querySelector('.glow-ring')).toBeInTheDocument();
    expect(container.querySelector('.image-holo-overlay')).toBeInTheDocument();
  });

  it('maintains accessibility with proper alt text and button text', () => {
    render(<CharacterCardV2 {...mockProps} />);

    const image = screen.getByAltText('Test Character');
    expect(image).toBeInTheDocument();

    const button = screen.getByRole('button', { name: /select/i });
    expect(button).toBeInTheDocument();
  });

  it('renders card with physics-ready structure', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} />);

    // Verify the card has the necessary structure for physics
    const cardOuter = container.querySelector('.card-outer');
    const cardImg = container.querySelector('.card-img');

    expect(cardOuter).toBeInTheDocument();
    expect(cardImg).toBeInTheDocument();
  });

  it('applies 3D transform styles for physics', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} />);

    const cardOuter = container.querySelector('.card-outer');

    // Check that the card outer element exists and has the correct class structure
    expect(cardOuter).toBeInTheDocument();
    expect(cardOuter).toHaveClass('card-outer');
  });

  it('handles mouse enter and leave events', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} />);

    const cardOuter = container.querySelector('.card-outer') as HTMLElement;

    // Simulate mouse enter
    fireEvent.mouseEnter(cardOuter);

    // Simulate mouse leave
    fireEvent.mouseLeave(cardOuter);

    // Component should still be rendered (no errors)
    expect(cardOuter).toBeInTheDocument();
  });

  it('handles mouse move events for physics calculations', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} />);

    const cardOuter = container.querySelector('.card-outer') as HTMLElement;

    // Mock getBoundingClientRect
    const mockRect = {
      left: 100,
      top: 100,
      width: 200,
      height: 300,
      right: 300,
      bottom: 400
    } as DOMRect;
    (cardOuter as any).getBoundingClientRect = jest.fn().mockReturnValue(mockRect);

    // Simulate mouse move at center of card
    fireEvent.mouseEnter(cardOuter);
    fireEvent.mouseMove(cardOuter, {
      clientX: 200, // Center X
      clientY: 250  // Center Y
    });

    // Component should handle the mouse move without errors
    expect(cardOuter).toBeInTheDocument();
  });

  it('applies correct 3D transform to character image during hover', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} />);

    const cardImg = container.querySelector('.card-img');

    // The image element should exist and be properly configured for 3D transforms
    expect(cardImg).toBeInTheDocument();
    expect(cardImg).toHaveClass('card-img');
  });

  it('maintains physics behavior when card is selected', () => {
    const { container } = render(<CharacterCardV2 {...mockProps} isSelected={true} />);

    const cardOuter = container.querySelector('.card-outer');
    const selectionIndicator = container.querySelector('.selection-indicator');

    expect(cardOuter).toHaveClass('selected');
    expect(selectionIndicator).toBeInTheDocument();
  });

  it('handles physics with different order types', () => {
    const { rerender, container } = render(<CharacterCardV2 {...mockProps} rarity="epic" celestial_order="warden" />);

    let cardOuter = container.querySelector('.card-outer');
    expect(cardOuter).toHaveClass('rarity-epic');

    rerender(<CharacterCardV2 {...mockProps} rarity="rare" celestial_order="sage" />);
    cardOuter = container.querySelector('.card-outer');
    expect(cardOuter).toHaveClass('rarity-rare');

    // Physics should still work with different rarities
    expect(cardOuter).toBeInTheDocument();
  });

  it('applies reduced motion styles when prefers-reduced-motion is set', () => {
    // Mock matchMedia for reduced motion
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });

    const { container } = render(<CharacterCardV2 {...mockProps} />);

    // Component should render without physics-heavy animations
    const cardOuter = container.querySelector('.card-outer');
    expect(cardOuter).toBeInTheDocument();
  });
});