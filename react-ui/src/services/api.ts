const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8000';

// Auth helper — inject Bearer token into fetch headers when available
export function getAuthHeader(token: string | null): HeadersInit {
  return token ? { 'Authorization': 'Bearer ' + token } : {}
}

// ── 401 Auto-Refresh Mechanism ────────────────────────────────────────────────
// AuthContext calls setAuthCallbacks() on mount so api.ts can silently refresh
// expired tokens and retry failed requests without importing React hooks.

type GetTokenFn = () => string | null
type RefreshFn = () => Promise<string | null>
type LogoutFn = () => void

let _getToken: GetTokenFn = () => null
let _refresh: RefreshFn = async () => null
let _logout: LogoutFn = () => {}

export function setAuthCallbacks(
  getToken: GetTokenFn,
  refresh: RefreshFn,
  logout: LogoutFn
): void {
  _getToken = getToken
  _refresh = refresh
  _logout = logout
}

/**
 * Authenticated fetch wrapper.
 * - Injects Bearer token automatically
 * - On 401: attempts silent token refresh, retries once
 * - On second 401: calls logout (redirects to /login via AuthContext)
 */
async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = _getToken()
  const authHeaders = getAuthHeader(token)

  const response = await fetch(url, {
    ...options,
    headers: { ...authHeaders, ...options.headers },
  })

  if (response.status !== 401) return response

  // First 401 — attempt silent refresh
  const newToken = await _refresh()
  if (!newToken) {
    _logout()
    return response
  }

  // Retry with new token
  const retried = await fetch(url, {
    ...options,
    headers: { ...getAuthHeader(newToken), ...options.headers },
  })

  if (retried.status === 401) {
    _logout()
  }

  return retried
}

interface PersonaJson {
  key: string;
  rarity: string;
  celestial_order?: string;
  display_name: string;
  style: string;
  coordinator_label: string;
  image: string;
  avatar: string;
  logo: string;
  bg?: string;
  emoji: string;
  allowed_mcp: string[];
  lore: string[];
  voice: any; // Simplified for now
  do: string[];
  dont: string[];
  behavior: any; // Simplified for now
  emotional_profile: any; // Simplified for now
  boundaries: any; // Simplified for now
  dialogue_prefs: any; // Simplified for now
  expertise: any; // Simplified for now
  signature_moves: string[];
  example_phrases: string[];
  escalation_policy: any; // Simplified for now
}

interface CharacterBio {
  key: string;
  summary: string; // 120-220 words CV-style bio from LLM
  hash: string;
  updated: string;
}


