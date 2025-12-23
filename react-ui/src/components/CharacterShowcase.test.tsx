import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import CharacterShowcase from './CharacterShowcase';
import { fetchPersonas, fetchCharacterBio } from '../services/api';

// Mock dependencies
jest.mock('../services/api');
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, onClick, ...props }: any) => (
      <div onClick={onClick} {...props}>{children}</div>
    )
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

const mockFetchPersonas = fetchPersonas as jest.MockedFunction<typeof fetchPersonas>;
const mockFetchCharacterBio = fetchCharacterBio as jest.MockedFunction<typeof fetchCharacterBio>;

const mockPersonas = [
  {
    key: 'eeva',
    display_name: 'Eeva — Bitcoin Expert',
    coordinator_label: 'Cryptocurrency Analyst',
    image: 'images/eeva_card.png',
    avatar: 'images/eeva_avatar.png',
    rarity: 'legendary',
    style: 'nerdy, charming, concise',
    logo: 'images/eeva_logo.png',
    emoji: '🧠',
    allowed_mcp: ['chat', 'graphrag'],
    lore: ['Eeva grew up dismantling gadgets...'],
    voice: {},
    do: [],
    dont: [],
    behavior: {},
    emotional_profile: {},
    boundaries: {},
    dialogue_prefs: {},
    expertise: {},
    signature_moves: [],
    example_phrases: [],
    escalation_policy: {}
  },
  {
    key: 'frieren',
    display_name: 'Frieren — Elf Mage',
    coordinator_label: 'Ancient Magic Scholar',
    image: 'images/frieren_card.png',
    avatar: 'images/frieren_avatar.png',
    rarity: 'epic',
    style: 'wise, calm, analytical',
    logo: 'images/frieren_logo.png',
    emoji: '🧙‍♀️',
    allowed_mcp: ['chat'],
    lore: ['Frieren is an elf mage...'],
    voice: {},
    do: [],
    dont: [],
    behavior: {},
    emotional_profile: {},
    boundaries: {},
    dialogue_prefs: {},
    expertise: {},
    signature_moves: [],
    example_phrases: [],
    escalation_policy: {}
  }
];

const mockBio = {
  key: 'eeva',
  summary: 'Eeva is a brilliant cryptocurrency analyst...',
  hash: 'abc123',
  updated: '2024-01-01'
};

