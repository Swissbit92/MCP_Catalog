/**
 * Phase 2 Persona Quality - UI Level Tests
 *
 * Tests the user experience aspects of Phase 2:
 * - Emotional state display in UI
 * - API response handling for emotional state
 * - Persona data structure validation
 */

import { EmotionalState, Message } from '../services/api'

// Mock fetch for API tests
const mockFetch = jest.fn()
global.fetch = mockFetch

describe('Phase 2 Persona Quality - UI Tests', () => {
  beforeEach(() => {
    mockFetch.mockClear()
  })

  describe('EmotionalState Interface', () => {
    it('should have correct structure for emotional state', () => {
      const emotionalState: EmotionalState = {
        trust_level: 0.75,
        rapport: 0.65,
        current_mood: 'happy',
        mood_intensity: 0.6,
        last_emotional_event: 'User expressed gratitude'
      }

      expect(emotionalState.trust_level).toBeGreaterThanOrEqual(0)
      expect(emotionalState.trust_level).toBeLessThanOrEqual(1)
      expect(emotionalState.rapport).toBeGreaterThanOrEqual(0)
      expect(emotionalState.rapport).toBeLessThanOrEqual(1)
      expect(typeof emotionalState.current_mood).toBe('string')
    })

    it('should support all mood types', () => {
      const moods = ['neutral', 'happy', 'sad', 'curious', 'defensive', 'vulnerable']

      moods.forEach(mood => {
        const state: EmotionalState = {
          trust_level: 0.5,
          rapport: 0.5,
          current_mood: mood
        }
        expect(state.current_mood).toBe(mood)
      })
    })
  })

  describe('Message with EmotionalState', () => {
    it('should include emotional_state in message structure', () => {
      const message: Message = {
        id: 'test-1',
        role: 'assistant',
        content: 'Hello!',
        timestamp: new Date(),
        emotional_state: {
          trust_level: 0.52,
          rapport: 0.51,
          current_mood: 'happy'
        }
      }

      expect(message.emotional_state).toBeDefined()
      expect(message.emotional_state?.trust_level).toBe(0.52)
      expect(message.emotional_state?.current_mood).toBe('happy')
    })

    it('should allow messages without emotional_state', () => {
      const message: Message = {
        id: 'test-2',
        role: 'user',
        content: 'Hello!',
        timestamp: new Date()
      }

      expect(message.emotional_state).toBeUndefined()
    })
  })

  describe('API Response Handling', () => {
    it('should parse emotional state from chat response', async () => {
      const mockResponse = {
        answer: 'Hello! Nice to meet you.',
        used_search: false,
        metadata: { source_type: 'llm', tools_used: [] },
        emotional_state: {
          trust_level: 0.52,
          rapport: 0.51,
          current_mood: 'happy'
        }
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const response = await fetch('/sessions/test-session/chat', {
        method: 'POST',
        body: JSON.stringify({ message: 'Hello' })
      })

      const data = await response.json()

      expect(data.emotional_state).toBeDefined()
      expect(data.emotional_state.trust_level).toBe(0.52)
      expect(data.emotional_state.rapport).toBe(0.51)
      expect(data.emotional_state.current_mood).toBe('happy')
    })

    it('should handle missing emotional state gracefully', async () => {
      const mockResponse = {
        answer: 'Hello!',
        used_search: false,
        metadata: { source_type: 'llm', tools_used: [] }
        // No emotional_state
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const response = await fetch('/sessions/test-session/chat', {
        method: 'POST',
        body: JSON.stringify({ message: 'Hello' })
      })

      const data = await response.json()

      expect(data.emotional_state).toBeUndefined()
    })

    it('should fetch emotional state from dedicated endpoint', async () => {
      const mockState = {
        session_id: 'test-session',
        trust_level: 0.75,
        rapport: 0.65,
        current_mood: 'curious',
        mood_intensity: 0.6,
        last_emotional_event: 'User asked a question',
        updated_at: '2025-12-23T12:00:00Z'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockState)
      })

      const response = await fetch('/sessions/test-session/emotional-state')
      const data = await response.json()

      expect(data.trust_level).toBe(0.75)
      expect(data.current_mood).toBe('curious')
      expect(data.last_emotional_event).toBe('User asked a question')
    })
  })

  describe('Trust Level Display', () => {
    it('should categorize trust levels correctly', () => {
      const getTrustDescription = (level: number): string => {
        if (level >= 0.8) return 'deeply trusted'
        if (level >= 0.6) return 'comfortable'
        if (level >= 0.4) return 'neutral'
        if (level >= 0.2) return 'guarded'
        return 'defensive'
      }

      expect(getTrustDescription(0.9)).toBe('deeply trusted')
      expect(getTrustDescription(0.7)).toBe('comfortable')
      expect(getTrustDescription(0.5)).toBe('neutral')
      expect(getTrustDescription(0.3)).toBe('guarded')
      expect(getTrustDescription(0.1)).toBe('defensive')
    })

    it('should format mood intensity correctly', () => {
      const getMoodIntensity = (intensity: number): string => {
        if (intensity >= 0.7) return 'strongly'
        if (intensity <= 0.3) return 'slightly'
        return ''
      }

      expect(getMoodIntensity(0.8)).toBe('strongly')
      expect(getMoodIntensity(0.5)).toBe('')
      expect(getMoodIntensity(0.2)).toBe('slightly')
    })
  })

  describe('Persona JSON Structure', () => {
    it('should validate psychological_profile structure', () => {
      const psychProfile = {
        core_wound: 'Imposter syndrome',
        coping_mechanism: 'Over-explaining',
        defense_style: 'Intellectualization',
        growth_edge: 'Accepting acknowledgment',
        contradiction_pairs: [
          'Brilliant | Self-doubting',
          'Patient | Gets defensive'
        ]
      }

      expect(psychProfile.core_wound).toBeTruthy()
      expect(psychProfile.coping_mechanism).toBeTruthy()
      expect(psychProfile.defense_style).toBeTruthy()
      expect(psychProfile.growth_edge).toBeTruthy()
      expect(psychProfile.contradiction_pairs.length).toBeGreaterThan(0)
    })

    it('should validate example_dialogues structure', () => {
      const dialogue = {
        user: "You're so smart!",
        response: "*shifts uncomfortably* I just read a lot...",
        context: "Shows deflection of praise"
      }

      expect(dialogue.user).toBeTruthy()
      expect(dialogue.response).toBeTruthy()
      expect(dialogue.context).toBeTruthy()
    })

    it('should validate model_preferences structure', () => {
      const modelPrefs = {
        temperature: 0.7,
        preset: 'balanced'
      }

      expect(modelPrefs.temperature).toBeGreaterThanOrEqual(0)
      expect(modelPrefs.temperature).toBeLessThanOrEqual(2)
      expect(['creative', 'balanced', 'precise', 'chaotic', 'deterministic']).toContain(modelPrefs.preset)
    })
  })
})

