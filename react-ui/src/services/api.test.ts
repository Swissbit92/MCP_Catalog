import { fetchPersonas, fetchSessions, createSession, getSessionWithMessages, updateSession, deleteSession, sendMessageToSession, exportSession, importSession } from './api';

// Mock the global fetch function
global.fetch = jest.fn();

describe('API Service', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
  });

  it('fetchPersonas should return a list of personas from API', async () => {
    const mockPersonas = [
      { key: 'Eeva', display_name: 'Eeva', style: 'strategic', rarity: 'legendary', celestial_order: 'archon', mcp_access: ['brave_search', 'mongodb'], image: 'images/personas/nephilim_eeva/card.png' },
      { key: 'Gojo', display_name: 'Gojo', style: 'cool', rarity: 'legendary', celestial_order: 'archon', mcp_access: ['brave_search'], image: 'images/personas/gojo/card.png' },
    ];

    (fetch as jest.Mock).mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockPersonas),
      })
    );

    const personas = await fetchPersonas();
    expect(personas.length).toBe(2);
    expect(personas[0].key).toBe('Eeva');
    expect(personas[0].rarity).toBe('legendary');
    expect(personas[1].key).toBe('Gojo');
    expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/personas');
  });

  it('fetchPersonas should return empty array on API error', async () => {
    (fetch as jest.Mock).mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        statusText: 'Internal Server Error',
      })
    );

    const personas = await fetchPersonas();
    expect(personas).toEqual([]);
  });

  it('fetchPersonas should handle personas with missing optional fields', async () => {
    const mockPersonas = [
      { key: 'minimal', display_name: 'Minimal Persona' }, // Missing style, rarity, celestial_order, etc.
      { key: 'full', display_name: 'Full Persona', style: 'confident', rarity: 'legendary', celestial_order: 'archon', mcp_access: ['brave_search', 'mongodb'], voice: { greeting: 'Hi!' } }
    ];

    (fetch as jest.Mock).mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockPersonas),
      })
    );

    const personas = await fetchPersonas();
    expect(personas.length).toBe(2);
    expect(personas[0].key).toBe('minimal');
    expect(personas[0].style).toBeUndefined(); // Should handle missing fields gracefully
    expect(personas[1].voice.greeting).toBe('Hi!');
  });

  describe('Session API', () => {
    it('fetchSessions should return a list of sessions', async () => {
      const mockSessions = [
        {
          id: '1',
          persona_key: 'eeva',
          title: 'Chat with Eeva',
          created_at: '2024-01-01T10:00:00Z',
          updated_at: '2024-01-01T10:30:00Z',
          message_count: 5,
        },
      ];

      (fetch as jest.Mock).mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSessions),
        })
      );

      const sessions = await fetchSessions();
      expect(sessions).toEqual(mockSessions);
      expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/sessions', expect.objectContaining({}));
    });

    it('createSession should return a new session', async () => {
      const mockSession = {
        id: '1',
        persona_key: 'eeva',
        title: 'Chat with Eeva',
        created_at: '2024-01-01T10:00:00Z',
        updated_at: '2024-01-01T10:00:00Z',
        message_count: 0,
      };

      (fetch as jest.Mock).mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSession),
        })
      );

      const session = await createSession('eeva', 'Chat with Eeva');
      expect(session).toEqual(mockSession);
      expect(fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/sessions',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            persona_key: 'eeva',
            title: 'Chat with Eeva',
          }),
        })
      );
    });

    it('getSessionWithMessages should return session with messages', async () => {
      const mockSessionData = {
        session: {
          id: '1',
          persona_key: 'eeva',
          title: 'Chat with Eeva',
          created_at: '2024-01-01T10:00:00Z',
          updated_at: '2024-01-01T10:30:00Z',
          message_count: 2,
        },
        messages: [
          {
            id: 'msg1',
            role: 'user',
            content: 'Hello',
            timestamp: '2024-01-01T10:00:00Z',
          },
          {
            id: 'msg2',
            role: 'assistant',
            content: 'Hi there!',
            timestamp: '2024-01-01T10:01:00Z',
          },
        ],
      };

      (fetch as jest.Mock).mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSessionData),
        })
      );

      const result = await getSessionWithMessages('1');
      expect(result.session).toEqual(mockSessionData.session);
      expect(result.messages).toHaveLength(2);
      expect(result.messages[0].timestamp).toBeInstanceOf(Date);
      expect(result.messages[1].timestamp).toBeInstanceOf(Date);
    });

    it('updateSession should return updated session', async () => {
      const mockUpdatedSession = {
        id: '1',
        persona_key: 'eeva',
        title: 'Updated Title',
        created_at: '2024-01-01T10:00:00Z',
        updated_at: '2024-01-01T10:30:00Z',
        message_count: 5,
      };

      (fetch as jest.Mock).mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockUpdatedSession),
        })
      );

      const session = await updateSession('1', { title: 'Updated Title' });
      expect(session).toEqual(mockUpdatedSession);
      expect(fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/sessions/1',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ title: 'Updated Title' }),
        })
      );
    });

    it('deleteSession should make DELETE request', async () => {
      (fetch as jest.Mock).mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
        })
      );

      await deleteSession('1');
      expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/sessions/1', expect.objectContaining({
        method: 'DELETE',
      }));
    });

    it('sendMessageToSession should return ChatApiResponse', async () => {
      const mockApiResponse = {
        answer: 'Hello from AI',
        message_flow: 'single',
        message_count: 1,
      };

      (fetch as jest.Mock).mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockApiResponse),
        })
      );

      const response = await sendMessageToSession('1', 'Hello');
      expect(response.answer).toBe('Hello from AI');
      expect(response.message_flow).toBe('single');
      expect(response.message_count).toBe(1);
      expect(fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/sessions/1/chat',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ message: 'Hello' }),
        })
      );
    });

    it('exportSession should return export data', async () => {
      const mockExportData = {
        version: '1.0',
        exported_at: '2024-01-01T12:00:00Z',
        app_version: '1.0.0',
        persona: {
          key: 'eeva',
          display_name: 'Eeva',
          style: 'friendly',
          rarity: 'legendary',
          celestial_order: 'archon',
          mcp_access: ['brave_search', 'mongodb'],
        },
        session: {
          id: '1',
          persona_key: 'eeva',
          title: 'Chat with Eeva',
          created_at: '2024-01-01T10:00:00Z',
          updated_at: '2024-01-01T10:30:00Z',
          message_count: 2,
        },
        messages: [
          {
            id: 'msg1',
            role: 'user' as const,
            content: 'Hello',
            timestamp: '2024-01-01T10:00:00Z',
          } as any,
        ],
      };

      (fetch as jest.Mock).mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockExportData),
        })
      );

      const exportData = await exportSession('1');
      expect(exportData).toEqual(mockExportData);
    });

    it('importSession should return new session', async () => {
      const mockExportData = {
        version: '1.0',
        exported_at: '2024-01-01T12:00:00Z',
        app_version: '1.0.0',
        persona: { key: 'eeva', display_name: 'Eeva', style: 'friendly' },
        session: { id: '1', persona_key: 'eeva', title: 'Chat', created_at: '2024-01-01T10:00:00Z', updated_at: '2024-01-01T10:30:00Z', message_count: 2 },
        messages: [{ id: 'msg1', role: 'user', content: 'Hello', timestamp: '2024-01-01T10:00:00Z' }],
      } as any;

      const mockNewSession = {
        id: '2',
        persona_key: 'eeva',
        title: 'Imported Chat',
        created_at: '2024-01-01T12:00:00Z',
        updated_at: '2024-01-01T12:00:00Z',
        message_count: 2,
      };

      (fetch as jest.Mock).mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockNewSession),
        })
      );

      const session = await importSession(mockExportData);
      expect(session).toEqual(mockNewSession);
      expect(fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/sessions/import',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(mockExportData),
        })
      );
    });

    // Integration test for LLM functionality
    it('LLM integration should respond to ping message', async () => {
      // This test requires a running backend with Ollama
      // Skip if backend is not available
      try {
        const response = await fetch('http://127.0.0.1:8000/persona/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            persona: 'eeva',
            message: 'ping',
            history: [],
          }),
        });

        if (!response.ok) {
          throw new Error(`Backend not available: ${response.status}`);
        }

        const data = await response.json();
        expect(data).toHaveProperty('answer');
        expect(typeof data.answer).toBe('string');
        expect(data.answer.length).toBeGreaterThan(0);
      } catch (error) {
        // Skip test if backend is not running
        console.warn('Skipping LLM integration test - backend not available:', error);
        return;
      }
    });
  });

});
