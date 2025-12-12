import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SourceIndicator } from './SourceIndicator';
import { ResponseMetadata } from '../services/api';

describe('SourceIndicator', () => {
  describe('when metadata is not provided', () => {
    it('should render nothing', () => {
      const { container } = render(<SourceIndicator />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('when source_type is llm', () => {
    const metadata: ResponseMetadata = {
      source_type: 'llm',
      tools_used: [],
    };

    it('should display Pure LLM Response label', () => {
      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText('Pure LLM Response')).toBeInTheDocument();
    });

    it('should apply purple color class', () => {
      const { container } = render(<SourceIndicator metadata={metadata} />);
      const badge = container.firstChild as HTMLElement;
      expect(badge).toHaveClass('text-purple-400');
    });
  });

  describe('when source_type is brave_mcp', () => {
    const metadata: ResponseMetadata = {
      source_type: 'brave_mcp',
      tools_used: ['brave_web_search'],
    };

    it('should display Web Search label', () => {
      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText('Web Search (Brave MCP)')).toBeInTheDocument();
    });

    it('should apply blue color class', () => {
      const { container } = render(<SourceIndicator metadata={metadata} />);
      const badge = container.firstChild as HTMLElement;
      expect(badge).toHaveClass('text-blue-400');
    });

    it('should display tools used', () => {
      render(<SourceIndicator metadata={metadata} />);
      // Should display "brave web search" in the tools section
      expect(screen.getByText(/• brave web search/i)).toBeInTheDocument();
    });
  });

  describe('when source_type is mongodb_mcp', () => {
    const metadata: ResponseMetadata = {
      source_type: 'mongodb_mcp',
      tools_used: ['bitcoin_current_price'],
      cache_status: 'miss',
      data_timestamp: '2025-12-11 20:00:00',
    };

    it('should display Trading Data label', () => {
      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText('Trading Data (MongoDB MCP)')).toBeInTheDocument();
    });

    it('should apply green color class', () => {
      const { container } = render(<SourceIndicator metadata={metadata} />);
      const badge = container.firstChild as HTMLElement;
      expect(badge).toHaveClass('text-green-400');
    });

    it('should display formatted tool name', () => {
      render(<SourceIndicator metadata={metadata} />);
      // bitcoin_current_price should be formatted as "current price"
      expect(screen.getByText(/current price/i)).toBeInTheDocument();
    });

    it('should display data timestamp', () => {
      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText(/Updated/i)).toBeInTheDocument();
    });
  });

  describe('when source_type is multi_mcp', () => {
    const metadata: ResponseMetadata = {
      source_type: 'multi_mcp',
      tools_used: ['brave_web_search', 'bitcoin_current_price'],
    };

    it('should display Multi-Source Analysis label', () => {
      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText('Multi-Source Analysis')).toBeInTheDocument();
    });

    it('should apply orange color class', () => {
      const { container } = render(<SourceIndicator metadata={metadata} />);
      const badge = container.firstChild as HTMLElement;
      expect(badge).toHaveClass('text-orange-400');
    });

    it('should display multiple tools', () => {
      render(<SourceIndicator metadata={metadata} />);
      const toolsText = screen.getByText(/web search.*current price/i);
      expect(toolsText).toBeInTheDocument();
    });
  });

  describe('cache status indicator', () => {
    it('should display lightning icon when cache_status is hit', () => {
      const metadata: ResponseMetadata = {
        source_type: 'mongodb_mcp',
        tools_used: ['bitcoin_current_price'],
        cache_status: 'hit',
      };

      render(<SourceIndicator metadata={metadata} />);
      // Check for lightning bolt icon by title
      expect(screen.getByTitle('Retrieved from cache')).toBeInTheDocument();
    });

    it('should not display lightning icon when cache_status is miss', () => {
      const metadata: ResponseMetadata = {
        source_type: 'mongodb_mcp',
        tools_used: ['bitcoin_current_price'],
        cache_status: 'miss',
      };

      render(<SourceIndicator metadata={metadata} />);
      expect(screen.queryByTitle('Retrieved from cache')).not.toBeInTheDocument();
    });

    it('should not display lightning icon when cache_status is null', () => {
      const metadata: ResponseMetadata = {
        source_type: 'llm',
        tools_used: [],
        cache_status: null,
      };

      render(<SourceIndicator metadata={metadata} />);
      expect(screen.queryByTitle('Retrieved from cache')).not.toBeInTheDocument();
    });
  });

  describe('relative time formatting', () => {
    beforeAll(() => {
      // Mock Date.now() to return a fixed timestamp
      jest.useFakeTimers();
      jest.setSystemTime(new Date('2025-12-11T20:00:00Z'));
    });

    afterAll(() => {
      jest.useRealTimers();
    });

    it('should format seconds correctly', () => {
      const metadata: ResponseMetadata = {
        source_type: 'mongodb_mcp',
        tools_used: [],
        data_timestamp: '2025-12-11T19:59:45Z', // 15 seconds ago
      };

      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText(/Updated 15s ago/i)).toBeInTheDocument();
    });

    it('should format minutes correctly', () => {
      const metadata: ResponseMetadata = {
        source_type: 'mongodb_mcp',
        tools_used: [],
        data_timestamp: '2025-12-11T19:55:00Z', // 5 minutes ago
      };

      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText(/Updated 5m ago/i)).toBeInTheDocument();
    });

    it('should format hours correctly', () => {
      const metadata: ResponseMetadata = {
        source_type: 'mongodb_mcp',
        tools_used: [],
        data_timestamp: '2025-12-11T18:00:00Z', // 2 hours ago
      };

      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText(/Updated 2h ago/i)).toBeInTheDocument();
    });

    it('should format days correctly', () => {
      const metadata: ResponseMetadata = {
        source_type: 'mongodb_mcp',
        tools_used: [],
        data_timestamp: '2025-12-09T20:00:00Z', // 2 days ago
      };

      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText(/Updated 2d ago/i)).toBeInTheDocument();
    });

    it('should handle invalid timestamp gracefully', () => {
      const metadata: ResponseMetadata = {
        source_type: 'mongodb_mcp',
        tools_used: [],
        data_timestamp: 'invalid-timestamp',
      };

      render(<SourceIndicator metadata={metadata} />);
      // Should not crash, and should not display timestamp
      expect(screen.queryByText(/Updated/i)).not.toBeInTheDocument();
    });
  });

  describe('tool name formatting', () => {
    it('should format bitcoin_current_price', () => {
      const metadata: ResponseMetadata = {
        source_type: 'mongodb_mcp',
        tools_used: ['bitcoin_current_price'],
      };

      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText(/current price/i)).toBeInTheDocument();
    });

    it('should format bitcoin_historical_prices', () => {
      const metadata: ResponseMetadata = {
        source_type: 'mongodb_mcp',
        tools_used: ['bitcoin_historical_prices'],
      };

      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText(/historical prices/i)).toBeInTheDocument();
    });

    it('should format bitcoin_trading_summary', () => {
      const metadata: ResponseMetadata = {
        source_type: 'mongodb_mcp',
        tools_used: ['bitcoin_trading_summary'],
      };

      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText(/trading summary/i)).toBeInTheDocument();
    });

    it('should format bitcoin_technical_analysis', () => {
      const metadata: ResponseMetadata = {
        source_type: 'mongodb_mcp',
        tools_used: ['bitcoin_technical_analysis'],
      };

      render(<SourceIndicator metadata={metadata} />);
      expect(screen.getByText(/technical analysis/i)).toBeInTheDocument();
    });
  });

  describe('className prop', () => {
    it('should apply custom className', () => {
      const metadata: ResponseMetadata = {
        source_type: 'llm',
        tools_used: [],
      };

      const { container } = render(<SourceIndicator metadata={metadata} className="custom-class" />);
      const badge = container.firstChild as HTMLElement;
      expect(badge).toHaveClass('custom-class');
    });
  });
});