export interface ChatSession {
  id: string;
  persona_key: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

// Response metadata for MCP data sources
export interface ResponseMetadata {
  source_type: 'llm' | 'brave_mcp' | 'mongodb_mcp' | 'multi_mcp' | 'wallet_mcp' | 'wallet_proposal' | 'wallet_flow';
  tools_used: string[];
  cache_status?: 'hit' | 'miss' | null;
  data_timestamp?: string | null;
  latency_breakdown?: Record<string, number> | null;
  // PHASE 2: Multi-message response fields
  is_multi_message?: boolean;
  message_count?: number;
  // WALLET: Proposal card injection
  proposal_type?: 'trade_proposal' | 'strategy_proposal' | 'wallet_deletion';
  proposal?: Record<string, any>;
}

// Phase 2.2: Emotional state tracking
export interface EmotionalState {
  trust_level: number;    // 0.0 (hostile) to 1.0 (deep trust)
  rapport: number;        // 0.0 (awkward) to 1.0 (strong connection)
  current_mood: string;   // neutral, happy, sad, curious, defensive, etc.
  mood_intensity?: number; // 0.0 (subtle) to 1.0 (intense)
  last_emotional_event?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  latency_ms?: number;
  used_search?: boolean; // Whether web search was used for this message
  search_results_count?: number; // Number of search results returned
  citation_valid?: boolean; // Whether citations were properly included
  metadata?: ResponseMetadata; // Response metadata from backend
  emotional_state?: EmotionalState; // Phase 2.2: Emotional state after this message
}

export interface SessionWithMessages {
  session: ChatSession;
  messages: Message[];
}

export interface ExportData {
  version: string;
  exported_at: string;
  app_version: string;
  persona: {
    key: string;
    display_name: string;
    style: string;
  };
  session: ChatSession;
  messages: Message[];
}

export const fetchPersonas = async (): Promise<PersonaJson[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/personas`);
    if (!response.ok) {
      throw new Error(`Failed to fetch personas: ${response.statusText}`);
    }
    const personas: PersonaJson[] = await response.json();
    return personas;
  } catch (error) {
    console.error('Error fetching personas from API:', error);
    // Fallback to empty array if API fails
    return [];
  }
};

interface ChatTurn {
  role: string;
  content: string;
}

export const sendMessage = async (persona: string, message: string, history: ChatTurn[]) => {
  const response = await fetch(`${API_BASE_URL}/persona/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      persona,
      message,
      history
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  const data = await response.json();
  return {
    answer: data.answer,
    used_search: data.used_search || false,
    search_results_count: data.search_results_count || 0,
    citation_valid: data.citation_valid,
    metadata: data.metadata || null,
  };
};

export const getPersonaGreeting = async (persona: string) => {
  const response = await fetch(`${API_BASE_URL}/persona/greet`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      persona
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Greeting API Error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  const data = await response.json();
  return data.answer;
};

// Session management functions — use fetchWithAuth for automatic 401 retry
export const fetchSessions = async (): Promise<ChatSession[]> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions`);
  if (!response.ok) {
    throw new Error(`Failed to fetch sessions: ${response.statusText}`);
  }
  return response.json();
};

export const createSession = async (personaKey: string, title?: string): Promise<ChatSession> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ persona_key: personaKey, title: title || 'New Chat' }),
  });
  if (!response.ok) {
    throw new Error(`Failed to create session: ${response.statusText}`);
  }
  return response.json();
};

export const getSessionWithMessages = async (sessionId: string): Promise<SessionWithMessages> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch session: ${response.statusText}`);
  }
  const data = await response.json();
  data.messages = data.messages.map((msg: any) => ({
    ...msg,
    timestamp: new Date(msg.timestamp),
    metadata: msg.source_type ? { source_type: msg.source_type, tools_used: [] } : undefined,
  }));
  return data;
};

export const updateSession = async (sessionId: string, updates: Partial<Pick<ChatSession, 'title'>>): Promise<ChatSession> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    throw new Error(`Failed to update session: ${response.statusText}`);
  }
  return response.json();
};

export const deleteSession = async (sessionId: string): Promise<void> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}`, { method: 'DELETE' });
  if (!response.ok) {
    throw new Error(`Failed to delete session: ${response.statusText}`);
  }
};

// Phase 2: Extended response type for multi-message
export interface ChatApiResponse {
  answer: string | string[]; // Single string or array of strings
  message_flow: 'single' | 'multi';
  message_count: number;
  used_search?: boolean;
  search_results_count?: number;
  citation_valid?: boolean;
  metadata?: ResponseMetadata | null;
  emotional_state?: EmotionalState | null;
}

export const sendMessageToSession = async (sessionId: string, message: string): Promise<ChatApiResponse> => {
  const response = await fetchWithAuth(`${API_BASE_URL}/sessions/${sessionId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Chat API Error: ${response.status} ${response.statusText} - ${errorText}`);
  }
  const data = await response.json();
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
  };
};

// Phase 2.2: Fetch emotional state for a session
export const getSessionEmotionalState = async (sessionId: string): Promise<EmotionalState> => {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/emotional-state`);
  if (!response.ok) {
    throw new Error(`Failed to fetch emotional state: ${response.statusText}`);
  }
  return response.json();
};

