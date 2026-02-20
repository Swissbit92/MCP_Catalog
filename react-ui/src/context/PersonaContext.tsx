/**
 * PersonaContext -- Backward-compatible composition wrapper.
 *
 * Internally composes ChatContext (conversation state) and CollectionContext
 * (gacha / collection state). The exported `usePersona()` hook merges both
 * contexts so every existing consumer continues to work without changes.
 *
 * New code should prefer the focused hooks:
 *   import { useChat } from './ChatContext'
 *   import { useCollection } from './CollectionContext'
 */

import React, { ReactNode } from 'react'
import { ChatProvider, useChat } from './ChatContext'
import type { ChatContextType } from './ChatContext'
import { CollectionProvider, useCollection } from './CollectionContext'
import type { CollectionContextType } from './CollectionContext'

// Re-export sub-context hooks for direct consumption
export { useChat } from './ChatContext'
export { useCollection } from './CollectionContext'

// Re-export types consumers may need
export type { PullRecord, PullStats, CollectionContextType } from './CollectionContext'
export type { ChatContextType } from './ChatContext'

/**
 * Combined type matching the original PersonaContextType exactly.
 * This keeps all existing destructuring patterns valid.
 */
export type PersonaContextType = ChatContextType & CollectionContextType

/**
 * Composition provider -- wraps both ChatProvider and CollectionProvider.
 * Drop-in replacement for the old monolithic PersonaProvider.
 */
export const PersonaProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <ChatProvider>
      <CollectionProvider>
        {children}
      </CollectionProvider>
    </ChatProvider>
  )
}

/**
 * Backward-compatible hook that returns everything from both contexts.
 * Existing consumers do not need to change their imports.
 */
export const usePersona = (): PersonaContextType => {
  const chat = useChat()
  const collection = useCollection()
  return { ...chat, ...collection }
}
