// ── NEPHILIM Progression System API ──────────────────────────────────────────

import { API_BASE_URL } from './base'

// ── Types ────────────────────────────────────────────────────────────────────

export interface SeekerProfile {
  user_id: string;
  rank_name: string;
  total_resonance: number;
  faction_primary: string | null;
  faction_secondary: string | null;
  rank_achieved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RankProgress {
  current_rank: string;
  current_resonance: number;
  next_rank: string | null;
  resonance_needed: number;
  progress_percent: number;
}

export interface PersonaAffinity {
  user_id: string;
  persona_key: string;
  messages_count: number;
  affinity_level: number;
  first_conversation: string | null;
  last_conversation: string | null;
}

export interface UnlockedLore {
  id: number;
  user_id: string;
  persona_key: string;
  fragment_id: string;
  unlocked_at: string;
}

export interface LoreFragment {
  fragment_id: string;
  fragment_title: string;
  fragment: string;
  messages_required: number;
  rarity: string;
  unlocked: boolean;
  unlocked_at: string | null;
}

export interface SeekerSummary {
  exists: boolean;
  user_id: string;
  rank: string | null;
  total_resonance: number | null;
  faction_primary: string | null;
  faction_secondary: string | null;
  rank_progress: RankProgress | null;
  persona_affinities: PersonaAffinity[];
  unlocked_lore_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface Faction {
  key: string;
  name: string;
  patron: string;
  values: string;
  color: string;
}

export interface RankInfo {
  name: string;
  resonance_required: number;
}

// ── API Functions ────────────────────────────────────────────────────────────

// Get seeker profile (creates if doesn't exist)
export const getSeekerProfile = async (userId: string): Promise<SeekerProfile> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch seeker profile: ${response.statusText}`)
  }
  return response.json()
}

// Get comprehensive seeker summary
export const getSeekerSummary = async (userId: string): Promise<SeekerSummary> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/summary`)
  if (!response.ok) {
    throw new Error(`Failed to fetch seeker summary: ${response.statusText}`)
  }
  return response.json()
}

// Set seeker faction
export const setSeekerFaction = async (
  userId: string,
  factionPrimary: string,
  factionSecondary?: string
): Promise<{ status: string; faction_primary: string }> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/faction`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      faction_primary: factionPrimary,
      faction_secondary: factionSecondary,
    }),
  })
  if (!response.ok) {
    throw new Error(`Failed to set faction: ${response.statusText}`)
  }
  return response.json()
}

// Get rank progress
export const getRankProgress = async (userId: string): Promise<RankProgress> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/rank`)
  if (!response.ok) {
    throw new Error(`Failed to fetch rank progress: ${response.statusText}`)
  }
  return response.json()
}

// Award resonance points
export const awardResonance = async (
  userId: string,
  amount: number,
  reason: string,
  personaKey?: string,
  sessionId?: string
): Promise<{
  status: string;
  new_resonance: number;
  new_rank: string;
  rank_changed: boolean;
  previous_rank?: string;
}> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/resonance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      amount,
      reason,
      persona_key: personaKey,
      session_id: sessionId,
    }),
  })
  if (!response.ok) {
    throw new Error(`Failed to award resonance: ${response.statusText}`)
  }
  return response.json()
}

// Get resonance history
export const getResonanceHistory = async (
  userId: string,
  limit: number = 50
): Promise<{ events: Record<string, unknown>[] }> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/resonance/history?limit=${limit}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch resonance history: ${response.statusText}`)
  }
  return response.json()
}

// Get all persona affinities
export const getAllAffinities = async (userId: string): Promise<PersonaAffinity[]> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/affinity`)
  if (!response.ok) {
    throw new Error(`Failed to fetch affinities: ${response.statusText}`)
  }
  return response.json()
}

// Get affinity with specific persona
export const getPersonaAffinity = async (userId: string, personaKey: string): Promise<PersonaAffinity> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/affinity/${personaKey}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch persona affinity: ${response.statusText}`)
  }
  return response.json()
}

// Get unlocked lore fragments
export const getUnlockedLore = async (userId: string, personaKey?: string): Promise<UnlockedLore[]> => {
  const url = personaKey
    ? `${API_BASE_URL}/nephilim/seeker/${userId}/lore?persona_key=${personaKey}`
    : `${API_BASE_URL}/nephilim/seeker/${userId}/lore`
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Failed to fetch unlocked lore: ${response.statusText}`)
  }
  return response.json()
}

// Get all lore fragments for a persona (with unlock status)
export const getPersonaLoreWithContent = async (userId: string, personaKey: string): Promise<LoreFragment[]> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/lore/${personaKey}/full`)
  if (!response.ok) {
    throw new Error(`Failed to fetch persona lore: ${response.statusText}`)
  }
  return response.json()
}

// Check and unlock new lore fragments
export const checkLoreUnlocks = async (
  userId: string,
  personaKey: string
): Promise<{ newly_unlocked: number; fragments: LoreFragment[] }> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/lore/${personaKey}/check`, {
    method: 'POST',
  })
  if (!response.ok) {
    throw new Error(`Failed to check lore unlocks: ${response.statusText}`)
  }
  return response.json()
}

// Get all rank info
export const getRankInfo = async (): Promise<{ ranks: RankInfo[] }> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/ranks`)
  if (!response.ok) {
    throw new Error(`Failed to fetch rank info: ${response.statusText}`)
  }
  return response.json()
}

// Get all faction info
export const getFactionInfo = async (): Promise<{ factions: Faction[] }> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/factions`)
  if (!response.ok) {
    throw new Error(`Failed to fetch faction info: ${response.statusText}`)
  }
  return response.json()
}
