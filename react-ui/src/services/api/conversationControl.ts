// ── Conversation-control API (ADR-011) ───────────────────────────────────────
// Regenerate/continue/undo/narrate/impersonate + session metadata + author's
// note. Thin callers of the coordinator session API — the Telegram gateway
// calls the same endpoints, so behavior is identical across both clients.

import { API_BASE_URL, fetchWithAuth } from './base'
import type { ChatApiResponse, ChatSession } from './types'

const parseChatApiResponse = (data: any): ChatApiResponse => ({
  answer: data.answer,
  message_flow: data.message_flow || 'single',
  message_count: data.message_count || 1,
  used_search: data.used_search || false,
  search_results_count: data.search_results_count || 0,
  citation_valid: data.citation_valid,
  metadata: data.metadata || null,
  emotional_state: data.emotional_state || null,
})

export const regenerateMessage = async (sessionId: string): Promise<ChatApiResponse> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Regenerate API Error: ${response.status} ${response.statusText} - ${errorText}`)
  }
  return parseChatApiResponse(await response.json())
}

export const continueMessage = async (sessionId: string): Promise<ChatApiResponse> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/continue`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Continue API Error: ${response.status} ${response.statusText} - ${errorText}`)
  }
  return parseChatApiResponse(await response.json())
}

export const undoLastTurn = async (sessionId: string): Promise<void> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/undo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Undo API Error: ${response.status} ${response.statusText} - ${errorText}`)
  }
}

export const narrateMessage = async (sessionId: string, text: string): Promise<ChatApiResponse> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/narrate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Narrate API Error: ${response.status} ${response.statusText} - ${errorText}`)
  }
  return parseChatApiResponse(await response.json())
}

export const impersonateDraft = async (sessionId: string, hint?: string): Promise<{ draft: string }> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/impersonate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(hint ? { hint } : {}),
  })
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Impersonate API Error: ${response.status} ${response.statusText} - ${errorText}`)
  }
  return response.json()
}

export const getSessionMeta = async (
  sessionId: string
): Promise<ChatSession & { display_name?: string; nsfw?: boolean }> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/meta`)
  if (!response.ok) {
    throw new Error(`Failed to fetch session meta: ${response.statusText}`)
  }
  return response.json()
}

export const setSessionNote = async (sessionId: string, note: string): Promise<void> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/note`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note }),
  })
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Set Note API Error: ${response.status} ${response.statusText} - ${errorText}`)
  }
}

export const getSessionNote = async (sessionId: string): Promise<{ note: string | null }> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/note`)
  if (!response.ok) {
    throw new Error(`Failed to fetch session note: ${response.statusText}`)
  }
  return response.json()
}

export const clearSessionNote = async (sessionId: string): Promise<void> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/note`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Clear Note API Error: ${response.status} ${response.statusText} - ${errorText}`)
  }
}
