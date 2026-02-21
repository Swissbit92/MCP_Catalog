// ── Wallet / Jupiter API — Trade proposals and strategies ────────────────────

import { API_BASE_URL } from './base'

// ── Types ────────────────────────────────────────────────────────────────────

export interface TradeProposalResponse {
  proposal_id: string;
  status: 'confirmed' | 'cancelled' | 'expired';
  tx_signature?: string;
  error?: string;
}

export interface StrategyResponse {
  strategy_id: string;
  status: 'active' | 'paused' | 'cancelled';
  message: string;
}

export interface WalletBalance {
  public_address: string;
  sol: number;
  tokens: Array<{ mint: string; symbol: string; amount: number; value_usdc?: number }>;
}

// ── API Functions ────────────────────────────────────────────────────────────

export async function confirmTrade(proposalId: string): Promise<TradeProposalResponse> {
  const res = await fetch(`${API_BASE_URL}/wallet/confirm/${proposalId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || `Confirm failed: ${res.status}`)
  }
  return res.json()
}

export async function cancelTrade(proposalId: string): Promise<TradeProposalResponse> {
  const res = await fetch(`${API_BASE_URL}/wallet/cancel/${proposalId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || `Cancel failed: ${res.status}`)
  }
  return res.json()
}

export async function approveStrategy(
  proposalId: string,
  strategyConfig: Record<string, unknown>
): Promise<StrategyResponse> {
  const res = await fetch(`${API_BASE_URL}/wallet/strategy/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ proposal_id: proposalId, strategy_config: strategyConfig }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || `Approval failed: ${res.status}`)
  }
  return res.json()
}

export async function rejectStrategy(proposalId: string): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE_URL}/wallet/strategy/reject/${proposalId}`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error(`Reject failed: ${res.status}`)
  return res.json()
}

export async function pauseStrategy(strategyId: string): Promise<StrategyResponse> {
  const res = await fetch(`${API_BASE_URL}/wallet/strategy/${strategyId}/pause`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error(`Pause failed: ${res.status}`)
  return res.json()
}

export async function resumeStrategy(strategyId: string): Promise<StrategyResponse> {
  const res = await fetch(`${API_BASE_URL}/wallet/strategy/${strategyId}/resume`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error(`Resume failed: ${res.status}`)
  return res.json()
}

export async function cancelStrategy(strategyId: string): Promise<StrategyResponse> {
  const res = await fetch(`${API_BASE_URL}/wallet/strategy/${strategyId}/cancel`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error(`Cancel failed: ${res.status}`)
  return res.json()
}

export async function listStrategies(userId: string): Promise<{ strategies: Record<string, unknown>[] }> {
  const res = await fetch(`${API_BASE_URL}/wallet/strategies?user_id=${encodeURIComponent(userId)}`)
  if (!res.ok) throw new Error(`List strategies failed: ${res.status}`)
  return res.json()
}

export async function getWalletBalance(userId: string): Promise<WalletBalance> {
  const res = await fetch(`${API_BASE_URL}/wallet/balance/${encodeURIComponent(userId)}`)
  if (!res.ok) throw new Error(`Balance check failed: ${res.status}`)
  return res.json()
}

export async function deleteWallet(userId: string): Promise<{ status: string; public_address: string }> {
  const res = await fetch(`${API_BASE_URL}/wallet/delete/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Deletion failed' }))
    throw new Error(err.detail || `Delete failed: ${res.status}`)
  }
  return res.json()
}
