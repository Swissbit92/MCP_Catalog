// ── Chat / Messaging API ─────────────────────────────────────────────────────

import { API_BASE_URL, fetchWithAuth } from './base'
import type { ChatApiResponse, Message } from './types'

export const sendMessageToSession = async (sessionId: string, message: string): Promise<ChatApiResponse> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Chat API Error: ${response.status} ${response.statusText} - ${errorText}`)
  }
  const data = await response.json()
  // Return full API response (Phase 2: includes multi-message fields)
  return {
    answer: data.answer,
    message_flow: data.message_flow || 'single',
    message_count: data.message_count || 1,
    used_search: data.used_search || false,
    search_results_count: data.search_results_count || 0,
    citation_valid: data.citation_valid,
    metadata: data.metadata || null,
    emotional_state: data.emotional_state || null,
  }
}

export const greetWithSession = async (sessionId: string, persona: string): Promise<Message> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/greet`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      persona,
    }),
  })
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Greeting API Error: ${response.status} ${response.statusText} - ${errorText}`)
  }
  const data = await response.json()
  // Convert API response to Message object
  return {
    id: `assistant-greeting-${Date.now()}`,
    role: 'assistant',
    content: data.answer,
    timestamp: new Date(),
  }
}
