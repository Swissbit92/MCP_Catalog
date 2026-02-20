import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { PersonaProvider, usePersona } from './PersonaContext';

// Mock all API functions
jest.mock('../services/api', () => ({
  fetchPersonas: jest.fn().mockResolvedValue([]),
  fetchSessions: jest.fn(),
  createSession: jest.fn(),
  getSessionWithMessages: jest.fn(),
  updateSession: jest.fn(),
  deleteSession: jest.fn(),
  sendMessageToSession: jest.fn(),
  exportSession: jest.fn(),
  importSession: jest.fn(),
  clearSessionMessages: jest.fn(),
}));

const mockApi = require('../services/api');

// Test component to access context
const TestComponent: React.FC = () => {
  const {
    sendMessage,
    retryMessage,
    messages,
    currentSession,
  } = usePersona();

  return (
    <div>
      <div data-testid="messages-count">{messages.length}</div>
      <div data-testid="current-session">{currentSession?.id || 'no-session'}</div>
      <button
        data-testid="send-button"
        onClick={() => sendMessage('test message')}
      >
        Send
      </button>
      <button
        data-testid="retry-button"
        onClick={() => retryMessage('failed-msg-id')}
      >
        Retry
      </button>
    </div>
  );
};

describe('PersonaContext', () => {
  const mockSession = {
    id: 'session1',
    persona_key: 'eeva',
    title: 'Chat with Eeva',
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:30:00Z',
    message_count: 0,
  };

  const mockAssistantMessage = {
    id: 'assistant-1',
    role: 'assistant',
    content: 'Hello from assistant',
    timestamp: new Date(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Re-apply fetchPersonas mock after clearAllMocks wipes the factory's mockResolvedValue
    mockApi.fetchPersonas.mockResolvedValue([]);
    mockApi.fetchSessions.mockResolvedValue([mockSession]);
    mockApi.sendMessageToSession.mockResolvedValue(mockAssistantMessage);
  });

  it('loads sessions on mount', async () => {
    render(
      <PersonaProvider>
        <TestComponent />
      </PersonaProvider>
    );

    await waitFor(() => {
      expect(mockApi.fetchSessions).toHaveBeenCalled();
    });

    expect(screen.getByTestId('current-session')).toHaveTextContent('no-session');
  });

  it('provides context methods to children', () => {
    render(
      <PersonaProvider>
        <TestComponent />
      </PersonaProvider>
    );

    expect(screen.getByTestId('send-button')).toBeInTheDocument();
    expect(screen.getByTestId('retry-button')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    mockApi.fetchSessions.mockRejectedValue(new Error('API Error'));

    // Mock console.error to avoid test output pollution
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <PersonaProvider>
        <TestComponent />
      </PersonaProvider>
    );

    // Should not crash despite API error
    expect(screen.getByTestId('send-button')).toBeInTheDocument();

    consoleSpy.mockRestore();
  });
});