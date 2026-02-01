// src/utils/personaFilter.ts
/**
 * Persona Filter Utilities
 *
 * Utilities for filtering personas between NEPHILIM and legacy types.
 */

export type PersonaFilterMode = 'all' | 'nephilim' | 'legacy';

const STORAGE_KEY = 'persona_filter_mode';

/**
 * Check if a persona key belongs to a NEPHILIM persona
 */
export const isNephilimPersona = (personaKey: string): boolean => {
  return personaKey.startsWith('nephilim_');
};

/**
 * Get the current filter mode from localStorage
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
 * Set the filter mode in localStorage
 */
export const setFilterMode = (mode: PersonaFilterMode): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, mode);
};

/**
 * Filter an array of personas based on the current filter mode
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
 * Get counts of personas by type
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
