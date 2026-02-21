// ── Persona listing / loading API ────────────────────────────────────────────

import { API_BASE_URL } from './base'
import type { PersonaJson } from './types'

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
