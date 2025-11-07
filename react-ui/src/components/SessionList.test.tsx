import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatSession } from '../services/api';
import SessionList from './SessionList';

// Mock the usePersona hook
const mockUsePersona = jest.fn();
jest.mock('../context/PersonaContext', () => ({
  usePersona: () => mockUsePersona(),
}));

describe('SessionList', () => {
  const mockSessions: ChatSession[] = [
    {
      id: '1',
      persona_key: 'eeva',
      title: 'Chat with Eeva',
      created_at: '2024-01-01T10:00:00Z',
      updated_at: '2024-01-01T10:30:00Z',
      message_count: 5,
    },
    {
      id: '2',
      persona_key: 'frieren',
      title: 'Chat with Frieren',
      created_at: '2024-01-02T10:00:00Z',
      updated_at: '2024-01-02T11:00:00Z',
      message_count: 10,
    },
  ];

  const mockOnSessionSelect = jest.fn();
  const mockDeleteSessionById = jest.fn();
  const mockUpdateSessionTitle = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockUsePersona.mockReturnValue({
      sessions: mockSessions,
      currentSession: mockSessions[0],
      deleteSessionById: mockDeleteSessionById,
      updateSessionTitle: mockUpdateSessionTitle,
    });

    // Mock window.confirm
    window.confirm = jest.fn();
  });

  it('renders session list correctly', () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    expect(screen.getByText('Chat History')).toBeInTheDocument();
    expect(screen.getByText('Chat with Eeva')).toBeInTheDocument();
    expect(screen.getByText('Chat with Frieren')).toBeInTheDocument();
    expect(screen.getByText(/5 messages/)).toBeInTheDocument();
    expect(screen.getByText(/10 messages/)).toBeInTheDocument();
  });

  it('shows empty state when no sessions', () => {
    mockUsePersona.mockReturnValue({
      sessions: [],
      currentSession: null,
      deleteSessionById: mockDeleteSessionById,
      updateSessionTitle: mockUpdateSessionTitle,
    });

    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    expect(screen.getByText('No chat sessions yet. Start a conversation!')).toBeInTheDocument();
  });

  it('highlights current session', () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    const currentSessionElement = screen.getByText('Chat with Eeva').closest('[class*="bg-blue-50"]');
    expect(currentSessionElement).toBeInTheDocument();
  });

  it('calls onSessionSelect when session is clicked', () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    const frierenSession = screen.getByText('Chat with Frieren');
    fireEvent.click(frierenSession);

    expect(mockOnSessionSelect).toHaveBeenCalledWith(mockSessions[1]);
  });

  it('enters edit mode when rename button is clicked', () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    const renameButton = screen.getAllByTitle('Rename')[0];
    fireEvent.click(renameButton);

    const input = screen.getByDisplayValue('Chat with Eeva');
    expect(input).toBeInTheDocument();
  });

  it('saves title when Save button is clicked', () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    const renameButton = screen.getAllByTitle('Rename')[0];
    fireEvent.click(renameButton);

    const input = screen.getByDisplayValue('Chat with Eeva');
    fireEvent.change(input, { target: { value: 'New Title' } });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    expect(mockUpdateSessionTitle).toHaveBeenCalledWith('1', 'New Title');
  });

  it('cancels edit when Cancel button is clicked', () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    const renameButton = screen.getAllByTitle('Rename')[0];
    fireEvent.click(renameButton);

    const input = screen.getByDisplayValue('Chat with Eeva');
    fireEvent.change(input, { target: { value: 'New Title' } });

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(mockUpdateSessionTitle).not.toHaveBeenCalled();
    expect(screen.queryByDisplayValue('New Title')).not.toBeInTheDocument();
  });

  it('deletes session when delete button is clicked and confirmed', () => {
    (window.confirm as jest.Mock).mockReturnValue(true);

    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    const deleteButton = screen.getAllByTitle('Delete')[0];
    fireEvent.click(deleteButton);

    expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to delete this chat session?');
    expect(mockDeleteSessionById).toHaveBeenCalledWith('1');
  });

  it('does not delete session when delete is cancelled', () => {
    (window.confirm as jest.Mock).mockReturnValue(false);

    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    const deleteButton = screen.getAllByTitle('Delete')[0];
    fireEvent.click(deleteButton);

    expect(mockDeleteSessionById).not.toHaveBeenCalled();
  });

  it('prevents session selection when clicking edit controls', () => {
    render(<SessionList onSessionSelect={mockOnSessionSelect} />);

    const renameButton = screen.getAllByTitle('Rename')[0];
    fireEvent.click(renameButton);

    expect(mockOnSessionSelect).not.toHaveBeenCalled();
  });
});