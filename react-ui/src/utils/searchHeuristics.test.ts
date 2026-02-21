import { predictWebSearch, formatPredictionLog } from './searchHeuristics';

describe('predictWebSearch', () => {
  describe('Search keyword detection', () => {
    it('predicts search for current stock price queries', () => {
      const result = predictWebSearch('What is the current price of Tesla stock?', 'epic');
      expect(result.willSearch).toBe(true);
      expect(result.confidence).toBe('high');
      expect(result.keywords_matched).toContain('current');
      expect(result.keywords_matched).toContain('price');
    });

    it('predicts search for latest news queries', () => {
      const result = predictWebSearch('What is the latest news on AI?', 'rare');
      expect(result.willSearch).toBe(true);
      expect(result.confidence).toBe('high');
      expect(result.keywords_matched).toContain('latest');
      expect(result.keywords_matched).toContain('news');
    });

    it('predicts search for current/last year queries', () => {
      const year = new Date().getFullYear();
      const result = predictWebSearch(`Who won the ${year} election?`, 'legendary');
      expect(result.willSearch).toBe(true);
      expect(result.confidence).toBe('high');
      expect(result.keywords_matched).toContain(String(year));
    });
  });

  describe('No-search keyword detection', () => {
    it('predicts no search for math queries', () => {
      const result = predictWebSearch('What is 2+2?', 'epic');
      expect(result.willSearch).toBe(false);
      expect(result.confidence).toBe('high');
    });

    it('predicts no search for calculation queries', () => {
      const result = predictWebSearch('Calculate 15% of 200', 'legendary');
      expect(result.willSearch).toBe(false);
      expect(result.confidence).toBe('high');
      expect(result.keywords_matched).toContain('calculate');
    });

    it('predicts no search for definition queries', () => {
      const result = predictWebSearch('Define blockchain technology', 'rare');
      expect(result.willSearch).toBe(false);
      expect(result.confidence).toBe('high');
      expect(result.keywords_matched).toContain('define');
    });
  });

  describe('MongoDB keyword detection', () => {
    it('predicts no search for Bitcoin price queries (epic persona)', () => {
      const result = predictWebSearch('What is the Bitcoin price?', 'epic');
      expect(result.willSearch).toBe(false);
      expect(result.confidence).toBe('high');
      expect(result.reason).toContain('MongoDB');
    });
  });

  describe('Rarity-based access control', () => {
    it('blocks search for common personas', () => {
      const result = predictWebSearch('What is the latest news?', 'common');
      expect(result.willSearch).toBe(false);
      expect(result.reason).toContain('does not have web search access');
    });

    it('allows search for rare personas', () => {
      const result = predictWebSearch('What is the latest news?', 'rare');
      expect(result.willSearch).toBe(true);
    });
  });

  describe('Math pattern detection', () => {
    it('detects simple addition', () => {
      const result = predictWebSearch('2+2', 'epic');
      expect(result.willSearch).toBe(false);
      expect(result.reason).toContain('math calculation');
    });
  });
});

describe('formatPredictionLog', () => {
  it('formats prediction log correctly', () => {
    const prediction = {
      willSearch: true,
      confidence: 'high' as const,
      reason: 'Search keywords detected',
      keywords_matched: ['latest', 'news'],
      toolType: 'brave' as const
    };

    const log = formatPredictionLog(prediction, 'What is the latest news?');

    expect(log).toContain('[SearchHeuristic]');
    expect(log).toContain('Prediction: SEARCH');
    expect(log).toContain('Confidence: high');
  });
});
