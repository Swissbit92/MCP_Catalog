import React from 'react';
import { render, screen } from '@testing-library/react';
import ChatMessage from './ChatMessage';

test('renders user message correctly', () => {
  const message = 'Hello, I am a user.';
  render(<ChatMessage message={message} isUser={true} />);
  const messageElement = screen.getByText(message);
  expect(messageElement).toBeInTheDocument();
  expect(messageElement.parentElement).toHaveStyle('justify-content: flex-end');
});

test('renders non-user message correctly', () => {
  const message = 'Hello, I am an AI.';
  render(<ChatMessage message={message} isUser={false} />);
  const messageElement = screen.getByText(message);
  expect(messageElement).toBeInTheDocument();
  expect(messageElement.parentElement).toHaveStyle('justify-content: flex-start');
});
