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

export interface ChatSession {
  id: string;
  persona_key: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  latency_ms?: number;
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
  const personaFiles = [
    'eeva.json',
    'frieren.json',
    'gojo.json',
    'hitler.json',
    'itachi.json',
  ];

  const fetchedPersonas: PersonaJson[] = [];
  for (const file of personaFiles) {
    try {
      const response = await fetch(`/personas/${file}`);
      if (!response.ok) {
        console.error(`Failed to fetch ${file}: ${response.statusText}`);
        continue;
      }
      const data: PersonaJson = await response.json();
      fetchedPersonas.push(data);
    } catch (error) {
      console.error('Error fetching persona:', error);
    }
  }
  return fetchedPersonas;
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
  return data.answer;
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
  };
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