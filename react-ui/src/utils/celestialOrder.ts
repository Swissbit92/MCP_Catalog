/**
 * Celestial Order mapping utilities.
 *
 * The Celestial Order system replaces the legacy gacha "rarity" vocabulary
 * with lore-aligned tier names: Archon, Warden, Sage, Wanderer.
 *
 * Colors, CSS selectors (.rarity-*), and visual effects are UNCHANGED —
 * only user-facing labels are remapped.
 */

/** Maps celestial_order → CSS rarity class name (for styling) */
export function orderToRarityClass(order: string): string {
  const map: Record<string, string> = {
    archon: 'legendary',
    warden: 'epic',
    sage: 'rare',
    wanderer: 'common',
  }
  return map[order.toLowerCase()] || 'common'
}

/** Maps legacy rarity → celestial_order (backward compat) */
export function rarityToOrder(rarity: string): string {
  const map: Record<string, string> = {
    legendary: 'archon',
    epic: 'warden',
    rare: 'sage',
    common: 'wanderer',
  }
  return map[rarity.toLowerCase()] || 'wanderer'
}

/** Get display order name for a persona (prefers celestial_order, falls back to rarity mapping) */
export function getDisplayOrder(persona: { celestial_order?: string; rarity?: string }): string {
  if (persona.celestial_order) return persona.celestial_order
  return rarityToOrder(persona.rarity || 'common')
}

/** Capitalize first letter of order for display */
export function formatOrderLabel(order: string): string {
  const labels: Record<string, string> = {
    archon: 'Archon',
    warden: 'Warden',
    sage: 'Sage',
    wanderer: 'Wanderer',
  }
  return labels[order.toLowerCase()] || order.charAt(0).toUpperCase() + order.slice(1)
}
