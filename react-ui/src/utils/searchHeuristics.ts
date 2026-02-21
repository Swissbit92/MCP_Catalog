/**
 * Client-side heuristics for predicting when web search will be triggered.
 * Mirrors backend keyword logic from src/coordinator/tool_definitions.py
 *
 * This is used to show SearchIndicator proactively before backend responds.
 * Accuracy: ~85-90% (matches backend keyword filtering)
 */

// Keywords that indicate NO web search needed (math, definitions, general knowledge)
const NO_SEARCH_KEYWORDS = [
  // Math/calculations
  'calculate', 'compute', 'what is', 'plus', 'minus', 'multiply', 'divide',
  'addition', 'subtraction', 'multiplication', 'division', 'equals',

  // Definitions/explanations (but allow if combined with data/opinion keywords)
  'define', 'definition', 'meaning of', 'explain what',
  'what are', 'what is a', 'explain the concept',

  // How-to (general knowledge)
  'how to', 'how do i', 'how does', 'how can i',

  // Common knowledge
  'who is', 'who was', 'what was', 'where is', 'when was',
  'capital of', 'president of', 'history of'
];

// Keywords that indicate web search IS needed
const SEARCH_KEYWORDS = [
  // Current/recent information
  'current', 'latest', 'recent', 'today', 'now', 'this week', 'this month',
  String(new Date().getFullYear()), String(new Date().getFullYear() - 1), 'breaking', 'update', 'news',

  // Market/price data
  'price', 'cost', 'worth', 'value', 'stock market', 'nasdaq', 'dow jones',

  // Events
  'election', 'vote', 'results', 'winner', 'outcome', 'happened',

  // Weather/conditions
  'weather', 'temperature', 'forecast', 'climate',

  // Trending/popularity
  'trending', 'trend', 'popular', 'viral', 'hot topic', 'buzz',

  // Happening/current events
  'happening', 'occurring', 'going on', "what's new", 'new with',
  'latest on', 'developments', 'progress',

  // Expert opinions/predictions
  'saying', 'experts say', 'analysts say', 'predictions',
  'forecasts', 'outlook', 'opinions', 'views', 'thoughts on',
  'expect', 'expecting', 'anticipated',

  // Social/community sentiment
  'talking about', 'discussing', 'debate', 'community',
  'twitter', 'reddit', 'social', 'sentiment', 'mood', 'feeling about',

  // Market commentary
  'commentary', 'analysis article', 'opinion piece',
  'market watch', 'crypto watch'
];

// MongoDB-specific keywords (epic/legendary personas only)
const MONGODB_KEYWORDS = [
  'bitcoin price', 'btc price', 'price of bitcoin',
  'bitcoin cost', 'btc cost', 'how much is bitcoin',
  'rsi', 'macd', 'bollinger', 'technical indicator',
  'my portfolio', 'my bitcoin', 'bought', 'purchased', 'dca'
];

export interface SearchPrediction {
  willSearch: boolean;
  confidence: 'high' | 'medium' | 'low';
  reason: string;
  keywords_matched: string[];
  toolType: 'brave' | 'mongodb' | 'none';
}

/**
 * Predict if a query will trigger web search based on keywords.
 *
 * @param query - User's message
 * @param personaRarity - Persona rarity (common/rare/epic/legendary)
 * @returns Prediction object with confidence level
 */
export function predictWebSearch(query: string, personaRarity?: string): SearchPrediction {
  const queryLower = query.toLowerCase();
  const matchedSearchKeywords: string[] = [];
  const matchedNoSearchKeywords: string[] = [];
  const matchedMongoKeywords: string[] = [];

  // Check for MongoDB keywords (epic/legendary only)
  const canUseMongoDB = personaRarity === 'epic' || personaRarity === 'legendary';
  if (canUseMongoDB) {
    for (const keyword of MONGODB_KEYWORDS) {
      if (queryLower.includes(keyword)) {
        matchedMongoKeywords.push(keyword);
      }
    }
  }

  // Check for no-search keywords
  for (const keyword of NO_SEARCH_KEYWORDS) {
    if (queryLower.includes(keyword)) {
      matchedNoSearchKeywords.push(keyword);
    }
  }

  // Check for search keywords
  for (const keyword of SEARCH_KEYWORDS) {
    if (queryLower.includes(keyword)) {
      matchedSearchKeywords.push(keyword);
    }
  }

  // Decision logic (mirrors backend tool_definitions.py)

  // MongoDB queries don't need web search
  if (matchedMongoKeywords.length > 0) {
    return {
      willSearch: false,
      confidence: 'high',
      reason: 'MongoDB query detected (will use database, not web search)',
      keywords_matched: matchedMongoKeywords,
      toolType: 'mongodb'
    };
  }

  // Queries with search keywords will search (even if they have definition keywords)
  if (matchedSearchKeywords.length > 0) {
    const canUseBrave = ['rare', 'epic', 'legendary'].includes(personaRarity || 'common');

    if (!canUseBrave) {
      return {
        willSearch: false,
        confidence: 'high',
        reason: 'Persona does not have web search access',
        keywords_matched: [],
        toolType: 'none'
      };
    }

    return {
      willSearch: true,
      confidence: 'high',
      reason: `Search keywords detected: ${matchedSearchKeywords.slice(0, 3).join(', ')}`,
      keywords_matched: matchedSearchKeywords,
      toolType: 'brave'
    };
  }

  // Queries with definition/math keywords won't search
  if (matchedNoSearchKeywords.length > 0) {
    return {
      willSearch: false,
      confidence: 'high',
      reason: `Educational/math query: ${matchedNoSearchKeywords[0]}`,
      keywords_matched: matchedNoSearchKeywords,
      toolType: 'none'
    };
  }

  // Check for simple math patterns (e.g., "2+2", "15% of 200")
  const mathPattern = /^\d+[\s]*[+\-*/÷×%][\s]*\d+|^\d+%\s+of\s+\d+/i;
  if (mathPattern.test(query.trim())) {
    return {
      willSearch: false,
      confidence: 'high',
      reason: 'Simple math calculation detected',
      keywords_matched: [],
      toolType: 'none'
    };
  }

  // Uncertain - let LLM decide (default to no search indicator)
  return {
    willSearch: false,
    confidence: 'low',
    reason: 'No clear indicators, defaulting to typing indicator',
    keywords_matched: [],
    toolType: 'none'
  };
}

/**
 * Format search prediction for logging.
 */
export function formatPredictionLog(prediction: SearchPrediction, query: string): string {
  return `[SearchHeuristic] Query: "${query.substring(0, 50)}..." | ` +
         `Prediction: ${prediction.willSearch ? 'SEARCH' : 'NO-SEARCH'} | ` +
         `Confidence: ${prediction.confidence} | ` +
         `Reason: ${prediction.reason}`;
}
