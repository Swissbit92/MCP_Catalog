import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface StrategyConfig {
  strategy_id: string
  strategy_type: 'RSIStrategy' | 'DCAStrategy'
  name: string
  token_pair: {
    from_token: string
    to_token: string
  }
  parameters: Record<string, any>
  risk_management: {
    stop_loss_pct?: number
    take_profit_pct?: number
  }
  guardrails: {
    max_trade_size_usdc: number
    daily_limit_usdc: number
  }
}

interface StrategyProposal {
  proposal_id: string
  proposal_type: 'strategy'
  user_id: string
  strategy_config: StrategyConfig
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
}

interface StrategyApprovalCardProps {
  proposal: StrategyProposal
  onApprove: (proposalId: string, strategyConfig: StrategyConfig) => Promise<void>
  onReject: (proposalId: string) => void
}

export default function StrategyApprovalCard({ proposal, onApprove, onReject }: StrategyApprovalCardProps) {
  const [status, setStatus] = useState(proposal.status)
  const [isLoading, setIsLoading] = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const config = proposal.strategy_config
  const isPending = status === 'pending'

  const handleApprove = async () => {
    setIsLoading(true)
    setError(null)
    try {
      await onApprove(proposal.proposal_id, config)
      setStatus('approved')
    } catch (e: any) {
      setError(e.message || 'Approval failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleReject = () => {
    onReject(proposal.proposal_id)
    setStatus('rejected')
  }

  const strategyTypeLabel =
    config.strategy_type === 'RSIStrategy' ? '\uD83D\uDCCA RSI Strategy' : '\uD83D\uDCC5 DCA Strategy'

  const renderParams = () => {
    const p = config.parameters
    if (config.strategy_type === 'RSIStrategy') {
      return (
        <>
          <Row label="RSI Period" value={p.rsi_period ?? 14} />
          <Row label="Buy below RSI" value={p.oversold_threshold ?? 30} highlight="green" />
          <Row label="Sell above RSI" value={p.overbought_threshold ?? 70} highlight="red" />
          <Row label="Timeframe" value={p.timeframe ?? '1d'} />
          <Row label="Check every" value={`${p.check_interval_minutes ?? 240} min`} />
        </>
      )
    }
    return (
      <>
        <Row label="Amount/cycle" value={`${p.amount_per_cycle_usdc ?? 20} USDC`} />
        <Row
          label="Frequency"
          value={`Every ${(p.cycle_frequency_hours ?? 168) / 24} days`}
        />
      </>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3 }}
      className="my-3 rounded-2xl border border-yellow-400/40 bg-black/50 backdrop-blur-xl overflow-hidden"
      style={{ fontFamily: 'Manrope, sans-serif' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-yellow-400/20 bg-yellow-400/5">
        <div className="flex items-center gap-2">
          <span className="text-yellow-400 text-lg" role="img" aria-label="Strategy">&#129302;</span>
          <div>
            <div
              className="text-yellow-400 font-semibold text-sm"
              style={{ fontFamily: 'Outfit, sans-serif' }}
            >
              Strategy Approval Required
            </div>
            <div className="text-white/50 text-xs">{strategyTypeLabel}</div>
          </div>
        </div>
        {status === 'approved' && (
          <span className="text-green-400 text-xs font-semibold"><span aria-hidden="true">&#10003;</span> Active</span>
        )}
        {status === 'rejected' && (
          <span className="text-red-400 text-xs font-semibold"><span aria-hidden="true">&#10005;</span> Rejected</span>
        )}
      </div>

      <div className="px-4 py-4">
        {/* Strategy name + pair */}
        <div className="mb-4">
          <div className="text-white font-bold text-base mb-1">{config.name}</div>
          <div className="text-white/50 text-sm">
            {config.token_pair.from_token} &#8594; {config.token_pair.to_token}
          </div>
        </div>

        {/* Guardrails summary */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          <GuardrailBadge label="Per trade" value={`${config.guardrails.max_trade_size_usdc} USDC`} />
          <GuardrailBadge label="Daily limit" value={`${config.guardrails.daily_limit_usdc} USDC`} />
          {config.risk_management.stop_loss_pct !== undefined && (
            <GuardrailBadge
              label="Stop-loss"
              value={`${config.risk_management.stop_loss_pct}%`}
              color="red"
            />
          )}
          {config.risk_management.take_profit_pct !== undefined && (
            <GuardrailBadge
              label="Take-profit"
              value={`${config.risk_management.take_profit_pct}%`}
              color="green"
            />
          )}
        </div>

        {/* Expandable details */}
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-white/40 text-xs hover:text-white/60 mb-3 flex items-center gap-1"
          aria-expanded={showDetails}
          aria-controls="strategy-params"
        >
          <span aria-hidden="true">{showDetails ? '▲' : '▼'}</span> {showDetails ? 'Hide' : 'Show'} parameters
        </button>
        <AnimatePresence>
          {showDetails && (
            <motion.div
              id="strategy-params"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden mb-3"
            >
              <div className="bg-white/5 rounded-xl px-3 py-3 space-y-1.5">
                {renderParams()}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Approval note */}
        {isPending && (
          <div className="bg-yellow-400/10 rounded-xl px-3 py-2 mb-4 text-yellow-400/80 text-xs">
            Approving enables autonomous trading within the guardrails above.
            Say &quot;pause [strategy name]&quot; anytime to stop.
          </div>
        )}

        {error && (
          <div className="mb-3 text-red-400 text-xs bg-red-500/10 rounded-lg px-3 py-2">{error}</div>
        )}

        {/* Actions */}
        {isPending && (
          <div className="flex gap-3">
            <button
              onClick={handleApprove}
              disabled={isLoading}
              className="flex-1 py-2.5 rounded-xl bg-yellow-400/20 border border-yellow-400/40 text-yellow-400 font-semibold text-sm hover:bg-yellow-400/30 transition-colors disabled:opacity-50"
              aria-label="Approve strategy"
            >
              {isLoading ? 'Activating...' : <><span aria-hidden="true">&#10003;</span> Approve Strategy</>}
            </button>
            <button
              onClick={handleReject}
              disabled={isLoading}
              className="flex-1 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white/60 font-semibold text-sm hover:bg-white/10 transition-colors"
              aria-label="Reject strategy"
            >
              <span aria-hidden="true">&#10005;</span> Reject
            </button>
          </div>
        )}
      </div>
    </motion.div>
  )
}

function Row({
  label,
  value,
  highlight,
}: {
  label: string
  value: any
  highlight?: 'green' | 'red'
}) {
  const valueClass =
    highlight === 'green'
      ? 'text-green-400'
      : highlight === 'red'
      ? 'text-red-400'
      : 'text-white/80'
  return (
    <div className="flex justify-between text-xs">
      <span className="text-white/50">{label}</span>
      <span className={`font-semibold ${valueClass}`}>{String(value)}</span>
    </div>
  )
}

function GuardrailBadge({
  label,
  value,
  color,
}: {
  label: string
  value: string
  color?: 'green' | 'red'
}) {
  const bg =
    color === 'green'
      ? 'bg-green-500/10 border-green-500/20'
      : color === 'red'
      ? 'bg-red-500/10 border-red-500/20'
      : 'bg-white/5 border-white/10'
  const text =
    color === 'green'
      ? 'text-green-400'
      : color === 'red'
      ? 'text-red-400'
      : 'text-white/80'
  return (
    <div className={`rounded-lg border px-3 py-2 ${bg}`}>
      <div className="text-white/40 text-xs">{label}</div>
      <div className={`font-bold text-sm ${text}`}>{value}</div>
    </div>
  )
}
