/**
 * Celestial Order mapping utilities.
 *
 * The Celestial Order system replaces the legacy gacha "rarity" vocabulary
 * with lore-aligned tier names: Archon, Warden, Sage, Wanderer.
 *
 * CSS classes now use order-* naming (e.g. .order-archon, .order-warden).
 */

/** Get display order name for a persona, defaulting to wanderer */
export function getDisplayOrder(persona: { celestial_order?: string }): string {
  return persona.celestial_order?.toLowerCase() || 'wanderer'
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
