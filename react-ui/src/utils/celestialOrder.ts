/**
 * Celestial Order mapping utilities.
 *
 * The Celestial Order system replaces the legacy gacha "rarity" vocabulary
 * with lore-aligned tier names: Archon, Warden, Sage, Wanderer.
 *
 * CSS classes now use order-* naming (e.g. .order-archon, .order-warden).
 */

/** Canonical hex colors for each Celestial Order tier */
export const ORDER_COLORS: Record<string, string> = {
  wanderer: '#C0C0C0',
  sage: '#00BFFF',
  warden: '#DA70D6',
  archon: '#FFD700',
}

/** Tailwind text classes for each Celestial Order tier */
export const ORDER_TEXT_CLASSES: Record<string, string> = {
  wanderer: 'text-gray-400',
  sage: 'text-cyan-400',
  warden: 'text-purple-400',
  archon: 'text-yellow-400',
}

/** Per-Nephilim-persona hex colors */
export const PERSONA_THEME_COLORS: Record<string, string> = {
  eeva: '#e0c3fc',
  aegis: '#4a90d9',
  solace: '#7eb8da',
  nyx: '#b07cc6',
  cipher: '#2ecc71',
  aurora: '#f39c12',
}

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
