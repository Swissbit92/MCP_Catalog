// src/components/nephilim/mcpNarratives.ts
/**
 * NEPHILIM MCP Narrative Configuration
 *
 * Maps MCP tool capabilities to immersive NEPHILIM narrative framing.
 * Used throughout the UI to transform technical features into story elements.
 */

// Source type narrative mappings
export interface NephilimSourceNarrative {
  patron: string           // Which Nephilim "owns" this power
  patronKey: string        // Persona key for styling
  narrativeName: string    // In-universe name
  icon: string            // Emoji icon
  color: string           // Hex color
  description: string     // Brief description
  accessingMessage: string // Loading state message
  completedMessage: string // Success message
}

export const NEPHILIM_SOURCE_NARRATIVES: Record<string, NephilimSourceNarrative> = {
  brave_mcp: {
    patron: 'Cipher',
    patronKey: 'nephilim_cipher',
    narrativeName: 'The Outer Archives',
    icon: '📚',
    color: '#2ecc71',
    description: 'Knowledge from the Outer Web',
    accessingMessage: 'Cipher consults the Archives...',
    completedMessage: 'Cipher found relevant knowledge',
  },
  mongodb_mcp: {
    patron: 'Aurora',
    patronKey: 'nephilim_aurora',
    narrativeName: 'The Crystal Grid',
    icon: '🔮',
    color: '#f39c12',
    description: 'Visions of market currents',
    accessingMessage: 'Aurora gazes into the Crystal Grid...',
    completedMessage: 'Aurora reveals the market visions',
  },
  multi_mcp: {
    patron: 'E.E.V.A.',
    patronKey: 'nephilim_eeva',
    narrativeName: 'Converged Insight',
    icon: '✧',
    color: '#e0c3fc',
    description: 'Multiple powers combined',
    accessingMessage: 'The Nephilim pool their knowledge...',
    completedMessage: 'The Convergence is complete',
  },
  llm: {
    patron: 'Self',
    patronKey: '',
    narrativeName: 'Inner Wisdom',
    icon: '💭',
    color: '#b07cc6',
    description: 'Pure insight from within',
    accessingMessage: 'Drawing upon inner wisdom...',
    completedMessage: 'Insight revealed',
  },
  wallet_mcp: {
    patron: 'E.E.V.A.',
    patronKey: 'nephilim_eeva',
    narrativeName: 'The Solana Nexus',
    icon: '⚡',
    color: '#FFD700',
    description: 'Solana wallet & Jupiter DEX operations',
    accessingMessage: 'E.E.V.A. channels the Solana streams...',
    completedMessage: 'The Nexus responds',
  },
  wallet_proposal: {
    patron: 'E.E.V.A.',
    patronKey: 'nephilim_eeva',
    narrativeName: 'Trade Proposal',
    icon: '⚡',
    color: '#FFD700',
    description: 'Awaiting your confirmation',
    accessingMessage: 'E.E.V.A. prepares the transaction...',
    completedMessage: 'Proposal ready for confirmation',
  },
  wallet_flow: {
    patron: 'E.E.V.A.',
    patronKey: 'nephilim_eeva',
    narrativeName: 'Wallet Setup',
    icon: '🔑',
    color: '#FFD700',
    description: 'Guided wallet creation',
    accessingMessage: 'E.E.V.A. prepares your vault...',
    completedMessage: 'Wallet ritual complete',
  },
}

// Tool-specific narrative mappings
export interface NephilimToolNarrative {
  narrativeName: string
  action: string
}