export const exportSession = async (sessionId: string): Promise<ExportData> => {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/export`);
  if (!response.ok) {
    throw new Error(`Failed to export session: ${response.statusText}`);
  }
  return response.json();
};

export const importSession = async (exportData: ExportData): Promise<ChatSession> => {
  const response = await fetch(`${API_BASE_URL}/sessions/import`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(exportData),
  });
  if (!response.ok) {
    throw new Error(`Failed to import session: ${response.statusText}`);
  }
  return response.json();
};

export const greetWithSession = async (sessionId: string, persona: string): Promise<Message> => {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/greet`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      persona,
    }),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Greeting API Error: ${response.status} ${response.statusText} - ${errorText}`);
  }
  const data = await response.json();
  // Convert API response to Message object
  return {
    id: `assistant-greeting-${Date.now()}`,
    role: 'assistant',
    content: data.answer,
    timestamp: new Date(),
  };
};

export const clearSessionMessages = async (sessionId: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Clear Messages API Error: ${response.status} ${response.statusText} - ${errorText}`);
  }
};

// Character showcase functions
export const fetchCharacterBio = async (personaKey: string): Promise<CharacterBio> => {
  const response = await fetch(`${API_BASE_URL}/persona/summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ persona: personaKey })
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch character bio: ${response.statusText}`);
  }
  return response.json();
};

// =============================================================
// NEPHILIM Progression System API
// =============================================================

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

// Get seeker profile (creates if doesn't exist)
export const getSeekerProfile = async (userId: string): Promise<SeekerProfile> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch seeker profile: ${response.statusText}`);
  }
  return response.json();
};

// Get comprehensive seeker summary
export const getSeekerSummary = async (userId: string): Promise<SeekerSummary> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/summary`);
  if (!response.ok) {
    throw new Error(`Failed to fetch seeker summary: ${response.statusText}`);
  }
  return response.json();
};

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
  });
  if (!response.ok) {
    throw new Error(`Failed to set faction: ${response.statusText}`);
  }
  return response.json();
};

// Get rank progress
export const getRankProgress = async (userId: string): Promise<RankProgress> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/rank`);
  if (!response.ok) {
    throw new Error(`Failed to fetch rank progress: ${response.statusText}`);
  }
  return response.json();
};

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
  });
  if (!response.ok) {
    throw new Error(`Failed to award resonance: ${response.statusText}`);
  }
  return response.json();
};

// Get resonance history
export const getResonanceHistory = async (
  userId: string,
  limit: number = 50
): Promise<{ events: any[] }> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/resonance/history?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch resonance history: ${response.statusText}`);
  }
  return response.json();
};

// Get all persona affinities
export const getAllAffinities = async (userId: string): Promise<PersonaAffinity[]> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/affinity`);
  if (!response.ok) {
    throw new Error(`Failed to fetch affinities: ${response.statusText}`);
  }
  return response.json();
};

// Get affinity with specific persona
export const getPersonaAffinity = async (userId: string, personaKey: string): Promise<PersonaAffinity> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/affinity/${personaKey}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch persona affinity: ${response.statusText}`);
  }
  return response.json();
};

// Get unlocked lore fragments
export const getUnlockedLore = async (userId: string, personaKey?: string): Promise<UnlockedLore[]> => {
  const url = personaKey
    ? `${API_BASE_URL}/nephilim/seeker/${userId}/lore?persona_key=${personaKey}`
    : `${API_BASE_URL}/nephilim/seeker/${userId}/lore`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch unlocked lore: ${response.statusText}`);
  }
  return response.json();
};

// Get all lore fragments for a persona (with unlock status)
export const getPersonaLoreWithContent = async (userId: string, personaKey: string): Promise<LoreFragment[]> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/lore/${personaKey}/full`);
  if (!response.ok) {
    throw new Error(`Failed to fetch persona lore: ${response.statusText}`);
  }
  return response.json();
};

// Check and unlock new lore fragments
export const checkLoreUnlocks = async (
  userId: string,
  personaKey: string
): Promise<{ newly_unlocked: number; fragments: any[] }> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/seeker/${userId}/lore/${personaKey}/check`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Failed to check lore unlocks: ${response.statusText}`);
  }
  return response.json();
};

