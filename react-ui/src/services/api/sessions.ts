// ── Session CRUD API ─────────────────────────────────────────────────────────

import { API_BASE_URL, fetchWithAuth } from './base'
import type { ChatSession, SessionWithMessages, ExportData } from './types'

export const fetchSessions = async (): Promise<ChatSession[]> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions`)
  if (!response.ok) {
    throw new Error(`Failed to fetch sessions: ${response.statusText}`)
  }
  return response.json()
}

export const createSession = async (personaKey: string, title?: string): Promise<ChatSession> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ persona_key: personaKey, title: title || 'New Chat' }),
  })
  if (!response.ok) {
    throw new Error(`Failed to create session: ${response.statusText}`)
  }
  return response.json()
}

export const getSessionWithMessages = async (sessionId: string): Promise<SessionWithMessages> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch session: ${response.statusText}`)
  }
  const data = await response.json()
  data.messages = data.messages.map((msg: any) => ({
    ...msg,
    timestamp: new Date(msg.timestamp),
    metadata: msg.source_type ? { source_type: msg.source_type, tools_used: [] } : undefined,
  }))
  return data
}

export const updateSession = async (sessionId: string, updates: Partial<Pick<ChatSession, 'title'>>): Promise<ChatSession> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })
  if (!response.ok) {
    throw new Error(`Failed to update session: ${response.statusText}`)
  }
  return response.json()
}

export const deleteSession = async (sessionId: string): Promise<void> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}`, { method: 'DELETE' })
  if (!response.ok) {
    throw new Error(`Failed to delete session: ${response.statusText}`)
  }
}

export const exportSession = async (sessionId: string): Promise<ExportData> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/export`)
  if (!response.ok) {
    throw new Error(`Failed to export session: ${response.statusText}`)
  }
  return response.json()
}

export const importSession = async (exportData: ExportData): Promise<ChatSession> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/import`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(exportData),
  })
  if (!response.ok) {
    throw new Error(`Failed to import session: ${response.statusText}`)
  }
  return response.json()
}

export const clearSessionMessages = async (sessionId: string): Promise<void> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Clear Messages API Error: ${response.status} ${response.statusText} - ${errorText}`)
  }
}
