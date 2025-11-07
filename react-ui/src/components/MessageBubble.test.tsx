import React from 'react';
import { render, screen } from '@testing-library/react';
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
});