// Get all rank info
export const getRankInfo = async (): Promise<{ ranks: RankInfo[] }> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/ranks`);
  if (!response.ok) {
    throw new Error(`Failed to fetch rank info: ${response.statusText}`);
  }
  return response.json();
};

// Get all faction info
export const getFactionInfo = async (): Promise<{ factions: Faction[] }> => {
  const response = await fetch(`${API_BASE_URL}/nephilim/factions`);
  if (!response.ok) {
    throw new Error(`Failed to fetch faction info: ${response.statusText}`);
  }
  return response.json();
};

// ============================================================
// WALLET / JUPITER API — Trade proposals and strategies
// ============================================================

export interface TradeProposalResponse {
  proposal_id: string;
  status: 'confirmed' | 'cancelled' | 'expired';
  tx_signature?: string;
  error?: string;
}

export interface StrategyResponse {
  strategy_id: string;
  status: 'active' | 'paused' | 'cancelled';
  message: string;
}

export interface WalletBalance {
  public_address: string;
  sol: number;
  tokens: Array<{ mint: string; symbol: string; amount: number; value_usdc?: number }>;
}

export async function confirmTrade(proposalId: string): Promise<TradeProposalResponse> {
  const res = await fetch(`${API_BASE_URL}/wallet/confirm/${proposalId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Confirm failed: ${res.status}`);
  }
  return res.json();
}

export async function cancelTrade(proposalId: string): Promise<TradeProposalResponse> {
  const res = await fetch(`${API_BASE_URL}/wallet/cancel/${proposalId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Cancel failed: ${res.status}`);
  }
  return res.json();
}

export async function approveStrategy(
  proposalId: string,
  strategyConfig: Record<string, any>
): Promise<StrategyResponse> {
  const res = await fetch(`${API_BASE_URL}/wallet/strategy/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ proposal_id: proposalId, strategy_config: strategyConfig }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Approval failed: ${res.status}`);
  }
  return res.json();
}

export async function rejectStrategy(proposalId: string): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE_URL}/wallet/strategy/reject/${proposalId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Reject failed: ${res.status}`);
  return res.json();
}

export async function pauseStrategy(strategyId: string): Promise<StrategyResponse> {
  const res = await fetch(`${API_BASE_URL}/wallet/strategy/${strategyId}/pause`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Pause failed: ${res.status}`);
  return res.json();
}

export async function resumeStrategy(strategyId: string): Promise<StrategyResponse> {
  const res = await fetch(`${API_BASE_URL}/wallet/strategy/${strategyId}/resume`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Resume failed: ${res.status}`);
  return res.json();
}

export async function cancelStrategy(strategyId: string): Promise<StrategyResponse> {
  const res = await fetch(`${API_BASE_URL}/wallet/strategy/${strategyId}/cancel`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Cancel failed: ${res.status}`);
  return res.json();
}

export async function listStrategies(userId: string): Promise<{ strategies: any[] }> {
  const res = await fetch(`${API_BASE_URL}/wallet/strategies?user_id=${encodeURIComponent(userId)}`);
  if (!res.ok) throw new Error(`List strategies failed: ${res.status}`);
  return res.json();
}

export async function getWalletBalance(userId: string): Promise<WalletBalance> {
  const res = await fetch(`${API_BASE_URL}/wallet/balance/${encodeURIComponent(userId)}`);
  if (!res.ok) throw new Error(`Balance check failed: ${res.status}`);
  return res.json();
}

export async function deleteWallet(userId: string): Promise<{ status: string; public_address: string }> {
  const res = await fetch(`${API_BASE_URL}/wallet/delete/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Deletion failed' }))
    throw new Error(err.detail || `Delete failed: ${res.status}`)
  }
  return res.json()
}

// ============================================================
// Auth API — Google OAuth + JWT refresh/logout
// ============================================================

export interface AuthTokenResponse {
  access_token: string
  token_type: string
  user: { sub: string; email: string; name: string; avatar: string }
}

export async function loginWithGoogle(credential: string): Promise<AuthTokenResponse> {
  const res = await fetch('/auth/google', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ credential }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Login failed' }))
    throw new Error(err.detail || `Login failed: ${res.status}`)
  }
  return res.json()
}

export async function refreshAccessToken(): Promise<AuthTokenResponse> {
  const res = await fetch('/auth/refresh', {
    method: 'POST',
    credentials: 'include',
  })
  if (!res.ok) throw new Error(`Refresh failed: ${res.status}`)
  return res.json()
}

export async function logoutApi(): Promise<void> {
  await fetch('/auth/logout', {
    method: 'POST',
    credentials: 'include',
  })
}