export const NEPHILIM_TOOL_NARRATIVES: Record<string, NephilimToolNarrative> = {
  brave_web_search: {
    narrativeName: 'Archive Query',
    action: 'searching the Archives',
  },
  bitcoin_current_price: {
    narrativeName: 'Price Vision',
    action: 'reading current price flows',
  },
  bitcoin_historical_prices: {
    narrativeName: 'Temporal Price Trace',
    action: 'tracing historical patterns',
  },
  bitcoin_market_analysis: {
    narrativeName: 'Market Divination',
    action: 'divining market sentiment',
  },
  bitcoin_portfolio_analysis: {
    narrativeName: 'Portfolio Scrying',
    action: 'scrying portfolio health',
  },
  // Jupiter Wallet tools
  wallet_get_balances: {
    narrativeName: 'Vault Scan',
    action: 'scanning your vault holdings',
  },
  wallet_create_guided: {
    narrativeName: 'Vault Ritual',
    action: 'initiating wallet creation ritual',
  },
  solana_get_quote: {
    narrativeName: 'Exchange Vision',
    action: 'reading Jupiter exchange rates',
  },
  solana_rsi_check: {
    narrativeName: 'Signal Reading',
    action: 'reading momentum signals',
  },
  solana_propose_swap: {
    narrativeName: 'Trade Proposal',
    action: 'preparing a trade proposal',
  },
  solana_propose_strategy: {
    narrativeName: 'Strategy Ritual',
    action: 'designing an autonomous strategy',
  },
  solana_trade_history: {
    narrativeName: 'Trade Chronicle',
    action: 'consulting the trade chronicle',
  },
}

// Loading state messages for different operations
export const NEPHILIM_LOADING_MESSAGES = {
  search: [
    'Cipher consults the infinite Archives...',
    'Scanning dimensional knowledge streams...',
    'The Archives reveal their secrets...',
    'Cipher deciphers the threads of information...',
  ],
  trading: [
    'Aurora gazes into the Crystal Grid...',
    'Market currents shimmer into view...',
    'The Crystal Grid pulses with data...',
    'Aurora reads the flow of value...',
  ],
  thinking: [
    'Contemplating the depths of wisdom...',
    'Drawing upon ancient knowledge...',
    'The answer takes shape...',
    'Insight crystallizes...',
  ],
  multi: [
    'The Nephilim share their visions...',
    'Powers converge at the Nexus...',
    'Multiple insights merge into clarity...',
    'The Convergence unfolds...',
  ],
}

// Get a random loading message for a source type
export const getRandomLoadingMessage = (sourceType: string): string => {
  let messages: string[]

  switch (sourceType) {
    case 'brave_mcp':
      messages = NEPHILIM_LOADING_MESSAGES.search
      break
    case 'mongodb_mcp':
      messages = NEPHILIM_LOADING_MESSAGES.trading
      break
    case 'multi_mcp':
      messages = NEPHILIM_LOADING_MESSAGES.multi
      break
    default:
      messages = NEPHILIM_LOADING_MESSAGES.thinking
  }

  return messages[Math.floor(Math.random() * messages.length)]
}

// Check if a persona key is a NEPHILIM persona
export const isNephilimPersona = (personaKey?: string): boolean => {
  return personaKey?.startsWith('nephilim_') ?? false
}

// Get the narrative label/description for a source type
export const getSourceNarrative = (
  sourceType: string,
): { label: string; description: string; icon: string; color: string } => {
  const labels: Record<string, { label: string; description: string; icon: string; color: string }> = {
    llm: { label: 'Inner Wisdom', description: 'Generated by AI', icon: '🧠', color: '#b07cc6' },
    brave_mcp: { label: 'The Outer Archives', description: 'Web search results', icon: '🔍', color: '#3b82f6' },
    mongodb_mcp: { label: 'The Crystal Grid', description: 'Market data', icon: '📊', color: '#22c55e' },
    multi_mcp: { label: 'Converged Insight', description: 'Combined sources', icon: '🔗', color: '#f97316' },
    wallet_mcp: { label: 'The Solana Nexus', description: 'Solana wallet operations', icon: '⚡', color: '#FFD700' },
    wallet_proposal: { label: 'Trade Proposal', description: 'Pending confirmation', icon: '⚡', color: '#FFD700' },
    wallet_flow: { label: 'Wallet Setup', description: 'Guided wallet creation', icon: '🔑', color: '#FFD700' },
  }
  return labels[sourceType] || labels.llm
}

// Format tool name for display
export const formatToolNarrative = (toolName: string): string => {
  return toolName.replace('bitcoin_', '').replace(/_/g, ' ')
}
