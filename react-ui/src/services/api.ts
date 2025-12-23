const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8000';

interface PersonaJson {
  key: string;
  rarity: string;
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
  source_type: 'llm' | 'brave_mcp' | 'mongodb_mcp' | 'multi_mcp';
  tools_used: string[];
  cache_status?: 'hit' | 'miss' | null;
  data_timestamp?: string | null;
  latency_breakdown?: Record<string, number> | null;
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

// Session management functions
export const fetchSessions = async (): Promise<ChatSession[]> => {
  const response = await fetch(`${API_BASE_URL}/sessions`);
  if (!response.ok) {
    throw new Error(`Failed to fetch sessions: ${response.statusText}`);
  }
  return response.json();
};

export const createSession = async (personaKey: string, title?: string): Promise<ChatSession> => {
  const response = await fetch(`${API_BASE_URL}/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      persona_key: personaKey,
      title: title || 'New Chat',
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to create session: ${response.statusText}`);
  }
  return response.json();
};

export const getSessionWithMessages = async (sessionId: string): Promise<SessionWithMessages> => {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch session: ${response.statusText}`);
  }
  const data = await response.json();
  // Convert timestamp strings to Date objects
  data.messages = data.messages.map((msg: any) => ({
    ...msg,
    timestamp: new Date(msg.timestamp),
  }));
  return data;
};

export const updateSession = async (sessionId: string, updates: Partial<Pick<ChatSession, 'title'>>): Promise<ChatSession> => {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    throw new Error(`Failed to update session: ${response.statusText}`);
  }
  return response.json();
};

export const deleteSession = async (sessionId: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete session: ${response.statusText}`);
  }
};

export const sendMessageToSession = async (sessionId: string, message: string): Promise<Message> => {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
    }),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Chat API Error: ${response.status} ${response.statusText} - ${errorText}`);
  }
  const data = await response.json();
  // Convert API response to Message object
  return {
    id: `assistant-${Date.now()}`,
    role: 'assistant',
    content: data.answer,
    timestamp: new Date(),
    used_search: data.used_search || false,
    search_results_count: data.search_results_count || 0,
    citation_valid: data.citation_valid,
    metadata: data.metadata || null,
    emotional_state: data.emotional_state || null, // Phase 2.2: Emotional state
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