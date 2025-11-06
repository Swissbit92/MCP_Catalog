import { fetchPersonas, sendMessage } from './api';

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
      })
    );

    const persona = 'eeva';
    const message = 'Hi';
    const history: ChatTurn[] = [];

    await expect(sendMessage(persona, message, history)).rejects.toThrow('Failed to send message');
  });
});
