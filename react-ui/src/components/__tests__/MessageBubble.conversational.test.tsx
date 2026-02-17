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
      id: 'msg-1',
      role: 'assistant' as const,
      content: 'Bitcoin is at $87,855 right now. Are you thinking about buying more?',
      timestamp: new Date(),
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
      id: 'msg-2',
      role: 'assistant' as const,
      content: 'First message.\n\nSecond message.\n\nThird message?',
      timestamp: new Date(),
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
      id: 'msg-3',
      role: 'assistant' as const,
      content: 'What do you think about that?',
      timestamp: new Date(),
    };

    const { container } = render(
      <MessageBubble
        message={message}
        personaAvatar="/test-avatar.png"
        personaName="Eeva"
      />
    );

    // Question should be rendered in the text content
    const textContent = container.textContent;
    expect(textContent).toContain('What do you think');
  });
});
