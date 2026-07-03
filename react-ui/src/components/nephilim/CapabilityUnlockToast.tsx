import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { CapabilityUnlock } from '../../services/api/types'

interface CapabilityUnlockToastProps {
  unlock: CapabilityUnlock | null
  onDismiss: () => void
}

/**
 * NEPHILIM Phase-2 diegetic "capability awakened" beat.
 *
 * A brief, non-interruptive toast shown OUTSIDE the chat bubble when a persona
 * awakens a new internal capability. It is the gamification reward moment — the
 * line is written in the persona's own voice. Deliberately not a browsable menu:
 * after it fades, the capability simply expresses itself in conversation.
 */
export function CapabilityUnlockToast({ unlock, onDismiss }: CapabilityUnlockToastProps) {
  useEffect(() => {
    if (!unlock) return
    const t = setTimeout(onDismiss, 6000)
    return () => clearTimeout(t)
  }, [unlock, onDismiss])

  return (
    <AnimatePresence>
      {unlock && (
        <motion.div
          key={unlock.id}
          initial={{ opacity: 0, y: 24, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 24, scale: 0.96 }}
          transition={{ duration: 0.45, ease: 'easeOut' }}
          className="fixed bottom-24 left-1/2 z-50 -translate-x-1/2 max-w-md px-5 py-4
                     rounded-2xl border border-[#FFD700]/40 bg-black/80 backdrop-blur-md
                     shadow-[0_0_24px_rgba(255,215,0,0.25)] text-center"
          role="status"
          aria-live="polite"
        >
          <div className="text-[11px] uppercase tracking-[0.2em] text-[#FFD700]/80 font-mono">
            Something awakens
          </div>
          <div className="mt-1 text-sm text-white/90 italic font-light">
            &ldquo;{unlock.persona_voice_line}&rdquo;
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
