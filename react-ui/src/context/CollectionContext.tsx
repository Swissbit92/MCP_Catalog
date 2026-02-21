import React, { createContext, useState, useContext, ReactNode } from 'react'

export interface PullRecord {
  personaKey: string
  rarity: string
  celestial_order?: string
  timestamp: number
  pullCount: number // 1, 5, or 10
}

export interface PullStats {
  totalPulls: number
  totalSpent: number // in gems
  archonCount: number
  wardenCount: number
  sageCount: number
  wandererCount: number
  averageRarity: number
  bestStreak: number
}

export interface CollectionContextType {
  // Collection management
  collectedPersonas: Set<string>
  addToCollection: (personaKey: string) => void
  isCollected: (personaKey: string) => boolean
  collectionStats: { total: number }
  // Pull history
  pullHistory: PullRecord[]
  addPullRecord: (record: Omit<PullRecord, 'timestamp'>) => void
  pullStats: PullStats
}

const CollectionContext = createContext<CollectionContextType | undefined>(undefined)

export const CollectionProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Collection management
  const [collectedPersonas, setCollectedPersonas] = useState<Set<string>>(() => {
    const stored = localStorage.getItem('collectedPersonas')
    return stored ? new Set(JSON.parse(stored)) : new Set()
  })

  // Pull history
  const [pullHistory, setPullHistory] = useState<PullRecord[]>(() => {
    const stored = localStorage.getItem('pullHistory')
    return stored ? JSON.parse(stored) : []
  })

  // Collection management functions
  const addToCollection = (personaKey: string) => {
    setCollectedPersonas(prev => {
      const newSet = new Set(prev)
      newSet.add(personaKey)
      localStorage.setItem('collectedPersonas', JSON.stringify(Array.from(newSet)))
      return newSet
    })
  }

  const isCollected = (personaKey: string) => {
    return collectedPersonas.has(personaKey)
  }

  // Calculate collection stats
  const collectionStats = React.useMemo(() => ({ total: collectedPersonas.size }), [collectedPersonas])

  // Pull history functions
  const addPullRecord = (record: Omit<PullRecord, 'timestamp'>) => {
    const newRecord: PullRecord = {
      ...record,
      timestamp: Date.now(),
    }
    setPullHistory(prev => {
      const newHistory = [...prev, newRecord]
      localStorage.setItem('pullHistory', JSON.stringify(newHistory))
      return newHistory
    })
  }

  // Calculate pull stats
  const pullStats = React.useMemo((): PullStats => {
    // Resolve each record's celestial order: prefer celestial_order field, else map rarity
    const getOrder = (record: PullRecord): string => {
      if (record.celestial_order) return record.celestial_order.toLowerCase()
      const rarityMap: Record<string, string> = {
        legendary: 'archon', epic: 'warden', rare: 'sage', common: 'wanderer',
      }
      return rarityMap[record.rarity?.toLowerCase()] || 'wanderer'
    }

    const stats: PullStats = {
      totalPulls: pullHistory.length,
      totalSpent: pullHistory.reduce((sum, record) => sum + (record.pullCount * 100), 0),
      archonCount: pullHistory.filter(r => getOrder(r) === 'archon').length,
      wardenCount: pullHistory.filter(r => getOrder(r) === 'warden').length,
      sageCount: pullHistory.filter(r => getOrder(r) === 'sage').length,
      wandererCount: pullHistory.filter(r => getOrder(r) === 'wanderer').length,
      averageRarity: 0,
      bestStreak: 0,
    }

    // Calculate average rarity (archon=4, warden=3, sage=2, wanderer=1)
    if (stats.totalPulls > 0) {
      const rarityScores = pullHistory.map(r => {
        switch (getOrder(r)) {
          case 'archon': return 4
          case 'warden': return 3
          case 'sage': return 2
          default: return 1
        }
      })
      stats.averageRarity = rarityScores.reduce((sum, score) => sum + score, 0) / stats.totalPulls
    }

    // Calculate best streak (consecutive sage+ pulls)
    let currentStreak = 0
    let bestStreak = 0
    for (const record of pullHistory.slice().reverse()) {
      const order = getOrder(record)
      if (order === 'sage' || order === 'warden' || order === 'archon') {
        currentStreak++
        bestStreak = Math.max(bestStreak, currentStreak)
      } else {
        currentStreak = 0
      }
    }
    stats.bestStreak = bestStreak

    return stats
  }, [pullHistory])

  return (
    <CollectionContext.Provider value={{
      collectedPersonas,
      addToCollection,
      isCollected,
      collectionStats,
      pullHistory,
      addPullRecord,
      pullStats,
    }}>
      {children}
    </CollectionContext.Provider>
  )
}

export const useCollection = () => {
  const context = useContext(CollectionContext)
  if (context === undefined) {
    throw new Error('useCollection must be used within a CollectionProvider')
  }
  return context
}
