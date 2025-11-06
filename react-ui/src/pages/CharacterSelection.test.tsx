import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CharacterSelection from '../pages/CharacterSelection';
import * as api from '../services/api'; // Import the entire module
import * as PersonaContextModule from '../context/PersonaContext'; // Import the context module

// Mock the useNavigate hook
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Mock the CSS module
jest.mock('../components/CharacterCard.module.css', () => ({
  __esModule: true,
  default: {
    'cards-grid': 'cards-grid',
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

describe('CharacterSelection', () => {
  // Mock the fetchPersonas function specifically before each test
  beforeEach(() => {
    jest.spyOn(api, 'fetchPersonas').mockImplementation(() =>
      Promise.resolve([
        { key: 'Eeva', display_name: 'Eeva', style: 'friendly', image: 'ui/images/eeva_card.png', rarity: 'Legendary', voice: { greeting: 'Hello Eeva' } } as any,
        { key: 'Frieren', display_name: 'Frieren', style: 'wise', image: 'ui/images/frieren_card.png', rarity: 'Epic', voice: { greeting: 'Hello Frieren' } } as any,
      ])
    );

    // Mock usePersona hook
    jest.spyOn(PersonaContextModule, 'usePersona').mockReturnValue({
      selectedPersona: null,
      setSelectedPersona: jest.fn(),
    });
  });

  // Restore the original implementation after each test
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders character cards after fetching personas', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <CharacterSelection />
        </MemoryRouter>
      );
    });

    // Use waitFor to explicitly wait for the asynchronous state update caused by fetchPersonas
    await waitFor(() => {
      expect(screen.getByText('Eeva')).toBeInTheDocument();
      expect(screen.getByText('Frieren')).toBeInTheDocument();
      expect(screen.getByAltText('Eeva')).toHaveAttribute('src', '/images/eeva_card.png');
      expect(screen.getByText('Legendary')).toBeInTheDocument();
      expect(screen.getByText('Epic')).toBeInTheDocument();
      expect(screen.getAllByRole('button', { name: /choose/i }).length).toBe(2); // Expect two choose buttons
    });
  });
});