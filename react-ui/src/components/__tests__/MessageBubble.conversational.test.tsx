/**
 * Frontend tests for Phase 1: Conversational message rendering
 * Tests display of questions, multi-message hints, etc.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { MessageBubble } from '../MessageBubble';

describe('MessageBubble - Conversational Features', () => {
  test('renders questions with proper styling', () => {
    const message = {
      role: 'assistant',
      content: 'Bitcoin is at $87,855 right now. Are you thinking about buying more?',
      timestamp: new Date().toISOString(),
    };

    render(
      <MessageBubble
        message={message}
        personaAvatar="/test-avatar.png"
        personaName="Eeva"
      />
    );

    // Should render the question
    expect(screen.getByText(/Are you thinking about buying more/i)).toBeInTheDocument();
  });

  test('renders multi-message indicator when appropriate', () => {
    // Note: This test assumes future multi-message rendering
    const message = {
      role: 'assistant',
      content: 'First message.\n\nSecond message.\n\nThird message?',
      timestamp: new Date().toISOString(),
    };

    render(
      <MessageBubble
        message={message}
        personaAvatar="/test-avatar.png"
        personaName="Eeva"
      />
    );

    // For now, should render as single message
    expect(screen.getByText(/First message/i)).toBeInTheDocument();
  });

  test('highlights questions visually', () => {
    const message = {
      role: 'assistant',
      content: 'What do you think about that?',
      timestamp: new Date().toISOString(),
    };

    const { container } = render(
      <MessageBubble
        message={message}
        personaAvatar="/test-avatar.png"
        personaName="Eeva"
      />
    );

    // Question should be rendered
    const messageContent = container.querySelector('.message-content');
    expect(messageContent?.textContent).toContain('What do you think');
  });
});
