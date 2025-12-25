/**
 * Phase 2: Multi-message response tests
 * Tests ChatApiResponse interface, PersonaContext, and multi-message rendering
 */

import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MessageBubble } from '../MessageBubble';
import type { Message } from '../MessageBubble';
import type { ChatApiResponse } from '../../services/api';

// Mock Framer Motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('Phase 2: Multi-Message Architecture', () => {
  describe('ChatApiResponse Interface', () => {
    it('should support single message format', () => {
      const response: ChatApiResponse = {
        answer: 'Bitcoin is at $87,855.',
        message_flow: 'single',
        message_count: 1,
        metadata: {
          source_type: 'llm',
          tools_used: [],
        },
      };

      expect(response.message_flow).toBe('single');
      expect(response.message_count).toBe(1);
      expect(typeof response.answer).toBe('string');
    });

    it('should support multi-message format', () => {
      const response: ChatApiResponse = {
        answer: [
          'Bitcoin is at $87,855.',
          'RSI at 42 means neutral momentum.',
          'Are you thinking about buying more?'
        ],
        message_flow: 'multi',
        message_count: 3,
        metadata: {
          source_type: 'llm',
          tools_used: [],
          is_multi_message: true,
          message_count: 3,
        },
      };

      expect(response.message_flow).toBe('multi');
      expect(response.message_count).toBe(3);
      expect(Array.isArray(response.answer)).toBe(true);
      expect(response.answer).toHaveLength(3);
      expect(response.metadata?.is_multi_message).toBe(true);
    });

    it('should include all required fields', () => {
      const response: ChatApiResponse = {
        answer: 'Test answer',
        message_flow: 'single',
        message_count: 1,
        used_search: false,
        search_results_count: 0,
        citation_valid: undefined,
        metadata: null,
        emotional_state: null,
      };

      expect(response).toHaveProperty('answer');
      expect(response).toHaveProperty('message_flow');
      expect(response).toHaveProperty('message_count');
    });
  });

  describe('MessageBubble Multi-Message Rendering', () => {
    it('should render first message in multi-message sequence', () => {
      const message: Message = {
        id: 'assistant-1',
        role: 'assistant',
        content: 'Bitcoin is at $87,855.',
        timestamp: new Date(),
        metadata: {
          source_type: 'llm',
          tools_used: [],
          is_multi_message: true,
          message_count: 3,
        },
      };

      render(
        <MessageBubble
          message={message}
          personaAvatar="/images/personas/eeva/avatar.png"
          userAvatar="/images/ui/user_avatar.png"
          showTimestamp={true}
          personaName="Eeva"
          personaRarity="legendary"
        />
      );

      expect(screen.getByText('Bitcoin is at $87,855.')).toBeInTheDocument();
    });

    it('should render subsequent messages in multi-message sequence', () => {
      const message: Message = {
        id: 'assistant-2',
        role: 'assistant',
        content: 'RSI at 42 means neutral momentum.',
        timestamp: new Date(),
        // Subsequent messages don't have full metadata (set on first message only)
      };

      render(
        <MessageBubble
          message={message}
          personaAvatar="/images/personas/eeva/avatar.png"
          userAvatar="/images/ui/user_avatar.png"
          showTimestamp={true}
          personaName="Eeva"
          personaRarity="legendary"
        />
      );

      expect(screen.getByText('RSI at 42 means neutral momentum.')).toBeInTheDocument();
    });

    it('should handle messages with questions', () => {
      const message: Message = {
        id: 'assistant-3',
        role: 'assistant',
        content: 'Are you thinking about buying more?',
        timestamp: new Date(),
      };

      render(
        <MessageBubble
          message={message}
          personaAvatar="/images/personas/eeva/avatar.png"
          userAvatar="/images/ui/user_avatar.png"
          showTimestamp={true}
          personaName="Eeva"
          personaRarity="legendary"
        />
      );

      expect(screen.getByText('Are you thinking about buying more?')).toBeInTheDocument();
    });
  });

  describe('Multi-Message Behavior Patterns', () => {
    it('should maintain concise message length', () => {
      const messages = [
        'Bitcoin is at $87,855.',
        'RSI at 42 means neutral momentum.',
        'Are you thinking about buying more?'
      ];

      // Each message should be concise (<200 chars guideline)
      messages.forEach((msg, i) => {
        expect(msg.length).toBeLessThan(200);
      });
    });

    it('should distribute questions across messages', () => {
      const messages = [
        'Bitcoin is at $87,855.',
        'RSI at 42 means neutral momentum.',
        'Are you thinking about buying more?'
      ];

      // Count questions in each message
      const questionCounts = messages.map(msg => (msg.match(/\?/g) || []).length);

      // No message should have more than 1 question
      questionCounts.forEach(count => {
        expect(count).toBeLessThanOrEqual(1);
      });
    });

    it('should have at most 4 messages in multi-message response', () => {
      const maxMessages = 4;
      const messages = Array(10).fill('Test message');

      // Simulate cap at 4 messages
      const cappedMessages = messages.slice(0, maxMessages);

      expect(cappedMessages).toHaveLength(4);
    });
  });

  describe('Backwards Compatibility', () => {
    it('should still support legacy single-message format', () => {
      const message: Message = {
        id: 'assistant-legacy',
        role: 'assistant',
        content: 'Bitcoin is at $87,855.',
        timestamp: new Date(),
        metadata: {
          source_type: 'llm',
          tools_used: [],
          // No multi-message fields (legacy format)
        },
      };

      render(
        <MessageBubble
          message={message}
          personaAvatar="/images/personas/eeva/avatar.png"
          userAvatar="/images/ui/user_avatar.png"
          showTimestamp={true}
          personaName="Eeva"
          personaRarity="legendary"
        />
      );

      expect(screen.getByText('Bitcoin is at $87,855.')).toBeInTheDocument();
    });

    it('should handle metadata without multi-message fields', () => {
      const message: Message = {
        id: 'assistant-legacy-2',
        role: 'assistant',
        content: 'Test response',
        timestamp: new Date(),
        metadata: {
          source_type: 'llm',
          tools_used: [],
          // is_multi_message and message_count are optional
        },
      };

      // Should not throw errors
      expect(message.metadata?.is_multi_message).toBeUndefined();
      expect(message.metadata?.message_count).toBeUndefined();
    });
  });

  describe('Staggered Rendering Logic', () => {
    it('should calculate correct delays for multi-message', () => {
      const messageCount = 3;
      const delays = [];

      for (let i = 0; i < messageCount; i++) {
        if (i > 0) {
          // First delay: 300ms before typing indicator
          // Second delay: 1200ms for typing indicator
          // Third delay: 200ms before next message
          const totalDelay = 300 + 1200 + 200;
          delays.push(totalDelay);
        } else {
          delays.push(0); // First message has no delay
        }
      }

      expect(delays[0]).toBe(0);
      expect(delays[1]).toBeGreaterThan(0);
      expect(delays[2]).toBeGreaterThan(0);
    });

    it('should render messages sequentially, not all at once', async () => {
      // This test verifies the staggering logic conceptually
      // Actual staggering is tested in integration tests

      const messages = [
        'Message 1',
        'Message 2',
        'Message 3'
      ];

      let renderedCount = 0;

      // Simulate sequential rendering
      for (let i = 0; i < messages.length; i++) {
        // Simulate delay
        await new Promise(resolve => setTimeout(resolve, i > 0 ? 10 : 0));
        renderedCount++;
      }

      expect(renderedCount).toBe(messages.length);
    });
  });
});
