/**
 * Canonical Persona type used across all frontend components.
 *
 * This is the "processed" persona -- image paths already have
 * the `images/` prefix stripped so they work with the public folder.
 *
 * Visual theming MUST use `celestial_order`, never `rarity`.
 * The `rarity` field is kept only for legacy pull-record compatibility
 * and backend MCP gating; it should NOT drive UI styling.
 */
export interface Persona {
  /** Unique persona identifier (e.g. "nephilim_eeva", "gojo") */
  key: string
  /** Human-readable name shown in the UI */
  display_name: string
  /** Short style/personality description */
  style: string
  /** Card image path (relative to /images/) */
  image: string
  /** Avatar image path (relative to /images/) */
  avatar?: string
  /** Background image path (relative to /images/) */
  bg?: string
  /**
   * Backend rarity value (legendary, epic, rare, common).
   * @deprecated Use `celestial_order` for all visual theming.
   * Kept for pull-record logging and backend MCP-gating compatibility.
   */
  rarity: string
  /** Celestial Order tier: archon | warden | sage | wanderer */
  celestial_order?: string
  /** Short label shown in coordinator / domain context */
  coordinator_label?: string
  /** MCP integrations this persona has access to */
  mcp_access?: string[]
  /** Voice configuration with greeting text */
  voice?: {
    greeting: string
  }
  /** Inter-Nephilim relationship descriptions (keyed by short name e.g. "aegis") */
  relationships?: Record<string, string>
  /** Realm domain for this Nephilim */
  realm_domain?: { name: string; description: string }
}