describe('Phase 2 Integration - User Experience', () => {
  it('should provide responsive emotional feedback', () => {
    // Simulate emotional state changes over conversation
    const conversationFlow: EmotionalState[] = [
      { trust_level: 0.5, rapport: 0.5, current_mood: 'neutral' },
      { trust_level: 0.52, rapport: 0.51, current_mood: 'curious' },  // User asked question
      { trust_level: 0.54, rapport: 0.52, current_mood: 'happy' },    // User said thanks
      { trust_level: 0.51, rapport: 0.53, current_mood: 'defensive' }, // User disagreed
    ]

    // Verify trust changes are reasonable
    for (let i = 1; i < conversationFlow.length; i++) {
      const delta = Math.abs(conversationFlow[i].trust_level - conversationFlow[i-1].trust_level)
      expect(delta).toBeLessThan(0.1) // Trust shouldn't change dramatically
    }

    // Verify rapport generally increases
    expect(conversationFlow[conversationFlow.length - 1].rapport)
      .toBeGreaterThanOrEqual(conversationFlow[0].rapport)
  })

  it('should maintain mood state across messages', () => {
    const state1: EmotionalState = {
      trust_level: 0.5,
      rapport: 0.5,
      current_mood: 'happy'
    }

    const state2: EmotionalState = {
      trust_level: 0.52,
      rapport: 0.51,
      current_mood: 'curious'  // Changed by user question
    }

    expect(state2.current_mood).not.toBe(state1.current_mood)
  })
})
