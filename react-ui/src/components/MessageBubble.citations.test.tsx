import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MessageBubble, Message } from './MessageBubble';

describe('MessageBubble - Citation Rendering', () => {
  const baseMessage: Message = {
    id: 'test-1',
    role: 'assistant',
    content: 'Test content',
    timestamp: new Date(),
  };

  describe('Citation Section Parsing', () => {
    it('renders citations separately from main content', () => {
      const messageWithCitations: Message = {
        ...baseMessage,
        content: `Bitcoin is trading at $91,735.99.

🔍 Sources:
• [Bitcoin Price - CoinMarketCap](https://coinmarketcap.com/)
• [BTC Data - Yahoo](https://finance.yahoo.com/)`,
        used_search: true,
        search_results_count: 2
      };

      const { container } = render(<MessageBubble message={messageWithCitations} />);
      
      // Should have main content
      expect(screen.getByText(/Bitcoin is trading at/)).toBeInTheDocument();
      
      // Should have separated citation section
      expect(screen.getByText(/🔍 Sources:/)).toBeInTheDocument();
    });

    it('handles citations without emoji', () => {
      const message: Message = {
        ...baseMessage,
        content: `Bitcoin info.

**Sources:**
• [Source 1](https://example.com/)`,
        used_search: true
      };

      render(<MessageBubble message={message} />);
      
      expect(screen.getByText(/Bitcoin info/)).toBeInTheDocument();
      expect(screen.getByText(/Sources:/)).toBeInTheDocument();
    });
  });

  describe('Search Badge Display', () => {
    it('shows search badge when used_search is true', () => {
      const message: Message = {
        ...baseMessage,
        used_search: true,
        search_results_count: 5
      };

      render(<MessageBubble message={message} />);
      
      expect(screen.getByText(/Web-enhanced answer/)).toBeInTheDocument();
      expect(screen.getByText(/5 sources/)).toBeInTheDocument();
    });

    it('does not show search badge when used_search is false', () => {
      const message: Message = {
        ...baseMessage,
        used_search: false
      };

      render(<MessageBubble message={message} />);
      
      expect(screen.queryByText(/Web-enhanced answer/)).not.toBeInTheDocument();
    });

    it('handles singular source count', () => {
      const message: Message = {
        ...baseMessage,
        used_search: true,
        search_results_count: 1
      };

      render(<MessageBubble message={message} />);
      
      expect(screen.getByText(/1 source/)).toBeInTheDocument();
      expect(screen.queryByText(/sources/)).not.toBeInTheDocument();
    });
  });

  describe('Citation Validation Warning', () => {
    it('shows warning when citations are missing', () => {
      const message: Message = {
        ...baseMessage,
        content: 'Bitcoin is around $91,000.',
        used_search: true,
        citation_valid: false,
        search_results_count: 5
      };

      render(<MessageBubble message={message} />);
      
      expect(screen.getByText(/This response used web search but citations were not included/)).toBeInTheDocument();
    });

    it('does not show warning when citations are valid', () => {
      const message: Message = {
        ...baseMessage,
        content: `Bitcoin is $91k.

🔍 Sources:
• [Source](https://example.com/)`,
        used_search: true,
        citation_valid: true
      };

      render(<MessageBubble message={message} />);
      
      expect(screen.queryByText(/citations were not included/)).not.toBeInTheDocument();
    });

    it('does not show warning when no search was used', () => {
      const message: Message = {
        ...baseMessage,
        content: 'Regular answer',
        used_search: false,
        citation_valid: undefined
      };

      render(<MessageBubble message={message} />);
      
      expect(screen.queryByText(/citations were not included/)).not.toBeInTheDocument();
    });
  });

  describe('User Messages', () => {
    it('does not show search-related features for user messages', () => {
      const message: Message = {
        ...baseMessage,
        role: 'user',
        content: 'What is the price?',
        used_search: true
      };

      render(<MessageBubble message={message} />);
      
      expect(screen.queryByText(/Web-enhanced answer/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Sources:/)).not.toBeInTheDocument();
    });
  });
});
