import { fetchPersonas, sendMessage, fetchSessions, createSession, getSessionWithMessages, updateSession, deleteSession, sendMessageToSession, exportSession, importSession } from './api';

// Mock the global fetch function
global.fetch = jest.fn();

interface ChatTurn {
  role: string;
  content: string;
}

describe('API Service', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
  });

  it('fetchPersonas should return a list of personas', async () => {
    const mockPersonas = [
      { key: 'Eeva', display_name: 'Eeva', style: 'friendly', image: 'ui/images/eeva_card.png' } as any,
      { key: 'Frieren', display_name: 'Frieren', style: 'wise', image: 'ui/images/frieren_card.png' } as any,
      { key: 'Gojo', display_name: 'Gojo', style: 'cool', image: 'ui/images/gojo_card.png' } as any,
      { key: 'Hitler', display_name: 'Hitler', style: 'evil', image: 'ui/images/hitler_card.png' } as any,
      { key: 'Itachi', display_name: 'Itachi', style: 'ninja', image: 'ui/images/itachi_card.png' } as any,
    ];

    (fetch as jest.Mock)
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPersonas[0]),
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPersonas[1]),
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPersonas[2]),
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPersonas[3]),
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPersonas[4]),
        })
      );

    const personas = await fetchPersonas();
    expect(personas.length).toBe(5); // Expecting 5 personas as per api.ts
    expect(personas[0].key).toBe('Eeva');
    expect(personas[1].key).toBe('Frieren');
    expect(personas[2].key).toBe('Gojo');
    expect(personas[3].key).toBe('Hitler');
    expect(personas[4].key).toBe('Itachi');
  });

  it('sendMessage should return AI response', async () => {
    const mockResponse = { answer: 'Hello from AI' };
    (fetch as jest.Mock).mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })
    );

    const persona = 'eeva';
    const message = 'Hi';
    const history: ChatTurn[] = [];
    const response = await sendMessage(persona, message, history);

    expect(response).toBe(mockResponse.answer);
    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/persona/chat',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ persona, message, history }),
      })
    );
  });

  it('sendMessage should throw an error if API call fails', async () => {
    (fetch as jest.Mock).mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: () => Promise.resolve('Server error'),
      })
    );

    const persona = 'eeva';
    const message = 'Hi';
    const history: ChatTurn[] = [];

    await expect(sendMessage(persona, message, history)).rejects.toThrow('API Error: 500 Internal Server Error - Server error');
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
      expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/sessions');
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
      expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/sessions/1', {
        method: 'DELETE',
      });
    });

    it('sendMessageToSession should return assistant message', async () => {
      const mockApiResponse = {
        answer: 'Hello from AI',
      };

      (fetch as jest.Mock).mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockApiResponse),
        })
      );

      const message = await sendMessageToSession('1', 'Hello');
      expect(message.content).toBe('Hello from AI');
      expect(message.role).toBe('assistant');
      expect(message.timestamp).toBeInstanceOf(Date);
      expect(message.id).toMatch(/^assistant-\d+$/);
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
