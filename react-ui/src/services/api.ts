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
  bg: string;
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
    body: JSON.stringify({ persona, message, history }),
  });
  if (!response.ok) {
    throw new Error('Failed to send message');
  }
  const data = await response.json();
  return data.answer;
};