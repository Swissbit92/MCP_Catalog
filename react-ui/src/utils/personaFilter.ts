// src/utils/personaFilter.ts
/**
 * Persona Filter Utilities
 *
 * Utilities for filtering personas between Nephilim and Wanderer types.
 * "Wanderers" is the frontend display label for non-Nephilim personas.
 * Wanderers are beings who drifted into the realm from beyond the known planes --
 * they are not bound to any House but walk their own path.
 *
 * Filter values ('all', 'nephilim', 'legacy') are kept for backward compatibility
 * with localStorage persistence. The 'legacy' value maps to "Wanderers" in the UI.
 */

export type PersonaFilterMode = 'all' | 'nephilim' | 'legacy';

const STORAGE_KEY = 'persona_filter_mode';

/**
 * Check if a persona key belongs to a NEPHILIM persona.
 * Wanderers (non-Nephilim) return false.
 */
export const isNephilimPersona = (personaKey: string): boolean => {
  return personaKey.startsWith('nephilim_');
};

/**
 * Get the current filter mode from localStorage.
 * Returns 'all' by default, showing both Nephilim and Wanderers.
 */
export const getFilterMode = (): PersonaFilterMode => {
  if (typeof window === 'undefined') return 'all';
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'nephilim' || stored === 'legacy' || stored === 'all') {
    return stored;
  }
  return 'all';
};

/**
 * Set the filter mode in localStorage.
 * Accepts 'all', 'nephilim', or 'legacy' (Wanderers).
 */
export const setFilterMode = (mode: PersonaFilterMode): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, mode);
};

/**
 * Filter an array of personas based on the current filter mode.
 * - 'nephilim': shows only Nephilim personas
 * - 'legacy': shows only Wanderer (non-Nephilim) personas
 * - 'all': shows both Nephilim and Wanderers
 */
export const filterPersonas = <T extends { key: string }>(
  personas: T[],
  mode: PersonaFilterMode
): T[] => {
  switch (mode) {
    case 'nephilim':
      return personas.filter(p => isNephilimPersona(p.key));
    case 'legacy':
      return personas.filter(p => !isNephilimPersona(p.key));
    case 'all':
    default:
      return personas;
  }
};

/**
 * Get counts of personas by type (Nephilim and Wanderers).
 * Note: "legacy" key is kept for API/data compatibility; displayed as "Wanderers" in the UI.
 */
export const getPersonaCounts = <T extends { key: string }>(
  personas: T[]
): { nephilim: number; legacy: number; total: number } => {
  const nephilim = personas.filter(p => isNephilimPersona(p.key)).length;
  const legacy = personas.filter(p => !isNephilimPersona(p.key)).length;
  return {
    nephilim,
    legacy,
    total: personas.length,
  };
};
