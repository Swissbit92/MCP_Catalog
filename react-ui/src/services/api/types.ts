// ── Shared type definitions used across API domain modules ───────────────────

export interface PersonaJson {
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
  mcp_access: string[];
  lore: string[];
  voice: Record<string, unknown>;
  do: string[];
  dont: string[];
  behavior: Record<string, unknown>;
  emotional_profile: Record<string, unknown>;
  boundaries: Record<string, unknown>;
  dialogue_prefs: Record<string, unknown>;
  expertise: Record<string, unknown>;
  signature_moves: string[];
  example_phrases: string[];
  escalation_policy: Record<string, unknown>;
  nephilim_lore?: {
    relationships?: Record<string, string>;
    realm_domain?: { name: string; description: string };
  };
}

export interface CharacterBio {
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

// Rank ceremony data returned when a seeker ranks up
export interface RankCeremony {
  title: string
  speaker: string
  monologue: string
  previous_rank: string
  new_rank: string
}

// NEPHILIM Phase-2: a newly-awakened internal capability (diegetic unlock beat)
export interface CapabilityUnlock {
  id: string
  display_name: string
  persona_voice_line: string
}

// Response metadata for MCP data sources
export interface ResponseMetadata {
  source_type: 'llm' | 'brave_mcp' | 'wallet_mcp' | 'wallet_proposal' | 'wallet_flow';
  tools_used: string[];
  cache_status?: 'hit' | 'miss' | null;
  data_timestamp?: string | null;
  latency_breakdown?: Record<string, number> | null;
  // PHASE 2: Multi-message response fields
  is_multi_message?: boolean;
  message_count?: number;
  // WALLET: Proposal card injection
  proposal_type?: 'trade_proposal' | 'strategy_proposal' | 'wallet_deletion';
  proposal?: Record<string, unknown>;
  // NEPHILIM: Rank ceremony overlay trigger
  rank_ceremony?: RankCeremony;
  // NEPHILIM Phase-2: internal capabilities newly awakened this turn (diegetic toast)
  capability_unlocks?: CapabilityUnlock[];
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
