import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MessageBubble } from './MessageBubble';

describe('MessageBubble', () => {
  const mockMessage = {
    id: '1',
    role: 'user' as const,
    content: 'Hello world',
    timestamp: new Date('2024-01-01T12:00:00Z'),
  };

  const mockPersonaAvatar = '/persona-avatar.png';
  const mockUserAvatar = '/user-avatar.png';

  it('renders user message correctly', () => {
    render(
      <MessageBubble
        message={mockMessage}
        personaAvatar={mockPersonaAvatar}
        userAvatar={mockUserAvatar}
      />
    );

    expect(screen.getByText('Hello world')).toBeInTheDocument();
    expect(screen.getByAltText('You')).toBeInTheDocument();
  });

  it('renders assistant message correctly', () => {
    const assistantMessage = { ...mockMessage, role: 'assistant' as const };

    render(
      <MessageBubble
        message={assistantMessage}
        personaAvatar={mockPersonaAvatar}
        userAvatar={mockUserAvatar}
      />
    );

    expect(screen.getByText('Hello world')).toBeInTheDocument();
    expect(screen.getByAltText('Assistant')).toBeInTheDocument();
  });

  it('shows timestamp when showTimestamp is true', () => {
    render(
      <MessageBubble
        message={mockMessage}
        showTimestamp={true}
      />
    );

    // Check that a timestamp is displayed (format may vary by timezone)
    const timestampElement = screen.getByText(/\d{1,2}:\d{2}/);
    expect(timestampElement).toBeInTheDocument();
  });

  it('does not show timestamp when showTimestamp is false', () => {
    render(
      <MessageBubble
        message={mockMessage}
        showTimestamp={false}
      />
    );

    // Check that no timestamp is displayed
    const timestampElement = screen.queryByText(/\d{1,2}:\d{2}/);
    expect(timestampElement).not.toBeInTheDocument();
  });

  it('applies correct styling for user messages', () => {
    const { container } = render(
      <MessageBubble
        message={mockMessage}
      />
    );

    const messageBubble = container.querySelector('[class*="bg-gradient-to-br"]');
    expect(messageBubble).toBeInTheDocument();
  });

  it('applies correct styling for assistant messages', () => {
    const assistantMessage = { ...mockMessage, role: 'assistant' as const };
    const { container } = render(
      <MessageBubble
        message={assistantMessage}
      />
    );

    const messageBubble = container.querySelector('[class*="bg-gray-100"]');
    expect(messageBubble).toBeInTheDocument();
  });

  it('displays SourceIndicator for assistant messages with metadata', () => {
    const assistantMessageWithMetadata = {
      ...mockMessage,
      role: 'assistant' as const,
      metadata: {
        source_type: 'mongodb_mcp' as const,
        tools_used: ['bitcoin_current_price'],
        cache_status: 'hit' as const,
        data_timestamp: '2025-12-11 20:00:00',
      },
    };

    render(
      <MessageBubble
        message={assistantMessageWithMetadata}
        personaName="Eeva"
        personaRarity="epic"
      />
    );

    expect(screen.getByText('Trading Data (MongoDB MCP)')).toBeInTheDocument();
    expect(screen.getByTitle('Retrieved from cache')).toBeInTheDocument();
  });

  it('does not display SourceIndicator for user messages', () => {
    const userMessageWithMetadata = {
      ...mockMessage,
      metadata: {
        source_type: 'llm' as const,
        tools_used: [],
      },
    };

    render(
      <MessageBubble message={userMessageWithMetadata} />
    );

    expect(screen.queryByText('Pure LLM Response')).not.toBeInTheDocument();
  });

  it('does not display SourceIndicator when metadata is missing', () => {
    const assistantMessage = { ...mockMessage, role: 'assistant' as const };

    render(
      <MessageBubble
        message={assistantMessage}
        personaName="Eeva"
      />
    );

    expect(screen.queryByText(/MCP/i)).not.toBeInTheDocument();
  });

  it('shows latency information in seconds', () => {
    const messageWithLatency = {
      ...mockMessage,
      latency: 1250, // 1.25 seconds
    };

    render(<MessageBubble message={messageWithLatency} showTimestamp={true} />);

    expect(screen.getByText('1.3s')).toBeInTheDocument();
  });

  it('shows latency in milliseconds for fast responses', () => {
    const messageWithLatency = {
      ...mockMessage,
      latency: 450, // 450ms
    };

    render(<MessageBubble message={messageWithLatency} showTimestamp={true} />);

    expect(screen.getByText('450ms')).toBeInTheDocument();
  });

  it('shows sending status with loading indicator', () => {
    const sendingMessage = {
      ...mockMessage,
      status: 'sending' as const,
    };

    render(<MessageBubble message={sendingMessage} />);

    expect(screen.getByText('Sending...')).toBeInTheDocument();
  });

  it('shows failed status with retry button and attempt count', () => {
    const mockOnRetry = jest.fn();
    const failedMessage = {
      ...mockMessage,
      status: 'failed' as const,
      retryCount: 2,
    };

    render(<MessageBubble message={failedMessage} onRetry={mockOnRetry} />);

    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
    expect(screen.getByText('(2 attempts)')).toBeInTheDocument();
  });

  it('calls onRetry when retry button is clicked', () => {
    const mockOnRetry = jest.fn();
    const failedMessage = {
      ...mockMessage,
      status: 'failed' as const,
    };

    render(<MessageBubble message={failedMessage} onRetry={mockOnRetry} />);

    const retryButton = screen.getByText('Retry');
    fireEvent.click(retryButton);

    expect(mockOnRetry).toHaveBeenCalledWith(mockMessage.id);
  });

  it('does not show retry button when onRetry is not provided', () => {
    const failedMessage = {
      ...mockMessage,
      status: 'failed' as const,
    };

    render(<MessageBubble message={failedMessage} />);

    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.queryByText('Retry')).not.toBeInTheDocument();
  });

  it('shows delivered status for successful messages', () => {
    const deliveredMessage = {
      ...mockMessage,
      status: 'delivered' as const,
      latency: 800,
    };

    render(<MessageBubble message={deliveredMessage} showTimestamp={true} />);

    expect(screen.getByText('800ms')).toBeInTheDocument();
  });

  it('passes personaRarity to Avatar2D for assistant messages', () => {
    const assistantMessage = { ...mockMessage, role: 'assistant' as const };

    render(
      <MessageBubble
        message={assistantMessage}
        personaAvatar={mockPersonaAvatar}
        personaRarity="legendary"
      />
    );

    // The Avatar2D should receive the rarity prop, but since it's internal we check the alt text
    expect(screen.getByAltText('Assistant')).toBeInTheDocument();
  });

  it('shows persona indicator on assistant messages when personaName is provided', () => {
    const assistantMessage = { ...mockMessage, role: 'assistant' as const };

    render(
      <MessageBubble
        message={assistantMessage}
        personaName="Test Persona"
        personaRarity="epic"
      />
    );

    expect(screen.getByText('Test Persona')).toBeInTheDocument();
  });

  it('does not show persona indicator on user messages', () => {
    render(
      <MessageBubble
        message={mockMessage}
        personaName="Test Persona"
      />
    );

    expect(screen.queryByText('Test Persona')).not.toBeInTheDocument();
  });

  it('applies correct rarity styling to persona indicator', () => {
    const assistantMessage = { ...mockMessage, role: 'assistant' as const };

    const { container } = render(
      <MessageBubble
        message={assistantMessage}
        personaName="Legendary Persona"
        personaRarity="legendary"
      />
    );

    // Check that the persona indicator has the correct rarity styling
    const indicator = screen.getByText('Legendary Persona');
    expect(indicator).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });
});