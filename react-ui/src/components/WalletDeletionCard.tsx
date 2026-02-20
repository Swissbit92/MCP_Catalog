import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

interface WalletDeletionProposal {
  proposal_id: string
  proposal_type: 'wallet_deletion'
  user_id: string
  wallet_name: string
  public_address: string
  status: 'pending' | 'confirmed' | 'cancelled' | 'expired'
  created_at: string
  expires_at: string
}

interface WalletDeletionCardProps {
  proposal: WalletDeletionProposal
  onConfirm: (userId: string) => Promise<void>
  onCancel: (proposalId: string) => void
}

export default function WalletDeletionCard({ proposal, onConfirm, onCancel }: WalletDeletionCardProps) {
  const [status, setStatus] = useState(proposal.status)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [timeLeft, setTimeLeft] = useState<number>(300)

  useEffect(() => {
    if (status !== 'pending') return
    const expires = new Date(proposal.expires_at).getTime()
    const tick = () => {
      const remaining = Math.max(0, Math.floor((expires - Date.now()) / 1000))
      setTimeLeft(remaining)
      if (remaining === 0) setStatus('expired')
    }
    tick()
    const interval = setInterval(tick, 1000)
    return () => clearInterval(interval)
  }, [proposal.expires_at, status])

  const handleConfirm = async () => {
    setIsLoading(true)
    setError(null)
    try {
      await onConfirm(proposal.user_id)
      setStatus('confirmed')
    } catch (e: any) {
      setError(e.message || 'Deletion failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCancel = () => {
    onCancel(proposal.proposal_id)
    setStatus('cancelled')
  }

  const formatTimer = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
  const timerColor = timeLeft < 30 ? 'text-red-400' : timeLeft < 60 ? 'text-orange-400' : 'text-white/60'

  const isPending = status === 'pending'
  const shortAddr = proposal.public_address.length > 12
    ? `${proposal.public_address.slice(0, 8)}...${proposal.public_address.slice(-4)}`
    : proposal.public_address

  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3 }}
      className="my-3 rounded-2xl border border-red-400/30 bg-white/[0.05] backdrop-blur-xl overflow-hidden"
      style={{ fontFamily: 'Manrope, sans-serif' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <span className="text-red-400 text-lg" aria-hidden="true">&#9888;</span>
          <span className="text-red-400 font-semibold text-sm" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Wallet Deletion
          </span>
        </div>
        {isPending && (
          <span className={`${timerColor} text-xs font-mono transition-colors`}>
            Expires {formatTimer(timeLeft)}
          </span>
        )}
        {status === 'confirmed' && <span className="text-green-400 text-xs font-semibold">&#10003; Deleted</span>}
        {status === 'cancelled' && <span className="text-white/60 text-xs font-semibold">&#10005; Cancelled</span>}
        {status === 'expired' && <span className="text-white/60 text-xs">Expired</span>}
      </div>

      {/* Wallet details */}
      <div className="px-4 py-4">
        <div className="mb-3">
          <div className="text-white/60 text-xs mb-1">Wallet</div>
          <div className="text-white font-bold text-lg">{proposal.wallet_name}</div>
          <div className="text-white/50 text-sm font-mono mt-1">{shortAddr}</div>
        </div>

        <div className="text-red-300/80 text-xs mb-4 bg-red-500/10 rounded-lg px-3 py-2">
          This action is irreversible. Transfer any remaining funds before confirming.
        </div>

        {error && (
          <div className="mb-3 text-red-400 text-xs bg-red-500/10 rounded-lg px-3 py-2">{error}</div>
        )}

        {/* Actions */}
        {isPending && (
          <div className="flex gap-3">
            <button
              onClick={handleConfirm}
              disabled={isLoading || timeLeft === 0}
              className="flex-1 py-2.5 rounded-xl bg-red-500/20 border border-red-500/40 text-red-400 font-semibold text-sm hover:bg-red-500/30 focus:ring-2 focus:ring-red-400/50 focus:outline-none transition-colors disabled:opacity-50"
              aria-label="Confirm wallet deletion"
            >
              {isLoading ? 'Deleting...' : <><span aria-hidden="true">&#9888;</span> Confirm Delete</>}
            </button>
            <button
              onClick={handleCancel}
              disabled={isLoading}
              className="flex-1 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white/60 font-semibold text-sm hover:bg-white/10 focus:ring-2 focus:ring-white/20 focus:outline-none transition-colors disabled:opacity-50"
              aria-label="Cancel wallet deletion"
            >
              <span aria-hidden="true">&#10005;</span> Cancel
            </button>
          </div>
        )}
      </div>
    </motion.div>
  )
}
