// ── Persona listing / loading API ────────────────────────────────────────────

import { API_BASE_URL, fetchWithAuth } from './base'
import type { PersonaJson, CharacterBio } from './types'

export const fetchPersonas = async (): Promise<PersonaJson[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/personas`)
    if (!response.ok) {
      throw new Error(`Failed to fetch personas: ${response.statusText}`)
    }
    const personas: PersonaJson[] = await response.json()
    return personas
  } catch (error) {
    console.error('Error fetching personas from API:', error)
    // Fallback to empty array if API fails
    return []
  }
}

// Character showcase functions
export const fetchCharacterBio = async (personaKey: string): Promise<CharacterBio> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/persona/summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ persona: personaKey })
  })
  if (!response.ok) {
    throw new Error(`Failed to fetch character bio: ${response.statusText}`)
  }
  return response.json()
}