describe('CharacterShowcase', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetchPersonas.mockResolvedValue(mockPersonas);
    mockFetchCharacterBio.mockResolvedValue(mockBio);
  });

  it('renders without crashing', () => {
    render(<CharacterShowcase />);
    expect(screen.getByText('Loading characters...')).toBeInTheDocument();
  });

  it('loads and displays personas', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(mockFetchPersonas).toHaveBeenCalled();
    });

    // Check that the image is displayed with correct alt text
    await waitFor(() => {
      const image = screen.getByAltText('Eeva — Bitcoin Expert');
      expect(image).toBeInTheDocument();
      expect(image).toHaveAttribute('src', '/images/eeva_card.png');
    });
  });

  it('displays character counter', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('1 / 2')).toBeInTheDocument();
    });
  });

  it('navigates to next character', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByAltText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    const nextButton = screen.getByText('›');
    fireEvent.click(nextButton);

    await waitFor(() => {
      expect(screen.getByAltText('Frieren — Elf Mage')).toBeInTheDocument();
      expect(screen.getByText('2 / 2')).toBeInTheDocument();
    });
  });

  it('navigates to previous character', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByAltText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Go to second character first
    const nextButton = screen.getByText('›');
    fireEvent.click(nextButton);

    await waitFor(() => {
      expect(screen.getByAltText('Frieren — Elf Mage')).toBeInTheDocument();
    });

    // Go back to first character
    const prevButton = screen.getByText('‹');
    fireEvent.click(prevButton);

    await waitFor(() => {
      expect(screen.getByAltText('Eeva — Bitcoin Expert')).toBeInTheDocument();
      expect(screen.getByText('1 / 2')).toBeInTheDocument();
    });
  });

  it('displays character information in overlay panel with bolted plate border', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Character name should be visible in the panel
    expect(screen.getByText('Cryptocurrency Analyst')).toBeInTheDocument();

    // Wait for bio to load
    await waitFor(() => {
      expect(screen.getByText('Eeva is a brilliant cryptocurrency analyst...')).toBeInTheDocument();
    });

    // Check that bolted plate border is applied to bio content (should have clip-path styling)
    const bioContent = screen.getByText(/Eeva is a brilliant cryptocurrency analyst/).closest('[style*="clip-path"]');
    expect(bioContent).toBeInTheDocument();
  });

  it('displays character image in overlay panel', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      const image = screen.getByAltText('Eeva — Bitcoin Expert');
      expect(image).toBeInTheDocument();
      expect(image).toHaveAttribute('src', '/images/eeva_card.png');
    });
  });

  it('loads character bio when panel opens', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(mockFetchCharacterBio).toHaveBeenCalledWith('eeva');
    });

    const poster = screen.getByAltText('Eeva — Bitcoin Expert');
    fireEvent.click(poster);

    await waitFor(() => {
      expect(screen.getByText('Eeva is a brilliant cryptocurrency analyst...')).toBeInTheDocument();
    });
  });

  it('displays bio content when loaded', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Bio should load and display
    await waitFor(() => {
      expect(screen.getByText('Eeva is a brilliant cryptocurrency analyst...')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    mockFetchPersonas.mockRejectedValue(new Error('API Error'));

    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByAltText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Should still work with fallback data
    expect(screen.getByText('1 / 1')).toBeInTheDocument();
  });

  it('converts API image paths correctly', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      const image = screen.getByAltText('Eeva — Bitcoin Expert');
      expect(image).toHaveAttribute('src', '/images/eeva_card.png');
    });
  });

  it('maintains fixed panel height for information section', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Information section should have fixed height
    const infoSection = screen.getByText('Eeva — Bitcoin Expert').closest('[class*="w-1/2"][class*="h-\\[600px\\]"]');
    expect(infoSection).toBeInTheDocument();
  });

  it('applies rarity-based bolted plate styling', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Wait for bio to load
    await waitFor(() => {
      expect(mockFetchCharacterBio).toHaveBeenCalledWith('eeva');
    });

    // Legendary rarity should have gold border styling on bio content
    const bioContent = screen.getByText('Eeva is a brilliant cryptocurrency analyst...');
    const borderElement = bioContent.closest('[class*="border-yellow-400"]');
    expect(borderElement).toBeInTheDocument();
  });

  it('limits bio content height with scroll', async () => {
    // Create a longer bio to test scrolling
    const longBio = {
      key: 'eeva',
      summary: 'Eeva is a brilliant cryptocurrency analyst who has been working in the field for over a decade. She specializes in technical analysis and has a deep understanding of blockchain technology. Her expertise includes market trends, investment strategies, and risk management. She has worked with major financial institutions and has published numerous articles on cryptocurrency markets. Her analytical skills are unmatched in the industry.'.repeat(3),
      hash: 'abc123',
      updated: '2024-01-01'
    };

    mockFetchCharacterBio.mockResolvedValue(longBio);

    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Wait for the long bio to load
    await waitFor(() => {
      expect(screen.getByText(/Eeva is a brilliant cryptocurrency analyst/)).toBeInTheDocument();
    });

    // Bio content should have overflow scroll
    const bioContent = screen.getByText(/Eeva is a brilliant cryptocurrency analyst/).closest('[class*="overflow-y-auto"]');
    expect(bioContent).toBeInTheDocument();
  });

  it('applies enhanced glassmorphism styling to main panel', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Main panel should have enhanced glassmorphism
    const mainPanel = screen.getByText('Eeva — Bitcoin Expert').closest('.backdrop-blur-2xl');
    expect(mainPanel).toBeInTheDocument();
    expect(mainPanel).toHaveClass('bg-slate-900/50');
  });



  it('applies enhanced typography styling', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Character name should have enhanced typography
    const characterName = screen.getByText('Eeva — Bitcoin Expert');
    expect(characterName).toHaveClass('tracking-wide', 'drop-shadow-lg');

    // Character title should have enhanced typography
    const characterTitle = screen.getByText('Cryptocurrency Analyst');
    expect(characterTitle).toHaveClass('tracking-wider', 'drop-shadow-md');
  });

  it('navigation buttons have enhanced hover effects', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Navigation buttons should have hover scale effects
    const prevButton = screen.getByText('‹');
    const nextButton = screen.getByText('›');

    expect(prevButton).toHaveClass('hover:scale-110', 'transition-all', 'duration-300');
    expect(nextButton).toHaveClass('hover:scale-110', 'transition-all', 'duration-300');
  });

  it('shows loading spinner during bio loading', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Should show loading spinner initially
    expect(screen.getByText('Loading character bio...')).toBeInTheDocument();

    // Should have animated spinner
    const spinner = document.querySelector('[class*="animate-spin"], [class*="rotate-360"]');
    expect(spinner).toBeInTheDocument();
  });

  it('handles keyboard navigation with arrow keys', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Simulate right arrow key press
    fireEvent.keyDown(window, { key: 'ArrowRight' });

    // Should eventually show the next character (Frieren)
    await waitFor(() => {
      expect(screen.getByText('Frieren')).toBeInTheDocument();
    });
  });

  it('handles Home and End key navigation', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Simulate End key press (should go to last character)
    fireEvent.keyDown(window, { key: 'End' });

    // Should show the last character
    await waitFor(() => {
      expect(screen.getByText('Frieren')).toBeInTheDocument();
    });

    // Simulate Home key press (should go to first character)
    fireEvent.keyDown(window, { key: 'Home' });

    // Should show the first character
    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });
  });

  it('disables navigation during transitions', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    const prevButton = screen.getByText('‹');
    const nextButton = screen.getByText('›');

    // Initially buttons should not be disabled
    expect(prevButton).not.toBeDisabled();
    expect(nextButton).not.toBeDisabled();

    // Click next to trigger transition
    fireEvent.click(nextButton);

    // Buttons should be disabled during transition
    expect(prevButton).toBeDisabled();
    expect(nextButton).toBeDisabled();
  });

  it('applies smooth transition animations', async () => {
    render(<CharacterShowcase />);

    await waitFor(() => {
      expect(screen.getByText('Eeva — Bitcoin Expert')).toBeInTheDocument();
    });

    // Main panel should have transition animations
    const mainPanel = screen.getByText('Eeva — Bitcoin Expert').closest('[class*="motion"]');
    expect(mainPanel).toBeInTheDocument();
  });
});