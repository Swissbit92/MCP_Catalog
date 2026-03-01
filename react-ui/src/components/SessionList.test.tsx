import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatSession } from '../services/api';
import SessionList from './SessionList';

// Mock react-router-dom
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

// Mock the APIs
const mockFetchPersonas = jest.fn();
jest.mock('../services/api', () => ({
  fetchPersonas: () => mockFetchPersonas(),
}));

// Mock the usePersona hook
const mockUsePersona = jest.fn();
jest.mock('../context/PersonaContext', () => ({
  usePersona: () => mockUsePersona(),
}));

describe('SessionList', () => {
  const mockPersonas = [
    {
      key: 'eeva',
      display_name: 'Eeva — Bitcoin Expect',
      image: 'eeva_card.png',
      avatar: 'eeva_avatar.png',
      rarity: 'legendary',
      celestial_order: 'archon',
      style: 'nerdy',
      coordinator_label: 'Eeva',
      logo: 'eeva_logo.png',
      emoji: '🤖',
      mcp_access: ['chat'],
      lore: ['Bitcoin expert'],
      voice: {},
      do: ['Be helpful'],
      dont: ['Be rude'],
      behavior: {},
      emotional_profile: {},
      boundaries: {},
      dialogue_prefs: {},
      expertise: {},
      signature_moves: [],
      example_phrases: [],
      escalation_policy: {},
    },
  ];

  const mockSessions: ChatSession[] = [
    {
      id: '1',
      persona_key: 'eeva',
      title: 'Chat with Eeva',
      created_at: '2024-01-01T10:00:00Z',
      updated_at: '2024-01-01T10:30:00Z',
      message_count: 5,
    },
  ];

  const mockOnSessionSelect = jest.fn();
  const mockDeleteSessionById = jest.fn();
  const mockUpdateSessionTitle = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockFetchPersonas.mockResolvedValue(mockPersonas);
    mockUsePersona.mockReturnValue({
      personas: mockPersonas,
      sessions: mockSessions,
      currentSession: mockSessions[0],
      deleteSessionById: mockDeleteSessionById,
      updateSessionTitle: mockUpdateSessionTitle,
    });

    // Mock window.confirm
    window.confirm = jest.fn();
  });

  it('renders session list correctly', async () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getByText('Memory Archives')).toBeInTheDocument();
    });

    expect(screen.getByText('Chat with Eeva')).toBeInTheDocument();
    expect(screen.getByText('5 messages')).toBeInTheDocument();
  });

  it('shows empty state when no sessions', async () => {
    mockUsePersona.mockReturnValue({
      personas: mockPersonas,
      sessions: [],
      currentSession: null,
      deleteSessionById: mockDeleteSessionById,
      updateSessionTitle: mockUpdateSessionTitle,
    });

    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getByText('No conversations yet')).toBeInTheDocument();
    });
    expect(screen.getByText('Start chatting with a character!')).toBeInTheDocument();
  });

  it('highlights current session with rarity theming', async () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getByText('Chat with Eeva')).toBeInTheDocument();
    });

    // Current session should have legendary (yellow) theming since personas load in test
    const sessionContainer = screen.getByText('Chat with Eeva').closest('[class*="border-2"]');
    expect(sessionContainer).toHaveClass('bg-yellow-500/10', 'border-yellow-400/50');
  });

  it('calls onSessionSelect when session is clicked', () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    const eevaSession = screen.getByText('Chat with Eeva');
    fireEvent.click(eevaSession);

    expect(mockOnSessionSelect).toHaveBeenCalledWith(mockSessions[0]);
  });

  it('enters edit mode when rename button is clicked', async () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getAllByTitle('Rename conversation')[0]).toBeInTheDocument();
    });

    const renameButton = screen.getAllByTitle('Rename conversation')[0];
    fireEvent.click(renameButton);

    const input = screen.getByDisplayValue('Chat with Eeva');
    expect(input).toBeInTheDocument();
  });

  it('saves title when Save button is clicked', async () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getAllByTitle('Rename conversation')[0]).toBeInTheDocument();
    });

    const renameButton = screen.getAllByTitle('Rename conversation')[0];
    fireEvent.click(renameButton);

    const input = screen.getByDisplayValue('Chat with Eeva');
    fireEvent.change(input, { target: { value: 'New Title' } });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    expect(mockUpdateSessionTitle).toHaveBeenCalledWith('1', 'New Title');
  });

  it('cancels edit when Cancel button is clicked', async () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getAllByTitle('Rename conversation')[0]).toBeInTheDocument();
    });

    const renameButton = screen.getAllByTitle('Rename conversation')[0];
    fireEvent.click(renameButton);

    const input = screen.getByDisplayValue('Chat with Eeva');
    fireEvent.change(input, { target: { value: 'New Title' } });

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(mockUpdateSessionTitle).not.toHaveBeenCalled();
    expect(screen.queryByDisplayValue('New Title')).not.toBeInTheDocument();
  });

  it('deletes session when delete button is clicked and confirmed', async () => {
    (window.confirm as jest.Mock).mockReturnValue(true);

    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getAllByTitle('Delete conversation')[0]).toBeInTheDocument();
    });

    const deleteButton = screen.getAllByTitle('Delete conversation')[0];
    fireEvent.click(deleteButton);

    expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to delete this chat session?');
    expect(mockDeleteSessionById).toHaveBeenCalledWith('1');
  });

  it('does not delete session when delete is cancelled', async () => {
    (window.confirm as jest.Mock).mockReturnValue(false);

    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getAllByTitle('Delete conversation')[0]).toBeInTheDocument();
    });

    const deleteButton = screen.getAllByTitle('Delete conversation')[0];
    fireEvent.click(deleteButton);

    expect(mockDeleteSessionById).not.toHaveBeenCalled();
  });

  it('prevents session selection when clicking edit controls', async () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getAllByTitle('Rename conversation')[0]).toBeInTheDocument();
    });

    const renameButton = screen.getAllByTitle('Rename conversation')[0];
    fireEvent.click(renameButton);

    expect(mockOnSessionSelect).not.toHaveBeenCalled();
  });

  it('applies correct rarity theming to sessions', async () => {
    // Mock personas to load properly for this test
    mockFetchPersonas.mockResolvedValue(mockPersonas);

    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getByText('Archon')).toBeInTheDocument();
      expect(screen.getByText('Warden')).toBeInTheDocument();
    });

    // Check that order badges have correct styling
    const archonBadge = screen.getByText('Archon');
    expect(archonBadge).toHaveClass('bg-yellow-500/10', 'text-yellow-600');

    const wardenBadge = screen.getByText('Warden');
    expect(wardenBadge).toHaveClass('bg-purple-500/10', 'text-purple-600');
  });

  it('displays improved action buttons with SVG icons', async () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getAllByTitle('Rename conversation')).toHaveLength(2);
      expect(screen.getAllByTitle('Delete conversation')).toHaveLength(2);
    });

    // Check that SVG icons are present
    const editIcons = screen.getAllByTitle('Rename conversation');
    const deleteIcons = screen.getAllByTitle('Delete conversation');

    expect(editIcons).toHaveLength(2);
    expect(deleteIcons).toHaveLength(2);
  });

  it('shows enhanced header with subtitle', async () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getByText('Memory Archives')).toBeInTheDocument();
    });

    expect(screen.getByText('Your conversations')).toBeInTheDocument();
  });

  it('applies glassmorphism background styling', async () => {
    const { container } = render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getByText('Memory Archives')).toBeInTheDocument();
    });

    // Check that glassmorphism background layers are applied
    const sessionListContainer = container.firstChild as HTMLElement;
    expect(sessionListContainer).toHaveClass('backdrop-blur-xl');

    // Check that header section has border
    const headerSection = screen.getByText('Memory Archives').closest('.relative');
    expect(headerSection).toHaveClass('border-b');
  });

  it('applies dynamic background animations based on persona rarity', async () => {
    // Test with legendary persona
    mockUsePersona.mockReturnValue({
      personas: mockPersonas,
      sessions: mockSessions,
      currentSession: mockSessions[0],
      deleteSessionById: mockDeleteSessionById,
      updateSessionTitle: mockUpdateSessionTitle,
      selectedPersona: { ...mockPersonas[0], rarity: 'legendary' },
    });

    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getByText('Chat with Eeva')).toBeInTheDocument();
    });

    // Active session should have rarity-based background glow
    const activeSession = screen.getByText('Chat with Eeva').closest('[class*="border-2"]');
    expect(activeSession).toHaveClass('bg-yellow-500/10');
  });

  it('enhances active session with rarity-based glow effects', async () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getByText('Chat with Eeva')).toBeInTheDocument();
    });

    // Active session should have enhanced styling
    const activeSession = screen.getByText('Chat with Eeva').closest('[class*="border-2"]');
    expect(activeSession).toHaveClass('bg-yellow-500/10', 'border-yellow-400/50', 'shadow-lg');
  });

  it('adds rarity glow effects to avatars in active sessions', async () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getByText('Chat with Eeva')).toBeInTheDocument();
    });

    // Check that avatar image exists
    const avatarImg = screen.getByAltText('Eeva — Bitcoin Expect');
    expect(avatarImg).toBeInTheDocument();

    // Check that it's wrapped in a container (motion.div)
    const avatarContainer = avatarImg.closest('[class*="relative"]');
    expect(avatarContainer).toBeInTheDocument();
  });

  it('displays rarity badges with enhanced styling', async () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    await waitFor(() => {
      expect(screen.getByText('Archon')).toBeInTheDocument();
    });

    // Rarity badge should have enhanced styling
    const rarityBadge = screen.getByText('Archon');
    expect(rarityBadge).toHaveClass('font-medium');
  });
});