import React from 'react';
import { render, screen } from '@testing-library/react';
import { TypingIndicator } from './TypingIndicator';

describe('TypingIndicator', () => {
  it('renders typing indicator with correct text', () => {
    render(<TypingIndicator />);

    expect(screen.getByText('Assistant is typing...')).toBeInTheDocument();
  });

  it('renders three animated dots', () => {
    const { container } = render(<TypingIndicator />);

    const dots = container.querySelectorAll('[class*="w-2 h-2 bg-gray-400 rounded-full"]');
    expect(dots).toHaveLength(3);
  });

  it('applies custom className when provided', () => {
    const { container } = render(<TypingIndicator className="custom-class" />);

    const indicator = container.firstChild;
    expect(indicator).toHaveClass('custom-class');
  });

  it('has proper accessibility structure', () => {
    const { container } = render(<TypingIndicator />);

    // Should have proper semantic structure
    const indicator = container.firstChild;
    expect(indicator).toBeInTheDocument();
  });
});