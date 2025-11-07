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

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, whileHover, whileTap, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, whileHover, whileTap, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
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
    'pull-button-container': 'pull-button-container',
    'pull-button': 'pull-button',
    'pull-instructions': 'pull-instructions',
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

  it('shows loading state initially', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <CharacterSelection />
        </MemoryRouter>
      );
    });

    expect(screen.getByText('Loading Characters...')).toBeInTheDocument();
  });

  it('renders pull button after fetching personas', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <CharacterSelection />
        </MemoryRouter>
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Ready to Pull?')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /pull character/i })).toBeInTheDocument();
    });
  });

  it('shows character reveal after pulling', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <CharacterSelection />
        </MemoryRouter>
      );
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /pull character/i })).toBeInTheDocument();
    });

    // Click the pull button
    const pullButton = screen.getByRole('button', { name: /pull character/i });
    await act(async () => {
      pullButton.click();
    });

    // Wait for the reveal to complete (this might need adjustment based on timing)
    await waitFor(() => {
      // After pulling, we should eventually see either the revealed character or pull again options
      expect(screen.queryByText('Ready to Pull?')).not.toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it('allows pulling again after character reveal', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <CharacterSelection />
        </MemoryRouter>
      );
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /pull character/i })).toBeInTheDocument();
    });

    // Click the pull button
    const pullButton = screen.getByRole('button', { name: /pull character/i });
    await act(async () => {
      pullButton.click();
    });

    // Wait for pull again button to appear (this simulates the reveal completing)
    await waitFor(() => {
      const pullAgainButton = screen.getByRole('button', { name: /pull again/i });
      expect(pullAgainButton).toBeInTheDocument();
    }, { timeout: 2000 });

    // Click pull again
    const pullAgainButton = screen.getByRole('button', { name: /pull again/i });
    await act(async () => {
      pullAgainButton.click();
    });

    // Should be back to ready state
    await waitFor(() => {
      expect(screen.getByText('Ready to Pull?')).toBeInTheDocument();
    });
  });

  it('does not load empty - always shows loading or content', async () => {
    // Test that the component never renders completely empty
    await act(async () => {
      render(
        <MemoryRouter>
          <CharacterSelection />
        </MemoryRouter>
      );
    });

    // Should always show either loading or content
    const heading = screen.getByRole('heading', { name: /character selection/i });
    expect(heading).toBeInTheDocument();

    // After loading, should show pull interface
    await waitFor(() => {
      expect(screen.queryByText('Loading Characters...')).not.toBeInTheDocument();
    });

    // Should have either pull button or revealed content
    const hasPullButton = screen.queryByRole('button', { name: /pull character/i });
    const hasStartChatButton = screen.queryByRole('button', { name: /start chat/i });

    expect(hasPullButton || hasStartChatButton).toBeTruthy();
  });
});