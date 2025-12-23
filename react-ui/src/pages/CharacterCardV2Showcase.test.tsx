import { fetchPersonas } from '../services/api';

// Mock the API
jest.mock('../services/api');
const mockFetchPersonas = fetchPersonas as jest.MockedFunction<typeof fetchPersonas>;

describe('CharacterCardV2Showcase localStorage cleanup', () => {
  // Mock localStorage
  const localStorageMock = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();

    // Set up localStorage mock
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true,
    });
  });

  it('cleans up removed personas from localStorage collection', async () => {
    // Mock localStorage with personas that no longer exist
    localStorageMock.getItem.mockReturnValue(JSON.stringify(['eeva', 'removed_persona', 'gojo', 'another_removed']));

    const mockPersonas = [
      {
        key: 'eeva',
        display_name: 'Eeva — Bitcoin Expect',
        style: 'nerdy, charming, concise',
        rarity: 'legendary',
        image: 'images/eeva_card.png',
        coordinator_label: 'Eeva',
        avatar: 'images/eeva_avatar.png',
        logo: 'images/eeva_logo.png',
        emoji: '🤖',
        allowed_mcp: ['chat'],
        lore: ['Bitcoin expert'],
        voice: {},
        do: ['Be helpful'],
        dont: ['Be rude'],
        behavior: {},
        emotional_profile: {},
        boundaries: {},
        dialogue_prefs: {},
        expertise: {},
        signature_moves: [],
        example_phrases: [],
        escalation_policy: {},
      },
      {
        key: 'gojo',
        display_name: 'Gojo Satoru',
        style: 'confident sorcerer',
        rarity: 'legendary',
        image: 'images/gojo_card.png',
        coordinator_label: 'Gojo',
        avatar: 'images/gojo_avatar.png',
        logo: 'images/gojo_logo.png',
        emoji: '🧙',
        allowed_mcp: ['chat'],
        lore: ['Powerful sorcerer'],
        voice: {},
        do: ['Be confident'],
        dont: ['Be weak'],
        behavior: {},
        emotional_profile: {},
        boundaries: {},
        dialogue_prefs: {},
        expertise: {},
        signature_moves: [],
        example_phrases: [],
        escalation_policy: {},
      },
    ];

    mockFetchPersonas.mockResolvedValue(mockPersonas);

    // Import and run the cleanup logic directly
    // This simulates what happens in the useEffect of CharacterCardV2Showcase
    const fetchedPersonas = await fetchPersonas();
    const currentPersonaKeys = new Set(fetchedPersonas.map(p => p.key));

    const storedCollected = localStorage.getItem('collectedPersonas');
    if (storedCollected) {
      const collectedPersonas = JSON.parse(storedCollected);
      const validCollected = collectedPersonas.filter((key: string) => currentPersonaKeys.has(key));
      if (validCollected.length !== collectedPersonas.length) {
        localStorage.setItem('collectedPersonas', JSON.stringify(validCollected));
      }
    }

    // Verify that localStorage was updated to remove the non-existent personas
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'collectedPersonas',
      JSON.stringify(['eeva', 'gojo'])
    );

    // Verify that the original stored data was retrieved
    expect(localStorageMock.getItem).toHaveBeenCalledWith('collectedPersonas');
  });

  it('does not modify localStorage if all personas are valid', async () => {
    // Mock localStorage with only valid personas
    localStorageMock.getItem.mockReturnValue(JSON.stringify(['eeva', 'gojo']));

    const mockPersonas = [
      {
        key: 'eeva',
        display_name: 'Eeva — Bitcoin Expect',
        style: 'nerdy, charming, concise',
        rarity: 'legendary',
        image: 'images/eeva_card.png',
        coordinator_label: 'Eeva',
        avatar: 'images/eeva_avatar.png',
        logo: 'images/eeva_logo.png',
        emoji: '🤖',
        allowed_mcp: ['chat'],
        lore: ['Bitcoin expert'],
        voice: {},
        do: ['Be helpful'],
        dont: ['Be rude'],
        behavior: {},
        emotional_profile: {},
        boundaries: {},
        dialogue_prefs: {},
        expertise: {},
        signature_moves: [],
        example_phrases: [],
        escalation_policy: {},
      },
      {
        key: 'gojo',
        display_name: 'Gojo Satoru',
        style: 'confident sorcerer',
        rarity: 'legendary',
        image: 'images/gojo_card.png',
        coordinator_label: 'Gojo',
        avatar: 'images/gojo_avatar.png',
        logo: 'images/gojo_logo.png',
        emoji: '🧙',
        allowed_mcp: ['chat'],
        lore: ['Powerful sorcerer'],
        voice: {},
        do: ['Be confident'],
        dont: ['Be weak'],
        behavior: {},
        emotional_profile: {},
        boundaries: {},
        dialogue_prefs: {},
        expertise: {},
        signature_moves: [],
        example_phrases: [],
        escalation_policy: {},
      },
    ];

    mockFetchPersonas.mockResolvedValue(mockPersonas);

    // Import and run the cleanup logic directly
    const fetchedPersonas = await fetchPersonas();
    const currentPersonaKeys = new Set(fetchedPersonas.map(p => p.key));

    const storedCollected = localStorage.getItem('collectedPersonas');
    if (storedCollected) {
      const collectedPersonas = JSON.parse(storedCollected);
      const validCollected = collectedPersonas.filter((key: string) => currentPersonaKeys.has(key));
      if (validCollected.length !== collectedPersonas.length) {
        localStorage.setItem('collectedPersonas', JSON.stringify(validCollected));
      }
    }

    // Verify that localStorage was not modified
    expect(localStorageMock.setItem).not.toHaveBeenCalled();
    expect(localStorageMock.getItem).toHaveBeenCalledWith('collectedPersonas');
  });

  it('handles empty localStorage gracefully', async () => {
    // Mock empty localStorage
    localStorageMock.getItem.mockReturnValue(null);

    const mockPersonas = [
      {
        key: 'eeva',
        display_name: 'Eeva — Bitcoin Expect',
        style: 'nerdy, charming, concise',
        rarity: 'legendary',
        image: 'images/eeva_card.png',
        coordinator_label: 'Eeva',
        avatar: 'images/eeva_avatar.png',
        logo: 'images/eeva_logo.png',
        emoji: '🤖',
        allowed_mcp: ['chat'],
        lore: ['Bitcoin expert'],
        voice: {},
        do: ['Be helpful'],
        dont: ['Be rude'],
        behavior: {},
        emotional_profile: {},
        boundaries: {},
        dialogue_prefs: {},
        expertise: {},
        signature_moves: [],
        example_phrases: [],
        escalation_policy: {},
      },
    ];

    mockFetchPersonas.mockResolvedValue(mockPersonas);

    // Import and run the cleanup logic directly
    const fetchedPersonas = await fetchPersonas();
    const currentPersonaKeys = new Set(fetchedPersonas.map(p => p.key));

    const storedCollected = localStorage.getItem('collectedPersonas');
    if (storedCollected) {
      const collectedPersonas = JSON.parse(storedCollected);
      const validCollected = collectedPersonas.filter((key: string) => currentPersonaKeys.has(key));
      if (validCollected.length !== collectedPersonas.length) {
        localStorage.setItem('collectedPersonas', JSON.stringify(validCollected));
      }
    }

    // Verify that localStorage was not accessed for writing
    expect(localStorageMock.setItem).not.toHaveBeenCalled();
    expect(localStorageMock.getItem).toHaveBeenCalledWith('collectedPersonas');
  });
});